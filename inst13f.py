"""Karryman · posiciones institucionales (Form 13F, SEC): quién compra y quién vende cada acción.

Cada trimestre los gestores de más de 100 M$ declaran sus posiciones 45 días después del cierre.
- read_holdings(zip): posiciones por gestor y CUSIP (solo acciones, sin opciones, sin enmiendas).
- quarter_metrics(cur, prev): por CUSIP, acciones y gestores totales y movimiento neto frente al trimestre anterior:
  nuevos gestores, gestores que salen, que aumentan, que reducen y ratio de compradores netos.
- map_cusips(): CUSIP -> ticker con OpenFIGI.
Los datos de un trimestre son públicos desde el cierre del plazo (periodo + 46 días): ese es el día a partir del cual
pueden usarse sin mirar al futuro. Investigación únicamente.
"""
import io
import re
import sys
import time
import zipfile
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

import sec_fundamentals as sec

PAGE = 'https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets'
BASE = 'https://www.sec.gov'
AVAILABLE_AFTER_DAYS = 46


def list_datasets(limiter):
    limiter.wait()
    r = requests.get(PAGE, headers=sec._ua(), timeout=60)
    r.raise_for_status()
    links = sorted(set(re.findall(r'(/files/structureddata/data/form-13f-data-sets/[A-Za-z0-9\-_]+_form13f\.zip)', r.text)))
    return [BASE + x for x in links]


def download(url, limiter, dest):
    limiter.wait()
    with requests.get(url, headers=sec._ua(), timeout=300, stream=True) as r:
        r.raise_for_status()
        size = 0
        with open(dest, 'wb') as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
                size += len(chunk)
    return size


def _read_tsv(zf, name, usecols=None, chunksize=None):
    cand = [n for n in zf.namelist() if n.upper().endswith(name)]
    if not cand:
        raise KeyError(f'{name} no está en el zip: {zf.namelist()}')
    kw = dict(sep='\t', dtype=str, usecols=lambda c: usecols is None or c.upper() in usecols, low_memory=False)
    return pd.read_csv(zf.open(cand[0]), chunksize=chunksize, **kw)


def read_holdings(path):
    """DataFrame [cik, cusip, shares, period] con las posiciones en acciones de cada gestor (solo 13F-HR originales)."""
    with zipfile.ZipFile(path) as zf:
        sub = _read_tsv(zf, 'SUBMISSION.TSV', {'ACCESSION_NUMBER', 'FILING_DATE', 'SUBMISSIONTYPE', 'CIK', 'PERIODOFREPORT'})
        sub.columns = [c.upper() for c in sub.columns]
        sub = sub[sub['SUBMISSIONTYPE'].str.upper().eq('13F-HR')]
        parts = []
        for ch in _read_tsv(zf, 'INFOTABLE.TSV', {'ACCESSION_NUMBER', 'CUSIP', 'SSHPRNAMT', 'SSHPRNAMTTYPE', 'PUTCALL'}, chunksize=1_000_000):
            ch.columns = [c.upper() for c in ch.columns]
            ch = ch[ch['ACCESSION_NUMBER'].isin(sub['ACCESSION_NUMBER'])]
            if 'SSHPRNAMTTYPE' in ch:
                ch = ch[ch['SSHPRNAMTTYPE'].fillna('SH').str.upper().eq('SH')]
            if 'PUTCALL' in ch:
                ch = ch[ch['PUTCALL'].isna() | ch['PUTCALL'].astype(str).str.strip().eq('')]
            ch = ch.assign(shares=pd.to_numeric(ch['SSHPRNAMT'], errors='coerce'), cusip=ch['CUSIP'].str.strip().str.upper())
            parts.append(ch[['ACCESSION_NUMBER', 'cusip', 'shares']].dropna())
        h = pd.concat(parts, ignore_index=True)
    h = h.merge(sub[['ACCESSION_NUMBER', 'CIK', 'PERIODOFREPORT']], on='ACCESSION_NUMBER', how='inner')
    h = h.rename(columns={'CIK': 'cik', 'PERIODOFREPORT': 'period'})
    h['period'] = pd.to_datetime(h['period'], format='mixed', errors='coerce')
    h = h.groupby(['period', 'cik', 'cusip'], as_index=False)['shares'].sum()
    return h[h['shares'] > 0]


def available_date(period):
    return pd.Timestamp(period) + pd.Timedelta(days=AVAILABLE_AFTER_DAYS)


