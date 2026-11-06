"""Karryman · panel de datos (acción x mes) y estudio de fundamentales con significación estadística.

1. Panel mensual: variables técnicas, fundamentales (SEC, sin mirar al futuro), de sector y de mercado,
   más resultados futuros (rentabilidad a 3/6/12 meses, máximo a 12 meses, x2, caída).
2. Significación: correlación de rango mes a mes (como Fama-MacBeth) con la rentabilidad futura y con
   "dobla en 12 meses"; quintiles con intervalos de confianza por remuestreo de meses.
3. Segmentos del BPA (pérdidas, giro a beneficios, crece, crece poco, cae) y de ventas.
4. Anticipación: estudio de eventos alrededor de cada mejora fundamental y momento en que se enciende
   cada señal fundamental dentro de las ganadoras (tramos x2).
Investigación únicamente. Sesgo de supervivencia: solo acciones que cotizan hoy.
"""
import argparse
import gzip
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import early_signals as es
import fundamental_study as fs
import sec_fundamentals as sec
import system_backtest as sb
import winners_study as ws

HORIZON = 252
BOOT = 400
MIN_PER_MONTH = 60
WINDOWS = [(-252, -189), (-189, -126), (-126, -63), (-63, -21), (-21, 0), (0, 21), (21, 63), (63, 126), (126, 252)]
EVENTS = {'ev_rev_infl': 'Ventas: de <15% a >=25% interanual', 'ev_rev_accel': 'Ventas aceleran >=10 pp (y >=20%)',
          'ev_eps_turn': 'BPA: giro de pérdidas a beneficios', 'ev_oi_turn': 'Resultado operativo: de pérdidas a beneficios',
          'ev_streak2': 'Ventas >=25% dos trimestres seguidos'}


# ------------------------------------------------------------------ variables de precio
def price_features(f, spy_c, rank, group_rank, sh):
    c, h, lo, v = f.Close, f.High, f.Low, f.Volume
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    hi252, lo252 = h.rolling(252, min_periods=200).max(), lo.rolling(252, min_periods=200).min()
    vol50, vol10 = v.shift(1).rolling(50).mean(), v.rolling(10).mean()
    prev = c.shift(1)
    tr = pd.concat([h - lo, (h - prev).abs(), (lo - prev).abs()], axis=1).max(axis=1) / c
    spy = spy_c.reindex(f.index).ffill()
    rsl = c / spy
    updown = (v.where(c > prev, 0).rolling(50).sum() + 1) / (v.where(c < prev, 0).rolling(50).sum() + 1)
    d = pd.DataFrame(index=f.index)
    for n in (21, 63, 126, 252):
        d[f'ret_{n}'] = c / c.shift(n) - 1
    d['dist_hi'], d['dist_lo'] = c / hi252 - 1, c / lo252 - 1
    d['c_ma50'], d['c_ma200'] = c / ma50 - 1, c / ma200 - 1
    d['ma200_slope'] = ma200 / ma200.shift(20) - 1
    d['atr_ratio'], d['vol_ratio'] = tr.rolling(10).mean() / tr.rolling(50).mean(), vol10 / vol50
    d['updown_vol'] = np.log(updown)
    d['tight20'] = (h.rolling(20).max() - lo.rolling(20).min()) / c
    d['log_price'], d['log_dvol'] = np.log10(c), np.log10((c * vol50).clip(lower=1))
    d['rs_rank'] = rank.reindex(f.index)
    d['rs_rank_chg'] = d['rs_rank'] - d['rs_rank'].shift(63)
    d['rs_line_hi'] = (rsl >= rsl.rolling(252, min_periods=200).max() * 0.999).astype(float)
    d['group_rank'] = group_rank
    d['group_leader'] = (group_rank >= 0.8).astype(float).where(group_rank.notna())
    d['log_mcap'] = np.log10((c * sh).clip(lower=1)) if sh is not None else np.nan
    d['liquid'] = ((c >= 5) & (vol50 >= 300_000) & ((c * vol50) >= 1e6)).astype(float)
    return d


