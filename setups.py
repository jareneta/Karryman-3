"""Karryman A+ research screener: objective daily OHLCV rules, NOT investment advice."""
import json, math, os, time
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

DATA=Path('data'); DATA.mkdir(exist_ok=True)
SOURCE=DATA/'discovery.json'; OUT=DATA/'setups.json'
LIMIT=max(1,min(500,int(os.getenv('SETUP_MAX_SYMBOLS','250'))))

def n(x):
    try:
        v=float(x)
        return round(v,3) if math.isfinite(v) else None
    except (ValueError,TypeError):return None

def calculate(t, raw, spy):
    d=raw[['Open','High','Low','Close','Volume']].dropna()
    if len(d)<210:return None
    c=d.Close; h=d.High; lo=d.Low; v=d.Volume
    close=float(c.iloc[-1]); vol=float(v.iloc[-1]); avg=float(v.iloc[-51:-1].mean())
    if avg<=0:return None
    ma50=float(c.iloc[-50:].mean()); ma200=float(c.iloc[-200:].mean()); ma200old=float(c.iloc[-220:-20].mean()) if len(c)>=220 else None
    ema10=float(c.ewm(span=10,adjust=False).mean().iloc[-1]); ema20=float(c.ewm(span=20,adjust=False).mean().iloc[-1]);
    high52=float(h.iloc[-252:].max()); low52=float(lo.iloc[-252:].min())
    volratio=vol/avg
    # Base window excludes current bar. At least 6 weeks (30 trading sessions).
    base_high=float(h.iloc[-31:-1].max()); base_low=float(lo.iloc[-31:-1].min())
    base_depth=(base_high/base_low-1)*100 if base_low>0 else 999
    # Compare recent 10-day daily ranges to the preceding 20-day daily ranges.
    r=(h-lo)/c.replace(0,float('nan'))
    recent_range=float(r.iloc[-11:-1].mean()); prior_range=float(r.iloc[-31:-11].mean())
    range_contraction=prior_range>0 and recent_range<=prior_range*.8
    # Volume dry-up: last 5 completed sessions vs preceding 20.
    prior_vol=float(v.iloc[-26:-6].mean()); recent_vol=float(v.iloc[-6:-1].mean())
    dryup=prior_vol>0 and recent_vol<=prior_vol*.8
    trend=close>ma50>ma200 and (ma200old is None or ma200>ma200old)
    near_high=close>=.85*high52
    # RS proxy: stock's 63-session return minus SPY return over matching dates.
    rs=None
    try:
        aligned=pd.concat([c.rename('stock'),spy.rename('spy')],axis=1).dropna()
        if len(aligned)>=64:
            stock_ret=float(aligned.stock.iloc[-1]/aligned.stock.iloc[-64]-1)
            spy_ret=float(aligned.spy.iloc[-1]/aligned.spy.iloc[-64]-1)
            rs=(stock_ret-spy_ret)*100
    except Exception:pass
    base_ok=base_depth<=25 and base_low>0
    breakout=(close>base_high and float(c.iloc[-2])<=base_high and volratio>=1.4 and base_ok)
    # Pullback: prior bar(s) near EMA20, reclaim EMA10 on last completed session.
    ema20series=c.ewm(span=20,adjust=False).mean()
    touch=bool((lo.iloc[-6:-1]<=ema20series.iloc[-6:-1]*1.02).any())
    pullback=(touch and close>ema10 and close>float(c.iloc[-2]) and volratio>=1.1 and dryup)
    if breakout:setup='ROTURA_BASE'; status='CONFIRMADA'
    elif pullback:setup='PULLBACK_EMA20';status='CONFIRMADA'
    elif base_ok and close>=base_high*.95:setup='BASE_6_SEMANAS';status='PREPARANDO'
    elif touch and close>=ema20*.97:setup='PULLBACK_FORMACION';status='PREPARANDO'
    else:setup='TENDENCIA';status='VIGILANCIA'
    # A+ requires trend, proximity, RS superiority, tightening base, dryup and close confirmation.
    # Pullback uses dryup, but does not require 30-day base or range contraction.
    technical_a_plus=(trend and near_high and rs is not None and rs>0 and
                      ((breakout and range_contraction and dryup) or pullback))
    # Stop below recent swing for pullbacks, below 10-day low for breakouts.
    stop=float(lo.iloc[-11:-1].min())
    if stop>=close:stop=None
    risk=(close-stop)/close*100 if stop is not None else None
    if risk is None or risk<=0 or risk>12:technical_a_plus=False
    return {'ticker':t,'last_session':str(d.index[-1].date()),'close':n(close),'setup':setup,'status':status,
        'technical_a_plus':bool(technical_a_plus),'trend_ok':bool(trend),'near_high_ok':bool(near_high),
        'base_6_weeks':bool(base_ok),'base_depth_pct':n(base_depth),'range_contraction':bool(range_contraction),
        'volume_dryup':bool(dryup),'volume_ratio':n(volratio),'rs_vs_spy_3m_pct':n(rs),
        'ma50':n(ma50),'ma200':n(ma200),'ema10':n(ema10),'ema20':n(ema20),
        'stop_reference':n(stop),'risk_pct':n(risk),
        'target_2r':n(close+2*(close-stop)) if stop is not None else None}

