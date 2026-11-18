"""Karryman · H15: réplica parcial del screener (15 acciones, vender al dejar de aparecer) según docs/V24_H15_SCREENER.md. Investigación únicamente."""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_h5 as h5
import v24_hipotesis as vh
from v24_regimen import period_list
import v24_regimen as rg

K = 15
N_POS = 15
COST = 0.001
N_SEEDS = 10


def screen_matrices(p, member):
    """Matrices booleanas (fecha × valor): screener parcial, solo tendencia y liquidez. Solo datos hasta el cierre de cada sesión."""
    C, H, V = p['close'], p['high'], p['volume']
    Dv = p['dividends'] if 'dividends' in p else pd.DataFrame(0.0, index=C.index, columns=C.columns)
    ret = lambda n: C / C.shift(n) - 1
    sma = lambda n: C.rolling(n).mean()
    hi252 = H.rolling(252).max()
    vol50 = V.rolling(50).mean()
    nodiv = Dv.fillna(0.0).rolling(252, min_periods=252).sum() == 0
    base = member & (C >= 5) & (vol50 > 500_000)
    full = (base & (ret(63) > 0.10) & (ret(21) > 0.01) & (ret(126) > 0) & (ret(252) > 0.01) & (C > sma(20)) & (C > sma(50)) & (C > sma(200))
            & (C / hi252 - 1 > -0.15) & nodiv)
    trend = base & (C > sma(200))
    liquid = member & (C >= 5) & (vol50 > 500_000)
    f = lambda m: m.fillna(False).to_numpy(bool) & C.notna().to_numpy()
    return {'screener_parcial': f(full), 'solo_tendencia': f(trend), 'liquidas': f(liquid)}


def _liquidate_gone(sh, cash, o, px_c):
    gone = (sh > 0) & np.isnan(o)
    if gone.any():
        cash += float((sh[gone] * px_c[gone]).sum())
        sh[gone] = 0.0
    return cash


def simulate_screen(O, C, passes, n_pos=N_POS, cost=COST, seed=1):
    """Salir de lo que deja de cumplir y comprar al azar entre las que cumplen hasta n_pos; ejecución a la apertura siguiente."""
    rng = np.random.default_rng(seed)
    O, C = np.asarray(O, float), np.asarray(C, float)
    T, N = C.shape
    sh = np.zeros(N)
    cash = 1.0
    last = np.where(np.isnan(C[0]), 0.0, C[0])
    eq = np.full(T, np.nan)
    held_counts, buys_n, sells_n = [], 0, 0
    for t in range(T):
        px_c = np.where(np.isnan(C[t]), last, C[t])
        last = px_c
        eq[t] = cash + float((sh * px_c).sum())
        held_counts.append(int((sh > 0).sum()))
        if t >= T - 1:
            break
        o = O[t + 1]
        cash = _liquidate_gone(sh, cash, o, px_c)
        out = (sh > 0) & ~passes[t] & ~np.isnan(o)
        if out.any():
            cash += float((sh[out] * o[out]).sum()) * (1 - cost)
            sells_n += int(out.sum())
            sh[out] = 0.0
        held = sh > 0
        slots = n_pos - int(held.sum())
        if slots > 0:
            cand = np.where(passes[t] & ~held & ~np.isnan(o))[0]
            if len(cand):
                pick = rng.permutation(cand)[:slots]
                eq_open = cash + float((sh * np.where(np.isnan(o), px_c, o)).sum())
                target = eq_open / n_pos
                for j in pick:
                    amt = min(target, cash / (1 + cost))
                    if amt <= 0:
                        break
                    q = amt / o[j]
                    sh[j] = q
                    cash -= q * o[j] * (1 + cost)
                    buys_n += 1
    return pd.Series(eq), {'compras': buys_n, 'ventas': sells_n, 'posiciones_medias': float(np.mean(held_counts)), 'efectivo_final': float(cash)}


def simulate_random_monthly(O, C, liquid, n_pos=N_POS, cost=COST, seed=1, every=21):
    """Control: 15 valores líquidos al azar, recompuestos por completo cada `every` sesiones."""
    rng = np.random.default_rng(seed)
    O, C = np.asarray(O, float), np.asarray(C, float)
    T, N = C.shape
    sh = np.zeros(N)
    cash = 1.0
    last = np.where(np.isnan(C[0]), 0.0, C[0])
    eq = np.full(T, np.nan)
    for t in range(T):
        px_c = np.where(np.isnan(C[t]), last, C[t])
        last = px_c
        eq[t] = cash + float((sh * px_c).sum())
        if t >= T - 1:
            break
        o = O[t + 1]
        cash = _liquidate_gone(sh, cash, o, px_c)
        if t % every == 0:
            sell = (sh > 0) & ~np.isnan(o)
            cash += float((sh[sell] * o[sell]).sum()) * (1 - cost)
            sh[sell] = 0.0
            cand = np.where(liquid[t] & ~np.isnan(o))[0]
            if len(cand):
                pick = rng.permutation(cand)[:n_pos]
                target = cash / len(pick) if len(pick) else 0
                eq_open = cash
                for j in pick:
                    amt = min(eq_open / n_pos, cash / (1 + cost))
                    if amt <= 0:
                        break
                    q = amt / o[j]
                    sh[j] = q
                    cash -= q * o[j] * (1 + cost)
    return pd.Series(eq)


