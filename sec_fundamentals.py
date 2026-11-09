"""Karryman · fundamentales históricos desde la SEC (EDGAR XBRL), con fecha de presentación.

- Ingresos y beneficio por acción diluido TRIMESTRALES (el 4.º trimestre se deriva: año - 9 meses).
- Cada valor se usa solo desde el día hábil siguiente a su presentación (sin mirar al futuro) y es
  el PRIMER valor presentado (no el reexpresado).
- Crecimiento interanual, aceleración y banderas tipo Minervini/CANSLIM.
- Código SIC (grupo de industria) desde la API de envíos.
Investigación únicamente. Respeta el límite de la SEC (<= 10 peticiones/s).
"""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd
import requests



def _ua():
    contact = os.environ.get('SEC_CONTACT', '').strip()
    if '@' not in contact:
        raise Blocked('Falta SEC_CONTACT: la SEC exige un contacto en la cabecera User-Agent')
    return {'User-Agent': f'KarrymanResearch {contact}', 'Accept-Encoding': 'gzip, deflate'}


REV_TAGS = ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet',
            'RevenueFromContractWithCustomerIncludingAssessedTax', 'SalesRevenueGoodsNet']
EPS_TAGS = ['EarningsPerShareDiluted', 'EarningsPerShareBasic']
FLOW_TAGS = {
    'gp': (['GrossProfit'], 'USD'),
    'oi': (['OperatingIncomeLoss'], 'USD'),
    'ni': (['NetIncomeLoss', 'ProfitLoss'], 'USD'),
    'cfo': (['NetCashProvidedByUsedInOperatingActivities', 'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'], 'USD'),
    'sh': (['WeightedAverageNumberOfDilutedSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic'], 'shares'),
}
INSTANT_TAGS = {
    'assets': (['Assets'], 'USD'),
    'liab': (['Liabilities'], 'USD'),
    'equity': (['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'], 'USD'),
    'cash': (['CashAndCashEquivalentsAtCarryingValue'], 'USD'),
}
STALE_DAYS = 140


class Blocked(RuntimeError):
    pass


class RateLimiter:
    def __init__(self, per_sec):
        self.gap, self.lock, self.t = 1.0 / per_sec, threading.Lock(), 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            wait = self.t + self.gap - now
            if wait > 0:
                time.sleep(wait)
            self.t = time.time()


def fetch_json(url, limiter, retries=4):
    last = None
    for k in range(retries):
        limiter.wait()
        try:
            r = requests.get(url, headers=_ua(), timeout=90)
        except requests.RequestException as exc:
            last = str(exc)[:80]
            time.sleep(2 * (k + 1))
            continue
        if r.status_code == 404:
            return None
        if r.status_code in (403, 429):
            last = f'HTTP {r.status_code}'
            time.sleep(5 * (k + 1))
            continue
        if r.status_code != 200:
            last = f'HTTP {r.status_code}'
            time.sleep(2)
            continue
        return r.json()
    raise Blocked(f'{url}: {last}')


def cik_map(limiter):
    js = fetch_json('https://www.sec.gov/files/company_tickers.json', limiter)
    return {v['ticker'].upper(): int(v['cik_str']) for v in js.values()}


# ------------------------------------------------------------------ extracción
def _d(s):
    return date.fromisoformat(s)


def _quarters(entries):
    """{fin_de_trimestre: (presentado, valor)} con Q4 derivado de anual - 9 meses."""
    best = {}
    for e in entries:
        s, en, f, v = e.get('start'), e.get('end'), e.get('filed'), e.get('val')
        if not (s and en and f) or v is None:
            continue
        k = (s, en)
        if k not in best or f < best[k][0]:
            best[k] = (f, float(v))
    q, ytd9, fy = {}, {}, {}
    for (s, en), (f, v) in best.items():
        days = (_d(en) - _d(s)).days
        if 75 <= days <= 105:
            q[en] = (f, v)
        elif 255 <= days <= 290:
            ytd9[s] = (en, f, v)
        elif 350 <= days <= 380:
            fy[s] = (en, f, v)
    for s, (en, f, v) in fy.items():
        if en in q:
            continue
        if s in ytd9:
            q[en] = (f, v - ytd9[s][2])
            continue
        inside = [(e2, val) for e2, (f2, val) in q.items() if _d(s) < _d(e2) < _d(en) and (_d(en) - _d(e2)).days > 60]
        if len(inside) == 3:
            q[en] = (f, v - sum(x[1] for x in inside))
    # Flujos que solo se presentan acumulados (p. ej. caja operativa): Q2 = 6M - Q1, Q3 = 9M - 6M
    ytd6 = {}
    for (s, en), (f, v) in best.items():
        if 165 <= (_d(en) - _d(s)).days <= 200:
            ytd6[s] = (en, f, v)
    q1 = {s: (en, f, v) for (s, en), (f, v) in best.items() if 75 <= (_d(en) - _d(s)).days <= 105}
    for s, (en6, f6, v6) in ytd6.items():
        if en6 not in q and s in q1:
            q[en6] = (f6, v6 - q1[s][2])
    for s, (en9, f9, v9) in ytd9.items():
        if en9 in q:
            continue
        if s in ytd6:
            q[en9] = (f9, v9 - ytd6[s][2])
    return q


