"""Karryman · análisis descriptivo: punto com (1998-2002) frente al mercado actual, con las caídas de hoy.
No es una hipótesis contrastada; no hay criterios de aceptación. Datos: sp500data point-in-time (hasta fin de snapshot) + Yahoo (hoy)."""
import argparse
import json
import os

import numpy as np
import pandas as pd

import v24_backtest as vb

SECT = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB', 'XLRE', 'XLC', 'SMH', 'QQQ', 'IWM']


def breadth(close, member, n):
    m = member.reindex(index=close.index, columns=close.columns).fillna(False)
    ma = close.rolling(n).mean()
    v = m & ma.notna() & close.notna()
    return ((close > ma) & v).sum(axis=1) / v.sum(axis=1).replace(0, np.nan) * 100


def share_near(close, member, hi=True, tol=0.10):
    m = member.reindex(index=close.index, columns=close.columns).fillna(False)
    ref = close.rolling(252, min_periods=200).max() if hi else close.rolling(252, min_periods=200).min()
    ok = (close >= ref * (1 - tol)) if hi else (close <= ref * (1 + tol))
    v = m & ref.notna() & close.notna()
    return (ok & v).sum(axis=1) / v.sum(axis=1).replace(0, np.nan) * 100


def top10_share(close, vol, member):
    m = member.reindex(index=close.index, columns=close.columns).fillna(False)
    dv = (close * vol).where(m).rolling(20, min_periods=10).mean()
    top = dv.apply(lambda r: r.nlargest(10).sum(), axis=1)
    return top / dv.sum(axis=1).replace(0, np.nan) * 100


def ew_index(close, member):
    m = member.reindex(index=close.index, columns=close.columns).fillna(False).shift(1, fill_value=False)
    r = close.pct_change().where(m)
    return (1 + r.mean(axis=1).fillna(0)).cumprod()


def state(d, spy, ew, b200, b50, near_hi, near_lo, top10):
    i = spy.index.get_loc(d)
    f = lambda s, k: round(float(s.iloc[k]), 1) if k >= 0 and pd.notna(s.iloc[k]) else None
    ret = lambda s, n: round(float((s.iloc[i] / s.iloc[i - n] - 1) * 100), 1) if i >= n else None
    return {'fecha': str(d.date()), 'spy_caida_desde_max_252d_pct': round(float((spy.iloc[i] / spy.iloc[max(0, i - 251):i + 1].max() - 1) * 100), 1),
            'spy_ret_12m_pct': ret(spy, 252), 'spy_ret_24m_pct': ret(spy, 504), 'igual_ponderado_ret_12m_pct': ret(ew, 252),
            'exceso_spy_menos_igual_ponderado_12m_pp': (round(ret(spy, 252) - ret(ew, 252), 1) if i >= 252 else None),
            'pct_miembros_sobre_sma200': f(b200, i), 'pct_miembros_sobre_sma50': f(b50, i), 'pct_cerca_max_52s_(10%)': f(near_hi, i),
            'pct_cerca_min_52s_(10%)': f(near_lo, i), 'cuota_top10_volumen_dolares_pct': f(top10, i),
            'volatilidad_20d_anual_pct': round(float(spy.pct_change().iloc[max(1, i - 19):i + 1].std() * np.sqrt(252) * 100), 1)}


def forward(spy, ew, peak):
    i = spy.index.get_loc(peak)
    out = {}
    for lab, n in (('1m', 21), ('3m', 63), ('6m', 126), ('12m', 252), ('24m', 504)):
        if i + n < len(spy):
            out[lab] = {'spy_pct': round(float((spy.iloc[i + n] / spy.iloc[i] - 1) * 100), 1), 'igual_ponderado_pct': round(float((ew.iloc[i + n] / ew.iloc[i] - 1) * 100), 1)}
    out['peor_caida_posterior_spy_pct'] = round(float((spy.iloc[i:] / spy.iloc[i] - 1).min() * 100), 1)
    return out