def run_period(p, member, bench, segs, level, n_seeds=N_SEEDS):
    O, C = p['open'], p['close']
    mats = screen_matrices(p, member)
    idx = C.index
    full = (segs[0][1][0], segs[-1][1][1])
    wins = segs + [('todo', full)]
    res = {'umbral': {k: float(v.sum(axis=1).mean()) for k, v in mats.items()}}
    series = {}
    stats = {}
    for name in ('screener_parcial', 'solo_tendencia'):
        eqs = []
        for sd in range(1, n_seeds + 1):
            e, st = simulate_screen(O.to_numpy(), C.to_numpy(), mats[name], seed=sd)
            e.index = idx
            eqs.append(e)
            stats.setdefault(name, []).append(st)
        series[name] = eqs
    series['azar_mensual'] = []
    for sd in range(1, n_seeds + 1):
        e = simulate_random_monthly(O.to_numpy(), C.to_numpy(), mats['liquidas'], seed=sd)
        e.index = idx
        series['azar_mensual'].append(e)
    spy = bench[(bench.index >= pd.Timestamp(full[0])) & (bench.index <= pd.Timestamp(full[1]))]
    r_ = C.pct_change(fill_method=None)
    w_ = member.shift(1, fill_value=False) & r_.notna()
    ew = (1 + r_.where(w_).mean(axis=1).fillna(0.0)).cumprod()
    ew = ew.loc[ew.index >= pd.Timestamp(full[0])]
    sl = lambda s, w: h5.sl(s.loc[full[0]:full[1]], w)
    res['spy'] = {k: h5.curve(h5.sl(spy, w)) for k, w in wins}
    res['igualponderada_miembros'] = {k: h5.curve(h5.sl(ew, w)) for k, w in wins}
    for name, eqs in series.items():
        res[name] = {'cagr_medio_por_tramo': {k: round(float(np.mean([h5.curve(sl(e, w))['cagr_pct'] for e in eqs])), 2) for k, w in wins},
                     'cagr_rango_por_tramo': {k: [round(float(min(h5.curve(sl(e, w))['cagr_pct'] for e in eqs)), 2), round(float(max(h5.curve(sl(e, w))['cagr_pct'] for e in eqs)), 2)] for k, w in wins},
                     'caida_max_media': {k: round(float(np.mean([h5.curve(sl(e, w))['max_dd_pct'] for e in eqs])), 2) for k, w in wins},
                     'sharpe_medio': {k: round(float(np.mean([h5.curve(sl(e, w))['sharpe'] for e in eqs])), 3) for k, w in wins}}
        if name in stats:
            res[name]['mecanica_media'] = {k: round(float(np.mean([s[k] for s in stats[name]])), 1) for k in ('compras', 'ventas', 'posiciones_medias')}
    # R1: media de semillas frente a SPY, IC de la diferencia mensual
    m_seed = pd.concat([vh.monthly(sl(e, full)) for e in series['screener_parcial']], axis=1).mean(axis=1)
    m_spy = vh.monthly(spy)
    diff = (m_seed - m_spy).dropna()
    lo, hi, mean = vh.boot_ci(diff, level)
    sp, ss = res['screener_parcial'], res['spy']['todo']
    r1 = bool(sp['cagr_medio_por_tramo']['todo'] > ss['cagr_pct'] and lo > 0 and sp['sharpe_medio']['todo'] >= ss['sharpe'])
    r2 = bool(all(sp['cagr_medio_por_tramo'][k] > res['solo_tendencia']['cagr_medio_por_tramo'][k] and sp['cagr_medio_por_tramo'][k] > res['azar_mensual']['cagr_medio_por_tramo'][k] for k, _ in segs))
    res['criterios'] = {'R1_supera_a_spy': {'cagr_screener': sp['cagr_medio_por_tramo']['todo'], 'cagr_spy': ss['cagr_pct'], 'dif_mensual_media': mean, 'ic': [lo, hi], 'nivel': level, 'pasa': r1},
                        'R2_mejor_que_solo_tendencia_y_azar_en_cada_tramo': r2, 'supera_al_sp500': bool(r1 and r2), 'mejor_que_azar_y_tendencia_pero_no_supera': bool(r2 and not r1)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_screener.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'regimen': rg.ACTIVE, 'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H15_SCREENER.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in period_list((
            ('A_2010_2020', '2007-01-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1996-01-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 0.95)), K):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al cierre cargados'
        res = run_period(p, member, bench, segs, level)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']['supera_al_sp500']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    out['veredicto'] = {'supera_al_sp500': bool(all(flags.values())), 'por_periodo': flags}
    print('RESUMEN_H15 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