def _instants(js, tags, unit):
    """{fecha: (presentado, valor)} de partidas de balance (primer valor presentado)."""
    gaap = js.get('facts', {}).get('us-gaap', {})
    merged = {}
    for tag in tags:
        ent = gaap.get(tag, {}).get('units', {}).get(unit)
        if not ent:
            continue
        best = {}
        for e in ent:
            en, f, v = e.get('end'), e.get('filed'), e.get('val')
            if not (en and f) or v is None or e.get('start'):
                continue
            if en not in best or f < best[en][0]:
                best[en] = (f, float(v))
        for en, fv in best.items():
            merged.setdefault(en, fv)
    return merged


def _flows(js, tags, unit):
    gaap = js.get('facts', {}).get('us-gaap', {})
    merged = {}
    for tag in tags:
        ent = gaap.get(tag, {}).get('units', {}).get(unit)
        if not ent:
            continue
        for end, fv in _quarters(ent).items():
            merged.setdefault(end, fv)
    return merged


def parse_companyfacts(js):
    flows = {'rev': _flows(js, REV_TAGS, 'USD'), 'eps': _flows(js, EPS_TAGS, 'USD/shares')}
    for k, (tags, unit) in FLOW_TAGS.items():
        flows[k] = _flows(js, tags, unit)
    inst = {k: _instants(js, tags, unit) for k, (tags, unit) in INSTANT_TAGS.items()}
    ends = sorted(set().union(*[set(v) for v in flows.values()]))
    rows = []
    for end in ends:
        row = {'end': end}
        for k, m in flows.items():
            f, v = m.get(end, (None, None))
            row[k], row[k + '_filed'] = v, f
        for k, m in inst.items():
            f, v = m.get(end, (None, None))
            row[k], row[k + '_filed'] = v, f
        rows.append(row)
    return rows


# ------------------------------------------------------------------ crecimiento
def growth_points(rows, key, eps=False):
    """[(presentado, g, g_previo)] con g = crecimiento interanual del trimestre."""
    pts = [(r['end'], r[key], r[key + '_filed']) for r in rows if r.get(key) is not None and r.get(key + '_filed')]
    pts.sort()
    vals = {e: v for e, v, _ in pts}
    out, prev_end, prev_g = [], None, None
    for e, v, f in pts:
        prior = None
        for e0, v0 in vals.items():
            if 350 <= (_d(e) - _d(e0)).days <= 380:
                prior = v0
                break
        if prior is None:
            g = np.nan
        elif eps:
            g = v / prior - 1 if prior > 0 else (9.99 if v > 0 else -1.0)
        else:
            g = v / prior - 1 if prior > 0 else np.nan
        gp = prev_g if (prev_end and 60 <= (_d(e) - _d(prev_end)).days <= 130) else np.nan
        out.append((f, g, gp))
        prev_end, prev_g = e, g
    return out


def _series(points, index, col):
    if not points:
        return pd.Series(np.nan, index=index)
    s = pd.Series([p[col] for p in points], index=pd.to_datetime([p[0] for p in points]) + pd.offsets.BDay(1))
    s = s[~s.index.duplicated(keep='last')].sort_index()
    return s.reindex(index, method='ffill')


def daily_flags(rows, index):
    """Banderas fundamentales alineadas con el calendario de precios (disponibles tras presentar)."""
    ep, rp = growth_points(rows, 'eps', eps=True), growth_points(rows, 'rev')
    eg, egp = _series(ep, index, 1), _series(ep, index, 2)
    rg, rgp = _series(rp, index, 1), _series(rp, index, 2)
    if ep or rp:
        filed = pd.DatetimeIndex(sorted(set(pd.to_datetime([p[0] for p in ep + rp]) + pd.offsets.BDay(1))))
        last = pd.Series(filed, index=filed).reindex(index, method='ffill')
        age = (pd.Series(index, index=index) - last).dt.days
        valid = (age <= STALE_DAYS).fillna(False)
    else:
        valid = pd.Series(False, index=index)
    eps25 = valid & (eg >= 0.25)
    eps_acc = eps25 & (eg > egp)
    rev25 = valid & (rg >= 0.25)
    rev_acc = valid & (rg >= 0.20) & (rg > rgp)
    out = {'EPS +25%': eps25, 'EPS +25% y acelera': eps_acc, 'Ingresos +25%': rev25, 'Ingresos +20% y aceleran': rev_acc,
           'EPS e ingresos +25%': eps25 & rev25, 'Doble aceleración (EPS e ingresos)': eps_acc & rev_acc}
    covered = valid & eg.notna() & rg.notna()
    return {k: v.fillna(False).to_numpy(bool) for k, v in out.items()}, covered.to_numpy(bool)