def hist_part(paths):
    p, member, bench, info = vb.load_sp500data(paths['prices.parquet'], paths['membership_intervals.parquet'], start='1997-01-01')
    close, vol, spy = p['close'], p['volume'], bench.dropna()
    ew = ew_index(close, member).reindex(spy.index).ffill()
    b200, b50 = breadth(close, member, 200).reindex(spy.index), breadth(close, member, 50).reindex(spy.index)
    nh, nl = share_near(close, member, True).reindex(spy.index), share_near(close, member, False).reindex(spy.index)
    t10 = top10_share(close, vol, member).reindex(spy.index)
    args = (spy, ew, b200, b50, nh, nl, t10)
    pk1 = spy.loc['1999-01-01':'2001-01-01'].idxmax()
    pk2 = spy.loc['2024-01-01':].idxmax()
    last = spy.index[-1]
    out = {'ultimo_dia_datos': str(last.date()), 'pico_punto_com': str(pk1.date()), 'pico_actual': str(pk2.date()), 'universo': info,
           'estados': {'punto_com_6m_antes_del_pico': state(spy.index[spy.index.get_loc(pk1) - 126], *args), 'punto_com_pico': state(pk1, *args),
                       'punto_com_3m_despues': state(spy.index[spy.index.get_loc(pk1) + 63], *args), 'actual_pico': state(pk2, *args), 'actual_ultimo_dia': state(last, *args)},
           'despues_del_pico_punto_com': forward(spy, ew, pk1), 'despues_del_pico_actual_hasta_hoy': forward(spy, ew, pk2) if pk2 != last else {}}
    last_members = list(member.columns[member.iloc[-1]])
    adv = (close * vol).where(member.reindex(index=close.index, columns=close.columns).fillna(False)).rolling(20, min_periods=10).mean().iloc[-1].nlargest(150).index.tolist()
    return out, last_members, adv


def today_part(members, liquid):
    import yfinance as yf
    tick = sorted(set(members) | set(SECT) | {'SPY', '^IXIC', '^GSPC', '^VIX'})
    d = yf.download(tick, period='2y', interval='1d', auto_adjust=True, progress=False, threads=True, timeout=90)['Close']
    d = d.dropna(how='all')
    last = d.index[-1]
    r1 = d.pct_change().iloc[-1] * 100
    out = {'ultima_sesion': str(last.date()), 'indices_1d_pct': {k: round(float(r1[k]), 2) for k in ('SPY', '^GSPC', '^IXIC', '^VIX') if k in r1 and pd.notna(r1[k])},
           'sectores_1d_pct': {k: round(float(r1[k]), 2) for k in SECT if k in r1 and pd.notna(r1[k])}}
    spyr = d['SPY'].pct_change().dropna() * 100
    out['spy_percentil_del_dia_en_2_anos'] = round(float((spyr < spyr.iloc[-1]).mean() * 100), 1)
    mem = [t for t in members if t in d.columns and d[t].notna().iloc[-1]]
    sub = d[mem]
    out['miembros_con_dato'] = len(mem)
    out['filas_con_hueco_total_ultimos_200d'] = int(sub.iloc[-200:].isna().all(axis=1).sum())
    out['pct_miembros_cayendo_hoy'] = round(float((r1[mem] < 0).mean() * 100), 1)
    out['pct_miembros_cayendo_mas_3pct_hoy'] = round(float((r1[mem] < -3).mean() * 100), 1)
    out['pct_miembros_sobre_sma200'] = round(float((sub.iloc[-1] > sub.rolling(200, min_periods=180).mean().iloc[-1]).mean() * 100), 1)
    out['pct_miembros_sobre_sma50'] = round(float((sub.iloc[-1] > sub.rolling(50, min_periods=45).mean().iloc[-1]).mean() * 100), 1)
    out['pct_miembros_cerca_max_52s_10pct'] = round(float((sub.iloc[-1] >= sub.iloc[-252:].max() * 0.9).mean() * 100), 1)
    spy = d['SPY'].dropna()
    out['spy'] = {'cierre': round(float(spy.iloc[-1]), 2), 'caida_desde_max_52s_pct': round(float((spy.iloc[-1] / spy.iloc[-252:].max() - 1) * 100), 1),
                  'vs_sma50_pct': round(float((spy.iloc[-1] / spy.rolling(50).mean().iloc[-1] - 1) * 100), 1), 'vs_sma200_pct': round(float((spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1) * 100), 1),
                  'ret_5d_pct': round(float((spy.iloc[-1] / spy.iloc[-6] - 1) * 100), 1), 'ret_1m_pct': round(float((spy.iloc[-1] / spy.iloc[-22] - 1) * 100), 1)}
    rows = []
    for t in [x for x in liquid if x in mem]:
        s = d[t].dropna()
        rows.append({'ticker': t, 'hoy_pct': round(float(r1[t]), 2), 'ret_5d_pct': round(float((s.iloc[-1] / s.iloc[-6] - 1) * 100), 1), 'dist_max_52s_pct': round(float((s.iloc[-1] / s.iloc[-252:].max() - 1) * 100), 1)})
    rows.sort(key=lambda x: x['hoy_pct'])
    out['mayores_caidas_hoy_entre_150_mas_liquidas'] = rows[:20]
    out['mayores_subidas_hoy_entre_150_mas_liquidas'] = rows[-8:][::-1]
    return out


