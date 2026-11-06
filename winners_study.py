"""Karryman · estudio de grandes ganadoras (superperformance) 2014-2026.

Para cada acción del universo de EE. UU. detecta los tramos en los que DOBLÓ su precio en
<= 12 meses (el tramo dura hasta caer un 30% desde su máximo) y analiza:
- sector/industria y rotación por años;
- momento en que el tramo era detectable (plantilla de tendencia de Minervini, ruptura de base,
  primer máximo de 52 semanas) y cuánto del tramo quedaba por delante;
- fuerza relativa (rango RS tipo IBD) en ese momento y situación del mercado (SPY);
- final del tramo: qué media se perdió primero, cuánto se devolvió y cuánto capturaría cada salida;
- rasgos de clímax en el techo.
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

MIN_GAIN = 2.0          # x2
MAX_DAYS_TO_DOUBLE = 252
END_DRAWDOWN = 0.30     # el tramo termina al caer un 30% desde el máximo


def indicators(f):
    d = f.copy()
    c, h, lo, v = d.Close, d.High, d.Low, d.Volume
    d['ema10'] = c.ewm(span=10, adjust=False).mean()
    d['ema21'] = c.ewm(span=21, adjust=False).mean()
    d['ma50'] = c.rolling(50).mean()
    d['ma150'] = c.rolling(150).mean()
    d['ma200'] = c.rolling(200).mean()
    d['hi252'] = h.rolling(252, min_periods=120).max()
    d['lo252'] = lo.rolling(252, min_periods=120).min()
    d['vol50'] = v.rolling(50).mean()
    d['dollar_vol'] = (c * v).rolling(50).mean()
    d['tt'] = ((c > d.ma50) & (d.ma50 > d.ma150) & (d.ma150 > d.ma200) & (d.ma200 > d.ma200.shift(20))
               & (c >= 1.30 * d.lo252) & (c >= 0.75 * d.hi252))
    week = d.index.to_period('W-FRI')
    wk = pd.Series(week, index=d.index)
    wclose = c.groupby(week).last()
    last_of_week = wk != wk.shift(-1)
    d['w10_break'] = last_of_week & wk.map(wclose < wclose.rolling(10).mean()).fillna(False).astype(bool)
    d['w50_break'] = last_of_week & wk.map(wclose < wclose.rolling(50).mean()).fillna(False).astype(bool)
    d['ret_week'] = c / c.shift(5) - 1
    d['ret_day'] = c / c.shift(1) - 1
    return d


def rs_score(c):
    """Puntuación RS tipo IBD: 40% 3 meses + 20% 6, 9 y 12 meses."""
    r = lambda n: c / c.shift(n) - 1
    return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)


def find_runs(d):
    """Tramos que doblan en <= 252 sesiones desde un mínimo local; terminan al caer un 30% del máximo."""
    cs = d.Close.reset_index(drop=True).astype(float)
    c = cs.to_numpy()
    n = len(c)
    fwd = cs[::-1].rolling(MAX_DAYS_TO_DOUBLE, min_periods=1).max()[::-1].to_numpy()
    locmin = cs.rolling(41, center=True, min_periods=1).min().to_numpy()
    cand = np.flatnonzero((fwd >= MIN_GAIN * c) & (c <= locmin) & (c >= 2) & (np.arange(n) >= 260))
    runs, next_ok = [], 0
    for i in cand:
        if i < next_ok:
            continue
        peak_i, peak, j = i, c[i], i
        while j < n:
            if c[j] > peak:
                peak, peak_i = c[j], j
            elif c[j] <= peak * (1 - END_DRAWDOWN):
                break
            j += 1
        end_i = min(j, n - 1)
        if peak >= MIN_GAIN * c[i]:
            runs.append((int(i), int(peak_i), int(end_i)))
        next_ok = end_i + 1
    return runs


def first_true(mask, start, stop):
    idx = np.flatnonzero(mask[start:stop])
    return start + int(idx[0]) if len(idx) else None


def analyze_run(tk, d, run, spy, rs_rank_row):
    i0, ip, ie = run
    c = d.Close.to_numpy(float)
    trough, peak = c[i0], c[ip]
    out = {'ticker': tk, 'start': str(d.index[i0].date()), 'peak': str(d.index[ip].date()),
           'gain_x': round(peak / trough, 2), 'days_to_peak': ip - i0,
           'dollar_vol_m_at_start': round(float(d.dollar_vol.iloc[i0] or 0) / 1e6, 1)}
    # Mercado al inicio
    sd = spy.reindex(d.index).ffill()
    sc = sd.Close.iloc[i0]
    out['spy_above_ma200_start'] = bool(sc > sd.ma200.iloc[i0])
    out['spy_dd_from_high_start'] = round(float(sc / sd.hi252.iloc[i0] - 1) * 100, 1)
    lo3m = float(sd.Close.iloc[max(0, i0 - 63):i0 + 1].min())
    out['spy_low_within_3m'] = bool(lo3m <= float(sd.lo252.iloc[i0]) * 1.001)
    # Puntos de entrada detectables
    tt = d.tt.to_numpy(bool)
    hi = d.hi252.to_numpy(float)
    vol, vol50 = d.Volume.to_numpy(float), d.vol50.to_numpy(float)
    k_tt = first_true(tt, i0, ip + 1)
    new_high = (c >= hi) & ~np.isnan(hi)
    k_nh = first_true(new_high, i0 + 1, ip + 1)
    piv30 = d.High.shift(1).rolling(30).max().to_numpy(float)
    brk = (c > piv30) & (vol >= 1.4 * vol50) & tt
    k_brk = first_true(brk, i0, ip + 1)
    for name, k in (('tt', k_tt), ('52wh', k_nh), ('breakout', k_brk)):
        if k is None:
            out[f'{name}_found'] = False
            continue
        out[f'{name}_found'] = True
        out[f'{name}_days_after_start'] = k - i0
        out[f'{name}_remaining_x'] = round(peak / c[k], 2)        # cuánto quedaba hasta el techo
        out[f'{name}_done_pct'] = round(math.log(c[k] / trough) / math.log(peak / trough) * 100, 1)
        if rs_rank_row is not None:
            try:
                out[f'{name}_rs_rank'] = round(float(rs_rank_row.loc[d.index[k]]), 1)
            except KeyError:
                out[f'{name}_rs_rank'] = None
        out[f'{name}_spy_above_ma50'] = bool(sd.Close.iloc[k] > sd.ma50.iloc[k])
    # Salidas desde la entrada en la plantilla de tendencia (si existe)
    entry_k = k_tt if k_tt is not None else k_brk
    if entry_k is not None:
        ce = c[entry_k]
        exits = {
            'cierre<EMA10': c < d.ema10.to_numpy(float),
            'cierre<EMA21': c < d.ema21.to_numpy(float),
            'cierre<MA50': c < d.ma50.to_numpy(float),
            'semana<MA10sem': d.w10_break.to_numpy(bool),
            'semana<MA50sem': d.w50_break.to_numpy(bool),
        }
        n = len(c)
        res = {}
        for name, mask in exits.items():
            k = first_true(mask, entry_k + 1, n)
            if k is None:
                k = n - 1
            res[name] = {'x': round(c[k] / ce, 2), 'days': k - entry_k, 'before_peak': k < ip,
                         'giveback_pct': round((1 - c[k] / peak) * 100, 1) if k >= ip else None}
        # trailing stops desde máximos
        for pct in (0.15, 0.25):
            run_max = np.maximum.accumulate(c[entry_k:])
            k_rel = np.flatnonzero(c[entry_k:] <= run_max * (1 - pct))
            k = entry_k + int(k_rel[0]) if len(k_rel) else n - 1
            res[f'trailing{int(pct*100)}%'] = {'x': round(c[k] / ce, 2), 'days': k - entry_k, 'before_peak': k < ip,
                                               'giveback_pct': round((1 - c[k] / peak) * 100, 1) if k >= ip else None}
        out['exits_from_entry'] = res
        out['ideal_from_entry_x'] = round(peak / ce, 2)
    # Deterioro tras el techo: qué se pierde primero
    order = []
    for name, mask in (('EMA10', c < d.ema10.to_numpy(float)), ('EMA21', c < d.ema21.to_numpy(float)),
                       ('MA50', c < d.ma50.to_numpy(float)), ('MA10sem', d.w10_break.to_numpy(bool)),
                       ('MA50sem', d.w50_break.to_numpy(bool))):
        k = first_true(mask, ip + 1, len(c))
        if k is not None:
            order.append((k, name, round((1 - c[k] / peak) * 100, 1)))
    order.sort()
    out['after_peak_breaks'] = [{'ma': nm, 'days_after_peak': k - ip, 'giveback_pct': g} for k, nm, g in order]
    # Clímax en el techo
    ma50p = d.ma50.iloc[ip]
    out['ext_above_ma50_at_peak_pct'] = round(float(peak / ma50p - 1) * 100, 1) if ma50p and ma50p > 0 else None
    seg = d.iloc[i0:ip + 1]
    out['biggest_week_gain_pct'] = round(float(seg.ret_week.max()) * 100, 1)
    out['biggest_week_days_before_peak'] = int(ip - d.index.get_loc(seg.ret_week.idxmax()))
    out['biggest_day_days_before_peak'] = int(ip - d.index.get_loc(seg.ret_day.idxmax()))
    return out


def sector_info(tickers, limit=1500):
    import yfinance as yf
    info = {}
    for k, t in enumerate(tickers[:limit]):
        try:
            i = yf.Ticker(t).info or {}
            info[t] = {'sector': i.get('sector') or 'Desconocido', 'industry': i.get('industry') or 'Desconocido'}
        except Exception:
            info[t] = {'sector': 'Desconocido', 'industry': 'Desconocido'}
        if k % 50 == 49:
            time.sleep(2)
    return info


def med(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return round(float(np.median(xs)), 2) if xs else None


def summarize(runs, info):
    df = pd.DataFrame(runs)
    df['year'] = pd.to_datetime(df.start).dt.year
    df['sector'] = df.ticker.map(lambda t: info.get(t, {}).get('sector', 'Desconocido'))
    df['industry'] = df.ticker.map(lambda t: info.get(t, {}).get('industry', 'Desconocido'))
    S = {'runs': len(df), 'tickers': int(df.ticker.nunique()),
         'median_gain_x': med(df.gain_x), 'median_days_to_peak': med(df.days_to_peak),
         'runs_per_year': df.groupby('year').size().to_dict(),
         'by_sector': df.sector.value_counts().head(12).to_dict(),
         'top_sector_by_year': {int(y): g.sector.value_counts().head(3).to_dict() for y, g in df.groupby('year')},
         'top_industries': df.industry.value_counts().head(15).to_dict()}
    S['market'] = {'pct_spy_above_ma200_at_start': round(df.spy_above_ma200_start.mean() * 100, 1),
                   'median_spy_dd_at_start_pct': med(df.spy_dd_from_high_start),
                   'pct_start_near_market_low_3m': round(df.spy_low_within_3m.mean() * 100, 1)}
    for name in ('tt', '52wh', 'breakout'):
        f = df[df.get(f'{name}_found', False) == True]  # noqa: E712
        S[f'entry_{name}'] = {'pct_runs_with_signal': round(len(f) / len(df) * 100, 1),
                              'median_days_after_start': med(f.get(f'{name}_days_after_start', [])),
                              'median_remaining_x': med(f.get(f'{name}_remaining_x', [])),
                              'median_pct_of_run_done': med(f.get(f'{name}_done_pct', [])),
                              'median_rs_rank': med(f.get(f'{name}_rs_rank', [])),
                              'pct_rs_rank_ge_80': round(float((f.get(f'{name}_rs_rank', pd.Series(dtype=float)) >= 80).mean() * 100), 1) if len(f) else None,
                              'pct_spy_above_ma50': round(float(f.get(f'{name}_spy_above_ma50', pd.Series(dtype=bool)).mean() * 100), 1) if len(f) else None}
    ex = [r['exits_from_entry'] for r in runs if 'exits_from_entry' in r]
    ideal = [r['ideal_from_entry_x'] for r in runs if 'exits_from_entry' in r]
    S['median_ideal_from_entry_x'] = med(ideal)
    S['exits'] = {}
    for name in ex[0].keys() if ex else []:
        xs = [e[name]['x'] for e in ex]
        S['exits'][name] = {'median_x': med(xs), 'mean_log_x': round(float(np.mean(np.log(np.maximum(xs, 0.01)))), 3),
                            'pct_before_peak': round(float(np.mean([e[name]['before_peak'] for e in ex])) * 100, 1),
                            'median_giveback_pct': med([e[name]['giveback_pct'] for e in ex]),
                            'median_days': med([e[name]['days'] for e in ex])}
    first = [r['after_peak_breaks'][0]['ma'] for r in runs if r['after_peak_breaks']]
    S['first_break_after_peak'] = pd.Series(first).value_counts().to_dict()
    gb = {}
    for r in runs:
        for b in r['after_peak_breaks']:
            gb.setdefault(b['ma'], []).append(b['giveback_pct'])
    S['giveback_at_break_pct'] = {k: med(v) for k, v in gb.items()}
    S['climax'] = {'median_ext_above_ma50_at_peak_pct': med(df.ext_above_ma50_at_peak_pct),
                   'pct_ext_over_50': round(float((df.ext_above_ma50_at_peak_pct > 50).mean() * 100), 1),
                   'median_biggest_week_pct': med(df.biggest_week_gain_pct),
                   'pct_biggest_week_in_last_15d': round(float((df.biggest_week_days_before_peak <= 15).mean() * 100), 1),
                   'pct_biggest_day_in_last_15d': round(float((df.biggest_day_days_before_peak <= 15).mean() * 100), 1)}
    big = df[df.gain_x >= 3]
    S['x3_or_more'] = {'runs': len(big), 'by_sector': big.sector.value_counts().head(8).to_dict(),
                       'median_days_to_peak': med(big.days_to_peak)}
    return S, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=7000)
    ap.add_argument('--start', default='2013-01-01')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--output', default='data/winners_study.json')
    a = ap.parse_args()
    t0 = time.time()
    names = sb.universe()
    random.Random(a.seed).shuffle(names)
    names = names[:a.symbols]
    frames = sb.download(['SPY'] + names, a.start)
    spy = frames.pop('SPY')
    spy = spy.assign(ma50=spy.Close.rolling(50).mean(), ma200=spy.Close.rolling(200).mean(),
                     hi252=spy.Close.rolling(252).max(), lo252=spy.Close.rolling(252).min())
    print(f'Descargadas {len(frames)} acciones en {time.time()-t0:.0f}s', flush=True)
    # Rango RS (percentil entre todo el universo, cada día)
    scores = pd.DataFrame({t: rs_score(f.Close) for t, f in frames.items()}).reindex(spy.index)
    liquid = pd.DataFrame({t: (f.Close * f.Volume).rolling(50).mean() >= 1e6 for t, f in frames.items()}).reindex(spy.index)
    rank = scores.where(liquid.fillna(False)).rank(axis=1, pct=True) * 100
    del scores, liquid
    runs = []
    for t, f in frames.items():
        d = indicators(f)
        if len(d) < 300:
            continue
        for run in find_runs(d):
            try:
                runs.append(analyze_run(t, d, run, spy, rank[t] if t in rank else None))
            except Exception as exc:  # una acción con datos raros no debe parar el estudio
                print('aviso', t, str(exc)[:80])
    print(f'Tramos x2 encontrados: {len(runs)} en {time.time()-t0:.0f}s', flush=True)
    tickers = sorted({r['ticker'] for r in runs}, key=lambda t: -max(r['gain_x'] for r in runs if r['ticker'] == t))
    info = sector_info(tickers)
    summary, df = summarize(runs, info)
    print('RESUMEN_GANADORAS ' + json.dumps(summary, ensure_ascii=False, default=str))
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps({'generated_utc': datetime.now(timezone.utc).isoformat(), 'summary': summary,
                                          'runs': runs, 'sectors': info}, ensure_ascii=False, default=str), encoding='utf-8')
    df.to_csv('data/winners_runs.csv', index=False)
    print(f'Listo en {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
