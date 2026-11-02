"""Research-only comparison of A+ intraday and close-confirmed stop policies.

Each symbol is simulated independently, not as a portfolio. No account access,
no orders, and no claim of statistical edge.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from aplus_backtest import run_aplus

def summarize(outcomes):
    summary={}
    for mode in ("intraday","close_next_open"):
        valid=[item[mode] for item in outcomes if mode in item]
        trades=[t for result in valid for t in result["trades"]]
        pnl=[float(t["pnl"]) for t in trades]
        gains=sum(max(0,p) for p in pnl)
        losses=sum(max(0,-p) for p in pnl)
        summary[mode]={
            "symbols":len(valid),
            "total_trades":len(trades),
            "winning_trades":sum(p>0 for p in pnl),
            "win_rate_pct":round(100*sum(p>0 for p in pnl)/len(pnl),2) if pnl else None,
            "mean_pnl_usd_per_trade":round(sum(pnl)/len(pnl),2) if pnl else None,
            "profit_factor":round(gains/losses,3) if losses else None,
            "sum_independent_symbol_pnl_usd":round(sum(pnl),2),
            "warning":"Not a combined portfolio P/L. Symbols reset capital and may overlap."
        }
    return summary

def compare_frames(frames,spy):
    results=[]
    for ticker,frame in frames.items():
        row={"ticker":ticker,"sessions":len(frame)}
        for mode in ("intraday","close_next_open"):
            outcome=run_aplus(frame,spy,stop_mode=mode)
            row[mode]={k:v for k,v in outcome.items() if k!="trades"}
            row[mode]["trades"]=outcome["trades"]
        results.append(row)
    return {"schema_version":1,"generated_utc":datetime.now(timezone.utc).isoformat(),
        "method":"A+ technical research, next-open entries, independent single-symbol runs, 1% maximum initial stop risk, 0.1% slippage, $1 per side",
        "limitations":"No fundamentals/earnings, delisted securities, portfolio simulation, untouched out-of-sample validation, mark-to-market drawdown, or proven edge. Intraday mode includes +2R target; close mode has no intraday target, so this is NOT an isolated comparison of stop policy.",
        "summary":summarize(results),"results":results}

def main():
    import pandas as pd
    import yfinance as yf
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["SPY","QQQ","AAPL","MSFT"])
    p.add_argument("--period",default="5y")
    p.add_argument("--output",default="data/aplus_stop_comparison.json")
    args=p.parse_args()
    spy=yf.download("SPY",period=args.period,auto_adjust=True,progress=False,threads=False,timeout=30)
    if isinstance(spy.columns,pd.MultiIndex):spy.columns=spy.columns.get_level_values(0)
    if spy.empty:raise RuntimeError("SPY reference unavailable")
    frames={}
    failures=[]
    for ticker in dict.fromkeys(args.symbols):
        try:
            frame=yf.download(ticker,period=args.period,auto_adjust=True,progress=False,threads=False,timeout=30)
            if isinstance(frame.columns,pd.MultiIndex):frame.columns=frame.columns.get_level_values(0)
            if len(frame)<254:raise ValueError("Insufficient historical sessions")
            frames[ticker]=frame
        except Exception as e:failures.append({"ticker":ticker,"error":str(e)[:150]})
    if not frames:raise RuntimeError("No valid historical symbols")
    report=compare_frames(frames,spy["Close"])
    report["failures"]=failures
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print("A+ stop research:",len(frames),"symbols;",len(failures),"failures")
if __name__=="__main__":main()
