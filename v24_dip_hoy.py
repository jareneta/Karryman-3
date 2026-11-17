"""Karryman · ¿qué acciones del S&P 500 cumplen hoy la señal de caída de H9b? (docs/V24_H9B_CAIDAS_SP500.md). Solo lectura; sin órdenes.
Usa exactamente la misma función de señal que los backtests (system_backtest.signals con v24_dip.CFG)."""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_backtest as vb
import v24_dip as dip

RECENT = 5


def current_members(intervals_path):
    iv = pd.read_parquet(intervals_path)
    cur = iv[iv['end'].isna()]['ticker']
    return sorted(set(str(t).split('-')[0] if '-' in str(t) and str(t).split('-')[-1].isdigit() else str(t) for t in cur))


def scan(prepared, regime, last_n=RECENT):
    """Devuelve para cada valor las señales de caída de las últimas `last_n` sesiones (índice relativo al final)."""
    out = []
    for tk, d in prepared.items():
        n = len(d)
        for sig in sb.signals(d, dip.CFG, regime):
            i = sig[0]
            if i >= n - last_n:
                out.append((tk, i, n - 1 - i))
    return out


def describe(tk, d, i, spy_up):
    c = d.Close.to_numpy()
    win = c[i - 60:i]
    row = {'ticker': tk, 'fecha_senal': str(d.index[i].date()), 'sesiones_desde_la_senal': int(len(d) - 1 - i), 'cierre_senal': round(float(c[i]), 2), 'ultimo_cierre': round(float(c[-1]), 2),
           'caida_vs_max60_pct': round(float((c[i] / win.max() - 1) * 100), 1), 'dias_desde_max60': int(60 - int(np.argmax(win))),
           'ret5_pct': round(float((c[i] / c[i - 5] - 1) * 100), 1), 'vol_vs_media50': round(float(d.Volume.iloc[i] / d.vol50.iloc[i]), 2),
           'dist_max252_pct': round(float((c[i] / d.hi252.iloc[i] - 1) * 100), 1), 'sobre_sma200_pct': round(float((c[i] / d.ma200.iloc[i] - 1) * 100), 1),
           'gap_apertura_pct': round(float((d.Open.iloc[i] / c[i - 1] - 1) * 100), 1), 'sma20_ultima': round(float(d.sma20.iloc[-1]), 2), 'stop_12pct_sobre_ultimo_cierre': round(float(c[-1] * 0.88), 2),
           'spy_sobre_sma200': bool(spy_up)}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='snapshot-2026-11')
    ap.add_argument('--output', default='data/v24_dip_hoy.json')
    a = ap.parse_args()
    import yfinance as yf
    t0 = time.time()
    paths, sha = vb.download_sp500data(a.tag, names=('membership_intervals.parquet',))
    names = current_members(paths['membership_intervals.parquet'])
    frames = {}
    for k in range(0, len(names) + 1, 50):
        part = names[k:k + 50] + (['SPY'] if k == 0 else [])
        if not part:
            continue
        try:
            data = yf.download(part, period='3y', interval='1d', auto_adjust=True, progress=False, group_by='ticker', threads=True, timeout=60)
        except Exception:
            continue
        for t in part:
            try:
                f = (data[t] if isinstance(data.columns, pd.MultiIndex) else data)[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                if len(f) >= 300:
                    frames[t] = f
            except Exception:
                pass
        time.sleep(1)
    spy = frames.pop('SPY')
    last_day = max(f.index.max() for f in frames.values())
    frames = {t: f for t, f in frames.items() if f.index.max() >= last_day - pd.Timedelta(days=4)}
    regime = sb.regime_series(spy)
    prepared = {}
    for t, f in frames.items():
        d = sb.prepare(f, spy.Close)
        d['member'] = True
        prepared[t] = d
    spy_up_s = spy.Close > spy.Close.rolling(200).mean()
    spy_up = bool(spy_up_s.iloc[-1])
    sigs = scan(prepared, regime, RECENT)
    rows = [describe(tk, prepared[tk], i, spy_up) for tk, i, _ in sigs]
    for r in rows:
        try:
            cal = yf.Ticker(r['ticker']).calendar
            if isinstance(cal, dict) and cal.get('Earnings Date'):
                r['proximos_resultados'] = str(cal['Earnings Date'][0])
            info = yf.Ticker(r['ticker']).info
            r['nombre'], r['sector'] = info.get('shortName'), info.get('sector')
        except Exception:
            pass
    # cerca de la señal: entre -10 % y -15 % bajo el máximo de 60 sesiones, sobre la SMA200, líquidas
    near = []
    for tk, d in prepared.items():
        c = d.Close.to_numpy()
        dd = c[-1] / c[-61:-1].max() - 1
        if -0.15 < dd <= -0.10 and c[-1] > d.ma200.iloc[-1] and c[-1] >= 5 and d.vol50.iloc[-1] >= 500_000:
            near.append({'ticker': tk, 'caida_vs_max60_pct': round(float(dd * 100), 1), 'ultimo_cierre': round(float(c[-1]), 2),
                         'precio_que_activa_la_senal': round(float(c[-61:-1].max() * 0.85), 2)})
    out = {'commit': os.environ.get('GITHUB_SHA'), 'ultima_sesion': str(last_day.date()), 'miembros_actuales_con_datos': len(prepared), 'spy_sobre_sma200': spy_up,
           'spy_caida_vs_max60_pct': round(float((spy.Close.iloc[-1] / spy.Close.iloc[-61:-1].max() - 1) * 100), 1),
           'senales_ultimas_5_sesiones': sorted(rows, key=lambda r: (r['sesiones_desde_la_senal'], r['ticker'])), 'cerca_de_la_senal': sorted(near, key=lambda r: r['caida_vs_max60_pct']),
           'nota': 'Solo lectura. La regla probada compra a la apertura de la sesión siguiente a la señal; una señal de hace varias sesiones ya no es una entrada de la regla.'}
    print('RESUMEN_DIP_HOY ' + json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()}), flush=True)
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    json.dump(out, open(a.output, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
