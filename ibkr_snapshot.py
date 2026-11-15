"""Karryman · instantánea de datos públicos de la lista de vigilancia (data/ibkr_watchlist.json). Solo lectura; sin órdenes."""
import json
import os
import sys

import numpy as np
import pandas as pd
import yfinance as yf


def main():
    syms = json.load(open('data/ibkr_watchlist.json'))['symbols']
    d = yf.download(syms + ['SPY'], period='2y', interval='1d', auto_adjust=True, progress=False, group_by='ticker', threads=True, timeout=60)
    spy = d['SPY']['Close'].dropna()
    rows = []
    for t in syms:
        try:
            f = d[t][['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            if len(f) < 60:
                rows.append({'ticker': t, 'error': 'pocos datos'})
                continue
            c = f.Close
            row = {'ticker': t, 'ultima_sesion': str(f.index[-1].date()), 'cierre': round(float(c.iloc[-1]), 2),
                   'dist_max_52s_pct': round(float((c.iloc[-1] / f.High.iloc[-252:].max() - 1) * 100), 1),
                   'dist_min_52s_pct': round(float((c.iloc[-1] / f.Low.iloc[-252:].min() - 1) * 100), 1),
                   'vs_sma50_pct': round(float((c.iloc[-1] / c.rolling(50).mean().iloc[-1] - 1) * 100), 1),
                   'vs_sma200_pct': round(float((c.iloc[-1] / c.rolling(200).mean().iloc[-1] - 1) * 100), 1) if len(c) >= 200 else None,
                   'ret_1m_pct': round(float((c.iloc[-1] / c.iloc[-22] - 1) * 100), 1), 'ret_3m_pct': round(float((c.iloc[-1] / c.iloc[-64] - 1) * 100), 1),
                   'ret_3m_vs_spy_pct': round(float(((c.iloc[-1] / c.iloc[-64]) - (spy.iloc[-1] / spy.iloc[-64])) * 100), 1),
                   'vol_medio_50d': int(f.Volume.iloc[-50:].mean()), 'vol_ult_vs_medio': round(float(f.Volume.iloc[-1] / f.Volume.iloc[-51:-1].mean()), 2),
                   'rango_10d_pct': round(float((f.High.iloc[-10:].max() - f.Low.iloc[-10:].min()) / c.iloc[-1] * 100), 1),
                   'max_10d': round(float(f.High.iloc[-10:].max()), 2), 'min_10d': round(float(f.Low.iloc[-10:].min()), 2),
                   'max_30d': round(float(f.High.iloc[-30:].max()), 2)}
            try:
                info = yf.Ticker(t).info
                row.update({'sector': info.get('sector'), 'industria': info.get('industry'), 'cap_mercado_M': round((info.get('marketCap') or 0) / 1e6),
                            'nombre': info.get('shortName')})
                cal = yf.Ticker(t).calendar
                if isinstance(cal, dict) and cal.get('Earnings Date'):
                    row['proximos_resultados'] = str(cal['Earnings Date'][0])
            except Exception:
                pass
            rows.append(row)
        except Exception as e:
            rows.append({'ticker': t, 'error': str(e)[:80]})
    out = {'commit': os.environ.get('GITHUB_SHA'), 'spy_ultima_sesion': str(spy.index[-1].date()), 'spy_ret_3m_pct': round(float((spy.iloc[-1] / spy.iloc[-64] - 1) * 100), 1),
           'spy_vs_sma50_pct': round(float((spy.iloc[-1] / spy.rolling(50).mean().iloc[-1] - 1) * 100), 1), 'valores': rows}
    print('RESUMEN_SNAPSHOT ' + json.dumps(out, default=str), flush=True)
    path = sys.argv[1] if len(sys.argv) > 1 else 'data/v24_snapshot.json'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(out, open(path, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
