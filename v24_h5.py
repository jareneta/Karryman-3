"""Karryman · contraste de H5 (sistema de plan.html) según docs/V24_H5_PLAN_HTML.md. Investigación únicamente.
Prueba final 2021-2026 bloqueada: los datos posteriores a LOCK_END no se cargan."""
import argparse
import json
import math
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_hipotesis as vh

LOCK_END = '2020-12-31'
TRAIN = ('2010-01-01', '2016-12-31')
VALID = ('2017-01-01', '2020-12-31')
ALL = ('2010-01-01', LOCK_END)
N_PLACEBO = 10
BOOT = 5000


def frames_from_wide(p, member, tickers, min_len=260):
    out = {}
    for t in tickers:
        f = pd.DataFrame({'Open': p['open'][t], 'High': p['high'][t], 'Low': p['low'][t], 'Close': p['close'][t], 'Volume': p['volume'][t]}).dropna()
        if len(f) >= min_len:
            out[t] = (f, member[t].reindex(f.index).fillna(False).astype(bool))
    return out


def rstats(r):
    r = np.asarray(r, float)
    if len(r) == 0:
        return {'trades': 0}
    boot = np.random.default_rng(1).choice(r, size=(BOOT, len(r)), replace=True).mean(axis=1)
    return {'trades': int(len(r)), 'expectancy_R': round(float(r.mean()), 4), 'ci95_R': [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
            'win_rate_pct': round(float((r > 0).mean() * 100), 1)}


def diff_ci(a, b, seed=2):
    rg = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    da = rg.choice(a, size=(BOOT, len(a)), replace=True).mean(axis=1)
    db = rg.choice(b, size=(BOOT, len(b)), replace=True).mean(axis=1)
    d = da - db
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(a.mean() - b.mean())


def curve(eq):
    s = sb.curve_stats(eq)
    if s:
        s['calmar'] = round(s['cagr_pct'] / abs(s['max_dd_pct']), 2) if s['max_dd_pct'] < 0 else None
    return s


def sl(s, w):
    x = s.loc[w[0]:w[1]]
    return x / x.iloc[0] if len(x) else x


def in_win(df, w):
    return df[(df.entry_date >= pd.Timestamp(w[0])) & (df.entry_date <= pd.Timestamp(w[1]))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_h5.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='2007-01-01', end=LOCK_END)
    assert p['close'].index.max() <= pd.Timestamp(LOCK_END), 'datos posteriores al bloqueo cargados'
    fr = frames_from_wide(p, member, list(p['close'].columns))
    spy = pd.DataFrame({'Close': bench}).dropna()
    regime = sb.regime_series(spy)
    prepared = {}
    for t, (f, m) in fr.items():
        d = sb.prepare(f, spy.Close)
        d['member'] = m.reindex(d.index).fillna(False).astype(bool)
        prepared[t] = d
    print(f'datos {info} · preparadas {len(prepared)} series · {time.time()-t0:.0f}s', flush=True)

    cfg = replace(sb.FINAL, name='H5_plan_html')
    tr = sb.simulate_independent(prepared, cfg, regime)
    tr = in_win(tr, ALL)
    pl = []
    for sd in range(1, N_PLACEBO + 1):
        x = sb.simulate_independent(prepared, replace(cfg, placebo=True, name=f'placebo{sd}'), regime, seed=sd)
        pl.append(in_win(x, ALL))
    plc = pd.concat(pl)
    print(f'operaciones H5={len(tr)} · placebo agrupado={len(plc)} · {time.time()-t0:.0f}s', flush=True)

    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H5_PLAN_HTML.md',
           'datos': {'tag': a.tag, 'sha256': sha, **info, 'ultimo_dia_cargado': str(p['close'].index.max().date()), 'bloqueo': f'datos posteriores a {LOCK_END} no cargados'},
           'operaciones': {k: rstats(in_win(tr, w).r) for k, w in {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}.items()},
           'placebo_agrupado': {k: rstats(in_win(plc, w).r) for k, w in {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}.items()}}
    q1 = (out['operaciones']['todo_2010_2020'].get('ci95_R', [0, 0])[0] > 0 and out['operaciones']['train'].get('expectancy_R', 0) > 0
          and out['operaciones']['valid'].get('expectancy_R', 0) > 0)
    lo, hi, mean = diff_ci(tr.r.values, plc.r.values) if len(tr) and len(plc) else (float('nan'),) * 3
    q2 = lo > 0
    n_ok = len(tr) >= 300
    # carteras
    start, end = pd.Timestamp(ALL[0]), pd.Timestamp(ALL[1])
    eq, ntr = sb.simulate_portfolio(prepared, cfg, regime, start, end)
    peq = []
    for sd in range(1, N_PLACEBO + 1):
        e, _ = sb.simulate_portfolio(prepared, replace(cfg, placebo=True), regime, start, end, seed=sd)
        peq.append(e)
    spyc = bench[(bench.index >= start) & (bench.index <= end)]
    wins = {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}
    out['cartera'] = {'h5': {k: curve(sl(eq, w)) for k, w in wins.items()}, 'spy': {k: curve(sl(spyc, w)) for k, w in wins.items()},
                      'placebo_cagr_mediana': {k: round(float(np.median([curve(sl(e, w))['cagr_pct'] for e in peq])), 2) for k, w in wins.items()},
                      'placebo_cagr_rango': {k: [round(float(min(curve(sl(e, w))['cagr_pct'] for e in peq)), 2), round(float(max(curve(sl(e, w))['cagr_pct'] for e in peq)), 2)] for k, w in wins.items()},
                      'operaciones_cartera': ntr}
    h, s_ = out['cartera']['h5']['todo_2010_2020'], out['cartera']['spy']['todo_2010_2020']
    q3 = (h['sharpe'] >= s_['sharpe']) or ((h.get('calmar') or 0) >= (s_.get('calmar') or 0) and h['cagr_pct'] >= 0.8 * s_['cagr_pct'])
    q4 = all(out['cartera']['h5'][k]['cagr_pct'] > out['cartera']['placebo_cagr_mediana'][k] for k in ('train', 'valid'))
    cand = bool(q1 and q2 and n_ok)
    out['criterios'] = {'N_operaciones_ge_300': bool(n_ok), 'Q1_esperanza_R_positiva': bool(q1),
                        'Q2_ic95_diferencia_vs_placebo': {'low': lo, 'high': hi, 'media': mean, 'pasa': bool(q2)},
                        'Q3_supera_al_indice_en_riesgo_retorno': bool(q3), 'Q4_cartera_sobre_mediana_placebo_en_train_y_valid': bool(q4),
                        'candidata': cand, 'supera_al_indice': bool(cand and q3 and q4), 'inconclusivo_por_pocas_operaciones': bool(not n_ok)}
    print('RESUMEN_H5 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