# ------------------------------------------------------------------ variables ampliadas
def _num(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)


def _ratio(a, b):
    a, b = _num(a), _num(b)
    return a / b if a is not None and b not in (None, 0.0) else np.nan


def _growth(v, prior):
    v, prior = _num(v), _num(prior)
    return v / prior - 1 if v is not None and prior is not None and prior > 0 else np.nan


FEATURES = ['rev_yoy', 'rev_yoy_prev', 'rev_accel', 'rev_streak', 'gm', 'gm_chg', 'om', 'om_chg', 'oi_turn', 'op_leverage',
            'eps_neg', 'eps_turn', 'eps_g25', 'eps_low', 'eps_fall', 'ni_margin', 'ni_pos', 'cfo_margin', 'cfo_pos',
            'dil_chg', 'equity_pos', 'lev', 'cash_assets', 'n_quarters', 'ni_gt_cfo', 'sh']


def quarter_table(rows):
    """Una fila por trimestre con variables y banderas de evento. Índice = día en que ya es público."""
    rows = sorted(rows, key=lambda r: r['end'])
    by_end = {r['end']: r for r in rows}

    def prior_year(r):
        for e0, r0 in by_end.items():
            if 350 <= (_d(r['end']) - _d(e0)).days <= 380:
                return r0
        return None

    out, rev_yoy_hist = [], {}
    for i, r in enumerate(rows):
        p = prior_year(r)
        pv = lambda k: p.get(k) if p else None
        rev_yoy = _growth(r.get('rev'), pv('rev'))
        rev_yoy_hist[r['end']] = rev_yoy
        prev = rows[i - 1] if i else None
        rev_yoy_prev = rev_yoy_hist.get(prev['end'], np.nan) if prev and 60 <= (_d(r['end']) - _d(prev['end'])).days <= 130 else np.nan
        streak, k = 0, i
        while k >= 0 and streak < 4 and rev_yoy_hist.get(rows[k]['end'], np.nan) >= 0.20:
            streak, k = streak + 1, k - 1
        rev, gp, oi, ni, cfo = r.get('rev'), r.get('gp'), r.get('oi'), r.get('ni'), r.get('cfo')
        gm, om = _ratio(gp, rev), _ratio(oi, rev)
        gm_p, om_p = _ratio(pv('gp'), pv('rev')), _ratio(pv('oi'), pv('rev'))
        eps, eps_p = _num(r.get('eps')), _num(pv('eps'))
        oi_g = _growth(oi, pv('oi'))
        have_eps = eps is not None and eps_p is not None
        eps_g = (eps / eps_p - 1) if (have_eps and eps_p > 0) else np.nan
        filed = [r[k + '_filed'] for k in ('rev', 'eps', 'gp', 'oi', 'ni', 'cfo', 'sh', 'assets', 'liab', 'equity', 'cash') if r.get(k + '_filed')]
        if not filed:
            continue
        sh, sh_p = _num(r.get('sh')), _num(pv('sh'))
        adjacent = prev is not None and 60 <= (_d(r['end']) - _d(prev['end'])).days <= 130
        prev_eps = _num(prev.get('eps')) if adjacent else None
        prev_oi = _num(prev.get('oi')) if adjacent else None
        out.append({
            'avail': max(filed), 'end': r['end'], 'rev_yoy': rev_yoy, 'rev_yoy_prev': rev_yoy_prev,
            'rev_accel': rev_yoy - rev_yoy_prev if not (np.isnan(rev_yoy) or np.isnan(rev_yoy_prev)) else np.nan,
            'rev_streak': float(streak), 'gm': gm, 'gm_chg': (gm - gm_p) * 100 if not (np.isnan(gm) or np.isnan(gm_p)) else np.nan,
            'om': om, 'om_chg': (om - om_p) * 100 if not (np.isnan(om) or np.isnan(om_p)) else np.nan,
            'oi_turn': float(_num(oi) is not None and oi > 0 and _num(pv('oi')) is not None and pv('oi') <= 0),
            'op_leverage': float(_num(oi) is not None and oi > 0 and not np.isnan(oi_g) and not np.isnan(rev_yoy) and rev_yoy > 0 and oi_g > rev_yoy),
            # BPA segmentado en situaciones excluyentes
            'eps_neg': float(eps is not None and eps < 0),
            'eps_turn': float(have_eps and eps > 0 and eps_p <= 0),
            'eps_g25': float(have_eps and eps > 0 and eps_p > 0 and eps_g >= 0.25),
            'eps_low': float(have_eps and eps > 0 and eps_p > 0 and 0 <= eps_g < 0.25),
            'eps_fall': float(have_eps and eps > 0 and eps_p > 0 and eps_g < 0),
            'ni_margin': _ratio(ni, rev), 'ni_pos': float(_num(ni) is not None and ni > 0),
            'cfo_margin': _ratio(cfo, rev), 'cfo_pos': float(_num(cfo) is not None and cfo > 0),
            'dil_chg': (sh / sh_p - 1) if (sh and sh_p and sh_p > 0) else np.nan,
            'equity_pos': float(_num(r.get('equity')) is not None and r['equity'] > 0),
            'lev': _ratio(r.get('liab'), r.get('assets')), 'cash_assets': _ratio(r.get('cash'), r.get('assets')),
            'n_quarters': float(i + 1), 'sh': sh if sh else np.nan,
            'ni_gt_cfo': float(_num(ni) is not None and _num(cfo) is not None and ni > 0 and ni > cfo),
            # eventos (para el estudio de anticipación)
            'ev_rev_infl': float(rev_yoy >= 0.25 and (not np.isnan(rev_yoy_prev)) and rev_yoy_prev < 0.15),
            'ev_rev_accel': float(rev_yoy >= 0.20 and (not np.isnan(rev_yoy_prev)) and rev_yoy - rev_yoy_prev >= 0.10),
            'ev_eps_turn': float(eps is not None and eps > 0 and prev_eps is not None and prev_eps <= 0),
            'ev_oi_turn': float(_num(oi) is not None and oi > 0 and prev_oi is not None and prev_oi <= 0),
            'ev_streak2': float(streak == 2 and rev_yoy >= 0.25)})
    return pd.DataFrame(out)


