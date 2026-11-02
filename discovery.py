"""Karryman 3.0: rotating discovery, auditable technical gates and optional fundamentals.
Research only. Yahoo Finance data is unofficial and may be delayed/incomplete.
"""
import io,json,math,os,time,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
import yfinance as yf

DATA=Path('data'); DATA.mkdir(exist_ok=True)
OUT=DATA/'discovery.json'; STATE=DATA/'discovery_state.json'; CACHE=DATA/'discovery_watchlist.json'; FUND=DATA/'discovery_fundamentals.json'
BATCH=max(1,min(500,int(os.getenv('DISCOVERY_BATCH','400'))))
FUND_LIMIT=max(0,min(80,int(os.getenv('FUNDAMENTAL_LOOKUPS','15'))))
URLS=[('nasdaq','https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt'),('other','https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt')]

def load(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def universe():
    names=set()
    for market,url in URLS:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=25) as r:raw=r.read().decode('utf-8-sig')
        df=pd.read_csv(io.StringIO(raw),sep='|',dtype=str)
        col='Symbol' if market=='nasdaq' else 'ACT Symbol'
        for _,r in df.iterrows():
            t=str(r.get(col,'')).strip()
            if r.get('Test Issue')=='N' and r.get('ETF')=='N' and t.isascii() and t.isalpha() and 1<=len(t)<=5:names.add(t)
    return sorted(names)

def num(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):return None

def analyze(t,df):
    if df is None:return None,'historial insuficiente'
    d=df[['Open','High','Low','Close','Volume']].dropna()
    if len(d)<210:return None,'historial insuficiente'
    c=d.Close;v=d.Volume;close=num(c.iloc[-1]);avg=num(v.iloc[-51:-1].mean())
    if close is None or avg is None or close<5 or avg<500000:return None,'precio/liquidez'
    m50=c.rolling(50).mean();m200=c.rolling(200).mean();e10=c.ewm(span=10,adjust=False).mean();e20=c.ewm(span=20,adjust=False).mean()
    ma50=num(m50.iloc[-1]);ma200=num(m200.iloc[-1]);ema20=num(e20.iloc[-1]);ema10=num(e10.iloc[-1])
    if not all(x is not None for x in (ma50,ma200,ema20,ema10)):return None,'medias no disponibles'
    if not ma50>ma200:return None,'tendencia MA50/MA200'
    high52=num(d.High.iloc[-252:].max())
    if not high52 or close<.85*high52:return None,'lejos de máximo 52S'
    if not close>ma50:return None,'precio bajo MA50'
    high30=float(d.High.iloc[-31:-1].max());low30=float(d.Low.iloc[-31:-1].min())
    tight=low30>0 and high30/low30-1<=.30
    vr=float(v.iloc[-1]/avg);prior=float(c.iloc[-2]);contract=float(v.iloc[-6:-1].mean())<avg*.85
    breakout=close>high30 and prior<=high30 and vr>=1.4 and tight
    touch=float(d.Low.iloc[-6:-1].min())<=float(e20.iloc[-2])*1.02
    pullback=touch and contract and close>ema10 and close>prior and vr>=1.1
    nearbase=tight and .95*high30<=close<=high30
    nearema=abs(close/ema20-1)<=.045 and close>=ema20*.97
    if breakout or pullback:status='CONFIRMADA';setup='ROTURA' if breakout else 'PULLBACK'
    elif nearbase or (nearema and contract):status='PREPARANDO';setup='BASE' if nearbase else 'PULLBACK EN FORMACIÓN'
    else:status='VIGILANCIA';setup='TENDENCIA'
    dist=100*(high52-close)/high52
    p3=(close/float(c.iloc[-64])-1)*100 if len(c)>64 else None
    p6=(close/float(c.iloc[-127])-1)*100 if len(c)>127 else None
    p12=(close/float(c.iloc[-253])-1)*100 if len(c)>253 else None
    stop=min(float(d.Low.iloc[-11:].min()),ema20*.985)
    if stop>=close:stop=None
    finviz_technical=close>2 and close>ema20 and close>ma50 and close>ma200 and dist<=10
    sa_technical=close>ema20 and close>ma50 and close>ma200 and all(p is not None and p>10 for p in (p3,p6,p12))
    score=round(30+max(0,20-dist)+min(vr,3)*6+(10 if tight else 0)+(10 if contract else 0)+(15 if status=='CONFIRMADA' else 5 if status=='PREPARANDO' else 0),1)
    return {'ticker':t,'category':status,'setup':setup,'score_preliminar':score,'close':round(close,2),'avg_volume':round(avg),'volume_ratio':round(vr,2),'stop_reference':round(stop,2) if stop else None,'target_2r':round(close+2*(close-stop),2) if stop else None,'ema20':round(ema20,2),'ma50':round(ma50,2),'ma200':round(ma200,2),'distance_high_pct':round(dist,1),'return_3m_pct':round(p3,1) if p3 is not None else None,'return_6m_pct':round(p6,1) if p6 is not None else None,'return_12m_pct':round(p12,1) if p12 is not None else None,'finviz_technical':finviz_technical,'sa_technical':sa_technical,'last_session':str(d.index[-1].date())},None

