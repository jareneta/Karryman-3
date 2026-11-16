"""Karryman · escaneo de anomalías de sección cruzada (familia A de docs/V24_ESCANEO_ANOMALIAS.md). Investigación únicamente.
Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
import argparse
import json
import math
import os
import time

import numpy as np
import pandas as pd

import v24_backtest as vb

HORIZONS = (1, 5, 21)
COST_ROUNDTRIP = 0.004          # 0,10 % por lado y por pata, rebalanceo completo
MIN_IC = 0.01


def features(p):
    C, O, H, L, V = p['close'], p['open'], p['high'], p['low'], p['volume']
    r1 = C.pct_change(fill_method=None)
    ret = lambda n: C / C.shift(n) - 1
    F = {}
    for n in (1, 2, 3, 5, 10, 21, 63, 126, 252):
        F[f'r{n}'] = ret(n)
    F['r126m21'] = C.shift(21) / C.shift(126) - 1
    F['r252m21'] = C.shift(21) / C.shift(252) - 1
    for n in (10, 21, 63):
        F[f'vol{n}'] = r1.rolling(n).std()
    tr = np.maximum(np.maximum((H - L).to_numpy(), (H - C.shift(1)).abs().to_numpy()), (L - C.shift(1)).abs().to_numpy())
    F['atr14pct'] = pd.DataFrame(tr, index=C.index, columns=C.columns).rolling(14).mean() / C
    F['dvol63'] = (r1.clip(upper=0) ** 2).rolling(63).mean() ** 0.5
    F['skew63'] = r1.rolling(63).skew()
    F['max21'] = r1.rolling(21).max()
    F['min21'] = r1.rolling(21).min()
    mkt = r1.mean(axis=1)
    var_m126, var_m63 = mkt.rolling(126).var(), mkt.rolling(63).var()
    F['beta126'] = r1.rolling(126).cov(mkt).div(var_m126, axis=0)
    beta63 = r1.rolling(63).cov(mkt).div(var_m63, axis=0)
    F['ivol63'] = (r1.rolling(63).var() - beta63 ** 2 * var_m63.values[:, None]).clip(lower=0) ** 0.5
    F['dh252'] = C / H.rolling(252).max() - 1
    F['dl252'] = C / L.rolling(252).min() - 1
    F['dh20'] = C / H.rolling(20).max() - 1
    F['dh50'] = C / H.rolling(50).max() - 1
    for n in (10, 20, 50, 200):
        F[f'c_sma{n}'] = C / C.rolling(n).mean() - 1
    F['sma50_200'] = C.rolling(50).mean() / C.rolling(200).mean() - 1
    F['logp'] = np.log(C)
    F['vratio1_50'] = V / V.shift(1).rolling(50).mean()
    F['vratio5_50'] = V.rolling(5).mean() / V.shift(5).rolling(50).mean()
    dv = C * V
    F['logdv'] = np.log(dv.rolling(20).mean().replace(0, np.nan))
    F['amihud63'] = (r1.abs() / dv.replace(0, np.nan)).rolling(63).mean()
    obv = (np.sign(r1.fillna(0)) * V).cumsum()
    F['obv21'] = (obv - obv.shift(21)) / V.rolling(21).sum().replace(0, np.nan)
    F['gap'] = O / C.shift(1) - 1
    F['intraday'] = C / O - 1
    clv = ((C - L) - (H - C)) / (H - L).replace(0, np.nan)
    F['clv1'] = clv
    F['clv5'] = clv.rolling(5).mean()
    rng = H - L
    F['nr7'] = (rng <= rng.rolling(7).min()).astype(float).where(rng.notna())
    F['inside'] = ((H < H.shift(1)) & (L > L.shift(1))).astype(float).where(H.notna() & H.shift(1).notna())
    s = np.sign(r1.fillna(0).to_numpy())
    run = np.zeros_like(s)
    for t in range(1, len(s)):
        run[t] = np.where(s[t] * s[t - 1] > 0, run[t - 1] + s[t], s[t])
    F['run'] = pd.DataFrame(run, index=C.index, columns=C.columns)
    F['rev5_x_vol21'] = (-F['r5']) * F['vol21']
    F['mom126m21_x_lowvol'] = F['r126m21'] * (1 - F['vol63'].rank(axis=1, pct=True))
    return {k: v.replace([np.inf, -np.inf], np.nan) for k, v in F.items()}


def forward(O, h):
    Of = O.ffill(limit=30)
    return Of.shift(-(h + 1)) / Of.shift(-1) - 1


def row_ic(F, R):
    """Correlación de rangos (Spearman) por fila con máscara conjunta."""
    m = F.notna() & R.notna()
    Fr = F.where(m).rank(axis=1)
    Rr = R.where(m).rank(axis=1)
    a = Fr.sub(Fr.mean(axis=1), axis=0)
    b = Rr.sub(Rr.mean(axis=1), axis=0)
    den = np.sqrt((a ** 2).sum(axis=1) * (b ** 2).sum(axis=1))
    return ((a * b).sum(axis=1) / den.replace(0, np.nan)), m.sum(axis=1)


def decile_spread(F, R):
    m = F.notna() & R.notna()
    pr = F.where(m).rank(axis=1, pct=True)
    top = R.where(pr >= 0.9).mean(axis=1)
    bot = R.where(pr <= 0.1).mean(axis=1)
    return top - bot


def tstat(x):
    x = np.asarray(pd.Series(x).dropna(), float)
    n = len(x)
    if n < 20 or x.std(ddof=1) == 0:
        return n, float(np.nan), float(np.nan), float(np.nan)
    t = x.mean() / (x.std(ddof=1) / math.sqrt(n))
    return n, float(x.mean()), float(t), float(math.erfc(abs(t) / math.sqrt(2)))


def bh(pvals, q=0.05):
    """Benjamini-Hochberg: devuelve un vector booleano de rechazos."""
    p = np.asarray(pvals, float)
    ok = ~np.isnan(p)
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    m = len(order)
    rej = np.zeros(len(p), bool)
    k = 0
    for rank, i in enumerate(order, 1):
        if p[i] <= q * rank / m:
            k = rank
    for i in order[:k]:
        rej[i] = True
    return rej


def sample_rows(idx, h):
    return idx[::h]


def analyze(p, member, window, feats=None):
    C, O = p['close'], p['open']
    elig = member & vb.liquidity_member(p) & C.notna() & O.notna()
    feats = feats if feats is not None else features(p)
    rows = {}
    dates = C.index[(C.index >= pd.Timestamp(window[0])) & (C.index <= pd.Timestamp(window[1]))]
    for h in HORIZONS:
        R = forward(O, h).where(elig)
        samp = dates[::h]
        for name, F in feats.items():
            Fm = F.where(elig).loc[samp]
            Rm = R.loc[samp]
            ic, n_names = row_ic(Fm, Rm)
            ic = ic[n_names >= 50]
            n, mean_ic, t, pv = tstat(ic)
            sp = decile_spread(Fm, Rm)
            sp = sp[n_names >= 50]
            sign = 1.0 if (mean_ic or 0) >= 0 else -1.0
            net = (sign * sp - COST_ROUNDTRIP).dropna()
            rows[(name, h)] = {'n': n, 'ic': mean_ic, 't': t, 'p': pv, 'neto_por_rebalanceo': float(net.mean()) if len(net) else float('nan'),
                               'bruto_por_rebalanceo': float((sign * sp).mean()) if len(sp.dropna()) else float('nan')}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_scan.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    res = {}
    for name, start, end, win in (('A_2010_2020', '2007-01-01', '2020-12-31', ('2010-01-01', '2020-12-31')),
                                  ('B_1997_2009', '1996-01-01', '2009-12-31', ('1997-01-01', '2009-12-31'))):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        res[name] = analyze(p, member, win)
        res[name + '_universo'] = info['miembros_con_precio_por_dia']
        print(f'{name}: {len(res[name])} pruebas · {time.time()-t0:.0f}s', flush=True)
    keys = list(res['A_2010_2020'].keys())
    pa = [res['A_2010_2020'][k]['p'] for k in keys]
    rej_a = bh(pa, 0.05)
    cands, table = [], []
    for k, rj in zip(keys, rej_a):
        a_, b_ = res['A_2010_2020'][k], res['B_1997_2009'][k]
        same = (a_['ic'] is not None and b_['ic'] is not None and not np.isnan(a_['ic']) and not np.isnan(b_['ic']) and np.sign(a_['ic']) == np.sign(b_['ic']))
        rep = bool(same and b_['p'] < 0.05)
        eff = bool(abs(a_['ic']) >= MIN_IC and abs(b_['ic']) >= MIN_IC) if same else False
        net = bool(a_['neto_por_rebalanceo'] > 0 and b_['neto_por_rebalanceo'] > 0)
        row = {'variable': k[0], 'horizonte': k[1], 'A': a_, 'B': b_, 'BH_A': bool(rj), 'replica_B': rep, 'efecto_min': eff, 'neto_positivo_ambos': net}
        table.append(row)
        if rj and rep and eff and net:
            cands.append(row)
    n_tests = len(keys)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_ESCANEO_ANOMALIAS.md', 'datos': {'tag': a.tag, 'sha256': sha},
           'resumen': {'pruebas_por_periodo': n_tests, 'falsos_positivos_esperados_al_5pct_sin_corregir': round(0.05 * n_tests, 1),
                       'significativas_A_sin_corregir_p<0.05': int(sum(1 for x in pa if x == x and x < 0.05)), 'significativas_A_BH': int(rej_a.sum()),
                       'replican_en_B': int(sum(1 for r in table if r['BH_A'] and r['replica_B'])), 'candidatas_finales': len(cands)},
           'candidatas': cands, 'tabla_completa': table}
    print('RESUMEN_ESCANEO ' + json.dumps(out['resumen']) + ' CAND ' + json.dumps([(c['variable'], c['horizonte']) for c in cands]), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
