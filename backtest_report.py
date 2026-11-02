"""Reproducible offline research report using historical daily OHLCV.

No orders or account access. Reports are deliberately NOT generated from the
current watchlist, which would introduce selection/survivorship bias.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import yfinance as yf
from backtest import run,Config

DEFAULT=['SPY','QQQ','AAPL','MSFT','NVDA','AMZN','GOOGL','META']
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--symbols',nargs='+',default=DEFAULT)
    p.add_argument('--period',default='5y')
    p.add_argument('--output',default='data/backtest_report.json')
    args=p.parse_args()
    results=[];failures=[]
    for symbol in dict.fromkeys(args.symbols):
        try:
            frame=yf.download(symbol,period=args.period,interval='1d',auto_adjust=True,progress=False,threads=False,timeout=30)
            if frame.empty:raise ValueError('Sin precios')
            if isinstance(frame.columns,pd.MultiIndex):
                frame.columns=frame.columns.get_level_values(0)
            rows=[{'open':float(x.Open),'high':float(x.High),'low':float(x.Low),
                   'close':float(x.Close),'volume':float(x.Volume)}
                  for x in frame.itertuples()]
            if len(rows)<252:raise ValueError('Menos de 252 sesiones')
            result=run(rows,Config())
            trades=result.pop('trades')
            result.update({'ticker':symbol,'sessions':len(rows),
                'first_session':str(frame.index[0].date()),'last_session':str(frame.index[-1].date()),
                'sample_trades':trades[-5:]})
            results.append(result)
        except Exception as e:
            failures.append({'ticker':symbol,'error':str(e)[:180]})
    if len(results)<max(1,len(set(args.symbols))//2):
        raise RuntimeError(f'Datos insuficientes: {len(results)} símbolos válidos, {len(failures)} fallos')
    payload={'schema_version':1,'generated_utc':datetime.now(timezone.utc).isoformat(),
       'source':'Yahoo Finance/yfinance historical adjusted daily prices',
       'method':'Mechanical 30-session breakout, next-session open, single-symbol independent runs, 1% max initial equity risk, 0.1% entry/exit slippage and $1 each-side commissions',
       'limitations':'Exploratory baseline only; NOT Karryman A+, not portfolio backtest, not out-of-sample, no delisted securities, no tax/FX/earnings filter, no statistical edge established.',
       'symbols_requested':list(dict.fromkeys(args.symbols)),
       'symbols_completed':len(results),'failures':failures,'results':results}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Backtest completado: {len(results)} símbolos; fallos {len(failures)}')
if __name__=='__main__':main()
