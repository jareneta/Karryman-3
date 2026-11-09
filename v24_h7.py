"""Karryman · contraste de H7 (sistema tipo Minervini) según docs/V24_H7_MINERVINI.md. Investigación únicamente.
Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
import argparse
import json
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_h5 as h5

N_PLACEBO = 10
K = 7
CFG = sb.Config(name='H7_minervini', breakout=True, pullback=False, entry='base', template=True, near_high=0.75, rs_min=-1000.0, rs_rank_min=70.0,
                min_base_weeks=5, max_base_depth=0.35, min_prior_advance=0.30, max_tight=0.12, vol_breakout=1.4, max_chase=0.05,
                max_risk=0.12, stop_pct=0.08, partial_r=3.0, partial_frac=1 / 3, be_after_partial=True, trail='ma50', regime='none')


def rs_rank_members(prepared, member, index):
    """Rango RS tipo IBD (40 % 3m + 20 % 6, 9 y 12 meses) en percentil entre los valores líquidos QUE SON MIEMBROS ese día."""
    def score(c):
        r = lambda n: c / c.shift(n) - 1
        return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)
    sc = pd.DataFrame({t: score(d.Close) for t, d in prepared.items()}).reindex(index)
    liq = pd.DataFrame({t: (d.Close >= 5) & (d.vol50 >= 300_000) for t, d in prepared.items()}).reindex(index).fillna(False)
    mem = member.reindex(index=index, columns=list(prepared)).fillna(False).astype(bool)
    rank = sc.where(liq & mem).rank(axis=1, pct=True) * 100
    for t, d in prepared.items():
        d['rs_rank'] = rank[t].reindex(d.index)


def prepare_all(p, member, bench):
    fr = h5.frames_from_wide(p, member, list(p['close'].columns))
    spy = pd.DataFrame({'Close': bench}).dropna()
    regime = sb.regime_series(spy)
    prepared = {}
    for t, (f, m) in fr.items():
        d = sb.prepare(f, spy.Close)
        d['member'] = m.reindex(d.index).fillna(False).astype(bool)
        prepared[t] = d
    rs_rank_members(prepared, member, p['close'].index)
    return prepared, regime


def run_period(prepared, regime, bench, segs, level_diff, tag, cfg=None):
    cfg = cfg or CFG
    full = (segs[0][1][0], segs[-1][1][1])
    tr = h5.in_win(sb.simulate_independent(prepared, cfg, regime), full)
    plc = pd.concat([h5.in_win(sb.simulate_independent(prepared, replace(cfg, placebo=True, name=f'p{s}'), regime, seed=s), full) for s in range(1, N_PLACEBO + 1)])
    res = {'operaciones': {k: h5.rstats(h5.in_win(tr, w).r) for k, w in segs + [('todo', full)]},
           'placebo_agrupado': {k: h5.rstats(h5.in_win(plc, w).r) for k, w in segs + [('todo', full)]}}
    n_ok = len(tr) >= 300
    todo = res['operaciones']['todo']
    q1 = bool(n_ok and todo.get('ci95_R', [0, 0])[0] > 0 and all(res['operaciones'][k].get('expectancy_R', 0) > 0 for k, _ in segs))
    rg = np.random.default_rng(5)
    if len(tr) and len(plc):
        dd = rg.choice(tr.r.values, size=(h5.BOOT, len(tr)), replace=True).mean(axis=1) - rg.choice(plc.r.values, size=(h5.BOOT, len(plc)), replace=True).mean(axis=1)
        al = (1 - level_diff) / 2 * 100
        lo, hi, mean = float(np.percentile(dd, al)), float(np.percentile(dd, 100 - al)), float(tr.r.mean() - plc.r.mean())
    else:
        lo, hi, mean = float('nan'), float('nan'), float('nan')
    start, end = pd.Timestamp(full[0]), pd.Timestamp(full[1])
    eq, ntr = sb.simulate_portfolio(prepared, cfg, regime, start, end)
    peq = [sb.simulate_portfolio(prepared, replace(cfg, placebo=True), regime, start, end, seed=s)[0] for s in range(1, N_PLACEBO + 1)]
    spyc = bench[(bench.index >= start) & (bench.index <= end)]
    wins = segs + [('todo', full)]
    res['cartera'] = {'h7': {k: h5.curve(h5.sl(eq, w)) for k, w in wins}, 'spy': {k: h5.curve(h5.sl(spyc, w)) for k, w in wins},
                      'placebo_cagr_mediana': {k: round(float(np.median([h5.curve(h5.sl(e, w))['cagr_pct'] for e in peq])), 2) for k, w in wins},
                      'operaciones_cartera': ntr}
    q3 = all(res['cartera']['h7'][k]['cagr_pct'] > res['cartera']['placebo_cagr_mediana'][k] for k, _ in segs)
    h, s_ = res['cartera']['h7']['todo'], res['cartera']['spy']['todo']
    idx = (h['sharpe'] >= s_['sharpe']) or ((h.get('calmar') or 0) >= (s_.get('calmar') or 0) and h['cagr_pct'] >= 0.8 * s_['cagr_pct'])
    res['criterios'] = {'N_ge_300': bool(n_ok), 'Q1_esperanza_R_positiva': q1,
                        'Q2_diferencia_vs_placebo': {'nivel_exigido': level_diff, 'low': lo, 'high': hi, 'media': mean, 'pasa': bool(lo > 0)},
                        'Q3_cartera_sobre_mediana_placebo': bool(q3), 'riesgo_retorno_vs_spy': bool(idx),
                        'periodo_pasa_N_Q1_Q2': bool(n_ok and q1 and lo > 0), 'Q3_y_riesgo': bool(q3 and idx)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_h7.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H7_MINERVINI.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in (
            ('A_2010_2020', '2007-01-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1996-01-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 0.95)):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        prepared, regime = prepare_all(p, member, bench)
        print(f'{name}: {len(prepared)} series preparadas · {time.time()-t0:.0f}s', flush=True)
        res = run_period(prepared, regime, bench, segs, level, name)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    cand = all(flags[k]['periodo_pasa_N_Q1_Q2'] for k in flags)
    out['veredicto'] = {'candidata': bool(cand), 'supera_al_indice': bool(cand and all(flags[k]['Q3_y_riesgo'] for k in flags))}
    print('RESUMEN_H7 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
