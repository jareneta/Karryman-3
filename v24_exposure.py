"""Karryman · H16, regla de exposición al mercado según docs/V24_H16_EXPOSICION_MERCADO.md.
Investigación únicamente. En régimen legacy 2021-2026 permanece bloqueado."""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_h5 as h5
import v24_hipotesis as vh
import v24_regimen as rg
from v24_regimen import period_list

K = 16
FEE = 0.001
N_SHIFT = 2000
IND = ('tend200', 'tend50', 'amp200', 'amp50', 'caida10', 'vol25')


def indicators(spy, close, member):
    """Seis indicadores booleanos al cierre de cada día (solo datos hasta ese día)."""
    sma200, sma50 = spy.rolling(200).mean(), spy.rolling(50).mean()
    ok = lambda s: s.fillna(False).astype(bool)
    out = {'tend200': ok(spy > sma200), 'tend50': ok(spy > sma50)}
    for n, k in ((200, 'amp200'), (50, 'amp50')):
        m = member.reindex(index=close.index, columns=close.columns).fillna(False)
        ma = close.rolling(n).mean()
        valid = m & ma.notna() & close.notna()
        share = ((close > ma) & valid).sum(axis=1) / valid.sum(axis=1).replace(0, np.nan)
        out[k] = ok((share >= 0.5).reindex(spy.index))
    out['caida10'] = ok(spy / spy.rolling(252, min_periods=200).max() - 1 > -0.10)
    vol = spy.pct_change().rolling(20).std() * np.sqrt(252)
    out['vol25'] = ok(vol < 0.25)
    return pd.DataFrame(out).reindex(spy.index)[list(IND)]


def exposure(ind, mode='primaria'):
    score = ind.sum(axis=1)
    if mode == 'primaria':
        return pd.Series(np.where(score >= 5, 1.0, np.where(score >= 3, 0.5, 0.0)), index=ind.index)
    if mode == 'dos_estados':
        return pd.Series(np.where(score >= 3, 1.0, 0.0), index=ind.index)
    return ind[mode].astype(float)


def equity(spy, expo, fee=FEE, cash_rate=0.0):
    """Exposición decidida al cierre de t, aplicada a la rentabilidad de t+1 a t+2 (un día de retraso)."""
    r = spy.pct_change().fillna(0.0)
    e = expo.shift(2).fillna(0.0)                                  # señal al cierre de t, se opera al cierre de t+1, rinde r[t+2]
    cash = (1 + cash_rate) ** (1 / 252) - 1
    net = e * r + (1 - e) * cash - fee * e.diff().abs().fillna(e.abs())
    return (1 + net).cumprod()


def sharpe(r):
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0


def placebo_p(spy, expo, w, rng, n=N_SHIFT):
    """P-valor: fracción de desplazamientos circulares aleatorios (≥ 63 sesiones) con Sharpe ≥ el de la regla."""
    ex = expo.loc[w[0]:w[1]]
    base = equity(spy, expo).loc[w[0]:w[1]].pct_change().dropna()
    s0, L = sharpe(base), len(ex)
    cnt = 0
    for _ in range(n):
        k = int(rng.integers(63, max(64, L - 63)))
        sh = pd.Series(np.roll(ex.to_numpy(), k), index=ex.index)
        full = expo.copy()
        full.loc[ex.index] = sh
        if sharpe(equity(spy, full).loc[w[0]:w[1]].pct_change().dropna()) >= s0:
            cnt += 1
    return (cnt + 1) / (n + 1)


def run_period(spy, close, member, segs, level, sens=True, n_shift=N_SHIFT):
    full = (segs[0][1][0], segs[-1][1][1])
    wins = segs + [('todo', full)]
    ind = indicators(spy, close, member)
    expo = exposure(ind)
    eq = equity(spy, expo)
    spy_eq = (1 + spy.pct_change().fillna(0.0)).cumprod()
    res = {'regla': {k: h5.curve(h5.sl(eq, w)) for k, w in wins}, 'spy': {k: h5.curve(h5.sl(spy_eq, w)) for k, w in wins},
           'exposicion_media_pct': {k: round(float(expo.loc[w[0]:w[1]].mean() * 100), 1) for k, w in wins},
           'dias_exposicion': {k: {str(v): int((expo.loc[w[0]:w[1]] == v).sum()) for v in (0.0, 0.5, 1.0)} for k, w in wins}}
    mix = {}
    for k, w in wins:
        m = float(expo.loc[w[0]:w[1]].mean())
        mix[k] = h5.curve(h5.sl(equity(spy, pd.Series(m, index=spy.index), fee=0.0), w))
    res['mezcla_constante'] = mix
    rng = np.random.default_rng(7)
    p = placebo_p(spy, expo, (full[0], full[1]), rng, n_shift)
    res['placebo_p_valor_todo'] = round(p, 4)
    diff = (vh.monthly(eq.loc[full[0]:full[1]]) - vh.monthly(spy_eq.loc[full[0]:full[1]])).dropna()
    lo, hi, mean = vh.boot_ci(diff, level)
    R, S, M = res['regla'], res['spy'], res['mezcla_constante']
    r1 = bool(all(R[k]['cagr_pct'] > S[k]['cagr_pct'] for k, _ in wins) and lo > 0)
    r2 = bool(all(R[k]['max_dd_pct'] > S[k]['max_dd_pct'] for k, _ in wins) and R['todo']['sharpe'] >= S['todo']['sharpe'])
    r3 = bool(all(R[k]['sharpe'] > M[k]['sharpe'] for k, _ in wins) and p < 0.05 / K)
    res['criterios'] = {'R1_supera_en_rentabilidad': {'pasa': r1, 'exceso_mensual_medio': mean, 'ic': [lo, hi], 'nivel': level},
                        'R2_reduce_riesgo': r2, 'R3_el_momento_aporta': r3, 'util_como_control_de_riesgo': bool(r2 and r3),
                        'supera_al_sp500': bool(r1 and r2 and r3)}
    if sens:
        sv = {}
        for name in IND + ('dos_estados',):
            e = equity(spy, exposure(ind, name))
            sv[name] = {k: h5.curve(h5.sl(e, w)) for k, w in wins}
        sv['coste_0.20pct'] = {k: h5.curve(h5.sl(equity(spy, expo, fee=0.002), w)) for k, w in wins}
        sv['efectivo_2pct'] = {k: h5.curve(h5.sl(equity(spy, expo, cash_rate=0.02), w)) for k, w in wins}
        res['sensibilidades_no_deciden'] = sv
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_exposure.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'regimen': rg.ACTIVE, 'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H16_EXPOSICION_MERCADO.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in period_list((
            ('A_2010_2020', '2008-06-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1995-06-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 1 - 0.05 / K)), K):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        res = run_period(bench.dropna(), p['close'], member, segs, level)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']['util_como_control_de_riesgo']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    out['veredicto'] = {'util_como_control_de_riesgo': bool(all(flags.values())),
                        'supera_al_sp500': bool(all(out[n]['criterios']['supera_al_sp500'] for n in flags)), 'por_periodo': flags}
    print('RESUMEN_H16 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
