"""Karryman · señales TEMPRANAS: ¿qué se puede detectar antes de que la subida lleve el 50%?

Para cada señal candidata se mide, sobre todo el mercado de EE. UU. (2013-2026):
- precisión: % de veces que la acción dobló (x2) en los 12 meses siguientes, frente al azar
  (misma población líquida, todos los días) -> "lift";
- cuánto de la subida de las ganadoras llevaba hecho en el primer aviso (% del tramo log);
- recall temprano: % de las ganadoras (tramos x2) avisadas antes de llevar el 30% del tramo;
- expectativa en R de operar la señal (stop = mínimo de 10 sesiones, máx. 12%; salida por
  trailing del 25% desde máximos de cierre), dentro y fuera de muestra (2021+), y según el
  mercado (SPY sobre MA50 al alza o no).
Investigación únicamente. Sesgo de supervivencia: solo acciones que cotizan hoy.
"""
import argparse
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import system_backtest as sb
import winners_study as ws

COST = 0.001
COOLDOWN = 60
HORIZON = 252
OOS_START = pd.Timestamp('2021-01-01')


def rs_score(c):
    r = lambda n: c / c.shift(n) - 1
    return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)


def pick(mask, cooldown=COOLDOWN):
    idx = np.flatnonzero(mask)
    out, last = [], -10 ** 9
    for i in idx:
        if i - last >= cooldown:
            out.append(int(i))
            last = i
    return out


def features(f, spy_c, up, rank):
    d = f
    c, h, lo, o, v = (d.Close.to_numpy(float), d.High.to_numpy(float), d.Low.to_numpy(float),
                      d.Open.to_numpy(float), d.Volume.to_numpy(float))
    cs = d.Close
    S = lambda x: pd.Series(x, index=d.index)
    ma50, ma150, ma200 = cs.rolling(50).mean(), cs.rolling(150).mean(), cs.rolling(200).mean()
    hi252 = S(h).rolling(252, min_periods=200).max()
    lo252 = S(lo).rolling(252, min_periods=200).min()
    vol50 = S(v).shift(1).rolling(50).mean()
    vol10 = S(v).rolling(10).mean()
    prev = cs.shift(1)
    tr = pd.concat([S(h) - S(lo), (S(h) - prev).abs(), (S(lo) - prev).abs()], axis=1).max(axis=1) / cs
    atr10, atr50 = tr.rolling(10).mean(), tr.rolling(50).mean()
    spy = spy_c.reindex(d.index).ffill()
    rsl = cs / spy
    rs_hi = rsl >= rsl.rolling(252, min_periods=200).max() * 0.999
    rk = rank.reindex(d.index)
    rk63 = rk.shift(63)
    liquid = (cs >= 5) & (vol50 >= 300_000) & ((cs * vol50) >= 1e6)
    trend = (cs > ma50) & (ma50 > ma150) & (ma150 > ma200) & (ma200 > ma200.shift(20)) & (cs >= 1.3 * lo252) & (cs >= 0.75 * hi252)
    gap = S(o) / prev - 1
    below150 = (cs < ma150).astype(float).rolling(100).mean() > 0.6
    cross150 = (cs > ma150) & (prev <= ma150.shift(1)) & (ma150 > ma150.shift(20))
    mom63 = cs / cs.shift(63) - 1
    sig = {
        'Plantilla de tendencia (referencia, tardía)': trend,
        'Máximo de 52 semanas con volumen': (cs >= hi252) & (S(v) >= 1.5 * vol50),
        'Línea RS en máximos con el precio aún lejos': rs_hi & (cs < 0.95 * hi252) & (cs > ma50) & (cs >= 0.7 * hi252),
        'Salto de fuerza relativa (rango <=50 -> >=80)': (rk >= 80) & (rk63 <= 50),
        'Contracción de volatilidad cerca de máximos': (cs > ma50) & (ma50 > ma200) & (cs >= 0.85 * hi252) & (atr10 <= 0.6 * atr50) & (vol10 <= 0.7 * vol50),
        'Giro de etapa 2 (cruza MA150 con volumen)': cross150.rolling(3).max().astype(bool) & below150.shift(5).fillna(False) & (S(v) >= 1.5 * vol50),
        'Pivote episódico (gap >=10% con volumen x3)': (gap >= 0.10) & (S(v) >= 3 * vol50) & (cs >= S(o)) & (cs >= 0.5 * hi252),
        'Empuje de momentum (+50% en 3 meses)': (mom63 >= 0.5) & (cs >= 0.9 * hi252),
    }
    out = {}
    for name, m in sig.items():
        out[name] = (m & liquid).fillna(False).to_numpy(bool)
    rk80, rk70 = (rk >= 80).fillna(False), (rk >= 70).fillna(False)
    upb = up.reindex(d.index).ffill().fillna(False).astype(bool)
    out['COMBO línea RS + contracción'] = out['Línea RS en máximos con el precio aún lejos'] & out['Contracción de volatilidad cerca de máximos']
    out['COMBO pivote episódico + RS>=70'] = out['Pivote episódico (gap >=10% con volumen x3)'] & rk70.to_numpy(bool)
    out['COMBO giro etapa 2 + RS>=60'] = out['Giro de etapa 2 (cruza MA150 con volumen)'] & (rk >= 60).fillna(False).to_numpy(bool)
    out['COMBO máximo 52s + volumen + RS>=80 + mercado alcista'] = out['Máximo de 52 semanas con volumen'] & rk80.to_numpy(bool) & upb.to_numpy(bool)
    out['COMBO salto RS + mercado alcista'] = out['Salto de fuerza relativa (rango <=50 -> >=80)'] & upb.to_numpy(bool)
    return out, liquid.fillna(False).to_numpy(bool), upb.to_numpy(bool)


