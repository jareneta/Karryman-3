"""Karryman · tipos de caída dentro de H9b (docs/V24_TIPOS_DE_CAIDA.md). Investigación únicamente. Exploratorio: sin datos de reserva."""
import argparse
import json
import math
import os
import time

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_dip as dip
import v24_h7 as h7
import v24_scan as sc

ERAS = (('A_2010_2020', '2007-01-01', '2020-12-31', ('2010-01-01', '2020-12-31')),
        ('B_1997_2009', '1996-01-01', '2009-12-31', ('1997-01-01', '2009-12-31')),
        ('C_2021_2026', '2019-01-01', '2026-10-31', ('2021-01-01', '2026-10-31')))
R_PCT = 12.0                                   # R = 12 % de la entrada
MIN_N = 150
MIN_DIFF = 0.02

GROUPS = [  # (característica, nombre del grupo, función que recibe la tabla de operaciones y devuelve máscara booleana)
    ('profundidad', '15-20%', lambda t: (t.dd <= -0.15) & (t.dd > -0.20)), ('profundidad', '20-25%', lambda t: (t.dd <= -0.20) & (t.dd > -0.25)),
    ('profundidad', '25-35%', lambda t: (t.dd <= -0.25) & (t.dd >= -0.35)),
    ('velocidad', 'rapida_ret5<=-10%', lambda t: t.ret5 <= -0.10), ('velocidad', 'gradual', lambda t: t.ret5 > -0.10),
    ('antiguedad_maximo', '<=10 sesiones', lambda t: t.dias_max <= 10), ('antiguedad_maximo', '11-30', lambda t: (t.dias_max > 10) & (t.dias_max <= 30)),
    ('antiguedad_maximo', '>30', lambda t: t.dias_max > 30),
    ('volumen_señal', '<1x', lambda t: t.vol_ratio < 1), ('volumen_señal', '1-1.5x', lambda t: (t.vol_ratio >= 1) & (t.vol_ratio < 1.5)),
    ('volumen_señal', '>=1.5x', lambda t: t.vol_ratio >= 1.5),
    ('mercado', 'SPY>SMA200', lambda t: t.spy_up), ('mercado', 'SPY<=SMA200', lambda t: ~t.spy_up),
    ('dist_max_252', '<25%', lambda t: t.dist252 > -0.25), ('dist_max_252', '25-40%', lambda t: (t.dist252 <= -0.25) & (t.dist252 > -0.40)),
    ('dist_max_252', '>=40%', lambda t: t.dist252 <= -0.40),
    ('hueco_apertura', 'bajista>=3%', lambda t: t.gap <= -0.03), ('hueco_apertura', 'resto', lambda t: t.gap > -0.03),
    ('sobre_SMA200', '<10%', lambda t: t.sma200 < 0.10), ('sobre_SMA200', '10-30%', lambda t: (t.sma200 >= 0.10) & (t.sma200 <= 0.30)),
    ('sobre_SMA200', '>30%', lambda t: t.sma200 > 0.30),
]
FAMILIES = {}
for fam, name, _ in GROUPS:
    FAMILIES.setdefault(fam, []).append(name)


def trade_features(tr, prepared, bench):
    """Une a cada operación las características de la sesión de la señal (solo datos hasta ese cierre)."""
    spy_up = (bench > bench.rolling(200).mean())
    rows = []
    for t in tr.itertuples(index=False):
        d = prepared[t.ticker]
        e = d.index.get_loc(t.entry_date)
        i = e - 1
        if i < 253:
            continue
        c = d.Close.to_numpy()
        win = c[i - 60:i]
        dd = c[i] / win.max() - 1
        rows.append({'ticker': t.ticker, 'entry_date': t.entry_date, 'r': t.r, 'dd': dd, 'ret5': c[i] / c[i - 5] - 1,
                     'dias_max': int(60 - int(np.argmax(win))), 'vol_ratio': float(d.Volume.iloc[i] / d.vol50.iloc[i]),
                     'dist252': float(c[i] / d.hi252.iloc[i] - 1), 'sma200': float(c[i] / d.ma200.iloc[i] - 1),
                     'gap': float(d.Open.iloc[i] / c[i - 1] - 1), 'spy_up': bool(spy_up.reindex([d.index[i]]).ffill().iloc[0]) if d.index[i] in spy_up.index else False})
    return pd.DataFrame(rows)


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 20 or len(b) < 20:
        return float('nan'), float('nan'), float('nan')
    d = a.mean() - b.mean()
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = d / se if se > 0 else float('nan')
    return float(d), float(t), float(math.erfc(abs(t) / math.sqrt(2)))