def labels(f, spy_c):
    c = f.Close
    n = len(c)
    cv = c.to_numpy(float)
    spy = spy_c.reindex(f.index).ffill()
    out = pd.DataFrame(index=f.index)
    for k in (63, 126, 252):
        out[f'fwd_ret_{k}'] = c.shift(-k) / c - 1
        out[f'fwd_spy_{k}'] = spy.shift(-k) / spy - 1
        out[f'fwd_exc_{k}'] = out[f'fwd_ret_{k}'] - out[f'fwd_spy_{k}']
    rev = pd.Series(cv[::-1]).rolling(HORIZON, min_periods=HORIZON).max().to_numpy()[::-1]
    fmax = np.r_[rev[1:], np.nan] / cv
    out['fwd_max_252'] = fmax
    out['hit2'] = np.where(np.isnan(fmax), np.nan, (fmax >= 2).astype(float))
    out['hit3'] = np.where(np.isnan(fmax), np.nan, (fmax >= 3).astype(float))
    rmin = pd.Series(cv[::-1]).rolling(126, min_periods=126).min().to_numpy()[::-1]
    out['fwd_dd_126'] = np.r_[rmin[1:], np.nan] / cv - 1
    return out.drop(columns=[c for c in out.columns if c.startswith('fwd_spy_')])


def group_rank_matrix(frames, tk_group, index, min_members=10):
    ret = pd.DataFrame({t: f.Close / f.Close.shift(126) - 1 for t, f in frames.items() if t in tk_group}).reindex(index)
    groups = pd.Series(tk_group)
    sizes = groups.value_counts()
    keep = [g for g, n in sizes.items() if n >= min_members]
    med = pd.DataFrame({g: ret[[t for t in groups.index[groups == g] if t in ret.columns]].median(axis=1) for g in keep})
    rank = med.rank(axis=1, pct=True)
    rank[med.notna().sum(axis=1) < 5] = np.nan
    return rank, sizes


def month_end_positions(index):
    m = index.month.to_numpy()
    return np.flatnonzero(np.r_[m[1:] != m[:-1], False])


def build_panel(frames, fund, spy_c, up, rank_df, grank, tk_group):
    parts = []
    spy_dd = spy_c / spy_c.rolling(252, min_periods=60).max() - 1
    spy_r63 = spy_c / spy_c.shift(63) - 1
    for t, f in frames.items():
        rows = (fund.get(t) or {}).get('rows') or []
        if len(f) < 400 or not rows:
            continue
        ff, valid = sec.fund_features(rows, f.index)
        g = tk_group.get(t)
        gr = grank[g].reindex(f.index).ffill() if g in grank.columns else pd.Series(np.nan, index=f.index)
        pf = price_features(f, spy_c, rank_df[t], gr, ff['sh'])
        lab = labels(f, spy_c)
        d = pd.concat([pf, ff.drop(columns=['sh']), lab], axis=1)
        d['fund_valid'] = valid.astype(float)
        d['spy_up'] = up.reindex(f.index).ffill().astype(float)
        d['spy_dd'], d['spy_ret_63'] = spy_dd.reindex(f.index).ffill(), spy_r63.reindex(f.index).ffill()
        pos = month_end_positions(f.index)
        pos = pos[pos >= 260]
        d = d.iloc[pos].copy()
        d.insert(0, 'ticker', t)
        d.insert(1, 'date', f.index[pos])
        d['group'] = g
        parts.append(d)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ------------------------------------------------------------------ estadística
def _is_binary(s):
    u = s.dropna().unique()
    return len(u) <= 2 and set(np.unique(u)) <= {0.0, 1.0}


def boot_ci(per_month, fn, rng, B=BOOT):
    """IC95 por remuestreo de meses de un estadístico fn(suma de contadores por mes)."""
    M = per_month.shape[0]
    vals = []
    for _ in range(B):
        idx = rng.integers(0, M, M)
        vals.append(fn(per_month[idx].sum(axis=0)))
    vals = np.array(vals, dtype=float)
    return [round(float(np.nanpercentile(vals, 2.5)), 4), round(float(np.nanpercentile(vals, 97.5)), 4)]


