"""Karryman: plan de entradas y cotizaciones de seguimiento -> data/plan.json.

Lee las candidatas que ya pasaron tus criterios (data/setups.json) y los tickers
de tus posiciones (data/tracked.json, solo tickers). Calcula pivote, stop, +1R,
+2R y estado de entrada; publica cotizaciones para que el navegador decida
stop / +2R / runner con tu cartera privada. Nunca envía órdenes.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

import trade_levels

DATA = Path('data')
OUT = DATA / 'plan.json'
TICKER = re.compile(r'^[A-Z][A-Z.\-]{0,9}$')


def read(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def tracked_tickers():
    raw = read('tracked.json', {}).get('tickers', [])
    return sorted({str(t).strip().upper() for t in raw if TICKER.match(str(t).strip().upper())})[:60]


def criteria(x):
    """Resumen de tus criterios ya calculados por Screener/Setups."""
    notes = x.get('validation_notes') or {}
    earnings = notes.get('next_earnings_date')
    checks = {
        'tendencia': x.get('trend_ok') is True,
        'cerca_maximos': x.get('near_high_ok') is True,
        'fuerza_vs_spy': (x.get('rs_vs_spy_3m_pct') or -1) > 0,
        'fundamentales': x.get('fundamental_status') == 'CUMPLE',
        'a_plus_tecnico': x.get('technical_a_plus') is True,
    }
    return checks, earnings


def build(candidates, frames, tracked):
    entries, quotes = [], {}
    for x in candidates:
        t = x.get('ticker')
        frame = frames.get(t)
        if frame is None:
            continue
        plan = trade_levels.entry_plan(frame, x.get('setup', 'TENDENCIA'))
        if plan.get('entry_status') == 'SIN_DATOS':
            continue
        checks, earnings = criteria(x)
        core = all(checks[k] for k in ('tendencia', 'cerca_maximos', 'fuerza_vs_spy', 'fundamentales'))
        warnings = []
        if not earnings:
            warnings.append('Fecha de resultados no verificada: revísala antes de comprar')
        elif (datetime.fromisoformat(earnings).date() - datetime.now(timezone.utc).date()).days <= 14:
            warnings.append(f'Resultados el {earnings}: evita entrar antes')
        entries.append({'ticker': t, 'setup': x.get('setup'), **plan, 'criteria': checks,
                        'meets_criteria': core, 'next_earnings_date': earnings,
                        'actionable': core and plan['entry_status'] == 'ACTIVADA',
                        'warnings': warnings, 'order_enabled': False})
    order = {'ACTIVADA': 0, 'ESPERANDO': 1, 'EXTENDIDA': 2, 'RIESGO_ALTO': 3, 'FALLIDA': 4, 'INVALIDADA': 5}
    entries.sort(key=lambda e: (not e['actionable'], not e['meets_criteria'],
                                order.get(e['entry_status'], 9), abs(e.get('distance_to_pivot_pct') or 99)))
    # Cotizaciones de candidatas y posiciones mezcladas, sin indicar cuáles son tuyas.
    for t in sorted(set(tracked) | {e['ticker'] for e in entries}):
        q = trade_levels.quote(frames.get(t))
        if q:
            quotes[t] = q
    return entries, quotes


def download(tickers):
    frames, errors = {}, []
    for k in range(0, len(tickers), 20):
        batch = tickers[k:k + 20]
        try:
            prices = yf.download(batch, period='1y', interval='1d', auto_adjust=True, progress=False,
                                 threads=True, group_by='ticker', timeout=30)
            for t in batch:
                try:
                    frame = prices[t] if isinstance(prices.columns, pd.MultiIndex) else prices
                    if trade_levels.clean(frame) is not None:
                        frames[t] = frame
                    else:
                        errors.append(f'{t}: sin datos')
                except Exception as exc:
                    errors.append(f'{t}: {str(exc)[:80]}')
        except Exception as exc:
            errors.extend(f'{t}: {str(exc)[:80]}' for t in batch)
        time.sleep(1)
    return frames, errors


def main():
    setups = read('setups.json', {})
    candidates = [x for x in setups.get('candidates', []) if x.get('ticker')]
    tracked = tracked_tickers()
    tickers = sorted({x['ticker'] for x in candidates} | set(tracked))
    frames, errors = download(tickers)
    if tickers and len(frames) < len(tickers) // 2:
        raise RuntimeError('Descargas insuficientes; se conserva el plan anterior')
    entries, quotes = build(candidates, frames, tracked)
    missing = [t for t in tracked if t not in quotes]
    payload = {
        'schema_version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'setups_generated_utc': setups.get('generated_utc'),
        'source': 'Yahoo Finance OHLCV vía yfinance (no oficial, puede tener retraso)',
        'rules': {'entry': 'Cierre > pivote con volumen >= 1,4x (pullback 1,1x); no comprar > pivote +5%',
                  'exit': 'Stop por cierre; +2R vender 1/3 y stop del resto a breakeven; runner sale con cierre bajo EMA20',
                  'risk': '1% por operación, 6% riesgo total, 20% peso máximo (editable en la app)'},
        'entries_count': len(entries), 'activated_count': sum(e['actionable'] for e in entries),
        'quotes_count': len(quotes), 'tracked_missing': missing, 'errors': errors[:20],
        'broker_connected': False, 'orders_enabled': False,
        'entries': entries, 'quotes': quotes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Entradas', len(entries), 'activadas', payload['activated_count'], 'cotizaciones', len(quotes))


if __name__ == '__main__':
    main()