def trade_R(i, o, h, lo, c, entry_next=True):
    n = len(c)
    j0 = i + 1
    if j0 >= n - 1:
        return None
    entry = o[j0] * (1 + COST)
    low10 = lo[max(0, i - 9):i + 1].min()
    stop0 = max(low10, entry * 0.88)
    if stop0 > entry * 0.97:
        stop0 = entry * 0.97
    risk = entry - stop0
    seg = c[j0:]
    runmax = np.maximum.accumulate(seg)
    hit = (seg <= stop0) | (seg <= runmax * 0.75)
    if hit.any():
        k = int(np.argmax(hit))
        ex_i = j0 + k
        px = o[ex_i + 1] * (1 - COST) if ex_i + 1 < n else c[ex_i]
        days = k
    else:
        px, days = c[-1], len(seg) - 1
    return (px - entry) / risk, days


def analyze_stock(tk, f, spy_c, up, rank):
    sigs, liquid, upb = features(f, spy_c, up, rank)
    c, h, lo, o = (f.Close.to_numpy(float), f.High.to_numpy(float), f.Low.to_numpy(float), f.Open.to_numpy(float))
    n = len(c)
    rev = pd.Series(c[::-1]).rolling(HORIZON, min_periods=HORIZON).max().to_numpy()[::-1]
    fwdmax = np.r_[rev[1:], np.nan] / c  # máximo de los 252 cierres siguientes / cierre de hoy
    dates = f.index
    years = dates.year.to_numpy()
    runs = ws.find_runs(f)
    base = {'n': 0, 'hit': 0, 'n_up': 0, 'hit_up': 0, 'n_dn': 0, 'hit_dn': 0, 'n_is': 0, 'hit_is': 0, 'n_oos': 0, 'hit_oos': 0}
    ok = liquid & ~np.isnan(fwdmax)
    hit = fwdmax >= 2
    base['n'], base['hit'] = int(ok.sum()), int((ok & hit).sum())
    base['n_up'], base['hit_up'] = int((ok & upb).sum()), int((ok & upb & hit).sum())
    base['n_dn'], base['hit_dn'] = int((ok & ~upb).sum()), int((ok & ~upb & hit).sum())
    oos = dates >= OOS_START
    base['n_is'], base['hit_is'] = int((ok & ~oos).sum()), int((ok & ~oos & hit).sum())
    base['n_oos'], base['hit_oos'] = int((ok & oos).sum()), int((ok & oos & hit).sum())
    events, runstats = [], []
    run_info = []
    for (i0, ip, ie) in runs:
        run_info.append((i0, ip, math.log(c[ip] / c[i0]) if c[ip] > c[i0] else 1e-9))
    for name, mask in sigs.items():
        evs = pick(mask)
        for i in evs:
            fm = fwdmax[i]
            rr = trade_R(i, o, h, lo, c)
            rd = np.nan
            for (i0, ip, lg) in run_info:
                if i0 <= i <= ip:
                    rd = math.log(c[i] / c[i0]) / lg
                    break
            events.append((name, years[i], bool(oos[i]), bool(upb[i]), float(fm) if not np.isnan(fm) else np.nan,
                           rr[0] if rr else np.nan, rr[1] if rr else np.nan, rd))
        # recall por tramo: primer evento dentro del tramo
        evset = np.array(evs, dtype=int)
        for (i0, ip, lg) in run_info:
            inside = evset[(evset >= i0) & (evset <= ip)] if len(evset) else evset
            first = float(math.log(c[inside[0]] / c[i0]) / lg) if len(inside) else np.nan
            runstats.append((name, first))
    return base, events, runstats, len(runs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=4000)
    ap.add_argument('--start', default='2012-06-01')
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--output', default='data/early_signals.json')
    a = ap.parse_args()
    t0 = time.time()
    names = sb.universe()
    random.Random(a.seed).shuffle(names)
    frames = sb.download(['SPY'] + names[:a.symbols], a.start)
    spy = frames.pop('SPY')
    up = sb.regime_series(spy)['spy_ma50_up']
    print(f'Descargadas {len(frames)} acciones en {time.time()-t0:.0f}s', flush=True)
    res = run_all(frames, spy.Close, up)
    res['seconds'] = round(time.time() - t0)
    res['generated_utc'] = datetime.now(timezone.utc).isoformat()
    print('RESUMEN_TEMPRANAS ' + json.dumps(res, ensure_ascii=False, default=str))
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps(res, ensure_ascii=False, default=str, indent=1), encoding='utf-8')


