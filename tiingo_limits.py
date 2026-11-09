"""Karryman · medición de límites y calidad de Tiingo para un universo amplio de acciones de EE. UU. (investigación).
Descarga series de una muestra de acciones ordinarias (activas y deslistadas) hasta el primer error de límite o hasta MAX_REQ.
NO guarda precios (los términos de Tiingo restringen la redistribución): solo estadísticas de acceso y calidad. La clave nunca se imprime."""
import json
import os
import random
import re
import sys
import time

import pandas as pd
import requests

import tiingo_probe as tp

MAX_REQ = 350
EXCL5 = set('WURFY')


def is_common(ticker):
    """Heurística sobre el símbolo (la lista de Tiingo no distingue clases de acción)."""
    t = str(ticker)
    if not re.fullmatch(r'[A-Z]{1,5}', t):
        return False
    return not (len(t) == 5 and t[-1] in EXCL5)


def common_universe(st):
    return st[st['ticker'].map(is_common)].copy()


def main():
    key = os.environ.get('TIINGO_API_KEY', '').strip()
    out = {'commit': os.environ.get('GITHUB_SHA')}
    info, st = tp.lista()
    out['lista'] = {'acciones_us': info.get('acciones_us')}
    if st is None or not key:
        out['estado'] = 'sin lista o sin clave'
        print('RESUMEN_TIINGO_LIMITES ' + json.dumps(out, default=str), flush=True)
        return
    cu = common_universe(st)
    out['universo_comun'] = {'total': int(len(cu)), 'activas': int(cu['activa'].sum()), 'inactivas': int((~cu['activa']).sum()),
                             'cotizando_1ene': {str(y): int(((cu['start'] <= pd.Timestamp(f'{y}-01-01')) & (cu['end'] >= pd.Timestamp(f'{y}-01-01'))).sum()) for y in (2005, 2010, 2015, 2020)}}
    rng = random.Random(11)
    cand = cu[(cu['end'] >= '2010-01-01') & (cu['start'] <= '2024-12-31')]
    sample = cand.sample(n=min(MAX_REQ, len(cand)), random_state=11)
    h = {'Authorization': f'Token {key}', 'Content-Type': 'application/json'}
    ok, stats, t0 = 0, [], time.time()
    stop = None
    for _, s in sample.iterrows():
        r = requests.get(f'{tp.API}/tiingo/daily/{s["ticker"]}/prices', headers=h, timeout=60,
                         params={'startDate': '2009-01-01', 'endDate': '2026-11-01', 'format': 'json'})
        if r.status_code != 200:
            stop = {'n_antes_del_error': ok, 'http': r.status_code, 'texto': r.text[:300],
                    'cabeceras': {k: v for k, v in r.headers.items() if 'limit' in k.lower() or 'retry' in k.lower() or 'remaining' in k.lower()},
                    'segundos': round(time.time() - t0)}
            break
        d = r.json()
        ok += 1
        if d:
            f0, l0 = pd.Timestamp(d[0]['date'][:10]), pd.Timestamp(d[-1]['date'][:10])
            valid = (f0 >= s['start'] - pd.Timedelta(days=40)) and (l0 <= s['end'] + pd.Timedelta(days=40)) and (l0 >= s['end'] - pd.Timedelta(days=40) or s['activa'])
            stats.append({'t': s['ticker'], 'filas': len(d), 'valida': bool(valid), 'activa': bool(s['activa'])})
        time.sleep(0.3)
    out['descarga'] = {'peticiones_ok': ok, 'error': stop, 'segundos_totales': round(time.time() - t0)}
    if stats:
        df = pd.DataFrame(stats)
        out['calidad'] = {'series': int(len(df)), 'con_fechas_coherentes_con_la_lista': int(df['valida'].sum()), 'pct_coherentes': round(float(df['valida'].mean() * 100), 1),
                          'filas_mediana': float(df['filas'].median()), 'inactivas_coherentes_pct': round(float(df[~df['activa']]['valida'].mean() * 100), 1) if (~df['activa']).any() else None}
    print('RESUMEN_TIINGO_LIMITES ' + json.dumps(out, default=str), flush=True)
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_tiingo_limites.json'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(out, open(path, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
