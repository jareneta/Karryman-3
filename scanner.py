import json, math, os, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

TICKERS = 'NRIX WAT TGTX HNGE ARQT CDNA HALO XERS AXGN CAI FLYW AVPT GCT FIGS LFST AMPL SN APPN SIBN FRSH CART LIND ATRC VRTX MAX HURN SPT'.split()
OUT = Path('data/signals.json')

def analyze(ticker):
    try:
        df = yf.download(ticker, period='2y', interval='1d', auto_adjust=True, progress=False, threads=False)
        if df.empty or len(df) < 210: return {'ticker':ticker,'status':'sin_datos'}
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df[['Open','High','Low','Close','Volume']].dropna()
        c, v = df.Close, df.Volume
        ema20 = c.ewm(span=20, adjust=False).mean()
        ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
        last = float(c.iloc[-1]); prev = float(c.iloc[-2]); vol = float(v.iloc[-1]); avgvol = float(v.iloc[-51:-1].mean())
        hi52 = float(df.High.iloc[-252:].max())
        base_hi = float(df.High.iloc[-31:-1].max())
        base_low = float(df.Low.iloc[-31:-1].min())
        tight = (base_hi/base_low - 1) <= .30 if base_low > 0 else False
        trend = last > float(ema20.iloc[-1]) > float(ma50.iloc[-1]) > float(ma200.iloc[-1]) and float(ma50.iloc[-1]) > float(ma50.iloc[-11])
        near_high = last >= .85 * hi52
        liquid = last >= 10 and avgvol >= 500000
        breakout = last > base_hi and prev <= float(df.High.iloc[-32:-2].max()) and vol >= 1.4*avgvol and tight
        pullback = trend and (float(df.Low.iloc[-6:-1].min()) <= float(ema20.iloc[-2])*1.02) and last > float(ema20.iloc[-1]) and last > prev and vol >= .8*avgvol
        setup = 'ROTURA' if breakout else ('PULLBACK' if pullback else 'VIGILAR')
        valid = trend and near_high and liquid and (breakout or pullback)
        stop = min(float(df.Low.iloc[-11:].min()), float(ema20.iloc[-1])*.985)
        risk = last - stop
        if risk <= 0: valid = False
        return {'ticker':ticker,'status':'senal' if valid else 'seguimiento','setup':setup,'close':round(last,2),'volume_ratio':round(vol/avgvol,2) if avgvol else None,'ema20':round(float(ema20.iloc[-1]),2),'ma50':round(float(ma50.iloc[-1]),2),'ma200':round(float(ma200.iloc[-1]),2),'base_high':round(base_hi,2),'stop_reference':round(stop,2) if risk>0 else None,'target_2r':round(last+2*risk,2) if risk>0 else None,'trend':bool(trend),'near_52w_high':bool(near_high),'liquid':bool(liquid),'last_session':str(df.index[-1].date()),'notes':'Filtro fundamental (capitalización y crecimiento de ingresos) pendiente de validación manual. Stop de referencia, no orden.'}
    except Exception as e:
        return {'ticker':ticker,'status':'error','detail':str(e)[:160]}

def main():
    results=[]
    for t in TICKERS:
        results.append(analyze(t)); print(t,results[-1]['status'],flush=True); time.sleep(.7)
    payload={'generated_utc':datetime.now(timezone.utc).isoformat(),'source':'Yahoo Finance via yfinance (gratuito, no garantizado)','method':'cierres diarios; filtros técnicos preliminares','risk_notice':'No son recomendaciones personalizadas ni órdenes. Confirmar precios, noticias, resultados y fundamentales antes de operar.','symbols':results}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