def fund_features(rows, index):
    """Variables fundamentales diarias (disponibles el día hábil siguiente a presentar) + máscara de validez."""
    qt = quarter_table(rows)
    cols = FEATURES
    if qt.empty:
        return pd.DataFrame(np.nan, index=index, columns=cols), np.zeros(len(index), dtype=bool)
    qt['avail_ts'] = pd.to_datetime(qt['avail']) + pd.offsets.BDay(1)
    qt = qt.sort_values('avail_ts').drop_duplicates('avail_ts', keep='last').set_index('avail_ts')
    daily = qt[cols].reindex(index, method='ffill')
    last = pd.Series(qt.index, index=qt.index).reindex(index, method='ffill')
    age = (pd.Series(index, index=index) - last).dt.days
    valid = (age <= STALE_DAYS).fillna(False)
    return daily, valid.to_numpy(bool)


# ------------------------------------------------------------------ descarga
def fetch_company(ticker, cik, limiter):
    cf = fetch_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json', limiter)
    rows = parse_companyfacts(cf) if cf else []
    sub = fetch_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', limiter) or {}
    return {'rows': rows, 'sic': str(sub.get('sic') or ''), 'sic_desc': sub.get('sicDescription') or ''}


def fetch_many(tickers, per_sec=8, workers=6, progress=200):
    lim = RateLimiter(per_sec)
    cmap = cik_map(lim)
    todo = [(t, cmap[t]) for t in tickers if t in cmap]
    out, done = {}, [0]
    lock = threading.Lock()

    def job(tc):
        t, c = tc
        try:
            res = fetch_company(t, c, lim)
        except Blocked:
            raise
        except Exception as exc:
            res = {'rows': [], 'sic': '', 'sic_desc': '', 'error': str(exc)[:80]}
        with lock:
            out[t] = res
            done[0] += 1
            if done[0] % progress == 0:
                print(f'  SEC {done[0]}/{len(todo)}', flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(job, todo))
    return out, len(cmap)


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        lim = RateLimiter(6)
        cm = cik_map(lim)
        print('tickers con CIK:', len(cm))
        for t in ('NVDA', 'CRWD', 'AAPL', 'SMCI', 'DAVE'):
            if t not in cm:
                print(t, 'sin CIK')
                continue
            r = fetch_company(t, cm[t], lim)
            rows = r['rows']
            print(f"{t}: {len(rows)} trimestres, SIC {r['sic']} {r['sic_desc']}")
            for row in rows[-6:]:
                print('   ', row)
            idx = pd.bdate_range('2023-01-02', '2026-11-05')
            fl, cov = daily_flags(rows, idx)
            print('    cobertura', round(float(cov.mean()) * 100), '% · EPS acelera', round(float(fl['EPS +25% y acelera'].mean()) * 100),
                  '% · doble aceleración', round(float(fl['Doble aceleración (EPS e ingresos)'].mean()) * 100), '%')