def month_ic(panel, feat, target):
    ics = []
    for _, g in panel.groupby('month'):
        d = g[[feat, target]].dropna()
        if len(d) >= MIN_PER_MONTH and d[feat].nunique() > 2:
            ics.append(d[feat].rank().corr(d[target].rank()))
    ics = np.array([x for x in ics if np.isfinite(x)])
    if len(ics) < 24:
        return None
    return {'mean': float(ics.mean()), 't': float(ics.mean() / (ics.std(ddof=1) / math.sqrt(len(ics)))), 'pos': float((ics > 0).mean()), 'n': int(len(ics))}


def quintile_stats(panel, feat, rng):
    """Acierto de 'dobla' y exceso medio por quintil (o por valor si es binaria), con IC por meses."""
    cats = 2 if _is_binary(panel[feat]) else 5
    months = sorted(panel['month'].unique())
    mi = {m: i for i, m in enumerate(months)}
    cnt = np.zeros((len(months), cats, 3))  # n, hits, suma exceso
    for m, g in panel.groupby('month'):
        d = g[[feat, 'hit2', 'fwd_exc_252']].dropna()
        if len(d) < MIN_PER_MONTH:
            continue
        if cats == 2:
            q = d[feat].astype(int).to_numpy()
        else:
            if d[feat].nunique() < 5:
                continue
            q = pd.qcut(d[feat].rank(method='first'), 5, labels=False).to_numpy()
        for k in range(cats):
            sel = q == k
            cnt[mi[m], k] = [sel.sum(), d['hit2'].to_numpy()[sel].sum(), d['fwd_exc_252'].to_numpy()[sel].sum()]
    flat = cnt.reshape(len(months), -1)
    tot = flat.sum(axis=0).reshape(cats, 3)
    if tot[:, 0].min() < 200:
        return None
    hit = tot[:, 1] / tot[:, 0] * 100
    exc = tot[:, 2] / tot[:, 0] * 100

    def spread_hit(v):
        a = v.reshape(cats, 3)
        return (a[-1, 1] / a[-1, 0] - a[0, 1] / a[0, 0]) * 100

    def spread_exc(v):
        a = v.reshape(cats, 3)
        return (a[-1, 2] / a[-1, 0] - a[0, 2] / a[0, 0]) * 100
    return {'groups': cats, 'n': tot[:, 0].astype(int).tolist(), 'hit2_pct': [round(float(x), 2) for x in hit],
            'excess_ret_pct': [round(float(x), 1) for x in exc], 'spread_hit2_pp': round(float(hit[-1] - hit[0]), 2),
            'spread_hit2_ci': boot_ci(flat, spread_hit, rng), 'spread_excess_pp': round(float(exc[-1] - exc[0]), 1),
            'spread_excess_ci': boot_ci(flat, spread_exc, rng)}


def segment_table(panel, segments, rng):
    """Cuota sobre el total, cuota entre las que doblan, acierto, exceso y IC de la diferencia con el resto."""
    base = panel.dropna(subset=['hit2', 'fwd_exc_252'])
    months = sorted(base['month'].unique())
    mi = {m: i for i, m in enumerate(months)}
    hit_all = base['hit2'].mean() * 100
    out = {}
    for name, mask in segments.items():
        m = mask.reindex(base.index).fillna(False).to_numpy(bool)
        if m.sum() < 200:
            continue
        cnt = np.zeros((len(months), 4))  # n_seg, hits_seg, n_rest, hits_rest
        mm = base['month'].map(mi).to_numpy()
        h = base['hit2'].to_numpy()
        for i in range(len(months)):
            sel = mm == i
            cnt[i] = [(sel & m).sum(), h[sel & m].sum(), (sel & ~m).sum(), h[sel & ~m].sum()]
        diff = lambda v: (v[1] / v[0] - v[3] / v[2]) * 100 if v[0] and v[2] else np.nan
        out[name] = {'n': int(m.sum()), 'share_all_pct': round(float(m.mean() * 100), 1),
                     'share_of_doublers_pct': round(float(m[h == 1].mean() * 100), 1), 'hit2_pct': round(float(h[m].mean() * 100), 2),
                     'hit2_vs_rest_pp': round(float(h[m].mean() * 100 - h[~m].mean() * 100), 2), 'hit2_vs_rest_ci': boot_ci(cnt, diff, rng),
                     'median_excess_12m_pct': round(float(base['fwd_exc_252'].to_numpy()[m].mean() * 100), 1),
                     'lift_vs_all': round(float(h[m].mean() * 100 / hit_all), 2)}
    out['_base'] = {'hit2_pct': round(float(hit_all), 2), 'n': int(len(base))}
    return out


