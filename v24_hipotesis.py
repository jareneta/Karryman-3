"""Karryman · contraste de las hipótesis H1-H4 registradas en docs/V24_HIPOTESIS.md (entrenamiento + validación).

Investigación únicamente. La prueba final (2021-2026) está BLOQUEADA: los datos posteriores a LOCK_END no se cargan.
Los veredictos se calculan con los criterios C1-C3 fijados antes de ejecutar.
"""
import argparse
import json
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_engine as ve

LOCK_END = '2020-12-31'
TRAIN = ('2010-01-01', '2016-12-31')
VALID = ('2017-01-01', '2020-12-31')
ALL = ('2010-01-01', LOCK_END)
N_PLACEBO = 10
K_HIPOTESIS = 4
BOOT = 5000


def series_metrics(s):
    s = s.dropna()
    r = s.pct_change().dropna()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    dd = float((s / s.cummax() - 1).min())
    return {'cagr_pct': round(float(cagr * 100), 2), 'max_dd_pct': round(dd * 100, 2),
            'sharpe': round(float(r.mean() / r.std() * np.sqrt(252)), 3), 'calmar': round(float(cagr / abs(dd)), 2)}


def monthly(eq):
    m = eq.dropna().resample('ME').last()
    return m.pct_change().dropna()


def boot_ci(diff, level, n=BOOT, seed=7):
    """IC de la media de `diff` remuestreando meses con reemplazo."""
    rg = np.random.default_rng(seed)
    d = np.asarray(diff.dropna())
    means = rg.choice(d, size=(n, len(d)), replace=True).mean(axis=1)
    a = (1 - level) / 2 * 100
    return float(np.percentile(means, a)), float(np.percentile(means, 100 - a)), float(d.mean())


def seg(res, s, e):
    return ve.metrics(res, s, e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_hipotesis.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='2008-01-01', end=LOCK_END)
    assert p['close'].index.max() <= pd.Timestamp(LOCK_END), 'datos posteriores al bloqueo cargados'
    on = (bench > bench.rolling(200).mean()).reindex(p['close'].index).ffill().fillna(False).to_numpy()
    print(f'datos {info} · hasta {p["close"].index.max().date()} · {time.time()-t0:.0f}s', flush=True)

    base = ve.Cfg(capital=100000, fractional=True, fee_min=0.0, min_order=0.0, top_in=15, top_out=45, max_pos=15, rank_every=21,
                  atr_mult=1e9, vol_target=10.0, protection='none', cooldown=0)
    allm = replace(base, top_in=600, top_out=600, max_pos=600, equal_over_selected=True, score_mode='mom_12_1')
    runs = {
        'H1_mom_12_1': ve.run(p, replace(base, score_mode='mom_12_1'), member),
        'H2_baja_volatilidad': ve.run(p, replace(base, score_mode='lowvol'), member),
        'H3_mom_12_1_con_filtro': ve.run(p, replace(base, score_mode='mom_12_1'), member, market_on=on),
        'H4_igualponderada_con_filtro': ve.run(p, allm, member, market_on=on),
        'REF_igualponderada_sin_filtro': ve.run(p, allm, member),
    }
    print(f'hipótesis ejecutadas · {time.time()-t0:.0f}s', flush=True)
    plac, plac_f = [], []
    for sd in range(1, N_PLACEBO + 1):
        c = replace(base, score_mode='random', seed=sd)
        plac.append(ve.run(p, c, member))
        plac_f.append(ve.run(p, c, member, market_on=on))
    print(f'placebos ejecutados · {time.time()-t0:.0f}s', flush=True)

    spy = bench[(bench.index >= ALL[0]) & (bench.index <= ALL[1])]
    out = {'commit': os.environ.get('GITHUB_SHA'), 'datos': {'tag': a.tag, 'sha256': sha, **info, 'ultimo_dia_cargado': str(p['close'].index.max().date()),
           'bloqueo': f'datos posteriores a {LOCK_END} no cargados'}, 'criterios': 'docs/V24_HIPOTESIS.md', 'spy': {k: series_metrics(spy.loc[s:e]) for k, (s, e) in
           {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}.items()}, 'hipotesis': {}, 'placebos': {}}
    for name, grp in (('placebo_sin_filtro', plac), ('placebo_con_filtro', plac_f)):
        out['placebos'][name] = {k: {'cagr_mediana': round(float(np.median([seg(r, *w)['cagr_pct'] for r in grp])), 2),
                                    'cagr_min': round(float(min(seg(r, *w)['cagr_pct'] for r in grp)), 2),
                                    'cagr_max': round(float(max(seg(r, *w)['cagr_pct'] for r in grp)), 2)}
                                 for k, w in {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}.items()}
    level = 1 - 0.05 / K_HIPOTESIS
    pm_nof = pd.concat([monthly(r['equity']) for r in plac], axis=1).mean(axis=1)
    pm_f = pd.concat([monthly(r['equity']) for r in plac_f], axis=1).mean(axis=1)
    spy_m = spy.resample('ME').last().pct_change().dropna()
    spy_all = out['spy']['todo_2010_2020']
    for name, res in runs.items():
        m = {k: seg(res, *w) for k, w in {'train': TRAIN, 'valid': VALID, 'todo_2010_2020': ALL}.items()}
        h = {'metricas': {k: {x: v[x] for x in ('cagr_pct', 'max_dd_pct', 'sharpe', 'calmar', 'orders', 'avg_exposure_pct')} for k, v in m.items()}}
        mm = monthly(res['equity'].loc[ALL[0]:ALL[1]])
        if name.startswith(('H1', 'H2', 'H3')):
            key = 'placebo_con_filtro' if name.startswith('H3') else 'placebo_sin_filtro'
            ref = pm_f if name.startswith('H3') else pm_nof
            c1 = all(m[k]['cagr_pct'] > out['placebos'][key][k]['cagr_mediana'] for k in ('train', 'valid'))
            lo, hi, mean = boot_ci((mm - ref).loc[ALL[0]:ALL[1]], level)
            c2 = lo > 0
            s_ = m['todo_2010_2020']
            c3 = (s_['sharpe'] >= spy_all['sharpe']) or (s_['calmar'] >= spy_all['calmar'] and s_['cagr_pct'] >= 0.8 * spy_all['cagr_pct'])
            h['criterios'] = {'C1_cagr_sobre_mediana_placebo_en_train_y_valid': bool(c1), 'C2_ic_diferencia_mensual_vs_placebo': {'nivel': level, 'low': lo, 'high': hi, 'media': mean, 'pasa': bool(c2)},
                              'C3_supera_al_indice': bool(c3), 'candidata': bool(c1 and c2), 'supera_al_indice': bool(c1 and c2 and c3)}
        elif name.startswith('H4'):
            r_ = {k: seg(runs['REF_igualponderada_sin_filtro'], *w) for k, w in {'todo_2010_2020': ALL}.items()}['todo_2010_2020']
            s_ = m['todo_2010_2020']
            ok = s_['max_dd_pct'] > r_['max_dd_pct'] and s_['cagr_pct'] >= 0.8 * r_['cagr_pct']
            h['criterios'] = {'ref_igualponderada_sin_filtro_2010_2020': {x: r_[x] for x in ('cagr_pct', 'max_dd_pct', 'sharpe', 'calmar')},
                              'reduce_caida_y_cagr_ge_80pct': bool(ok), 'candidata': bool(ok)}
        out['hipotesis'][name] = h
        print(name, json.dumps(h['metricas']['todo_2010_2020']), h.get('criterios', {}).get('candidata'), flush=True)
    print('RESUMEN_HIPOTESIS ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
