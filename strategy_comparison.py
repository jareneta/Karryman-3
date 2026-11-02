"""Comparable, research-only strategy filters; not authentic proprietary implementations.

The Minervini-inspired filter deliberately omits IBD RS percentile because it
requires a historical cross-sectional universe. Kell-inspired uses daily EMA
reclaim and base break, not intraday/65-minute discretionary rules.
"""
def _avg(series,n):
    return sum(series[-n:])/n

def classify(rows):
    """Chronological daily OHLCV dicts; current session is last."""
    if len(rows)<252:return {'minervini_proxy':False,'kell_proxy':False,'reason':'insufficient_history'}
    c=[float(x['close']) for x in rows]
    h=[float(x['high']) for x in rows]
    l=[float(x['low']) for x in rows]
    v=[float(x['volume']) for x in rows]
    close=c[-1]
    ma50=_avg(c,50);ma150=_avg(c,150);ma200=_avg(c,200)
    ma200_20ago=_avg(c[-220:-20],200)
    high52=max(h[-252:]);low52=min(l[-252:])
    trend=(close>ma50>ma150>ma200 and ma200>ma200_20ago
           and close>=1.25*low52 and close>=.75*high52)
    # Objective, imperfect VCP proxy: three successive, shrinking ranges.
    def depth(window):
        section=rows[window[0]:window[1]]
        return (max(float(x['high']) for x in section)/
                min(float(x['low']) for x in section)-1) if section else 1e9
    d1=depth((-60,-40));d2=depth((-40,-20));d3=depth((-20,0))
    contraction=d1>d2>d3 and d3<=.15
    dryup=_avg(v[-6:-1],5)<.8*_avg(v[-26:-6],20) if _avg(v[-26:-6],20)>0 else False
    pivot=max(h[-31:-1])
    minervini_proxy=trend and contraction and dryup and close>pivot and v[-1]>=1.4*_avg(v[-51:-1],50)
    # Kell-style EMA crossback: reclaim 10 EMA after touching 20 EMA.
    def ema(values,period):
        alpha=2/(period+1);out=values[0]
        result=[]
        for val in values:
            out=alpha*val+(1-alpha)*out
            result.append(out)
        return result
    e10=ema(c,10);e20=ema(c,20)
    touch=any(l[j]<=e20[j]*1.02 for j in range(-6,-1))
    crossback=touch and c[-2]<=e10[-2] and close>e10[-1] and close>c[-2]
    base_break=close>pivot and c[-2]<=pivot and v[-1]>=1.4*_avg(v[-51:-1],50)
    kell_proxy=close>ma50>ma200 and (crossback or base_break)
    return {'minervini_proxy':bool(minervini_proxy),'kell_proxy':bool(kell_proxy),
            'minervini_trend':bool(trend),'vcp_range_proxy':bool(contraction),
            'volume_dryup':bool(dryup),'kell_crossback':bool(crossback),
            'kell_base_break':bool(base_break),
            'note':'Research approximations only. Minervini RS rank unavailable; Kell intraday and discretionary rules not modeled.'}