# ------------------------------------------------------------------ anticipación
def event_study_stock(f, spy_c, qt, store):
    if qt is None or qt.empty:
        return
    n = len(f)
    c = np.log(f.Close.to_numpy(float))
    spy = np.log(spy_c.reindex(f.index).ffill().to_numpy(float))
    avail = pd.to_datetime(qt['avail']) + pd.offsets.BDay(1)
    pos = f.index.searchsorted(avail.to_numpy())
    ok = (pos >= 252) & (pos + 252 < n)
    for kind in list(EVENTS) + ['todos']:
        sel = ok if kind == 'todos' else ok & (qt[kind].to_numpy() == 1)
        for p in pos[sel]:
            store.setdefault(kind, []).append([float((c[p + b] - c[p + a]) - (spy[p + b] - spy[p + a])) for a, b in WINDOWS])


def summarize_events(store):
    out = {}
    for kind, rows in store.items():
        a = np.array(rows)
        if len(a) < 30:
            continue
        pct = lambda x: round(float((np.exp(x) - 1) * 100), 1)
        pre, post = a[:, :5].sum(axis=1), a[:, 5:].sum(axis=1)
        out[kind] = {'label': EVENTS.get(kind, 'Todos los trimestres presentados (control)'), 'n': int(len(a)),
                     'median_excess_pct_by_window': {f'{x}..{y}': pct(float(np.median(a[:, i]))) for i, (x, y) in enumerate(WINDOWS)},
                     'pre_12m_median_pct': pct(float(np.median(pre))), 'post_12m_median_pct': pct(float(np.median(post))),
                     'pre_9m_median_pct': pct(float(np.median(a[:, 1:5].sum(axis=1)))),
                     'pre_3m_median_pct': pct(float(np.median(a[:, 3:5].sum(axis=1)))),
                     'share_pre_12m_positive': round(float((pre > 0).mean() * 100), 1),
                     'share_post_12m_positive': round(float((post > 0).mean() * 100), 1)}
    return out


def winner_flags(df):
    g = lambda k: df[k].to_numpy(float)
    eps_pos = (np.nan_to_num(g('eps_turn')) + np.nan_to_num(g('eps_g25')) + np.nan_to_num(g('eps_low')) + np.nan_to_num(g('eps_fall'))) > 0
    return {'Ventas +25% interanual': g('rev_yoy') >= 0.25,
            'Ventas aceleran (>=+5 pp y >=15%)': (g('rev_accel') >= 0.05) & (g('rev_yoy') >= 0.15),
            'Racha de 3 trimestres con ventas >=20%': g('rev_streak') >= 3,
            'BPA positivo': eps_pos, 'BPA negativo': g('eps_neg') == 1, 'Giro de pérdidas a beneficios (BPA)': g('eps_turn') == 1,
            'Margen bruto sube >=2 pp': g('gm_chg') >= 2, 'Margen operativo sube >=3 pp': g('om_chg') >= 3,
            'Beneficio neto positivo': g('ni_pos') == 1, 'Caja operativa positiva': g('cfo_pos') == 1}


