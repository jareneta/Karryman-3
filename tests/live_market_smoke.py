"""Live Yahoo Finance smoke test, without modifying data/ or placing orders."""
import sys
import yfinance as yf
import pandas as pd
from setups import calculate

def main():
    tickers=["AAPL","MSFT","NVDA"]
    spy_df=yf.download("SPY",period="18mo",interval="1d",auto_adjust=True,progress=False,threads=False,timeout=30)
    if spy_df.empty:
        raise RuntimeError("SPY: no data")
    spy=spy_df["Close"]
    if isinstance(spy,pd.DataFrame):spy=spy.iloc[:,0]
    valid=0
    for ticker in tickers:
        raw=yf.download(ticker,period="18mo",interval="1d",auto_adjust=True,progress=False,threads=False,timeout=30)
        if raw.empty:raise RuntimeError(ticker+": no data")
        if isinstance(raw.columns,pd.MultiIndex):
            raw.columns=raw.columns.get_level_values(0)
        result=calculate(ticker,raw,spy)
        if result is None:raise RuntimeError(ticker+": insufficient history")
        assert result["ticker"]==ticker
        assert result["close"]>0
        print(ticker,"session",result["last_session"],"close",result["close"],"A+ technical",result["technical_a_plus"])
        valid+=1
    if valid!=3:sys.exit(1)
    print("Live data smoke test passed (3/3), no orders")

if __name__=="__main__":main()
