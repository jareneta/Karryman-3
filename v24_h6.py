"""Karryman · contraste de H6 (momentum 63 sesiones, top 15 hasta salir del top 45) según docs/V24_H6_MOMENTUM_63.md.
Investigación únicamente. Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
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

N_PLACEBO = 10
K = 6


def run_period(p, member, bench, wins, level, tag):
    base = ve.Cfg(capital=100000, fractional=True, fee_min=0.0, min_order=0.0, top_in=15, top_out=45, max_pos=15, rank_every=1,
                  mom_n=63, atr_mult=1e9, vol_target=10.0, protection='none', cooldown=0)
    h6 = ve.run(p, replace(base, score_mode='momentum'), member)
    plac = [ve.run(p, replace(base, score_mode='random', seed=s), member) for s in range(1, N_PLACEBO + 1)]
    segs = {k: w for k, w in wins.items() if w is not None}
    first, last = min(w[0] for w in segs.values()), max(w[1] for w in segs.values())
    spy = bench[(bench.index >= first) & (bench.index <= last)]
    res = {'spy': {k: vh.series_metrics(spy.loc[w[0]:w[1]]) for k, w in segs.items()},
           'spy_todo': vh.series_metrics(spy)}
    allw = (first, last)
    m = {k: ve.metrics(h6, *w) for k, w in {**{k: w for k, w in segs.items()}, 'todo': allw}.items()}
    res['h6'] = {k: {x: v[x] for x in ('cagr_pct', 'max_dd_pct', 'sharpe', 'calmar', 'orders', 'avg_exposure_pct')} for k, v in m.items()}
    res['placebos'] = {k: {'cagr_mediana': round(float(np.median([ve.metrics(r, *w)['cagr_pct'] for r in plac])), 2),
                          'cagr_min': round(float(min(ve.metrics(r, *w)['cagr_pct'] for r in plac)), 2),
                          'cagr_max': round(float(max(ve.metrics(r, *w)['cagr_pct'] for r in plac)), 2)}
                       for k, w in {**{k: w for k, w in segs.items()}, 'todo': allw}.items()}
    pm = pd.concat([vh.monthly(r['equity']) for r in plac], axis=1).mean(axis=1)
    mm = vh.monthly(h6['equity'].loc[allw[0]:allw[1]])
    lo, hi, mean = vh.boot_ci((mm - pm).loc[allw[0]:allw[1]], level)
    seg_keys = [k for k in wins if k != 'todo']
    c1 = all(m[k]['cagr_pct'] > res['placebos'][k]['cagr_mediana'] for k in seg_keys)
    c2 = lo > 0
    s_, spy_ = m['todo'], res['spy_todo']
    c3 = (s_['sharpe'] >= spy_['sharpe']) or (s_['calmar'] >= spy_['calmar'] and s_['cagr_pct'] >= 0.8 * spy_['cagr_pct'])
    res['criterios'] = {f'{tag}1_cagr_sobre_mediana_placebo_en_ambos_tramos': bool(c1),
                        f'{tag}2_ic_diferencia_mensual': {'nivel': level, 'low': lo, 'high': hi, 'media': mean, 'pasa': bool(c2)},
                        f'{tag}3_supera_al_indice': bool(c3), 'pasa': bool(c1 and c2)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_h6.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H6_MOMENTUM_63.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    pA, mA, bA, iA = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='2008-01-01', end='2020-12-31')
    assert pA['close'].index.max() <= pd.Timestamp('2020-12-31')
    out['A_2010_2020'] = {'universo': iA, **run_period(pA, mA, bA, {'train_2010_16': ('2010-01-01', '2016-12-31'), 'valid_2017_20': ('2017-01-01', '2020-12-31'), 'todo': None}, 1 - 0.05 / K, 'A')}
    print(f'periodo A listo · {time.time()-t0:.0f}s', flush=True)
    pB, mB, bB, iB = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='1996-01-01', end='2009-12-31')
    assert pB['close'].index.max() <= pd.Timestamp('2009-12-31')
    out['B_1997_2009'] = {'universo': iB, **run_period(pB, mB, bB, {'P1_1997_02': ('1997-01-01', '2002-12-31'), 'P2_2003_09': ('2003-01-01', '2009-12-31'), 'todo': None}, 0.95, 'B')}
    a_ok, b_ok = out['A_2010_2020']['criterios']['pasa'], out['B_1997_2009']['criterios']['pasa']
    def sup(r):
        return list(r['criterios'].values())[2]
    out['veredicto'] = {'candidata': bool(a_ok and b_ok), 'supera_al_indice': bool(a_ok and b_ok and sup(out['A_2010_2020']) and sup(out['B_1997_2009'])),
                        'A_pasa': bool(a_ok), 'B_pasa': bool(b_ok)}
    print('RESUMEN_H6 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
