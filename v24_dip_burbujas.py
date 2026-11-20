"""Karryman · H9b en la burbuja punto com y en las correcciones 2015-2026 según docs/V24_H9B_BURBUJAS.md (exploratorio)."""
import argparse
import json
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_dip as dip
import v24_h7 as h7

WINDOWS = {'D0_burbuja_alcista': ('1998-10-09', '2000-03-24'), 'D1_caida_2000_2002': ('2000-03-25', '2002-10-09'), 'D2_recuperacion': ('2002-10-10', '2004-12-31'),
           'C2018': ('2018-08-30', '2018-12-24'), 'C2020': ('2020-02-20', '2020-03-23'), 'C2022': ('2021-11-22', '2022-12-28'), 'C2026_hasta_30oct': ('2026-10-07', '2026-10-30')}
ERAS = {'1998_2004': ('1998-01-01', '2004-12-31'), '2015_2026': ('2015-01-01', '2026-10-30')}
BUCKETS = [('mayor_-5', -0.05, 1.0), ('-5_a_-10', -0.10, -0.05), ('-10_a_-20', -0.20, -0.10), ('menor_-20', -9.0, -0.20)]
N_PLACEBO = 10
BOOT = 5000


def bucket(dd):
    for name, lo, hi in BUCKETS:
        if lo <= dd < hi or (name == 'mayor_-5' and dd >= -0.05):
            return name
    return 'menor_-20'


def month_boot_diff(r1, m1, r0, m0, n=BOOT, seed=3):
    """Diferencia de medias de R (operaciones - placebo) con IC 95 % remuestreando meses de entrada."""
    months = sorted(set(m1) | set(m0))
    if not months or len(r1) == 0 or len(r0) == 0:
        return None
    ix = {m: i for i, m in enumerate(months)}
    s1, c1, s0, c0 = (np.zeros(len(months)) for _ in range(4))
    for r, m in zip(r1, m1):
        s1[ix[m]] += r; c1[ix[m]] += 1
    for r, m in zip(r0, m0):
        s0[ix[m]] += r; c0[ix[m]] += 1
    g = np.random.default_rng(seed).integers(0, len(months), size=(n, len(months)))
    a, b = s1[g].sum(1) / np.maximum(c1[g].sum(1), 1), s0[g].sum(1) / np.maximum(c0[g].sum(1), 1)
    d = a - b
    return {'dif_R': round(float(r1.mean() - r0.mean()), 4), 'ic95': [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]}


def summarize(tr, pl):
    """tr: operaciones reales; pl: placebo agrupado de las semillas (con columna seed)."""
    n = len(tr)
    out = {'n': int(n), 'nivel': 'no_concluyente' if n < 100 else ('indicativo' if n < 300 else 'evaluable')}
    if n == 0:
        return out
    seeds = pl.groupby('seed').r.mean() if len(pl) else pd.Series(dtype=float)
    out.update({'esperanza_R': round(float(tr.r.mean()), 4), 'ganadoras_pct': round(float((tr.r > 0).mean() * 100), 1),
                'placebo_mediana_R': round(float(seeds.median()), 4) if len(seeds) else None, 'placebo_n_medio': int(len(pl) / max(1, pl.seed.nunique())) if len(pl) else 0})
    if len(pl):
        d = month_boot_diff(tr.r.to_numpy(), tr.entry_date.dt.to_period('M'), pl.r.to_numpy(), pl.entry_date.dt.to_period('M'))
        out['vs_placebo'] = d
        out['senal_de_ventaja_sin_corregir'] = bool(d and d['dif_R'] > 0 and d['ic95'][0] > 0 and n >= 100)
    return out


def in_w(df, w):
    return df[(df.entry_date >= pd.Timestamp(w[0])) & (df.entry_date <= pd.Timestamp(w[1]))]


def spy_dd_at(bench, dates):
    dd = bench / bench.rolling(252, min_periods=200).max() - 1
    return dd.shift(1).reindex(dates, method='ffill').to_numpy()     # cierre de la sesión anterior a la entrada


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_dip_burbujas.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='1996-01-01', end='2026-10-30')
    prepared, regime = h7.prepare_all(p, member, bench)
    print(f'preparado {len(prepared)} series · {time.time()-t0:.0f}s', flush=True)
    tr = sb.simulate_independent(prepared, dip.CFG, regime)
    pl = pd.concat([sb.simulate_independent(prepared, replace(dip.CFG, placebo=True), regime, seed=s).assign(seed=s) for s in range(1, N_PLACEBO + 1)])
    print(f'simulado {len(tr)} operaciones y {len(pl)} de placebo · {time.time()-t0:.0f}s', flush=True)
    bench = bench.dropna()
    tr, pl = tr.assign(dd=spy_dd_at(bench, tr.entry_date)), pl.assign(dd=spy_dd_at(bench, pl.entry_date))
    tm = dip.tech_map()
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H9B_BURBUJAS.md', 'datos': {'tag': a.tag, 'sha256': sha}, 'universo': info, 'tipo': 'exploratorio, sin corrección por multiplicidad'}
    out['ventanas'] = {k: summarize(in_w(tr, w), in_w(pl, w)) for k, w in WINDOWS.items()}
    out['por_estado_del_mercado'] = {}
    for era, w in ERAS.items():
        t, q = in_w(tr, w), in_w(pl, w)
        out['por_estado_del_mercado'][era] = {name: summarize(t[t.dd.map(bucket) == name], q[q.dd.map(bucket) == name]) for name, _, _ in BUCKETS}
    if tm is not None:
        out['tecnologicas_sesgado'] = {}
        for era, w in ERAS.items():
            t = in_w(tr, w)
            q = in_w(pl, w)
            f = lambda d, v: d[d.ticker.map(lambda x: bool(tm.get(x)) == v)]
            out['tecnologicas_sesgado'][era] = {'tecnologicas_clasificadas': summarize(f(t, True), f(q, True)), 'resto_o_sin_clasificar': summarize(f(t, False), f(q, False)),
                                                 'cobertura_clasificadas_pct': round(float(t.ticker.map(lambda x: x in tm).mean() * 100), 1)}
    print('RESUMEN_BURBUJAS ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
