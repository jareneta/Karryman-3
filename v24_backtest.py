"""Karryman V24 · backtest con el motor corregido (v24_engine) sobre datos de Yahoo.

Investigación únicamente. Universo: acciones cotizadas hoy (sesgo de supervivencia, declarado) con filtro de
liquidez vigente día a día (mediana de 60 sesiones de volumen en dólares y precio mínimo, solo datos hasta ese día).
Tramos fijos, sin optimizar sobre ellos: entrenamiento 2010-2016, validación 2017-2020, prueba 2021-2026.
"""
import argparse
import json
import random
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_engine as ve

SEGS = {'entrenamiento_2010_16': ('2010-01-01', '2016-12-31'), 'validacion_2017_20': ('2017-01-01', '2020-12-31'),
        'prueba_2021_26': ('2021-01-01', None), 'todo': (None, None)}


def to_wide(frames):
    out = {}
    for k in ('Open', 'High', 'Low', 'Close', 'Volume'):
        out[k.lower()] = pd.DataFrame({t: f[k] for t, f in frames.items()}).sort_index()
    return out


def liquidity_member(p, min_dollar_vol=5e6, min_price=5.0):
    dv = (p['close'] * p['volume']).rolling(60, min_periods=40).median()
    return (dv >= min_dollar_vol) & (p['close'] >= min_price)


def benchmark(spy):
    rows = {}
    for seg, (a, b) in SEGS.items():
        s = spy.loc[a:b] if (a or b) else spy
        yrs = (s.index[-1] - s.index[0]).days / 365.25
        rows[seg] = {'cagr_pct': round(float(((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100), 2),
                     'max_dd_pct': round(float((s / s.cummax() - 1).min() * 100), 2)}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=300)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--start', default='2009-06-01')
    ap.add_argument('--output', default='data/v24_results.json')
    ap.add_argument('--capital', type=float, default=3000)
    ap.add_argument('--fee-min', type=float, default=1.0)
    ap.add_argument('--min-order', type=float, default=100.0)
    ap.add_argument('--fractional', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    names = sb.universe()
    random.Random(a.seed).shuffle(names)
    frames = sb.download(['SPY'] + names[:a.symbols * 2], a.start)   # se piden el doble: muchas no pasan filtros
    spy = frames.pop('SPY')['Close']
    keep = list(frames)[:a.symbols] if len(frames) > a.symbols else list(frames)
    p = to_wide({t: frames[t] for t in keep})
    member = liquidity_member(p)
    print(f'Series: {len(keep)} · desde {p["close"].index[0].date()} hasta {p["close"].index[-1].date()} · {time.time()-t0:.0f}s', flush=True)
    base = ve.Cfg(capital=a.capital, fee_min=a.fee_min, min_order=a.min_order, fractional=a.fractional, rank_every=1)
    models = {
        'v24_base_sin_proteccion': replace(base, protection='none'),
        'v24_freno_fijo_8_50': replace(base, protection='fixed'),
        'v24_progresiva': replace(base, protection='progressive'),
        'v24_progresiva_banda10': replace(base, protection='progressive', band=0.10),
        'v24_progresiva_ma100': replace(base, protection='progressive', ma100_guard=True),
        'v24_progresiva_rank_mensual': replace(base, protection='progressive', rank_every=21),
    }
    out = {'parametros': {'capital': a.capital, 'fee_min': a.fee_min, 'min_order': a.min_order, 'fractional': a.fractional, 'symbols': a.symbols, 'seed': a.seed},
           'universo': {'series': len(keep), 'nota': 'acciones cotizadas hoy: sesgo de supervivencia; filtro de liquidez vigente día a día'},
           'modelos': {}, 'comisiones': [], 'benchmark_spy': benchmark(spy)}
    runs = {}
    for name, cfg in models.items():
        runs[name] = ve.run(p, cfg, member)
        out['modelos'][name] = {seg: ve.metrics(runs[name], s, e) for seg, (s, e) in SEGS.items()}
        m = out['modelos'][name]['todo']
        print(f'{name}: CAGR {m["cagr_pct"]}% · DD {m["max_dd_pct"]}% · Sharpe {m["sharpe"]} · órdenes {m["orders"]} · {time.time()-t0:.0f}s', flush=True)
    cfg = replace(base, protection='progressive', band=0.10)
    out['comisiones'] = json.loads(ve.fee_sensitivity(p, cfg, fees=(0.35, 0.50, 1.00), min_order=a.min_order, member=member).to_json(orient='records'))
    r = runs['v24_progresiva_banda10']
    tr = r['trades']
    gaps = tr.date.sort_values().diff().dt.days.dropna()
    out['anti_bloqueo'] = {'ultima_orden': str(tr.date.max().date()), 'efectivo_final': round(r['cash_end'], 2),
                           'patrimonio_final': round(float(r['equity'].iloc[-1]), 2), 'mayor_periodo_sin_operar_dias': int(gaps.max())}
    print('RESUMEN_V24 ' + json.dumps(out, default=float), flush=True)
    import os
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
