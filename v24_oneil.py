"""Karryman · contraste de H10 (sistema tipo O'Neil, parte técnica de CAN SLIM) según docs/V24_H10_ONEIL.md. Investigación únicamente.
Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
import argparse
import json
import os
import time

import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_h7 as h7

K = 10
CFG = sb.Config(name='H10_oneil', entry='base', breakout=False, pullback=False, template=False, near_high=0.85, rs_min=-1000.0, rs_rank_min=80.0,
                min_base_weeks=5, max_base_depth=0.33, min_prior_advance=0.30, max_tight=0.12, vol_breakout=1.5, max_chase=0.05, max_risk=0.12,
                oneil_bases=True, fixed_stop=True, stop_pct=0.08, tp_pct=0.25, eight_week=True, partial_r=0.0, partial_frac=0.0, be_after_partial=False,
                trail='none', regime='spy_ma50', placebo=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_oneil.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H10_ONEIL.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in (
            ('A_2010_2020', '2007-01-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1996-01-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 0.95)):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        prepared, regime = h7.prepare_all(p, member, bench)
        print(f'{name}: {len(prepared)} series preparadas · {time.time()-t0:.0f}s', flush=True)
        res = h7.run_period(prepared, regime, bench, segs, level, name, cfg=CFG)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    cand = all(flags[k]['periodo_pasa_N_Q1_Q2'] for k in flags)
    out['veredicto'] = {'candidata': bool(cand), 'supera_al_indice': bool(cand and all(flags[k]['Q3_y_riesgo'] for k in flags))}
    print('RESUMEN_H10 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
