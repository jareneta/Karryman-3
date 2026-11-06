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
    return q


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
    rev, eps = _flows(js, REV_TAGS, 'USD'), _flows(js, EPS_TAGS, 'USD/shares')
    rows = []
    for end in sorted(set(rev) | set(eps)):
        rows.append({'end': end, 'rev': rev.get(end, (None, None))[1], 'rev_filed': rev.get(end, (None, None))[0],
                     'eps': eps.get(end, (None, None))[1], 'eps_filed': eps.get(end, (None, None))[0]})
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
