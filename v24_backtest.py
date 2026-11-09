"""Karryman V24 · backtest con el motor corregido (v24_engine) sobre datos de Yahoo.

Investigación únicamente. Universo: acciones cotizadas hoy (sesgo de supervivencia, declarado) con filtro de
liquidez vigente día a día (mediana de 60 sesiones de volumen en dólares y precio mínimo, solo datos hasta ese día).
Tramos fijos, sin optimizar sobre ellos: entrenamiento 2010-2016, validación 2017-2020, prueba 2021-2026.
"""
import argparse
import json
import random
import time
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_engine as ve

SEGS = {'entrenamiento_2010_16': ('2010-01-01', '2016-12-31'), 'validacion_2017_20': ('2017-01-01', '2020-12-31'),
        'prueba_2021_26': ('2021-01-01', None), 'todo': (None, None)}


def to_wide(frames):
    out = {}
    for k in ('Open', 'High', 'Low', 'Close', 'Volume'):
        out[k.lower()] = pd.DataFrame({t: f[k] for t, f in frames.items()}).sort_index()
    return out


def liquidity_member(p, min_dollar_vol=5e6, min_price=5.0):
    dv = (p['close'] * p['volume']).rolling(60, min_periods=40).median()
    return (dv >= min_dollar_vol) & (p['close'] >= min_price)

SP500_REPO = 'Johnbrick123/sp500-data'


def download_sp500data(tag, dest='/tmp/sp500'):
    """Descarga prices.parquet y members.parquet de la release `tag` y devuelve rutas y huella SHA-256."""
    import hashlib
    import os
    import requests
    os.makedirs(dest, exist_ok=True)
    paths, sha = {}, {}
    for name in ('prices.parquet', 'members.parquet'):
        p = f'{dest}/{tag}_{name}'
        if not os.path.exists(p):
            r = requests.get(f'https://github.com/{SP500_REPO}/releases/download/{tag}/{name}', timeout=900)
            r.raise_for_status()
            open(p, 'wb').write(r.content)
        paths[name] = p
        sha[name] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return paths, sha


def load_sp500data(prices_path, members_path, start='2009-06-01', end=None, benchmark='SPY'):
    """Lee los parquet y construye el universo (ver build_universe)."""
    members = pd.read_parquet(members_path)
    tickers = sorted(members[members['date'] >= pd.Timestamp(start)]['ticker'].unique())
    d = pd.read_parquet(prices_path, filters=[('date', '>=', pd.Timestamp(start)), ('ticker', 'in', tickers + [benchmark])])
    return build_universe(d, members, start, end, benchmark)


def build_universe(d, members, start='2009-06-01', end=None, benchmark='SPY'):
    """Precios OHLC ajustados por dividendos y splits (factor adj_close/close), máscara de pertenencia diaria al
    S&P 500 (incluye empresas deslistadas) y serie del benchmark."""
    members = members[members['date'] >= pd.Timestamp(start)]
    d = d[d['date'] >= pd.Timestamp(start)]
    if end:
        members, d = members[members['date'] <= pd.Timestamp(end)], d[d['date'] <= pd.Timestamp(end)]
    tickers = sorted(members['ticker'].unique())
    bench = d[d['ticker'] == benchmark].set_index('date')['adj_close'].sort_index()
    d = d[d['ticker'].isin(tickers)].dropna(subset=['close', 'adj_close'])
    d = d[(d['close'] > 0) & (d['adj_close'] > 0)].copy()
    f = d['adj_close'] / d['close']
    for k in ('open', 'high', 'low'):
        d[k] = d[k] * f
    d['close'] = d['adj_close']
    srcs = d['source'].value_counts().to_dict() if 'source' in d else {}
    wide = {k: d.pivot(index='date', columns='ticker', values=k).sort_index() for k in ('open', 'high', 'low', 'close', 'volume')}
    idx, cols = wide['close'].index, wide['close'].columns
    mem = members.assign(v=True).pivot(index='date', columns='ticker', values='v').reindex(index=idx, columns=cols).fillna(False).astype(bool)
    return wide, mem, bench, {'filas_precios_usadas': int(len(d)), 'series': int(len(cols)), 'por_fuente': srcs}


