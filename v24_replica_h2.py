"""Karryman · replicación independiente de H2 (baja volatilidad) en 1997-2009, según docs/V24_REPLICA_H2.md.
Investigación únicamente. No se carga ningún dato posterior a 2009-12-31."""
import argparse
import json
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_engine as ve
import v24_hipotesis as vh

END = '2009-12-31'
P1 = ('1997-01-01', '2002-12-31')
P2 = ('2003-01-01', END)
ALL = ('1997-01-01', END)
N_PLACEBO = 10
LEVEL = 0.95


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_replica_h2.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='1996-01-01', end=END)
    assert p['close'].index.max() <= pd.Timestamp(END), 'datos posteriores al bloqueo cargados'
    print(f'datos {info} · {p["close"].index.min().date()} → {p["close"].index.max().date()} · {time.time()-t0:.0f}s', flush=True)
    base = ve.Cfg(capital=100000, fractional=True, fee_min=0.0, min_order=0.0, top_in=15, top_out=45, max_pos=15, rank_every=21,
                  atr_mult=1e9, vol_target=10.0, protection='none', cooldown=0)
    h2 = ve.run(p, replace(base, score_mode='lowvol'), member)
    plac = [ve.run(p, replace(base, score_mode='random', seed=s), member) for s in range(1, N_PLACEBO + 1)]
    print(f'ejecutado · {time.time()-t0:.0f}s', flush=True)
    spy = bench[(bench.index >= ALL[0]) & (bench.index <= ALL[1])]
    wins = {'P1_1997_2002': P1, 'P2_2003_2009': P2, 'todo_1997_2009': ALL}
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_REPLICA_H2.md',
           'datos': {'tag': a.tag, 'sha256': sha, **info, 'primer_dia': str(p['close'].index.min().date()), 'ultimo_dia_cargado': str(p['close'].index.max().date())},
           'spy': {k: vh.series_metrics(spy.loc[w[0]:w[1]]) for k, w in wins.items()}}
    m = {k: ve.metrics(h2, *w) for k, w in wins.items()}
    out['h2'] = {k: {x: v[x] for x in ('cagr_pct', 'max_dd_pct', 'sharpe', 'calmar', 'orders', 'avg_exposure_pct')} for k, v in m.items()}
    out['placebos'] = {k: {'cagr_mediana': round(float(np.median([ve.metrics(r, *w)['cagr_pct'] for r in plac])), 2),
                          'cagr_min': round(float(min(ve.metrics(r, *w)['cagr_pct'] for r in plac)), 2),
                          'cagr_max': round(float(max(ve.metrics(r, *w)['cagr_pct'] for r in plac)), 2)} for k, w in wins.items()}
    pm = pd.concat([vh.monthly(r['equity']) for r in plac], axis=1).mean(axis=1)
    mm = vh.monthly(h2['equity'].loc[ALL[0]:ALL[1]])
    lo, hi, mean = vh.boot_ci((mm - pm).loc[ALL[0]:ALL[1]], LEVEL)
    r1 = all(m[k]['cagr_pct'] > out['placebos'][k]['cagr_mediana'] for k in ('P1_1997_2002', 'P2_2003_2009'))
    r2 = lo > 0
    s_, spy_ = m['todo_1997_2009'], out['spy']['todo_1997_2009']
    r3 = (s_['sharpe'] >= spy_['sharpe']) or (s_['calmar'] >= spy_['calmar'] and s_['cagr_pct'] >= 0.8 * spy_['cagr_pct'])
    out['criterios'] = {'R1_cagr_sobre_mediana_placebo_en_P1_y_P2': bool(r1),
                        'R2_ic95_diferencia_mensual': {'low': lo, 'high': hi, 'media': mean, 'pasa': bool(r2)},
                        'R3_supera_al_indice': bool(r3), 'replica': bool(r1 and r2), 'replica_y_supera_al_indice': bool(r1 and r2 and r3)}
    print('RESUMEN_REPLICA_H2 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