def main():
    if not SOURCE.exists():raise RuntimeError('Falta data/discovery.json; ejecutar primero Discovery')
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    entries=source.get('candidates',[])
    entries=[x for x in entries if x.get('ticker') and x.get('fundamental_status')!='NO_CUMPLE'][:LIMIT]
    tickers=list(dict.fromkeys(x['ticker'] for x in entries))
    spy_df=yf.download('SPY',period='18mo',auto_adjust=True,progress=False,threads=False)
    if spy_df.empty:raise RuntimeError('No se pudo descargar SPY para fuerza relativa')
    spy=spy_df['Close'];spy=spy.iloc[:,0] if isinstance(spy,pd.DataFrame) else spy
    results=[]; errors=[]; processed=0
    lookup={x['ticker']:x for x in entries}
    for k in range(0,len(tickers),20):
        batch=tickers[k:k+20]
        try:
            prices=yf.download(batch,period='18mo',interval='1d',auto_adjust=True,progress=False,threads=True,group_by='ticker',timeout=30)
            for t in batch:
                try:
                    frame=prices[t] if isinstance(prices.columns,pd.MultiIndex) else prices
                    x=calculate(t,frame,spy)
                    if x:
                        previous=lookup[t]
                        x['fundamental_status']=previous.get('fundamental_status','NO_VERIFICADO')
                        x['revenue_growth_pct']=previous.get('revenue_growth_pct')
                        x['market_cap']=previous.get('market_cap')
                        x['fundamentals_checked_utc']=previous.get('fundamentals_checked_utc')
                        # A+ operational readiness is separate from purely technical A+.
                        x['operable_a_plus']=bool(x['technical_a_plus'] and x['fundamental_status']=='CUMPLE' and False)
                        x['pending_checks']=['Resultados próximos','Verificación de datos fundamentales y cierre','Riesgo y cartera']
                        results.append(x)
                    processed+=1
                except Exception as exc:errors.append(f'{t}: {str(exc)[:100]}')
        except Exception as exc:errors.extend(f'{t}: {str(exc)[:100]}' for t in batch)
        time.sleep(1)
    if tickers and processed<len(tickers)//2:raise RuntimeError('Descargas insuficientes; no sobrescribir datos anteriores')
    rank={'CONFIRMADA':0,'PREPARANDO':1,'VIGILANCIA':2}
    results.sort(key=lambda x:(not x['technical_a_plus'],rank.get(x['status'],3),-(x['rs_vs_spy_3m_pct'] or -999)))
    payload={'schema_version':1,'generated_utc':datetime.now(timezone.utc).isoformat(),
      'source':'Yahoo Finance OHLCV vía yfinance; SPY para fuerza relativa',
      'source_discovery_generated_utc':source.get('generated_utc'),
      'symbols_requested':len(tickers),'symbols_processed':processed,'results_count':len(results),
      'technical_a_plus_count':sum(x['technical_a_plus'] for x in results),'errors':errors[:20],
      'notes':'Base >=30 sesiones; profundidad <=25%; contracción rango 20 vs 10 sesiones; volumen seco 5 vs 20; RS 63 sesiones vs SPY. A+ técnico es heurístico, no validado estadísticamente. Sin earnings ni autorización de órdenes. Los datos fundamentales pueden estar desactualizados.',
      'candidates':results}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Analizadas',processed,'A+ técnicos',payload['technical_a_plus_count'],'errores',len(errors))

if __name__=='__main__':main()
