"""Conservative research backtest for daily OHLCV; never executes orders.

Signals use only information available at the signal close. Entry is the NEXT
session's open, never the same closing price. Stops use intraday lows, with gap
risk modelled at the opening price. Costs and slippage are configurable.
This is a mechanical baseline, NOT a validated A+ strategy.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Config:
    initial_equity: float = 10000.0
    risk_fraction: float = .01
    commission_per_order: float = 1.0
    slippage_fraction: float = .001
    max_holding_sessions: int = 20

def run(rows, cfg=Config()):
    """Rows: chronological dicts with open/high/low/close/volume.
    Prior close > 50d MA > 200d MA, break above previous 30d high,
    volume >=1.4x prior 50d volume. Stop = prior 10d low.
    At most one position; long-only; no borrowing.
    """
    if cfg.initial_equity<=0 or not 0<cfg.risk_fraction<=.01 or cfg.max_holding_sessions<1:
        raise ValueError('Invalid backtest config')
    equity=cfg.initial_equity
    trades=[]
    position=None
    for i,row in enumerate(rows):
        o,h,l,c,v=[float(row[k]) for k in ('open','high','low','close','volume')]
        if not all(isfinite(z) and z>0 for z in (o,h,l,c,v)) or l>min(o,c) or h<max(o,c):
            raise ValueError(f'Invalid OHLCV at row {i}')
        if position is not None:
            position['bars']+=1
            exit_price=None
            reason=None
            if o<=position['stop']:
                exit_price=o*(1-cfg.slippage_fraction)
                reason='gap_stop'
            elif l<=position['stop']:
                exit_price=position['stop']*(1-cfg.slippage_fraction)
                reason='stop'
            elif h>=position['target']:
                exit_price=position['target']*(1-cfg.slippage_fraction)
                reason='target_2r'
            elif position['bars']>=cfg.max_holding_sessions:
                exit_price=c*(1-cfg.slippage_fraction)
                reason='time'
            if exit_price is not None:
                pnl=position['shares']*(exit_price-position['entry'])-2*cfg.commission_per_order
                equity+=pnl
                trades.append({**position,'exit_index':i,'exit':round(exit_price,4),
                    'pnl':round(pnl,2),'exit_reason':reason,'equity_after':round(equity,2)})
                position=None
        # Signal from previous close, executed at today's open.
        if position is None and i>=201:
            prev=rows[i-1]
            closes=[float(x['close']) for x in rows[i-201:i]]
            highs=[float(x['high']) for x in rows[i-31:i-1]]
            lows=[float(x['low']) for x in rows[i-11:i-1]]
            vols=[float(x['volume']) for x in rows[i-51:i-1]]
            prev_close=float(prev['close'])
            ma50=sum(closes[-50:])/50
            ma200=sum(closes[-200:])/200
            base_high=max(highs)
            avg_vol=sum(vols)/50
            signal=prev_close>ma50>ma200 and prev_close>base_high and float(prev['volume'])>=1.4*avg_vol
            if signal:
                stop=min(lows)
                entry=o*(1+cfg.slippage_fraction)
                if 0<stop<entry and (entry-stop)/entry<=.12:
                    risk_budget=max(0,equity)*cfg.risk_fraction
                    shares=min(int(risk_budget/(entry-stop)),int(max(0,equity-cfg.commission_per_order)/entry))
                    if shares>0:
                        position={'signal_index':i-1,'entry_index':i,'entry':round(entry,4),
                            'stop':round(stop,4),'target':round(entry+2*(entry-stop),4),
                            'shares':shares,'bars':0}
    if position is not None:
        last=float(rows[-1]['close'])*(1-cfg.slippage_fraction)
        pnl=position['shares']*(last-position['entry'])-2*cfg.commission_per_order
        equity+=pnl
        trades.append({**position,'exit_index':len(rows)-1,'exit':round(last,4),
            'pnl':round(pnl,2),'exit_reason':'end_of_data','equity_after':round(equity,2)})
    wins=sum(t['pnl']>0 for t in trades)
    gains=sum(max(0,t['pnl']) for t in trades)
    losses=sum(max(0,-t['pnl']) for t in trades)
    return {'strategy':'baseline_30d_breakout_next_open','trades':trades,
        'trade_count':len(trades),'win_rate_pct':round(100*wins/len(trades),2) if trades else None,
        'profit_factor':round(gains/losses,3) if losses else None,
        'initial_equity':cfg.initial_equity,'final_equity':round(equity,2),
        'return_pct':round(100*(equity/cfg.initial_equity-1),2),
        'limitations':'Single-symbol sequential baseline; no survivorship, corporate-action or out-of-sample controls. Not proof of edge.'}