def winner_timing_stock(f, ff, valid, store):
    runs = ws.find_runs(f)
    if not runs:
        return
    c = f.Close.to_numpy(float)
    flags = winner_flags(ff)
    for (i0, ip, ie) in runs:
        if not valid[i0] or ip <= i0 + 5:
            continue
        lg = math.log(c[ip] / c[i0]) if c[ip] > c[i0] else 1e-9
        for name, a in flags.items():
            a = np.asarray(a, dtype=bool) & valid
            rec = store.setdefault(name, {'n': 0, 'true_start': 0, 'lag_days': [], 'done': [], 'never': 0, 'days_on': []})
            rec['n'] += 1
            if a[i0]:
                rec['true_start'] += 1
                off = np.flatnonzero(~a[:i0])
                rec['days_on'].append(int(i0 - (off[-1] if len(off) else -1)))
            else:
                nxt = np.flatnonzero(a[i0 + 1:ip + 1])
                if len(nxt):
                    j = i0 + 1 + int(nxt[0])
                    rec['lag_days'].append(j - i0)
                    rec['done'].append(float(math.log(c[j] / c[i0]) / lg))
                else:
                    rec['never'] += 1


def summarize_timing(store):
    out = {}
    for name, r in store.items():
        med = lambda x: round(float(np.median(x)), 1) if len(x) else None
        out[name] = {'runs': r['n'], 'true_at_start_pct': round(100 * r['true_start'] / r['n'], 1),
                     'turns_on_before_peak_pct': round(100 * len(r['lag_days']) / r['n'], 1),
                     'median_days_until_on': med(r['lag_days']), 'median_pct_of_run_done_when_on': round(100 * float(np.median(r['done'])), 1) if r['done'] else None,
                     'median_days_already_on_at_start': med(r['days_on'])}
    return out


# ------------------------------------------------------------------ principal
def analyze(panel, store_events, store_timing, seed=1):
    rng = np.random.default_rng(seed)
    panel = panel.copy()
    panel['month'] = pd.to_datetime(panel['date']).dt.to_period('M').astype(str)
    liquid = panel['liquid'] == 1
    pop = panel[liquid & (panel['fund_valid'] == 1) & panel['fwd_ret_252'].notna()].copy()
    meta = {'observations': int(len(pop)), 'months': int(pop['month'].nunique()), 'stocks': int(pop['ticker'].nunique()),
            'hit2_pct': round(float(pop['hit2'].mean() * 100), 2)}
    skip = {'ticker', 'date', 'month', 'group', 'liquid', 'fund_valid', 'n_quarters'} | {c for c in pop.columns if c.startswith(('fwd_', 'hit'))}
    feats = [c for c in pop.columns if c not in skip and pop[c].notna().mean() > 0.3]
    rows = {}
    for ft in feats:
        ic_r = month_ic(pop, ft, 'fwd_exc_252')
        ic_h = month_ic(pop, ft, 'hit2')
        if ic_r is None:
            continue
        q = quintile_stats(pop, ft, rng)
        rows[ft] = {'ic_excess_ret': round(ic_r['mean'], 4), 't_excess_ret': round(ic_r['t'], 2), 'pct_months_positive': round(ic_r['pos'] * 100, 0),
                    'ic_hit2': round(ic_h['mean'], 4) if ic_h else None, 't_hit2': round(ic_h['t'], 2) if ic_h else None,
                    'binary': _is_binary(pop[ft]), 'quantiles': q}
    seg = {}
    p = pop
    seg['eps'] = segment_table(p, {'BPA negativo (pérdidas)': p.eps_neg == 1, 'Giro de pérdidas a beneficios': p.eps_turn == 1,
                                   'BPA positivo y crece >=25%': p.eps_g25 == 1, 'BPA positivo y crece <25%': p.eps_low == 1,
                                   'BPA positivo pero cae': p.eps_fall == 1}, rng)
    rv = p.rev_yoy
    seg['ventas'] = segment_table(p, {'Ventas caen (<0%)': rv < 0, 'Ventas 0-10%': (rv >= 0) & (rv < .10), 'Ventas 10-20%': (rv >= .10) & (rv < .20),
                                      'Ventas 20-30%': (rv >= .20) & (rv < .30), 'Ventas 30-50%': (rv >= .30) & (rv < .50), 'Ventas >=50%': rv >= .50}, rng)
    prof, grow = p.ni_pos == 1, p.rev_yoy >= 0.20
    seg['etapa'] = segment_table(p, {'Rentable y crece >=20%': prof & grow, 'Rentable y crece <20%': prof & ~grow & p.rev_yoy.notna(),
                                     'No rentable y crece >=20%': ~prof & grow & p.ni_pos.notna(), 'No rentable y crece <20%': ~prof & ~grow & p.ni_pos.notna() & p.rev_yoy.notna()}, rng)
    seg['mercado_y_ventas'] = segment_table(p, {'Mercado alcista + ventas >=25%': (p.spy_up == 1) & (p.rev_yoy >= .25), 'Mercado bajista + ventas >=25%': (p.spy_up == 0) & (p.rev_yoy >= .25)}, rng)
    return {'meta': meta, 'features': rows, 'segments': seg, 'event_study': summarize_events(store_events),
            'winner_timing': summarize_timing(store_timing)}


