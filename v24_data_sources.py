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
    br = m.get('default_branch')
    out['md'] = [p for p, _ in files if p.lower().endswith('.md')]
    out['licencia_ficheros'] = [p for p, _ in files if p.lower().split('/')[-1].startswith(('license', 'licence', 'copying'))]
    docs = {}
    for p in out['md'][:7]:
        r = requests.get(f'https://raw.githubusercontent.com/{REPO}/{br}/{p}', timeout=60)
        docs[p] = r.text[:9000]
    out['docs_md'] = docs
    rel = gh(f'/repos/{REPO}/releases?per_page=5')
    if rel.status_code == 200:
        out['releases'] = [{'tag': x.get('tag_name'), 'fecha': x.get('published_at'),
                            'assets': [(a['name'], a['size']) for a in x.get('assets', [])][:15]} for x in rel.json()]
    out['csv_ficheros'] = [(p, s) for p, s in files if p.lower().endswith('.csv')]
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


def probe_dataset(tag='snapshot-2026-11'):
    """Descarga los ficheros de la release y mide su estructura (no asume nombres de columnas)."""
    import pyarrow.parquet as pq
    base = f'https://github.com/{REPO}/releases/download/{tag}/'
    out = {'tag': tag}
    os.makedirs('/tmp/sp500', exist_ok=True)
    for name in ('verification_report.txt', 'membership_intervals.parquet', 'prices.parquet', 'members.parquet'):
        r = requests.get(base + name, timeout=600)
        out[f'{name}_http'] = r.status_code
        if r.status_code != 200:
            continue
        open(f'/tmp/sp500/{name}', 'wb').write(r.content)
        out[f'{name}_bytes'] = len(r.content)
    vr = '/tmp/sp500/verification_report.txt'
    if os.path.exists(vr):
        out['verification_report'] = open(vr, errors='replace').read()[:7000]
    for name in ('membership_intervals.parquet', 'members.parquet', 'prices.parquet'):
        p = f'/tmp/sp500/{name}'
        if not os.path.exists(p):
            continue
        pf = pq.ParquetFile(p)
        info = {'filas': pf.metadata.num_rows, 'columnas': [(f.name, str(f.type)) for f in pf.schema_arrow]}
        d = pd.read_parquet(p)
        info['head'] = d.head(3).astype(str).values.tolist()
        info['tail'] = d.tail(2).astype(str).values.tolist()
        for c in d.columns:
            lc = c.lower()
            if lc in ('ticker', 'symbol', 'label', 'permno'):
                info[f'n_{c}'] = int(d[c].nunique())
            if 'date' in lc or lc in ('start', 'end', 'from', 'to'):
                try:
                    info[f'rango_{c}'] = [str(d[c].min()), str(d[c].max())]
                except Exception:
                    pass
        out[name] = info
    return out


def sp500_changes():
    import warnings
    warnings.simplefilter('ignore')
    html = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers={'User-Agent': 'karryman-research/1.0'}, timeout=60).text
    tabs = pd.read_html(io.StringIO(html))
    cur, ch = tabs[0], None
    for t in tabs[1:]:
        t = t.copy()
        t.columns = [' '.join(dict.fromkeys(map(str, c))).strip() if isinstance(c, tuple) else str(c) for c in t.columns]
        if any('Added' in c for c in t.columns) and any('Removed' in c for c in t.columns):
            ch = t
            break
    if ch is None:
        raise ValueError('tabla de cambios no encontrada; columnas: ' + str([list(map(str, t.columns))[:6] for t in tabs[1:4]]))
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
        out['dataset_release'] = probe_dataset()
    except Exception as e:
        out['dataset_release'] = {'error': f'{type(e).__name__}: {str(e)[:300]}'}
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
