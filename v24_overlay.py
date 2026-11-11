"""Karryman · contraste de H11 (SPY como base + comprar caídas como complemento) según docs/V24_H11_SPY_MAS_CAIDAS.md.
Investigación únicamente. Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
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
import v24_h5 as h5
import v24_h7 as h7
import v24_hipotesis as vh

K = 11
N_PLACEBO = 10


def sim(prepared, regime, bench, cfg, start, end, seed=7, risk=0.01, total=0.06):
    eq, n = sb.simulate_portfolio(prepared, cfg, regime, start, end, seed=seed, risk_pct=risk, total_risk=total, spy_close=bench, sweep=True)
    return eq, n


def run_period(prepared, regime, bench, segs, level, sens=True, cfg=None, n_placebo=N_PLACEBO):
    cfg = cfg or dip.CFG
    full = (segs[0][1][0], segs[-1][1][1])
    start, end = pd.Timestamp(full[0]), pd.Timestamp(full[1])
    wins = segs + [('todo', full)]
    eq, ntr = sim(prepared, regime, bench, cfg, start, end)
    peq = [sim(prepared, regime, bench, replace(cfg, placebo=True), start, end, seed=s)[0] for s in range(1, n_placebo + 1)]
    spy = bench[(bench.index >= start) & (bench.index <= end)]
    res = {'h11': {k: h5.curve(h5.sl(eq, w)) for k, w in wins}, 'spy': {k: h5.curve(h5.sl(spy, w)) for k, w in wins},
           'placebo_cagr_mediana': {k: round(float(np.median([h5.curve(h5.sl(e, w))['cagr_pct'] for e in peq])), 2) for k, w in wins},
           'placebo_cagr_rango': {k: [round(float(min(h5.curve(h5.sl(e, w))['cagr_pct'] for e in peq)), 2), round(float(max(h5.curve(h5.sl(e, w))['cagr_pct'] for e in peq)), 2)] for k, w in wins},
           'operaciones_complemento': ntr}
    m1, m2 = vh.monthly(eq), vh.monthly(spy)
    diff = (m1 - m2).dropna()
    lo, hi, mean = vh.boot_ci(diff, level)
    h, s = res['h11']['todo'], res['spy']['todo']
    e1 = bool(h['cagr_pct'] > s['cagr_pct'] and lo > 0)
    e2 = bool(all(res['h11'][k]['cagr_pct'] > res['placebo_cagr_mediana'][k] for k, _ in segs))
    e3 = bool(h['sharpe'] >= s['sharpe'] and h['max_dd_pct'] >= s['max_dd_pct'])
    res['criterios'] = {'E1_supera_al_sp500': {'cagr_h11': float(h['cagr_pct']), 'cagr_spy': float(s['cagr_pct']), 'exceso_mensual_medio': mean, 'ic': [lo, hi], 'nivel': level, 'pasa': e1},
                        'E2_mejor_que_placebo_en_cada_tramo': e2, 'E3_sharpe_y_caida_no_peores': e3, 'periodo_pasa': bool(e1 and e2 and e3)}
    if sens:
        sv = {}
        old = sb.COST
        try:
            for c in (0.002, 0.003):
                sb.COST = c
                e, _ = sim(prepared, regime, bench, cfg, start, end)
                sv[f'coste_{c*100:.1f}pct_por_lado'] = {'h11': h5.curve(h5.sl(e, full)), 'exceso_cagr_vs_spy': round(float(h5.curve(h5.sl(e, full))['cagr_pct'] - s['cagr_pct']), 2)}
        finally:
            sb.COST = old
        for r, t in ((0.02, 0.12), (0.03, 0.18)):
            e, _ = sim(prepared, regime, bench, cfg, start, end, risk=r, total=t)
            sv[f'riesgo_{int(r*100)}pct'] = {'h11': h5.curve(h5.sl(e, full)), 'exceso_cagr_vs_spy': round(float(h5.curve(h5.sl(e, full))['cagr_pct'] - s['cagr_pct']), 2)}
        res['sensibilidades_no_deciden'] = sv
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_overlay.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H11_SPY_MAS_CAIDAS.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in (
            ('A_2010_2020', '2007-01-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1996-01-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 0.95)):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        prepared, regime = h7.prepare_all(p, member, bench)
        print(f'{name}: {len(prepared)} series preparadas · {time.time()-t0:.0f}s', flush=True)
        res = run_period(prepared, regime, bench, segs, level)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']['periodo_pasa']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    out['veredicto'] = {'supera_al_sp500': bool(all(flags.values())), 'por_periodo': flags}
    print('RESUMEN_H11 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