def quarter_metrics(cur, prev=None):
    """Métricas por CUSIP de un trimestre (cur) y su movimiento frente al anterior (prev)."""
    g = cur.groupby('cusip')
    m = pd.DataFrame({'inst_shares': g['shares'].sum(), 'inst_holders': g['cik'].nunique()})
    if prev is not None and len(prev):
        j = cur[['cik', 'cusip', 'shares']].merge(prev[['cik', 'cusip', 'shares']], on=['cik', 'cusip'], how='outer', suffixes=('', '_p'))
        s, sp = j['shares'].fillna(0), j['shares_p'].fillna(0)
        j['new'], j['closed'] = (sp == 0) & (s > 0), (s == 0) & (sp > 0)
        j['added'], j['reduced'] = (sp > 0) & (s > sp), (s > 0) & (s < sp)
        j['delta'] = s - sp
        gj = j.groupby('cusip')
        mv = pd.DataFrame({'new_holders': gj['new'].sum(), 'closed_holders': gj['closed'].sum(), 'added_holders': gj['added'].sum(),
                           'reduced_holders': gj['reduced'].sum(), 'net_shares': gj['delta'].sum(), 'prev_shares': sp.groupby(j['cusip']).sum()})
        m = m.join(mv, how='left')
        buyers = m['new_holders'] + m['added_holders']
        sellers = m['closed_holders'] + m['reduced_holders']
        m['buyer_ratio'] = buyers / (buyers + sellers).replace(0, np.nan)
        m['shares_chg_pct'] = m['net_shares'] / m['prev_shares'].replace(0, np.nan)
        prev_h = prev.groupby('cusip')['cik'].nunique()
        m['holders_chg_pct'] = (m['inst_holders'] / prev_h.reindex(m.index) - 1).replace([np.inf, -np.inf], np.nan)
    return m.reset_index()


def map_cusips(cusips, batch=10, pause=2.6):
    """CUSIP -> ticker de acciones de EE. UU. con OpenFIGI (sin clave: 10 CUSIP por petición, 25 peticiones/min)."""
    out = {}
    cusips = list(cusips)
    for k in range(0, len(cusips), batch):
        part = cusips[k:k + batch]
        jobs = [{'idType': 'ID_CUSIP', 'idValue': c, 'exchCode': 'US'} for c in part]
        for attempt in range(4):
            r = requests.post('https://api.openfigi.com/v3/mapping', json=jobs, headers={'Content-Type': 'application/json'}, timeout=60)
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            break
        if r.status_code != 200:
            continue
        for c, res in zip(part, r.json()):
            for d in res.get('data') or []:
                if d.get('marketSector') == 'Equity' and d.get('securityType') in ('Common Stock', 'REIT', 'ADR', 'Depositary Receipt', 'Tracking Stk'):
                    out[c] = d.get('ticker')
                    break
        time.sleep(pause)
    return out


def smoke():
    lim = sec.RateLimiter(5)
    links = list_datasets(lim)
    print(f'conjuntos 13F encontrados: {len(links)}')
    for u in links[:2] + links[-3:]:
        print('  ', u)
    if not links:
        return
    import tempfile
    t0 = time.time()
    got = []
    with tempfile.TemporaryDirectory() as tmp:
        for u in links[-2:][::-1]:   # los dos más recientes
            dest = f'{tmp}/{u.split("/")[-1]}'
            size = download(u, lim, dest)
            print(f'descargado {u.split("/")[-1]}: {size/1e6:.0f} MB en {time.time()-t0:.0f}s')
            with zipfile.ZipFile(dest) as zf:
                print('  ficheros:', [(n, zf.getinfo(n).file_size // 1_000_000) for n in zf.namelist()])
                for nm in ('SUBMISSION.TSV', 'INFOTABLE.TSV', 'COVERPAGE.TSV'):
                    hit = [n for n in zf.namelist() if n.upper().endswith(nm)]
                    if hit:
                        print(f'  {nm} columnas:', pd.read_csv(zf.open(hit[0]), sep='\t', nrows=2, dtype=str).columns.tolist())
            h = read_holdings(dest)
            print(f'  posiciones: {len(h):,} · gestores {h.cik.nunique():,} · CUSIP {h.cusip.nunique():,} · periodos {sorted(h.period.dropna().dt.date.astype(str).unique())[-3:]} · {time.time()-t0:.0f}s')
            got.append(h)
    cur, prev = got[0], got[1]
    cur = cur[cur.period == cur.period.max()]
    prev = prev[prev.period == prev.period.max()]
    m = quarter_metrics(cur, prev).sort_values('inst_shares', ascending=False)
    print('top 8 por acciones institucionales:\n', m.head(8).to_string())
    tick = map_cusips(m.head(30)['cusip'])
    print('OpenFIGI (30 CUSIP):', len(tick), 'mapeados ·', dict(list(tick.items())[:10]))


if __name__ == '__main__':
    if '--smoke' in sys.argv:
        smoke()
