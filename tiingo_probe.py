"""Karryman · sondeo de Tiingo como fuente de acciones de EE. UU. con deslistadas (investigación).

1) Sin clave: lista pública de valores soportados (supported_tickers.zip) -> cuántas acciones, cuántas deslistadas, cobertura por años.
2) Con clave (variable de entorno TIINGO_API_KEY, secreto del repositorio): prueba de precios de una muestra de deslistadas y observación de los
   límites de la capa gratuita tal como los devuelve la propia API. La clave nunca se imprime.
No hace nada más que leer datos públicos de Tiingo.
"""
import io
import json
import os
import random
import sys
import time
import zipfile

import pandas as pd
import requests

LIST_URL = 'https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip'
API = 'https://api.tiingo.com'
US_EX = {'NYSE', 'NASDAQ', 'NYSE MKT', 'NYSE ARCA', 'AMEX', 'BATS', 'NYSE NAT'}


def lista():
    r = requests.get(LIST_URL, timeout=120, headers={'User-Agent': 'karryman-research/1.0'})
    out = {'http': r.status_code, 'bytes': len(r.content)}
    if r.status_code != 200:
        return out, None
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df = pd.read_csv(z.open(z.namelist()[0]), dtype=str)
    out['columnas'] = list(df.columns)
    out['filas'] = int(len(df))
    df['start'] = pd.to_datetime(df.get('startDate'), errors='coerce')
    df['end'] = pd.to_datetime(df.get('endDate'), errors='coerce')
    out['por_assetType'] = df['assetType'].value_counts(dropna=False).head(8).to_dict()
    out['por_exchange'] = df['exchange'].value_counts(dropna=False).head(15).to_dict()
    st = df[(df['assetType'] == 'Stock') & (df['exchange'].isin(US_EX)) & df['start'].notna() & df['end'].notna()].copy()
    last = df['end'].max()
    out['fecha_final_maxima_en_lista'] = str(last.date())
    st['activa'] = st['end'] >= last - pd.Timedelta(days=7)
    out['acciones_us'] = {'total': int(len(st)), 'activas': int(st['activa'].sum()), 'deslistadas_o_inactivas': int((~st['activa']).sum()),
                          'primer_inicio': str(st['start'].min().date())}
    por = {}
    for y in (2000, 2005, 2010, 2015, 2020):
        d = pd.Timestamp(f'{y}-01-01')
        por[str(y)] = int(((st['start'] <= d) & (st['end'] >= d)).sum())
    out['acciones_us_cotizando_el_1_enero'] = por
    out['deslistadas_por_ano_de_fin'] = {str(k): int(v) for k, v in st[~st['activa']]['end'].dt.year.value_counts().sort_index().items() if k >= 2005}
    return out, st


def precios(st, n=25, seed=3):
    key = os.environ.get('TIINGO_API_KEY', '').strip()
    if not key:
        return {'estado': 'sin clave (TIINGO_API_KEY no definida): prueba de precios no ejecutada'}
    h = {'Authorization': f'Token {key}', 'Content-Type': 'application/json'}
    out = {'estado': 'con clave'}
    r = requests.get(f'{API}/api/test', headers=h, timeout=30)
    out['test_clave'] = {'http': r.status_code, 'texto': r.text[:150]}
    if r.status_code != 200:
        return out
    cand = st[(~st['activa']) & (st['end'] >= '2010-01-01') & (st['end'] <= '2024-12-31')]
    sample = cand.sample(n=min(n, len(cand)), random_state=seed)
    rows = []
    for _, s in sample.iterrows():
        t0 = time.time()
        rr = requests.get(f'{API}/tiingo/daily/{s["ticker"]}/prices', headers=h, timeout=60,
                          params={'startDate': '2009-01-01', 'endDate': '2026-11-01', 'format': 'json'})
        info = {'ticker': s['ticker'], 'fin_en_lista': str(s['end'].date()), 'http': rr.status_code, 'seg': round(time.time() - t0, 2)}
        for hk in ('x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'retry-after'):
            if hk in rr.headers:
                info[hk] = rr.headers[hk]
        if rr.status_code == 200:
            try:
                d = rr.json()
                info.update({'filas': len(d), 'primer_dia': d[0]['date'][:10] if d else None, 'ultimo_dia': d[-1]['date'][:10] if d else None,
                             'campos': sorted(d[0].keys()) if d else None})
            except Exception as e:
                info['error_json'] = str(e)[:80]
        else:
            info['texto'] = rr.text[:200]
        rows.append(info)
        if rr.status_code == 429:
            break
        time.sleep(0.5)
    out['muestra'] = rows
    ok = [x for x in rows if x['http'] == 200 and x.get('filas')]
    out['resumen'] = {'probadas': len(rows), 'con_precios': len(ok), 'http_distintos': sorted({x['http'] for x in rows}),
                      'filas_medias': round(sum(x['filas'] for x in ok) / max(len(ok), 1), 1)}
    return out


def main():
    res = {'commit': os.environ.get('GITHUB_SHA')}
    try:
        res['lista_publica'], st = lista()
    except Exception as e:
        res['lista_publica'], st = {'error': f'{type(e).__name__}: {str(e)[:200]}'}, None
    if st is not None:
        try:
            res['precios_con_clave'] = precios(st)
        except Exception as e:
            res['precios_con_clave'] = {'error': f'{type(e).__name__}: {str(e)[:200]}'}
    print('RESUMEN_TIINGO ' + json.dumps(res, default=str), flush=True)
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_tiingo.json'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(res, open(path, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