def benchmark(spy):
    rows = {}
    for seg, (a, b) in SEGS.items():
        s = spy.loc[a:b] if (a or b) else spy
        yrs = (s.index[-1] - s.index[0]).days / 365.25
        rows[seg] = {'cagr_pct': round(float(((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100), 2),
                     'max_dd_pct': round(float((s / s.cummax() - 1).min() * 100), 2)}
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=300)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--start', default='2009-06-01')
    ap.add_argument('--output', default='data/v24_results.json')
    ap.add_argument('--capital', type=float, default=3000)
    ap.add_argument('--fee-min', type=float, default=1.0)
    ap.add_argument('--min-order', type=float, default=100.0)
    ap.add_argument('--fractional', action='store_true')
    ap.add_argument('--source', default='yahoo', choices=['yahoo', 'sp500data'])
    ap.add_argument('--tag', default='snapshot-2026-11')
    a = ap.parse_args()
    t0 = time.time()
    meta = {}
    if a.source == 'sp500data':
        paths, sha = download_sp500data(a.tag)
        p, member, spy, info = load_sp500data(paths['prices.parquet'], paths['members.parquet'], a.start)
        keep = list(p['close'].columns)
        meta = {'fuente': 'sp500data', 'tag': a.tag, 'sha256': sha, **info,
                'nota': 'S&P 500 point-in-time con deslistadas; sin licencia explícita en el repositorio; no verificado de forma independiente'}
        print(f'sp500data {a.tag}: {info} · {time.time()-t0:.0f}s', flush=True)
    else:
        names = sb.universe()
        random.Random(a.seed).shuffle(names)
        frames = sb.download(['SPY'] + names[:a.symbols * 2], a.start)   # se piden el doble: muchas no pasan filtros
        spy = frames.pop('SPY')['Close']
        keep = list(frames)[:a.symbols] if len(frames) > a.symbols else list(frames)
        p = to_wide({t: frames[t] for t in keep})
        member = liquidity_member(p)
        meta = {'fuente': 'yahoo', 'nota': 'acciones cotizadas hoy: sesgo de supervivencia'}
    print(f'Series: {len(keep)} · desde {p["close"].index[0].date()} hasta {p["close"].index[-1].date()} · {time.time()-t0:.0f}s', flush=True)
    chg = p['close'].pct_change(fill_method=None).abs()
    sus = {t: int((chg[t] > 0.40).sum()) for t in chg.columns if (chg[t] > 0.40).any()}
    base = ve.Cfg(capital=a.capital, fee_min=a.fee_min, min_order=a.min_order, fractional=a.fractional, rank_every=1)
    models = {
        'v24_base_sin_proteccion': replace(base, protection='none'),
        'v24_freno_fijo_8_50': replace(base, protection='fixed'),
        'v24_progresiva': replace(base, protection='progressive'),
        'v24_progresiva_banda10': replace(base, protection='progressive', band=0.10),
        'v24_progresiva_ma100': replace(base, protection='progressive', ma100_guard=True),
        'v24_progresiva_rank_mensual': replace(base, protection='progressive', rank_every=21),
        # --- controles: mismo universo, costes y reglas de riesgo; solo cambia el ranking ---
        'control_v24_base_rank_mensual': replace(base, protection='none', rank_every=21),
        'control_placebo_aleatorio_mensual_s1': replace(base, protection='none', rank_every=21, score_mode='random', seed=1),
        'control_placebo_aleatorio_mensual_s2': replace(base, protection='none', rank_every=21, score_mode='random', seed=2),
        'control_placebo_aleatorio_mensual_s3': replace(base, protection='none', rank_every=21, score_mode='random', seed=3),
    }
    import os as _os
    out = {'commit': _os.environ.get('GITHUB_SHA'), 'parametros': {'capital': a.capital, 'fee_min': a.fee_min, 'min_order': a.min_order, 'fractional': a.fractional, 'symbols': a.symbols, 'seed': a.seed},
           'datos': meta, 'universo': {'series': len(keep), 'nota': 'acciones cotizadas hoy: sesgo de supervivencia; filtro de liquidez vigente día a día'},
           'calidad_datos': {'series_con_saltos_diarios_mayores_40pct': len(sus), 'detalle': dict(list(sus.items())[:30]), 'nota': 'posibles splits sin ajustar o errores de datos'},
           'modelos': {}, 'comisiones': [], 'benchmark_spy': benchmark(spy)}
    runs = {}
    for name, cfg in models.items():
        runs[name] = ve.run(p, cfg, member)
        out['modelos'][name] = {seg: ve.metrics(runs[name], s, e) for seg, (s, e) in SEGS.items()}
        m = out['modelos'][name]['todo']
        print(f'{name}: CAGR {m["cagr_pct"]}% · DD {m["max_dd_pct"]}% · Sharpe {m["sharpe"]} · órdenes {m["orders"]} · {time.time()-t0:.0f}s', flush=True)
    # control del dato: cartera igualponderada de todos los miembros del día anterior, rebalanceo diario (sin costes)
    ew = None
    if a.source == 'sp500data':
        r_ = p['close'].pct_change(fill_method=None)
        w_ = member.shift(1, fill_value=False) & r_.notna()
        ew_ret = r_.where(w_).mean(axis=1).fillna(0.0)
        ew = (1 + ew_ret).cumprod()
        out['control_igualponderado_sp500'] = benchmark(ew.loc[ew.index >= pd.Timestamp('2010-01-01')])
    cfg = replace(base, protection='progressive', band=0.10)
    out['comisiones'] = json.loads(ve.fee_sensitivity(p, cfg, fees=(0.35, 0.50, 1.00), min_order=a.min_order, member=member).to_json(orient='records'))
    r = runs['v24_progresiva_banda10']
    tr = r['trades']
    gaps = tr.date.sort_values().diff().dt.days.dropna()
    out['anti_bloqueo'] = {'ultima_orden': str(tr.date.max().date()), 'efectivo_final': round(r['cash_end'], 2),
                           'patrimonio_final': round(float(r['equity'].iloc[-1]), 2), 'mayor_periodo_sin_operar_dias': int(gaps.max())}
    print('RESUMEN_V24 ' + json.dumps(out, default=float), flush=True)
    import os
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