def get_fundamentals(t,cache):
    cached=cache.get(t)
    if cached:
        try:
            if datetime.now(timezone.utc)-datetime.fromisoformat(cached['checked_utc'])<timedelta(days=7):return cached,False
        except (KeyError,ValueError):pass
    try:
        info=yf.Ticker(t).info
        cap=num(info.get('marketCap'))
        # Yahoo fields have different periods and may be absent; do not fabricate growth.
        growth=num(info.get('revenueGrowth'))
        eps=num(info.get('trailingEps'))
        result={'checked_utc':datetime.now(timezone.utc).isoformat(),'market_cap':cap,'revenue_growth_pct':round(100*growth,2) if growth is not None else None,'eps_ttm':eps,'source':'Yahoo Finance info (indicative, not audited)'}
    except Exception as e:
        result={'checked_utc':datetime.now(timezone.utc).isoformat(),'market_cap':None,'revenue_growth_pct':None,'eps_ttm':None,'source':'unavailable','error':str(e)[:100]}
    cache[t]=result
    return result,True

def enrich(item,fund):
    cap=fund.get('market_cap');growth=fund.get('revenue_growth_pct');eps=fund.get('eps_ttm')
    cap_ok=None if cap is None else cap>=300e6
    growth_ok=None if growth is None else growth>10
    finviz_eps=None if eps is None else eps>-1  # Not the Finviz quarterly EPS growth filter.
    item.update({'market_cap':cap,'revenue_growth_pct':growth,'eps_ttm':eps,'fundamentals_checked_utc':fund.get('checked_utc'),
        'cap_pass':cap_ok,'growth_pass':growth_ok,'fundamental_status':'NO_VERIFICADO' if cap_ok is None or growth_ok is None else 'CUMPLE' if cap_ok and growth_ok else 'NO_CUMPLE',
        'finviz_proxy':item['finviz_technical'] and cap_ok is True and growth_ok is True,
        'sa_proxy':item['sa_technical'] and cap_ok is True and growth_ok is True and finviz_eps is True,
        'earnings_verified':False})
    item['a_plus_status']='PENDIENTE_VALIDACION' if item['category']=='CONFIRMADA' else 'SIN_CONFIRMACION'
    return item