def run_all(frames, spy_c, up):
    scores = pd.DataFrame({t: rs_score(f.Close) for t, f in frames.items()}).reindex(spy_c.index)
    liq = pd.DataFrame({t: (f.Close >= 5) & (f.Volume.rolling(50).mean() >= 300_000) for t, f in frames.items()}).reindex(spy_c.index).fillna(False)
    rank = scores.where(liq).rank(axis=1, pct=True) * 100
    del scores, liq
    base_tot, ev_all, rs_all, total_runs = {}, [], [], 0
    for tk, f in frames.items():
        if len(f) < 400:
            continue
        try:
            base, evs, rstats, nr = analyze_stock(tk, f, spy_c, up, rank[tk])
        except Exception as exc:
            print('aviso', tk, str(exc)[:80])
            continue
        for k, v in base.items():
            base_tot[k] = base_tot.get(k, 0) + v
        ev_all += evs
        rs_all += rstats
        total_runs += nr
    ev = pd.DataFrame(ev_all, columns=['sig', 'year', 'oos', 'up', 'fm', 'R', 'days', 'run_done'])
    rs = pd.DataFrame(rs_all, columns=['sig', 'first'])
    b = lambda k: base_tot.get(k, 0)
    pr = lambda h_, n_: round(100 * h_ / n_, 2) if n_ else None
    baseline = {'hit2_pct': pr(b('hit'), b('n')), 'hit2_up_pct': pr(b('hit_up'), b('n_up')), 'hit2_dn_pct': pr(b('hit_dn'), b('n_dn')),
                'hit2_is_pct': pr(b('hit_is'), b('n_is')), 'hit2_oos_pct': pr(b('hit_oos'), b('n_oos')), 'days': b('n')}
    years = max(1, ev.year.max() - ev.year.min() + 1)
    rows = {}
    for name, g in ev.groupby('sig'):
        gf = g.dropna(subset=['fm'])
        prec = lambda x: round(float((x.fm >= 2).mean() * 100), 2) if len(x) else None
        rr = lambda x: round(float(x.R.mean()), 3) if len(x) else None
        r = rs[rs.sig == name]
        inrun = g.dropna(subset=['run_done'])
        rows[name] = {
            'events': int(len(g)), 'events_per_year': round(len(g) / years, 0),
            'precision_x2_pct': prec(gf), 'lift_vs_random': round(prec(gf) / baseline['hit2_pct'], 2) if prec(gf) and baseline['hit2_pct'] else None,
            'precision_x3_pct': round(float((gf.fm >= 3).mean() * 100), 2) if len(gf) else None,
            'median_future_max_x': round(float(gf.fm.median()), 2) if len(gf) else None,
            'precision_is_pct': prec(gf[~gf.oos]), 'precision_oos_pct': prec(gf[gf.oos]),
            'precision_market_up_pct': prec(gf[gf.up]), 'precision_market_down_pct': prec(gf[~gf.up]),
            'expectancy_R': rr(g), 'win_rate_pct': round(float((g.R > 0).mean() * 100), 1),
            'expectancy_R_is': rr(g[~g.oos]), 'expectancy_R_oos': rr(g[g.oos]),
            'expectancy_R_market_up': rr(g[g.up]), 'median_days_in_trade': round(float(g.days.median()), 0),
            'runs_total': int(len(r)), 'recall_any_pct': round(float(r['first'].notna().mean() * 100), 1) if len(r) else None,
            'recall_before_30pct_done': round(float((r['first'] <= 0.30).mean() * 100), 1) if len(r) else None,
            'median_pct_run_done_at_first_signal': round(float(r['first'].median() * 100), 1) if r['first'].notna().any() else None,
            'events_inside_winner_runs_pct': round(float(len(inrun) / len(g) * 100), 1)}
    return {'baseline': baseline, 'runs_total': total_runs, 'signals': rows}


if __name__ == '__main__':
    main()
