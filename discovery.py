"""Rotating US equity discovery; preliminary technical candidates, not orders."""
import io, json, math, os, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

OUT=Path('data/discovery.json')
STATE=Path('data/discovery_state.json')
MAX_PER_RUN=int(os.getenv('DISCOVERY_BATCH','120'))
URLS=[('nasdaq','https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt'),('other','https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt')]

def universe():
    names=set()
    for market,url in URLS:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 Karryman research'})
        with urllib.request.urlopen(req,timeout=25) as r: raw=r.read().decode('utf-8-sig')
        df=pd.read_csv(io.StringIO(raw),sep='|',dtype=str)
        sym='Symbol' if market=='nasdaq' else 'ACT Symbol'
        etf='ETF'
        for _,row in df.iterrows():
            t=str(row.get(sym,'')).strip()
            if (row.get('Test Issue')=='N' and row.get(etf)=='N' and t.isascii() and t.isalpha() and 1<=len(t)<=5): names.add(t)
    return sorted(names)

def analyze(t,df):
    if df is None or len(df)<210:return None
    df=df[['Open','High','Low','Close','Volume']].dropna()
    if len(df)<210:return None
    c=df.Close; v=df.Volume; close=float(c.iloc[-1]); avg=float(v.iloc[-51:-1].mean()); vol=float(v.iloc[-1]);
    if close<10 or avg<500000 or not math.isfinite(close):return None
    e10=c.ewm(span=10,adjust=False).mean();e20=c.ewm(span=20,adjust=False).mean();m50=c.rolling(50).mean();m200=c.rolling(200).mean()
    trend=close>float(e20.iloc[-1])>float(m50.iloc[-1])>float(m200.iloc[-1]) and float(m50.iloc[-1])>float(m50.iloc[-21])
    high52=float(df.High.iloc[-252:].max())
    if not trend or close<.85*high52:return None
    base_hi=float(df.High.iloc[-31:-1].max());base_lo=float(df.Low.iloc[-31:-1].min())
    six_hi=float(df.High.iloc[-31:-1].max());six_lo=float(df.Low.iloc[-31:-1].min())
    tight= six_lo>0 and six_hi/six_lo-1<=.30
    ratio=vol/avg if avg else 0
    breakout=close>base_hi and float(c.iloc[-2])<=base_hi and ratio>=1.4 and tight
    touch=float(df.Low.iloc[-6:-1].min())<=float(e20.iloc[-2])*1.02
    contraction=float(v.iloc[-6:-1].mean())<avg*.85
    pullback=touch and contraction and close>float(e10.iloc[-1]) and close>float(c.iloc[-2]) and ratio>=1.1
    if not (breakout or pullback):return None
    stop=min(float(df.Low.iloc[-11:].min()),float(e20.iloc[-1])*.985)
    if stop>=close:return None
    setup='ROTURA' if breakout else 'PULLBACK'
    score=round((25 if breakout else 20)+min(ratio,3)*10+(10 if contraction else 0)+max(0,15-100*(high52-close)/high52),1)
    return {'ticker':t,'status':'candidata_tecnica','setup':setup,'score_preliminar':score,'close':round(close,2),'stop_reference':round(stop,2),'target_2r':round(close+2*(close-stop),2),'volume_ratio':round(ratio,2),'ema20':round(float(e20.iloc[-1]),2),'ma50':round(float(m50.iloc[-1]),2),'ma200':round(float(m200.iloc[-1]),2),'base_high':round(base_hi,2),'last_session':str(df.index[-1].date()),'fundamentals_verified':False,'earnings_verified':False,'note':'Candidata técnica. No se han verificado capitalización, ingresos, EPS ni próximos resultados.'}

def main():
    try: symbols=universe()
    except Exception as e:
        print('No se pudo descargar el universo:',repr(e));raise
    old=json.loads(STATE.read_text()) if STATE.exists() else {}
    offset=int(old.get('offset',0))%len(symbols)
    selected=[symbols[(offset+i)%len(symbols)] for i in range(min(MAX_PER_RUN,len(symbols)))]
    candidates=[];errors=[];completed=0
    for k in range(0,len(selected),20):
        batch=selected[k:k+20]
        try:
            prices=yf.download(batch,period='15mo',interval='1d',auto_adjust=True,progress=False,threads=True,group_by='ticker',timeout=25)
            for t in batch:
                try:
                    d=prices[t] if isinstance(prices.columns,pd.MultiIndex) else prices
                    found=analyze(t,d)
                    if found:candidates.append(found)
                    completed+=1
                except Exception as e:errors.append(t+': '+str(e)[:70])
        except Exception as e:errors.extend(t+': '+str(e)[:70] for t in batch)
        time.sleep(2)
    # Avoid presenting an incomplete scan as a successful scan.
    if completed < max(1,len(selected)//2):
        raise RuntimeError(f'Fuentes de precios insuficientes: {completed}/{len(selected)}. No se sobrescriben resultados.')
    candidates.sort(key=lambda x:x['score_preliminar'],reverse=True)
    payload={'generated_utc':datetime.now(timezone.utc).isoformat(),'source':'Nasdaq Trader symbol directories + Yahoo Finance via yfinance','universe_size':len(symbols),'scanned_this_run':len(selected),'processed':completed,'errors_count':len(errors),'offset_start':offset,'coverage':'ROTATIVA: no se analiza todo el mercado en una ejecución','risk_notice':'Señales preliminares, no órdenes. Verificar sesión, gráficos, fundamentales, resultados y liquidez antes de operar.','candidates':candidates,'errors_sample':errors[:10]}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    STATE.write_text(json.dumps({'offset':(offset+len(selected))%len(symbols),'universe_size':len(symbols),'updated_utc':payload['generated_utc']},indent=2),encoding='utf-8')
    print(f'Universo {len(symbols)}, analizadas {completed}, candidatas {len(candidates)}, errores {len(errors)}')

if __name__=='__main__':main()
