"""Karryman · contraste de H14 ("no pelees contra la Fed": S&P 500 solo si los tipos a corto plazo no se endurecen) según docs/V24_H14_LIQUIDEZ_FED.md.
Investigación únicamente. Prueba final 2021-2026 bloqueada: los datos posteriores a 2020-12-31 no se usan."""
import argparse
import json
import os

import numpy as np
import pandas as pd

import index_leverage as il
import v24_h5 as h5
import v24_hipotesis as vh

K = 14
LOCK_END = '2020-12-31'
PERIODS = {'P1_1961_1989': ('1961-01-01', '1989-12-31'), 'P2_1990_2009': ('1990-01-01', '2009-12-31'), 'P3_2010_2020': ('2010-01-01', LOCK_END)}
FULL = ('1961-01-01', LOCK_END)
SWITCH_COST = 0.001


def tightening(rate, lookback=126, thr=0.005):
    """Régimen de endurecimiento: el rendimiento a 3 meses ha subido más de `thr` (decimal) frente a hace `lookback` sesiones."""
    return (rate - rate.shift(lookback)) > thr


def simulate_on(px, rate, on):
    """1x en el índice cuando `on` (señal al cierre, ejecución al día siguiente); si no, letras del Tesoro."""
    ret = px.pct_change().fillna(0) + il.DIV_YIELD / 252
    cash_r = rate / 252
    on = on.reindex(px.index).fillna(False).astype(bool).shift(1).fillna(False)
    strat = ret.where(on, cash_r) - on.astype(int).diff().abs().fillna(0) * SWITCH_COST
    return (1 + strat).cumprod()


def run_all(px, rate, tnx=None):
    px = px[px.index <= pd.Timestamp(LOCK_END)]
    rate = rate.reindex(px.index).ffill()
    eqs = {'B_1x_comprar_y_mantener': il.simulate(px, rate, 1, None), 'S_no_pelees_contra_la_Fed': simulate_on(px, rate, ~tightening(rate))}
    sens = {}
    for thr in (0.0025, 0.01):
        sens[f'sens_umbral_{thr*100:.2f}pp'] = simulate_on(px, rate, ~tightening(rate, 126, thr))
    for lb in (63, 252):
        sens[f'sens_ventana_{lb}'] = simulate_on(px, rate, ~tightening(rate, lb, 0.005))
    ma200 = px > px.rolling(200).mean()
    sens['sens_solo_MA200'] = simulate_on(px, rate, ma200)
    sens['sens_liquidez_y_MA200'] = simulate_on(px, rate, (~tightening(rate)) & ma200)
    if tnx is not None:
        t = tnx.reindex(px.index).ffill() / 100
        sens['sens_curva_10a_menos_3m_positiva'] = simulate_on(px, rate, (t - rate) > 0)
    eqs.update(sens)
    wins = {**PERIODS, 'todo_1961_2020': FULL}
    out = {'ultimo_dia_usado': str(px.index.max().date()), 'metricas': {n: {k: h5.curve(h5.sl(e, w)) for k, w in wins.items()} for n, e in eqs.items()},
           'dias_en_regimen_de_endurecimiento_pct': round(float(tightening(rate).loc[FULL[0]:FULL[1]].mean() * 100), 1)}
    level = 1 - 0.05 / K
    s, b = eqs['S_no_pelees_contra_la_Fed'], eqs['B_1x_comprar_y_mantener']
    diff = (vh.monthly(s.loc[FULL[0]:FULL[1]]) - vh.monthly(b.loc[FULL[0]:FULL[1]])).dropna()
    lo, hi, mean = vh.boot_ci(diff, level)
    m, bm = out['metricas']['S_no_pelees_contra_la_Fed'], out['metricas']['B_1x_comprar_y_mantener']
    m1 = bool(all(m[k]['cagr_pct'] > bm[k]['cagr_pct'] for k in PERIODS))
    m2 = bool(lo > 0)
    m3 = bool(m['todo_1961_2020']['sharpe'] >= bm['todo_1961_2020']['sharpe'])
    m4 = bool(m['todo_1961_2020']['max_dd_pct'] >= bm['todo_1961_2020']['max_dd_pct'])
    out['criterios'] = {'M1_cagr_mayor_en_los_tres_periodos': m1, 'M2_ic_exceso_mensual': {'nivel': level, 'low': lo, 'high': hi, 'media': mean, 'pasa': m2},
                        'M3_sharpe_no_peor': m3, 'M4_caida_maxima_no_peor': m4,
                        'supera_al_sp500': bool(m1 and m2 and m3 and m4), 'reduce_riesgo_sin_superar_en_rentabilidad': bool((not (m1 and m2)) and m3 and m4)}
    return out


def load_tnx():
    try:
        import yfinance as yf
        x = yf.download('^TNX', start='1959-01-01', auto_adjust=False, progress=False)['Close']
        return x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='data/v24_macro.json')
    a = ap.parse_args()
    px, rate = il.load()
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H14_LIQUIDEZ_FED.md', **run_all(px, rate, load_tnx())}
    print('RESUMEN_H14 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
