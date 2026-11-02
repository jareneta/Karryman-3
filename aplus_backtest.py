"""Research-only A+ historical simulator, using the production setup classifier.

No orders. Daily signal at completed close, fill at next open. One long
position per symbol; no leverage. Stops use intraday prices for this simulation
and are NOT the production close-based stop policy.
"""
from dataclasses import dataclass
from math import isfinite
from backtest import Config
from setups import calculate

def run_aplus(frame,spy,cfg=Config(),warmup=252,stop_mode='intraday'):
    if stop_mode not in ('intraday','close_next_open'):\n        raise ValueError('Invalid stop mode')\n    if cfg.initial_equity<=0 or not 0<cfg.risk_fraction<=.01:
        raise ValueError('Invalid risk config')
    if cfg.slippage_fraction<0 or cfg.slippage_fraction>=1 or cfg.commission_per_order<0:
        raise ValueError('Invalid cost config')
    if len(frame)<warmup+2:return {'trade_count':0,'trades':[],'initial_equity':cfg.initial_equity,'final_equity':cfg.initial_equity,'return_pct':0.0}
    equity=cfg.initial_equity
    position=None
    trades=[]
    pending=None\n    pending_exit=None\n    for i in range(warmup,len(frame)):
        bar=frame.iloc[i]
        o,h,l,c=[float(bar[k]) for k in ('Open','High','Low','Close')]
        if not all(isfinite(z) and z>0 for z in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError('Invalid daily OHLC')
        exited=False\n        if position is not None and pending_exit is not None:\n            exit_price=o*(1-cfg.slippage_fraction)\n            pnl=position['shares']*(exit_price-position['entry'])-2*cfg.commission_per_order\n            equity+=pnl\n            trades.append({**position,'exit_index':i,'exit':round(exit_price,4),\n                           'exit_reason':'close_stop_next_open','pnl':round(pnl,2)})\n            position=None\n            pending_exit=None\n            exited=True\n        if position is None and pending is not None:
            entry=o*(1+cfg.slippage_fraction)
            stop=pending['stop']
            if stop>0 and entry>stop and (entry-stop)/entry<=.12:
                shares=min(int(equity*cfg.risk_fraction/(entry-stop)),
                           int(max(0,equity-cfg.commission_per_order)/entry))
                if shares>0:
                    position={'entry_index':i,'signal_index':i-1,'entry':entry,'stop':stop,
                              'target':entry+2*(entry-stop),'shares':shares,
                              'setup':pending['setup'],'bars':0}
            pending=None
        if position is not None:\n            position['bars']+=1
            reason=None;exit_price=None
            if stop_mode=='intraday' and o<=position['stop']:\n                reason='gap_stop';exit_price=o*(1-cfg.slippage_fraction)\n            elif stop_mode=='intraday' and l<=position['stop']:\n                reason='stop';exit_price=position['stop']*(1-cfg.slippage_fraction)\n            elif stop_mode=='intraday' and h>=position['target']:
                reason='target_2r';exit_price=position['target']*(1-cfg.slippage_fraction)
            elif stop_mode=='close_next_open' and c<=position['stop'] and i<len(frame)-1:\n                pending_exit='close_stop'\n            elif position['bars']>=cfg.max_holding_sessions:
                reason='time';exit_price=c*(1-cfg.slippage_fraction)
            if reason:
                pnl=position['shares']*(exit_price-position['entry'])-2*cfg.commission_per_order
                equity+=pnl
                trades.append({**position,'exit_index':i,'exit':round(exit_price,4),
                               'exit_reason':reason,'pnl':round(pnl,2)})
                position=None
                exited=True
        # Calculate signal strictly from completed bars through today's close.
        # Never use future SPY bars in relative strength.
        if position is None and not exited and i<len(frame)-1:
            signal=calculate('RESEARCH',frame.iloc[:i+1],spy.loc[:frame.index[i]])
            if signal and signal['technical_a_plus'] and signal['status']=='CONFIRMADA':
                stop=signal['stop_reference']
                if stop is not None and stop<c:
                    pending={'stop':float(stop),'setup':signal['setup']}
    if position is not None:
        exit_price=float(frame.iloc[-1]['Close'])*(1-cfg.slippage_fraction)
        pnl=position['shares']*(exit_price-position['entry'])-2*cfg.commission_per_order
        equity+=pnl
        trades.append({**position,'exit_index':len(frame)-1,'exit':round(exit_price,4),
                       'exit_reason':'end_of_data','pnl':round(pnl,2)})
    wins=sum(t['pnl']>0 for t in trades)
    return {'strategy':'research_aplus_daily_next_open','stop_mode':stop_mode,'trade_count':len(trades),
            'trades':trades,'initial_equity':cfg.initial_equity,
            'final_equity':round(equity,2),'return_pct':round(100*(equity/cfg.initial_equity-1),2),
            'win_rate_pct':round(100*wins/len(trades),2) if trades else None,
            'limitations':'Research proxy of A+ technical classification only; no fundamentals/earnings; stop_mode=close_next_open models closing breach and next-open gap; 2R intraday target is disabled in this mode; one symbol; no portfolio simulation or edge proven.'}