def main():
    symbols=universe()
    if not symbols:raise RuntimeError('Universo vacío')
    state=load(STATE,{});offset=int(state.get('offset',0))%len(symbols)
    # Rotate across the full alphabet via modular stride, instead of adjacent alphabetic names.
    stride=next((n for n in range(997,100,-1) if math.gcd(n,len(symbols))==1),1)
    positions=[(offset+i*stride)%len(symbols) for i in range(min(BATCH,len(symbols)))]
    selected=[symbols[i] for i in positions]
    cache=load(CACHE,{}).get('by_ticker',{});fundcache=load(FUND,{})
    found=[];errors=[];processed=0;counts={}
    for k in range(0,len(selected),20):
        batch=selected[k:k+20]
        try:
            prices=yf.download(batch,period='18mo',interval='1d',auto_adjust=True,progress=False,threads=True,group_by='ticker',timeout=30)
            for t in batch:
                try:
                    frame=prices[t] if isinstance(prices.columns,pd.MultiIndex) else prices
                    item,reason=analyze(t,frame)
                    counts[reason or 'pasa filtro técnico']=counts.get(reason or 'pasa filtro técnico',0)+1
                    if item:found.append(item)
                    processed+=1
                except Exception as e:errors.append(t+': '+str(e)[:100])
        except Exception as e:errors.extend(t+': '+str(e)[:100] for t in batch)
        time.sleep(1)
    if processed<max(1,len(selected)//2):raise RuntimeError(f'Datos insuficientes: {processed}/{len(selected)}; se conservan los resultados anteriores')
    # Candidates that have been rescanned but no longer qualify are removed.
    for t in selected:cache.pop(t,None)
    lookups=0
    for item in sorted(found,key=lambda x:-x['score_preliminar']):
        t=item['ticker'];old=fundcache.get(t)
        fresh=False
        if old:
            try:fresh=datetime.now(timezone.utc)-datetime.fromisoformat(old['checked_utc'])<timedelta(days=7)
            except (ValueError,KeyError):pass
        if fresh:fund=old
        elif lookups<FUND_LIMIT:
            fund,did=get_fundamentals(t,fundcache);lookups+=int(did)
        else:fund={'market_cap':None,'revenue_growth_pct':None,'eps_ttm':None,'source':'pending rate limit'}
        enrich(item,fund)
        if item['fundamental_status']!='NO_CUMPLE':cache[t]=item
    # Remove stale cached entries older than 21 days; a past signal must not look current.
    cutoff=(datetime.now(timezone.utc)-timedelta(days=10)).date().isoformat()
    cache={t:x for t,x in cache.items() if x.get('last_session','')>=cutoff and x.get('fundamental_status')!='NO_CUMPLE'}
    rank={'CONFIRMADA':0,'PREPARANDO':1,'VIGILANCIA':2}
    candidates=sorted(cache.values(),key=lambda x:(rank.get(x['category'],3),-x['score_preliminar']))[:500]
    payload={'schema_version':3,'generated_utc':datetime.now(timezone.utc).isoformat(),'source':'Nasdaq Trader + Yahoo Finance (yfinance)','universe_size':len(symbols),'scanned_this_run':len(selected),'processed':processed,'errors_count':len(errors),'errors_sample':errors[:12],'filter_counts':counts,'fundamental_lookups':lookups,'watchlist_count':len(candidates),'scan_policy':'Rotación de hasta 400 símbolos por ejecución, dos veces al día de lunes a viernes; universo de cotizadas completo, lista de candidatas reducida por filtros','selection_method':'Equilibrado: precio >=5, volumen medio >=500k, MA50>MA200, precio>MA50, distancia máximo 52S <=15%; capitalización >=300M y crecimiento ingresos >10% comprobados cuando disponibles','limitations':'Exploración rotativa, NO barrido completo. Perfiles Finviz/SA son aproximaciones técnicas, no réplicas exactas. EPS trimestral y crecimiento anual no comprobados. Sin validación de earnings, fortaleza relativa ni backtest.','candidates':candidates}
    # Write results before advancing state; state only advances after a successful scan.
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    CACHE.write_text(json.dumps({'by_ticker':{x['ticker']:x for x in candidates}},ensure_ascii=False,indent=2),encoding='utf-8')
    FUND.write_text(json.dumps(fundcache,ensure_ascii=False,indent=2),encoding='utf-8')
    STATE.write_text(json.dumps({'offset':(offset+len(selected)*stride)%len(symbols),'stride':stride,'universe_size':len(symbols),'updated_utc':payload['generated_utc']},indent=2),encoding='utf-8')
    print(f'Universo={len(symbols)} procesadas={processed} candidatas={len(candidates)} errores={len(errors)} fundamentales_consultados={lookups}')
    print('Descartes:',counts)

if __name__=='__main__':main()
