"""Karryman · contraste de H13 (arbitraje estadístico diario larga-corta, reversión de corto plazo) según docs/V24_H13_ARBITRAJE_ESTADISTICO.md.
Investigación únicamente. Prueba final 2021-2026 bloqueada: no se carga ningún dato posterior a 2020-12-31."""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_hipotesis as vh

K = 13
COST = 0.001            # por lado, sobre el nominal operado
BORROW = 0.01           # coste anual de préstamo de las posiciones cortas
Q = 0.10                # decil


def weights(score, elig, q=Q):
    """Pesos largos y cortos (cada lado suma 1 por sesión con valores elegibles)."""
    pct = score.where(elig).rank(axis=1, pct=True)
    long = (pct >= 1 - q) & elig
    short = (pct <= q) & elig
    wl = long.astype(float).div(long.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    ws = short.astype(float).div(short.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return wl, ws


def forward_returns(O):
    """Rentabilidad de la apertura de t+1 a la de t+2; sin precio (deslistado) = 0."""
    return (O.shift(-2) / O.shift(-1) - 1).fillna(0.0)


def long_short(score, elig, fwd, cost=COST, borrow=BORROW, q=Q):
    wl, ws = weights(score, elig, q)
    turn_l = wl.diff().abs().sum(axis=1)
    turn_s = ws.diff().abs().sum(axis=1)
    gl = (wl * fwd).sum(axis=1)
    gs = -(ws * fwd).sum(axis=1)
    net = gl + gs - (turn_l + turn_s) * cost - ws.sum(axis=1) * borrow / 252
    net_long_only = gl - turn_l * cost
    return net, net_long_only, (turn_l + turn_s)


def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 and eq.iloc[-1] > 0 else -1.0
    return {'cagr_pct': round(float(cagr * 100), 2), 'sharpe': round(float(r.mean() / r.std() * np.sqrt(252)), 3) if r.std() > 0 else 0.0,
            'max_dd_pct': round(float((eq / eq.cummax() - 1).min() * 100), 2), 'media_diaria_pct': round(float(r.mean() * 100), 4)}


def monthly(r):
    return r.resample('ME').apply(lambda x: float((1 + x).prod() - 1)).dropna()


def run_period(p, member, bench, segs, level, sens=True):
    O, C = p['open'], p['close']
    elig = member & vb.liquidity_member(p) & C.notna()
    fwd = forward_returns(O)
    h = 5
    score = -(C / C.shift(h) - 1)
    full = (segs[0][1][0], segs[-1][1][1])
    sl = lambda r, w: r.loc[w[0]:w[1]].iloc[:-2]
    net, net_lo, turn = long_short(score, elig, fwd)
    pl = {f'placebo_obsoleto_{k}': long_short(score.shift(k), elig, fwd)[0] for k in (20, 40)}
    spy = bench.pct_change().reindex(net.index).fillna(0.0)
    wins = segs + [('todo', full)]
    res = {'h13': {k: stats(sl(net, w)) for k, w in wins}, 'spy': {k: stats(sl(spy, w)) for k, w in wins},
           'placebos': {n: {k: stats(sl(r, w)) for k, w in wins} for n, r in pl.items()},
           'rotacion_media_diaria_nominal': round(float(sl(turn, (full[0], full[1])).mean()), 3)}
    m = monthly(sl(net, (full[0], full[1])))
    lo, hi, mean = vh.boot_ci(m, level)
    j1 = bool(lo > 0)
    j2 = bool(all(res['h13'][k]['sharpe'] > res['placebos'][n][k]['sharpe'] for k, _ in segs for n in pl))
    ms = monthly(sl(spy, (full[0], full[1])))
    al = pd.concat([m, ms], axis=1).dropna()
    beta = float(np.polyfit(al.iloc[:, 1], al.iloc[:, 0], 1)[0]) if len(al) > 5 else None
    corr = float(al.corr().iloc[0, 1]) if len(al) > 5 else None
    t, s = res['h13']['todo'], res['spy']['todo']
    sup = bool(t['cagr_pct'] > s['cagr_pct'] and t['sharpe'] >= s['sharpe'])
    res['criterios'] = {'J1_ic_media_mensual_neta': {'media': mean, 'low': lo, 'high': hi, 'nivel': level, 'pasa': j1}, 'J2_sharpe_mayor_que_ambos_placebos_en_cada_tramo': j2,
                        'esperanza_positiva_en_el_periodo': bool(j1 and j2), 'supera_a_spy_cagr_y_sharpe': sup, 'beta_mensual_con_spy': beta, 'correlacion_mensual_con_spy': corr}
    if sens:
        sv = {}
        for hh in (1, 21):
            sv[f'horizonte_{hh}_sesiones'] = stats(sl(long_short(-(C / C.shift(hh) - 1), elig, fwd)[0], (full[0], full[1])))
        for c in (0.0005, 0.002):
            sv[f'coste_{c*100:.2f}pct_por_lado'] = stats(sl(long_short(score, elig, fwd, cost=c)[0], (full[0], full[1])))
        sv['solo_lado_largo_neto'] = stats(sl(net_lo, (full[0], full[1])))
        res['sensibilidades_no_deciden'] = sv
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_statarb.json')
    a = ap.parse_args()
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'registro': 'docs/V24_H13_ARBITRAJE_ESTADISTICO.md', 'datos': {'tag': a.tag, 'sha256': sha}}
    flags = {}
    for name, start, end, segs, level in (
            ('A_2010_2020', '2007-01-01', '2020-12-31', [('train', ('2010-01-01', '2016-12-31')), ('valid', ('2017-01-01', '2020-12-31'))], 1 - 0.05 / K),
            ('B_1997_2009', '1996-01-01', '2009-12-31', [('P1', ('1997-01-01', '2002-12-31')), ('P2', ('2003-01-01', '2009-12-31'))], 0.95)):
        p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start=start, end=end)
        assert p['close'].index.max() <= pd.Timestamp(end), 'datos posteriores al bloqueo cargados'
        res = run_period(p, member, bench, segs, level)
        res['universo'] = info
        out[name] = res
        flags[name] = res['criterios']
        print(f'{name} listo · {time.time()-t0:.0f}s', flush=True)
    pos = all(f['esperanza_positiva_en_el_periodo'] for f in flags.values())
    out['veredicto'] = {'esperanza_positiva': bool(pos), 'supera_a_spy': bool(pos and all(f['supera_a_spy_cagr_y_sharpe'] for f in flags.values()))}
    print('RESUMEN_H13 ' + json.dumps(out, default=float), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
