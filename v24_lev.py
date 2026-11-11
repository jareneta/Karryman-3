"""Karryman · contraste de H12 (S&P 500 2x con filtro de tendencia) según docs/V24_H12_INDICE_APALANCADO.md.
Investigación únicamente. Prueba final 2021-2026 bloqueada: los datos posteriores a 2020-12-31 no se usan."""
import argparse
import json
import os

import pandas as pd

import index_leverage as il
import v24_h5 as h5
import v24_hipotesis as vh

K = 12
LOCK_END = '2020-12-31'
PERIODS = {'P1_1960_1989': ('1960-01-01', '1989-12-31'), 'P2_1990_2009': ('1990-01-01', '2009-12-31'), 'P3_2010_2020': ('2010-01-01', LOCK_END)}
FULL = ('1960-01-01', LOCK_END)


def run_all(px, rate):
    px = px[px.index <= pd.Timestamp(LOCK_END)]
    rate = rate.reindex(px.index).ffill()
    eqs = {'B_1x_comprar_y_mantener': il.simulate(px, rate, 1, None), 'S_2x_filtro_MA200': il.simulate(px, rate, 2, 'ma200'),
           'sens_2x_sin_filtro': il.simulate(px, rate, 2, None), 'sens_3x_filtro_MA200': il.simulate(px, rate, 3, 'ma200'),
           'sens_2x_filtro_10_meses': il.simulate(px, rate, 2, 'ma10m'), 'sens_1x_filtro_MA200': il.simulate(px, rate, 1, 'ma200')}
    wins = {**PERIODS, 'todo_1960_2020': FULL}
    out = {'ultimo_dia_usado': str(px.index.max().date()), 'metricas': {n: {k: h5.curve(h5.sl(e, w)) for k, w in wins.items()} for n, e in eqs.items()}}
    level = 1 - 0.05 / K
    s, b = eqs['S_2x_filtro_MA200'], eqs['B_1x_comprar_y_mantener']
    diff = (vh.monthly(s.loc[FULL[0]:FULL[1]]) - vh.monthly(b.loc[FULL[0]:FULL[1]])).dropna()
    lo, hi, mean = vh.boot_ci(diff, level)
    m, bm = out['metricas']['S_2x_filtro_MA200'], out['metricas']['B_1x_comprar_y_mantener']
    l1 = all(m[k]['cagr_pct'] > bm[k]['cagr_pct'] for k in PERIODS)
    l2 = bool(lo > 0)
    l3 = bool(m['todo_1960_2020']['sharpe'] >= bm['todo_1960_2020']['sharpe'])
    l4 = bool(m['todo_1960_2020']['max_dd_pct'] >= bm['todo_1960_2020']['max_dd_pct'])
    out['criterios'] = {'L1_cagr_mayor_en_los_tres_periodos': bool(l1), 'L2_ic_exceso_mensual': {'nivel': level, 'low': lo, 'high': hi, 'media': mean, 'pasa': l2},
                        'L3_sharpe_no_peor': l3, 'L4_caida_maxima_no_peor': l4,
                        'caida_maxima_por_periodo': {k: {'S': m[k]['max_dd_pct'], 'B': bm[k]['max_dd_pct']} for k in {**PERIODS, 'todo_1960_2020': FULL}},
                        'supera_al_sp500': bool(l1 and l2 and l3 and l4), 'rinde_mas_pero_con_mas_riesgo': bool(l1 and l2 and l3 and not l4)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='data/v24_lev.json')
    a = ap.parse_args()
    px, rate = il.load()
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H12_INDICE_APALANCADO.md', **run_all(px, rate)}
    print('RESUMEN_H12 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
