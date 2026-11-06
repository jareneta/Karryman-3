"""Karryman · ¿doblar al índice con el propio índice? Apalancamiento + filtro de tendencia.

Simula con el S&P 500 (^GSPC, desde 1950) y las letras del Tesoro a 3 meses (^IRX):
- comprar y mantener 1x;
- 2x y 3x diarios (como SSO/UPRO) con coste de financiación (tipo de las letras) y comisión del fondo;
- las mismas con filtro de tendencia: invertido si el cierre está sobre su media de 200 sesiones
  (o 10 meses), si no, en letras del Tesoro. La señal se ejecuta al día siguiente.
Sin dividendos en ^GSPC (se suma una rentabilidad por dividendo aproximada del 2%/año en todas las
estrategias invertidas para no perjudicar a comprar y mantener). Investigación únicamente.
"""
import json
import math
import sys

import numpy as np
import pandas as pd
import yfinance as yf

DIV_YIELD = 0.02
FEE = {1: 0.0, 2: 0.009, 3: 0.009}


def load():
    px = yf.download('^GSPC', start='1949-01-01', auto_adjust=False, progress=False)['Close']
    px = px.iloc[:, 0] if isinstance(px, pd.DataFrame) else px
    irx = yf.download('^IRX', start='1959-01-01', auto_adjust=False, progress=False)['Close']
    irx = irx.iloc[:, 0] if isinstance(irx, pd.DataFrame) else irx
    rate = (irx.reindex(px.index).ffill().fillna(4.0) / 100)
    return px.dropna(), rate


def simulate(px, rate, lev=1, filt=None):
    ret = px.pct_change().fillna(0) + DIV_YIELD / 252
    cash_r = rate / 252
    daily = lev * ret - (lev - 1) * cash_r - FEE[lev] / 252
    if filt is None:
        strat = daily
    else:
        if filt == 'ma200':
            on = px > px.rolling(200).mean()
        elif filt == 'ma10m':
            m = px.resample('ME').last()
            on_m = m > m.rolling(10).mean()
            on = on_m.reindex(px.index, method='ffill').fillna(False)
        on = on.shift(1).fillna(False)  # se actúa al día siguiente de la señal
        strat = daily.where(on, cash_r)
        switches = on.astype(int).diff().abs().fillna(0)
        strat = strat - switches * 0.001  # coste de cambiar de posición
    return (1 + strat).cumprod()


def stats(eq):
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    dd = (eq / eq.cummax() - 1).min()
    r = eq.pct_change().dropna()
    sharpe = r.mean() / r.std() * math.sqrt(252) if r.std() > 0 else 0
    return {'cagr_pct': round(cagr * 100, 2), 'max_dd_pct': round(dd * 100, 1), 'sharpe': round(float(sharpe), 2),
            'x': round(float(eq.iloc[-1] / eq.iloc[0]), 1)}


def main():
    px, rate = load()
    strategies = {'S&P 500 1x comprar y mantener': (1, None), '2x siempre': (2, None), '3x siempre': (3, None),
                  '1x + filtro MA200': (1, 'ma200'), '2x + filtro MA200': (2, 'ma200'), '3x + filtro MA200': (3, 'ma200'),
                  '2x + filtro 10 meses': (2, 'ma10m'), '3x + filtro 10 meses': (3, 'ma10m')}
    periods = {'1960-2026': '1960-01-01', '1990-2026': '1990-01-01', '2000-2026': '2000-01-01',
               '2008-2026': '2008-01-01', '2014-2026': '2014-01-01'}
    out = {}
    for pname, start in periods.items():
        p, r = px[px.index >= pd.Timestamp(start) - pd.Timedelta(days=400)], rate
        out[pname] = {}
        for name, (lev, filt) in strategies.items():
            eq = simulate(p, r.reindex(p.index).ffill(), lev, filt)
            eq = eq[eq.index >= start]
            out[pname][name] = stats(eq / eq.iloc[0])
        print(f'=== {pname} ===')
        for name, s in out[pname].items():
            print(f"{name:32s} CAGR={s['cagr_pct']:6}%  caída máx={s['max_dd_pct']:6}%  Sharpe={s['sharpe']:5}  x{s['x']}")
    # año a año 2014-2026
    p = px[px.index >= '2013-01-01']
    yr = {}
    for name in ('S&P 500 1x comprar y mantener', '2x + filtro MA200', '3x + filtro MA200'):
        lev, filt = strategies[name]
        eq = simulate(p, rate.reindex(p.index).ffill(), lev, filt)
        y = eq.groupby(eq.index.year).last()
        yr[name] = (y / y.shift(1) - 1).dropna().mul(100).round(1).to_dict()
        print(name[:30].ljust(30), ' '.join(f'{int(k)}:{v:6}' for k, v in yr[name].items()))
    json.dump({'periods': out, 'yearly': yr}, open(sys.argv[1] if len(sys.argv) > 1 else 'data/index_leverage.json', 'w'),
              ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