def collect(frames, fund, spy_c, up, tk_group, grank):
    scores = pd.DataFrame({t: es.rs_score(f.Close) for t, f in frames.items()}).reindex(spy_c.index)
    liq = pd.DataFrame({t: (f.Close >= 5) & (f.Volume.rolling(50).mean() >= 300_000) for t, f in frames.items()}).reindex(spy_c.index).fillna(False)
    rank_df = scores.where(liq).rank(axis=1, pct=True) * 100
    del scores, liq
    panel = build_panel(frames, fund, spy_c, up, rank_df, grank, tk_group)
    store_events, store_timing = {}, {}
    for t, f in frames.items():
        rows = (fund.get(t) or {}).get('rows') or []
        if len(f) < 400 or not rows:
            continue
        qt = sec.quarter_table(rows)
        event_study_stock(f, spy_c, qt, store_events)
        ff, valid = sec.fund_features(rows, f.index)
        winner_timing_stock(f, ff, valid, store_timing)
    return panel, store_events, store_timing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=4000)
    ap.add_argument('--start', default='2012-06-01')
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--output', default='data/panel_study.json')
    ap.add_argument('--panel', default='data/panel.csv.gz')
    ap.add_argument('--sec-cache', default='data/sec_rows.json.gz')
    a = ap.parse_args()
    t0 = time.time()
    names = sb.universe()
    random.Random(a.seed).shuffle(names)
    lim = sec.RateLimiter(8)
    cmap = sec.cik_map(lim)
    cand = [t for t in names if t in cmap][:a.symbols]
    print(f'Universo {len(names)} · con CIK {sum(t in cmap for t in names)} · muestra {len(cand)}', flush=True)
    frames = sb.download(['SPY'] + cand, a.start)
    spy = frames.pop('SPY')
    up = sb.regime_series(spy)['spy_ma50_up']
    print(f'Precios de {len(frames)} acciones en {time.time()-t0:.0f}s', flush=True)
    fund, _ = sec.fetch_many(list(frames))
    print(f'SEC: {sum(1 for d in fund.values() if d["rows"])}/{len(frames)} con trimestres · {time.time()-t0:.0f}s', flush=True)
    Path(a.sec_cache).parent.mkdir(exist_ok=True)
    with gzip.open(a.sec_cache, 'wt', encoding='utf-8') as fh:
        json.dump(fund, fh)
    tk_group = fs.group_names(fund)
    grank, sizes = group_rank_matrix(frames, tk_group, spy.Close.index)
    panel, ev, tm = collect(frames, fund, spy.Close, up, tk_group, grank)
    print(f'Panel: {len(panel)} filas · {panel.ticker.nunique()} acciones · {time.time()-t0:.0f}s', flush=True)
    panel.to_csv(a.panel, index=False, compression='gzip', float_format='%.5g')
    res = analyze(panel, ev, tm)
    res['group_sizes'] = {g: int(n) for g, n in sizes.head(40).items()}
    res['panel_columns'] = list(panel.columns)
    res['seconds'] = round(time.time() - t0)
    res['generated_utc'] = datetime.now(timezone.utc).isoformat()
    print('RESUMEN_PANEL ' + json.dumps(res, ensure_ascii=False, default=str))
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps(res, ensure_ascii=False, default=str, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
