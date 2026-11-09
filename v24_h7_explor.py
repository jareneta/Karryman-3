"""Karryman · H7 exploratoria en acciones que cotizan hoy (sesgo de supervivencia declarado). docs/V24_H7_EXPLORATORIA.md.
Prueba final 2021-2026 bloqueada: la descarga termina en 2020-12-31."""
import argparse
import json
import os
import random
import time

import numpy as np
import pandas as pd

import system_backtest as sb
import tiingo_limits as tl
import v24_h5 as h5
import v24_h7 as h7

END = '2020-12-31'
SEGS = [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))]


def download(tickers, start='2007-01-01', end=END, batch=40):
    import yfinance as yf
    frames = {}
    for k in range(0, len(tickers), batch):
        part = tickers[k:k + batch]
        for attempt in range(3):
            try:
                data = yf.download(part, start=start, end=end, interval='1d', auto_adjust=True, progress=False, threads=True, group_by='ticker', timeout=60)
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            continue
        for t in part:
            try:
                f = (data[t] if isinstance(data.columns, pd.MultiIndex) else data)[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                if len(f) >= 260 and f.index.max() <= pd.Timestamp(END):
                    frames[t] = f
            except Exception:
                pass
        time.sleep(1)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=2500)
    ap.add_argument('--output', default='data/v24_h7_explor.json')
    a = ap.parse_args()
    t0 = time.time()
    names = [t for t in sb.universe() if tl.is_common(t)]
    random.Random(42).shuffle(names)
    frames = download(['SPY'] + names[:int(a.n * 1.25)])
    spy = frames.pop('SPY')
    keep = list(frames)[:a.n]
    print(f'descargadas {len(frames)} series ({len(keep)} usadas) hasta {max(f.index.max() for f in frames.values()).date()} · {time.time()-t0:.0f}s', flush=True)
    regime = sb.regime_series(spy)
    prepared = {t: sb.prepare(frames[t], spy.Close) for t in keep}
    idx = pd.DatetimeIndex(sorted(set().union(*[set(d.index) for d in prepared.values()])))
    sb.attach_rs_rank(prepared, idx)
    print(f'preparadas · {time.time()-t0:.0f}s', flush=True)
    bench = spy.Close
    res = h7.run_period(prepared, regime, bench, SEGS, 0.95, 'EXPL')
    c = res['criterios']
    res['lectura'] = {'sesgo_esperanza_placebo_aqui_vs_sp500_pit_0.38R': res['placebo_agrupado']['todo'].get('expectancy_R'),
                      'diferencia_media_R': c['Q2_diferencia_vs_placebo']['media'], 'ic95': [c['Q2_diferencia_vs_placebo']['low'], c['Q2_diferencia_vs_placebo']['high']],
                      'media_positiva_en_ambos_tramos': bool(all(res['operaciones'][k].get('expectancy_R', 0) - res['placebo_agrupado'][k].get('expectancy_R', 0) > 0 for k, _ in SEGS)),
                      'senal_favorable': bool(c['Q2_diferencia_vs_placebo']['low'] > 0 and all(res['operaciones'][k].get('expectancy_R', 0) - res['placebo_agrupado'][k].get('expectancy_R', 0) > 0 for k, _ in SEGS))}
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H7_EXPLORATORIA.md', 'aviso': 'universo de acciones que cotizan hoy: sesgo de supervivencia; exploratoria',
           'universo': {'series': len(keep), 'ultimo_dia_cargado': str(max(f.index.max() for f in frames.values()).date())}, 'resultado': res}
    print('RESUMEN_H7_EXPLOR ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
