"""Karryman V24 · sondeo de fuentes de datos históricas con empresas deslistadas.

Mide, no supone: (1) el repositorio candidato Johnbrick123/sp500-data (licencia, estructura, muestras);
(2) cambios históricos del S&P 500 en Wikipedia (qué valores salieron desde 2010);
(3) cobertura real de Yahoo Finance para esos valores salidos (¿hay precios de empresas deslistadas?).
Investigación únicamente.
"""
import io
import json
import os
import sys
import time

import pandas as pd
import requests

REPO = 'Johnbrick123/sp500-data'
UA = {'User-Agent': 'karryman-research/1.0', 'Accept': 'application/vnd.github+json'}


def gh(path, **kw):
    h = dict(UA)
    if os.environ.get('GITHUB_TOKEN'):
        h['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    return requests.get('https://api.github.com' + path, headers=h, timeout=60, **kw)


def probe_repo():
    out = {'repo': REPO}
    m = gh(f'/repos/{REPO}')
    if m.status_code != 200:
        return {**out, 'error': f'HTTP {m.status_code}'}
    m = m.json()
    out.update({'licencia': (m.get('license') or {}).get('spdx_id'), 'rama': m.get('default_branch'), 'ultimo_push': m.get('pushed_at'),
                'estrellas': m.get('stargazers_count'), 'tamano_kb': m.get('size'), 'archivado': m.get('archived')})
    t = gh(f'/repos/{REPO}/git/trees/{m.get("default_branch", "HEAD")}?recursive=1').json()
    files = [(x['path'], x.get('size', 0)) for x in t.get('tree', []) if x['type'] == 'blob']
    out['n_ficheros'], out['truncado'] = len(files), bool(t.get('truncated'))
    ext = {}
    for p, s in files:
        e = p.rsplit('.', 1)[-1].lower() if '.' in p else ''
        ext[e] = ext.get(e, 0) + 1
    out['extensiones'] = ext
    out['ejemplos'] = [p for p, _ in files[:25]]
    out['mayores'] = sorted(files, key=lambda x: -x[1])[:8]
    rd = [p for p, _ in files if p.lower().startswith('readme')]
    if rd:
        r = requests.get(f'https://raw.githubusercontent.com/{REPO}/{m.get("default_branch")}/{rd[0]}', timeout=60)
        out['readme_inicio'] = r.text[:1500]
    samples = []
    for p, s in [x for x in files if x[0].lower().endswith('.csv') and x[1] < 8_000_000][:3]:
        r = requests.get(f'https://raw.githubusercontent.com/{REPO}/{m.get("default_branch")}/{p}', timeout=60)
        try:
            d = pd.read_csv(io.StringIO(r.text))
            info = {'fichero': p, 'filas': len(d), 'columnas': list(d.columns)[:12], 'primeras': d.head(2).astype(str).values.tolist(), 'ultimas': d.tail(2).astype(str).values.tolist()}
        except Exception as e:
            info = {'fichero': p, 'error': str(e)[:100]}
        samples.append(info)
    out['muestras_csv'] = samples
    return out


def sp500_changes():
    import warnings
    warnings.simplefilter('ignore')
    html = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers={'User-Agent': 'karryman-research/1.0'}, timeout=60).text
    tabs = pd.read_html(io.StringIO(html))
    cur = tabs[0]
    ch = tabs[1]
    ch.columns = [' '.join(map(str, c)).strip() if isinstance(c, tuple) else str(c) for c in ch.columns]
    date_col = [c for c in ch.columns if 'Date' in c][0]
    rem = [c for c in ch.columns if 'Removed' in c and 'Ticker' in c][0]
    add = [c for c in ch.columns if 'Added' in c and 'Ticker' in c][0]
    ch['d'] = pd.to_datetime(ch[date_col], errors='coerce')
    ch = ch[ch['d'] >= '2010-01-01']
    removed = sorted(set(ch[rem].dropna().astype(str)) - {'nan'})
    added = sorted(set(ch[add].dropna().astype(str)) - {'nan'})
    return {'actuales': int(len(cur)), 'cambios_desde_2010': int(len(ch)), 'salidas_unicas': len(removed), 'entradas_unicas': len(added),
            'fecha_min': str(ch['d'].min().date()), 'fecha_max': str(ch['d'].max().date())}, ch.rename(columns={rem: 'removed', add: 'added'})[['d', 'removed', 'added']]


def yahoo_coverage(ch):
    import yfinance as yf
    rem = ch.dropna(subset=['removed']).copy()
    rem['removed'] = rem['removed'].astype(str)
    last = rem.groupby('removed')['d'].max()
    tickers = list(last.index)
    got = {}
    for k in range(0, len(tickers), 40):
        part = tickers[k:k + 40]
        try:
            d = yf.download(part, start='2009-01-01', auto_adjust=True, progress=False, threads=True, group_by='ticker', timeout=60)
        except Exception:
            continue
        for t in part:
            try:
                s = (d[t] if isinstance(d.columns, pd.MultiIndex) else d)['Close'].dropna()
                if len(s):
                    got[t] = (s.index[0], s.index[-1], len(s))
            except Exception:
                pass
        time.sleep(1)
    full, partial, none = [], [], []
    for t in tickers:
        if t not in got:
            none.append(t)
            continue
        a, b, n = got[t]
        # ¿hay precios hasta (cerca de) la fecha de salida del índice?
        (full if b >= last[t] - pd.Timedelta(days=30) and a <= last[t] - pd.Timedelta(days=365) else partial).append(t)
    return {'salidas_probadas': len(tickers), 'con_precios_hasta_su_salida': len(full), 'con_datos_parciales_o_reutilizado': len(partial),
            'sin_datos_en_yahoo': len(none), 'pct_sin_datos': round(100 * len(none) / max(len(tickers), 1), 1),
            'ejemplos_sin_datos': none[:40], 'ejemplos_con_datos': full[:15]}


def main():
    out = {}
    for name, fn in (('repo_candidato', probe_repo),):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {'error': f'{type(e).__name__}: {str(e)[:200]}'}
    try:
        info, ch = sp500_changes()
        out['wikipedia_cambios_sp500'] = info
        out['yahoo_cobertura_de_salidas'] = yahoo_coverage(ch)
    except Exception as e:
        out['wikipedia_cambios_sp500'] = {'error': f'{type(e).__name__}: {str(e)[:200]}'}
    out['commit'] = os.environ.get('GITHUB_SHA')
    print('RESUMEN_FUENTES ' + json.dumps(out, default=str), flush=True)
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_fuentes.json'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(out, open(path, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