def contrasts(T):
    out = {}
    for fam, name, fn in GROUPS:
        in_group = fn(T).to_numpy(bool)
        sib = [g for g in GROUPS if g[0] == fam]
        in_family = np.zeros(len(T), bool)
        for g in sib:
            in_family |= g[2](T).to_numpy(bool)
        rest = in_family & ~in_group                    # el resto de las operaciones de esa característica
        d, t, p = welch(T.r[in_group], T.r[rest])
        out[(fam, name)] = {'n': int(in_group.sum()), 'n_resto': int(rest.sum()), 'esperanza_R': float(T.r[in_group].mean()) if in_group.any() else float('nan'),
                            'esperanza_pct': float(T.r[in_group].mean() * R_PCT) if in_group.any() else float('nan'),
                            'esperanza_resto_R': float(T.r[rest].mean()) if rest.any() else float('nan'), 'dif_R': d, 't': t, 'p': p}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_dip_tipos.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    res, total = {}, {}
    for era, start, end, win in ERAS:
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end)
        prepared, regime = h7.prepare_all(p, member, bench)
        tr = sb.simulate_independent(prepared, dip.CFG, regime)
        tr = tr[(tr.entry_date >= pd.Timestamp(win[0])) & (tr.entry_date <= pd.Timestamp(win[1]))]
        T = trade_features(tr, prepared, bench)
        res[era] = contrasts(T)
        total[era] = {'operaciones': int(len(T)), 'esperanza_R': float(T.r.mean()), 'esperanza_pct': float(T.r.mean() * R_PCT)}
        print(f'{era}: {len(T)} operaciones · {time.time()-t0:.0f}s', flush=True)
    keys = list(res['A_2010_2020'].keys())
    rej = sc.bh([res['A_2010_2020'][k]['p'] for k in keys], 0.05)
    table, cands = [], []
    for k, rj in zip(keys, rej):
        A, B, C = res['A_2010_2020'][k], res['B_1997_2009'][k], res['C_2021_2026'][k]
        same = all(x['dif_R'] == x['dif_R'] for x in (A, B, C)) and np.sign(A['dif_R']) == np.sign(B['dif_R']) == np.sign(C['dif_R'])
        rep = bool(same and B['p'] < 0.05 and C['p'] < 0.05)
        eff = bool(all(abs(x['dif_R']) >= MIN_DIFF for x in (A, B, C))) if same else False
        n_ok = bool(all(x['n'] >= MIN_N for x in (A, B, C)))
        row = {'caracteristica': k[0], 'grupo': k[1], 'A': A, 'B': B, 'C': C, 'BH_A': bool(rj), 'replica_B_y_C': rep, 'efecto_minimo': eff, 'n_minimo': n_ok}
        table.append(row)
        if rj and rep and eff and n_ok:
            cands.append(row)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_TIPOS_DE_CAIDA.md', 'datos': {'tag': a.tag, 'sha256': sha}, 'total_h9b': total,
           'resumen': {'contrastes': len(keys), 'falsos_positivos_esperados_5pct': round(0.05 * len(keys), 1), 'significativos_A_sin_corregir': int(sum(1 for k in keys if res['A_2010_2020'][k]['p'] < 0.05)),
                       'significativos_A_BH': int(rej.sum()), 'candidatos_finales': len(cands)}, 'candidatos': cands, 'tabla': table}
    print('RESUMEN_TIPOS ' + json.dumps({'total': total, 'resumen': out['resumen'], 'cands': [(c['caracteristica'], c['grupo']) for c in cands]}), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
