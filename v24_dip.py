"""Karryman · contraste de H9b (comprar caídas en el S&P 500) según docs/V24_H9B_CAIDAS_SP500.md. Investigación únicamente.
Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
import argparse
import glob
import json
import os
import time

import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_h5 as h5
import v24_h7 as h7

K = 9
CFG = sb.Config(name='H9b_caidas', entry='dip', breakout=False, pullback=False, template=False, near_high=0.0, rs_min=-1000.0, rs_rank_min=0.0,
                max_chase=0.05, max_risk=0.13, stop_pct=0.12, partial_r=0.0, partial_frac=0.0, be_after_partial=False, trail='none',
                exit_above_sma20=True, max_hold=20, regime='none', placebo=False)


def tech_map():
    fs = sorted(glob.glob('results/v24/v24_sic_*.json'))
    if not fs:
        return None
    return {k: bool(v.get('tech')) for k, v in json.load(open(fs[-1])).get('mapa', {}).items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_dip.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    tm = tech_map()
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H9B_CAIDAS_SP500.md', 'datos': {'tag': a.tag, 'sha256': sha}}
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
        if tm is not None:   # descriptivo (sesgado: la clasificación de deslistadas es incompleta); no decide nada
            full = (segs[0][1][0], segs[-1][1][1])
            tr = h5.in_win(sb.simulate_independent(prepared, CFG, regime), full)
            tr = tr.assign(tech=tr.ticker.map(lambda t: tm.get(t)))
            res['descriptivo_tecnologicas_sesgado'] = {'tecnologicas_clasificadas': h5.rstats(tr[tr.tech == True].r), 'resto_o_sin_clasificar': h5.rstats(tr[tr.tech != True].r)}
        out[name] = res
        flags[name] = res['criterios']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    cand = all(flags[k]['periodo_pasa_N_Q1_Q2'] for k in flags)
    out['veredicto'] = {'candidata': bool(cand), 'supera_al_indice': bool(cand and all(flags[k]['Q3_y_riesgo'] for k in flags))}
    print('RESUMEN_H9B ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
