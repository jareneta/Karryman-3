"""Karryman · escaneo de anomalías de calendario sobre el índice (familia B de docs/V24_ESCANEO_ANOMALIAS.md). Investigación únicamente.
Datos hasta 2020-12-31; la prueba final 2021-2026 no se usa."""
import argparse
import json
import math
import os

import numpy as np
import pandas as pd

import index_leverage as il
import v24_scan as sc

LOCK_END = '2020-12-31'
PERIODS = {'C1_1950_1979': ('1950-01-01', '1979-12-31'), 'C2_1980_1999': ('1980-01-01', '1999-12-31'), 'C3_2000_2020': ('2000-01-01', LOCK_END)}


def groups(idx):
    """Variables binarias de calendario por sesión (solo con la fecha, sin precios)."""
    d = pd.DataFrame(index=idx)
    for k, name in enumerate(['lun', 'mar', 'mie', 'jue', 'vie']):
        d[f'dia_{name}'] = (idx.weekday == k)
    for m in range(1, 13):
        d[f'mes_{m:02d}'] = (idx.month == m)
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)
    pos_in_month = ym.groupby(ym).cumcount()
    size_month = ym.groupby(ym).transform('size')
    last = (pos_in_month == size_month - 1)
    first3 = (pos_in_month <= 2)
    d['cambio_de_mes'] = (last | first3).to_numpy()
    nxt = pd.Series(idx, index=idx).shift(-1)
    gap = (nxt - pd.Series(idx, index=idx)).dt.days
    wd = idx.weekday
    d['vispera_festivo'] = (((wd < 4) & (gap > 1)) | ((wd == 4) & (gap > 3))).to_numpy()
    d['halloween_nov_abr'] = np.isin(idx.month, [11, 12, 1, 2, 3, 4])
    return d.astype(bool)


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 30 or nb < 30:
        return float('nan'), float('nan'), float('nan')
    diff = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / na + b.var(ddof=1) / nb)
    t = diff / se if se > 0 else float('nan')
    return float(diff), float(t), float(math.erfc(abs(t) / math.sqrt(2)))


def run_all(px):
    px = px[px.index <= pd.Timestamp(LOCK_END)]
    r = px.pct_change().dropna()
    g = groups(r.index)
    res = {}
    for pn, (s, e) in PERIODS.items():
        rr = r.loc[s:e]
        gg = g.loc[rr.index]
        res[pn] = {}
        for col in gg.columns:
            diff, t, p = welch(rr[gg[col]], rr[~gg[col]])
            res[pn][col] = {'dif_media_diaria_pct': diff * 100 if diff == diff else None, 't': t, 'p': p, 'n_grupo': int(gg[col].sum())}
    cols = list(g.columns)
    p1 = [res['C1_1950_1979'][c]['p'] for c in cols]
    rej = sc.bh(p1, 0.05)
    cands, table = [], []
    for c, rj in zip(cols, rej):
        a, b, d = res['C1_1950_1979'][c], res['C2_1980_1999'][c], res['C3_2000_2020'][c]
        same = all(x['dif_media_diaria_pct'] is not None for x in (a, b, d)) and np.sign(a['dif_media_diaria_pct']) == np.sign(b['dif_media_diaria_pct']) == np.sign(d['dif_media_diaria_pct'])
        rep = bool(same and b['p'] < 0.05 and d['p'] < 0.05)
        row = {'variable': c, 'C1': a, 'C2': b, 'C3': d, 'BH_C1': bool(rj), 'replica_C2_C3': rep}
        table.append(row)
        if rj and rep:
            cands.append(row)
    return {'ultimo_dia_usado': str(px.index.max().date()),
            'resumen': {'pruebas': len(cols), 'falsos_positivos_esperados_al_5pct': round(0.05 * len(cols), 1), 'significativas_C1_sin_corregir': int(sum(1 for x in p1 if x == x and x < 0.05)),
                        'significativas_C1_BH': int(rej.sum()), 'candidatas_finales': len(cands)}, 'candidatas': cands, 'tabla_completa': table}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='data/v24_calendar.json')
    a = ap.parse_args()
    px, _ = il.load()
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_ESCANEO_ANOMALIAS.md', **run_all(px)}
    print('RESUMEN_CALENDARIO ' + json.dumps(out['resumen']) + ' CAND ' + json.dumps([c['variable'] for c in out['candidatas']]), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
