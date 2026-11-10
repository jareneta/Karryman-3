"""Karryman · clasificación sectorial (SIC de la SEC) del S&P 500 point-in-time y medición de su cobertura (docs/V24_H9_CAIDAS_TECH.md).
Investigación únicamente. Necesita el contacto de la SEC en la variable SEC_CONTACT (secreto del repositorio; no se imprime)."""
import json
import os
import re
import sys
import time

import pandas as pd

import sec_fundamentals as sec
import v24_backtest as vb

TECH_RANGES = [(3570, 3579), (3660, 3679), (7370, 7379)]


def base_ticker(label):
    return re.sub(r'-\d{6}(_.*)?$', '', str(label)).upper()


def is_tech_sic(sic):
    try:
        v = int(str(sic))
    except (TypeError, ValueError):
        return False
    return any(a <= v <= b for a, b in TECH_RANGES)


def main():
    t0 = time.time()
    paths, sha = vb.download_sp500data('snapshot-2026-11', names=('membership_intervals.parquet',))
    iv = pd.read_parquet(paths['membership_intervals.parquet'])
    iv = iv[iv['end'].isna() | (iv['end'] >= pd.Timestamp('1996-01-01'))].copy()
    iv['base'] = iv['ticker'].map(base_ticker)
    iv['activa'] = iv['end'].isna() | (iv['end'] >= pd.Timestamp('2026-01-01'))
    lim = sec.RateLimiter(8)
    cmap = sec.cik_map(lim)
    iv['cik'] = iv['base'].map(cmap)
    mapped = iv.dropna(subset=['cik']).copy()
    sic = {}
    for k, cik in enumerate(sorted(set(int(x) for x in mapped['cik']))):
        js = sec.fetch_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json', lim) or {}
        sic[cik] = str(js.get('sic') or '')
        if k % 200 == 0:
            print(f'  {k} CIK consultados · {time.time()-t0:.0f}s', flush=True)
    iv['sic'] = iv['cik'].map(lambda x: sic.get(int(x), '') if pd.notna(x) else '')
    iv['clasificada'] = iv['sic'].astype(str).str.len() > 0
    iv['tech'] = iv['sic'].map(is_tech_sic)

    def cov(df):
        n = len(df)
        return {'intervalos': int(n), 'con_cik': int(df['cik'].notna().sum()), 'clasificadas_con_sic': int(df['clasificada'].sum()),
                'pct_clasificadas': round(float(df['clasificada'].mean() * 100), 1) if n else None, 'tecnologicas': int(df['tech'].sum())}
    out = {'tag': 'snapshot-2026-11', 'activas': cov(iv[iv['activa']]), 'deslistadas': cov(iv[~iv['activa']]), 'total': cov(iv)}
    des = iv[~iv['activa']]
    out['deslistadas_tecnologicas_ejemplos_clasificadas'] = sorted(set(des[des['tech']]['base']))[:40]
    out['deslistadas_sin_clasificar_ejemplos'] = sorted(set(des[~des['clasificada']]['base']))[:60]
    out['regla_cobertura_70pct'] = {'umbral': 70.0, 'cumple': bool((out['deslistadas']['pct_clasificadas'] or 0) >= 70.0)}
    out['mapa'] = {r.ticker: {'cik': int(r.cik) if pd.notna(r.cik) else None, 'sic': r.sic, 'tech': bool(r.tech)} for r in iv.itertuples()}
    print('RESUMEN_SIC ' + json.dumps({k: v for k, v in out.items() if k != 'mapa'}, default=str), flush=True)
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_sic.json'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(out, open(path, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