def nasdaq_part():
    import yfinance as yf
    x = yf.download(['^IXIC', '^GSPC'], start='1996-01-01', interval='1d', auto_adjust=False, progress=False, timeout=90)['Close'].dropna()
    res = {}
    for nm, lo, hi in (('punto_com', '1998-01-01', '1998-12-31'), ('actual', '2022-01-01', '2022-12-31')):
        t0 = x['^IXIC'].loc[lo:hi].idxmin()
        seg = x.loc[t0:]
        pk_hi = '2001-01-01' if nm == 'punto_com' else '2100-01-01'
        pk = x['^IXIC'].loc[t0:pk_hi].idxmax()
        res[nm] = {'suelo': str(t0.date()), 'pico_nasdaq': str(pk.date()), 'meses_suelo_a_pico': round((pk - t0).days / 30.44, 1),
                   'nasdaq_subida_suelo_a_pico_pct': round(float((x['^IXIC'][pk] / x['^IXIC'][t0] - 1) * 100), 1), 'sp500_subida_suelo_a_pico_pct': round(float((x['^GSPC'][pk] / x['^GSPC'][t0] - 1) * 100), 1),
                   'nasdaq_caida_hasta_hoy_o_suelo_posterior_pct': round(float((x['^IXIC'].loc[pk:].min() / x['^IXIC'][pk] - 1) * 100), 1),
                   'nasdaq_ahora_vs_pico_pct': round(float((x['^IXIC'].iloc[-1] / x['^IXIC'][pk] - 1) * 100), 1) if nm == 'actual' else None,
                   'ratio_nasdaq_sp500_pico_vs_suelo': round(float((x['^IXIC'][pk] / x['^GSPC'][pk]) / (x['^IXIC'][t0] / x['^GSPC'][t0])), 2)}
        if nm == 'punto_com':
            tr = x['^IXIC'].loc[pk:'2003-12-31'].idxmin()
            res[nm].update({'suelo_posterior': str(tr.date()), 'nasdaq_caida_pico_a_suelo_pct': round(float((x['^IXIC'][tr] / x['^IXIC'][pk] - 1) * 100), 1), 'sp500_caida_pico_a_suelo_pct': round(float((x['^GSPC'].loc[pk:'2003-12-31'].min() / x['^GSPC'][pk] - 1) * 100), 1)})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_mercado_hoy.json')
    a = ap.parse_args()
    paths, sha = vb.download_sp500data(a.tag)
    out = {'commit': os.environ.get('GITHUB_SHA'), 'tipo': 'descriptivo, sin criterios de aceptación', 'datos': {'tag': a.tag, 'sha256': sha}}
    out['historico'], members, liquid = hist_part(paths)
    for k, fn in (('hoy', lambda: today_part(members, liquid)), ('nasdaq_comparado', nasdaq_part)):
        try:
            out[k] = fn()
        except Exception as e:
            out[k] = {'error': str(e)[:200]}
    print('RESUMEN_MERCADO ' + json.dumps(out, default=str), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
