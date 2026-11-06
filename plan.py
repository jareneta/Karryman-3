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

import screener
import trade_levels

DATA = Path('data')
OUT = DATA / 'plan.json'
TICKER = re.compile(r'^[A-Z][A-Z.\-]{0,9}$')


def read(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


PARTIAL_R = 3.0          # vender 1/3 en +3R (backtest: mejor que +2R)
MAX_EARNINGS_LOOKUPS = 80
UNIVERSE_MAX = 2500


def universe_tickers():
    """Lista exportada de tu screener de Stock Analysis (solo tickers)."""
    u = read('universe.json', {})
    tickers = sorted({str(t).strip().upper() for t in u.get('tickers', []) if TICKER.match(str(t).strip().upper())})
    return tickers[:UNIVERSE_MAX], u


def tracked_tickers():
    raw = read('tracked.json', {}).get('tickers', [])
    return sorted({str(t).strip().upper() for t in raw if TICKER.match(str(t).strip().upper())})[:60]


EARNINGS_BLOCK_DAYS = 14
CRITERIA_TEXT = {
    'tendencia': 'Tendencia: precio > MA50 > MA200 y MA200 subiendo',
    'cerca_maximos': 'Cerca de máximos: a menos de un 15% del máximo de 52 semanas',
    'fuerza_vs_spy': 'Fuerza relativa: mejor que el SPY en 3 meses',
    'fundamentales': 'Fundamentales: capitalización > 300 M$ y ventas creciendo > 10%',
    'liquidez': 'Liquidez: precio >= 5 $ y volumen medio >= 500.000',
}


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    if hasattr(value, 'date') and hasattr(value, 'hour'):
        return value.date()
    return value if hasattr(value, 'isoformat') else None


def earnings_info(ticker):
    """Próxima y última fecha de resultados según Yahoo: calendario y, si falta, historial."""
    today = datetime.now(timezone.utc).date()
    dates = []
    try:
        cal = yf.Ticker(ticker).calendar
        raw = cal.get('Earnings Date') if isinstance(cal, dict) else None
        dates += list(raw) if isinstance(raw, (list, tuple)) else [raw]
    except Exception:
        pass
    try:
        hist = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if hist is not None and len(hist):
            dates += list(hist.index)
    except Exception:
        pass
    days = {d for d in (_as_date(x) for x in dates) if d}
    future = [d for d in days if d >= today]
    past = [d for d in days if d < today]
    return {'next': min(future).isoformat() if future else None,
            'last': max(past).isoformat() if past else None}


def earnings_date(ticker):
    return earnings_info(ticker)['next']


SCREENER_TEXT = {
    'price_over_5': 'precio < 5 $', 'average_volume_over_500k': 'volumen medio < 500.000',
    'market_cap_over_300m': 'capitalización <= 300 M$', 'return_3m_over_10': 'subida 3 meses <= 10%',
    'return_6m_over_10': 'subida 6 meses <= 10%', 'return_1y_over_10': 'subida 1 año <= 10%',
    'within_15pct_52w_high': 'a más de un 15% del máximo de 52 semanas', 'above_ma50': 'precio bajo MA50',
    'above_ma200': 'precio bajo MA200', 'annual_revenue_growth_over_10': 'ventas anuales crecen <= 10%',
    'eps_over_minus_1': 'BPA <= -1', 'zero_dividend_yield': 'paga dividendo',
    'quarterly_revenue_growth_over_10': 'ventas trimestrales crecen <= 10%', 'above_ma20': 'precio bajo MA20',
}


def funnel():
    """Por qué se descartan acciones antes de llegar al plan."""
    discovery = read('discovery.json', {})
    discards = []
    for x in discovery.get('candidates', []):
        if not x.get('ticker'):
            continue
        r = screener.evaluate(x)
        if r['stock_analysis_status'] == 'DESCARTADA':
            discards.append({'ticker': r['ticker'],
                             'reasons': [SCREENER_TEXT.get(k, k) for k in r['failed']]})
    counts = discovery.get('filter_counts', {})
    return {'discovery_generated_utc': discovery.get('generated_utc'),
            'discovery_scanned': discovery.get('scanned_this_run'),
            'discovery_filter_counts': {k: v for k, v in counts.items() if k != 'pasa filtro técnico'},
            'discovery_passed': counts.get('pasa filtro técnico'),
            'screener_discards': sorted(discards, key=lambda d: d['ticker'])}


def criteria(x):
    """Resumen de tus criterios ya calculados por Screener/Setups."""
    notes = x.get('validation_notes') or {}
    earnings = notes.get('next_earnings_date')
    checks = {
        'tendencia': x.get('trend_ok') is True,
        'cerca_maximos': x.get('near_high_ok') is True,
        'fuerza_vs_spy': (x.get('rs_vs_spy_3m_pct') or -1) > 0,
        'fundamentales': x.get('fundamental_status') == 'CUMPLE',
    }
    if 'liquid_ok' in x:
        checks['liquidez'] = x.get('liquid_ok') is True
    return checks, earnings


def build(candidates, frames, tracked, earnings_lookup=None, compact=False):
    entries, quotes = [], {}
    lookups = 0
    for x in candidates:
        t = x.get('ticker')
        frame = frames.get(t)
        if frame is None:
            continue
        plan = trade_levels.entry_plan(frame, x.get('setup', 'TENDENCIA'), partial_r=PARTIAL_R)
        if plan.get('entry_status') == 'SIN_DATOS':
            continue
        checks, earnings = criteria(x)
        # Con universos grandes solo se guardan las que cumplen los criterios o están activadas.
        if compact and not all(checks.values()) and plan['entry_status'] != 'ACTIVADA':
            continue
        last_earnings = None
        relevant = plan['entry_status'] in ('ACTIVADA', 'ESPERANDO') and all(checks.values())
        if not earnings and earnings_lookup and (relevant or not compact) and lookups < MAX_EARNINGS_LOOKUPS:
            lookups += 1
            found = earnings_lookup(t)
            if isinstance(found, dict):
                earnings, last_earnings = found.get('next'), found.get('last')
            else:
                earnings = found
        failed = [CRITERIA_TEXT[k] for k in CRITERIA_TEXT if k in checks and not checks[k]]
        core = not failed
        warnings, blockers = [], []
        days = None
        if earnings:
            days = (datetime.fromisoformat(earnings).date() - datetime.now(timezone.utc).date()).days
            if days <= EARNINGS_BLOCK_DAYS:
                blockers.append(f'Resultados el {earnings} (en {days} días): no entrar a menos de '
                                f'{EARNINGS_BLOCK_DAYS} días de resultados')
        elif last_earnings and (datetime.now(timezone.utc).date()
                                - datetime.fromisoformat(last_earnings).date()).days <= 45:
            warnings.append(f'Publicó resultados el {last_earnings}; los próximos aún sin fecha '
                            '(normalmente unos 3 meses después)')
        else:
            warnings.append('Yahoo no publica fecha de resultados: compruébala en IBKR antes de comprar')
        blockers += ['No cumple ' + f for f in failed]
        entries.append({'ticker': t, 'setup': x.get('setup'), **plan, 'criteria': checks,
                        'meets_criteria': core, 'next_earnings_date': earnings, 'last_earnings_date': last_earnings,
                        'days_to_earnings': days,
                        'blockers': blockers,
                        'actionable': not blockers and plan['entry_status'] == 'ACTIVADA',
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


def download(tickers, period='2y'):
    frames, errors = {}, []
    for k in range(0, len(tickers), 20):
        batch = tickers[k:k + 20]
        try:
            prices = yf.download(batch, period=period, interval='1d', auto_adjust=True, progress=False,
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


def universe_candidates(tickers, frames, spy_close):
    """Candidatas a partir de la lista de Stock Analysis: criterios técnicos con precios.
    Los fundamentales los aplicó tu screener de Stock Analysis al exportar la lista."""
    out, counts = [], {}
    for t in tickers:
        f = frames.get(t)
        crit = trade_levels.criteria_from_prices(f, spy_close) if f is not None else None
        if crit is None:
            counts['sin datos suficientes'] = counts.get('sin datos suficientes', 0) + 1
            continue
        for key, label in (('liquid_ok', 'liquidez'), ('trend_ok', 'tendencia'), ('near_high_ok', 'lejos de máximos')):
            if not crit[key]:
                counts[label] = counts.get(label, 0) + 1
        if (crit['rs_vs_spy_3m_pct'] or -1) <= 0:
            counts['fuerza relativa <= SPY'] = counts.get('fuerza relativa <= SPY', 0) + 1
        out.append({'ticker': t, 'setup': 'RUPTURA_BASE', 'fundamental_status': 'CUMPLE', **crit})
    return out, counts


def main():
    tracked = tracked_tickers()
    universe, umeta = universe_tickers()
    setups = read('setups.json', {})
    if universe:
        tickers = sorted(set(universe) | set(tracked) | {'SPY'})
        frames, errors = download(tickers)
        spy = frames.pop('SPY', None)
        if spy is None:
            raise RuntimeError('No se pudo descargar SPY para la fuerza relativa')
        spy_close = trade_levels.clean(spy).Close
        if len(frames) < len(tickers) // 2:
            raise RuntimeError('Descargas insuficientes; se conserva el plan anterior')
        candidates, counts = universe_candidates(universe, frames, spy_close)
        entries, quotes = build(candidates, frames, tracked, earnings_lookup=earnings_info, compact=True)
        source = {'mode': 'stock_analysis', 'universe_size': len(universe), 'universe_updated_utc': umeta.get('updated_utc'),
                  'with_data': sum(1 for t in universe if t in frames), 'filter_counts': counts}
    else:
        candidates = [x for x in setups.get('candidates', []) if x.get('ticker')]
        tickers = sorted({x['ticker'] for x in candidates} | set(tracked))
        frames, errors = download(tickers)
        if tickers and len(frames) < len(tickers) // 2:
            raise RuntimeError('Descargas insuficientes; se conserva el plan anterior')
        entries, quotes = build(candidates, frames, tracked, earnings_lookup=earnings_info)
        source = {'mode': 'discovery', **funnel()}
    missing = [t for t in tracked if t not in quotes]
    payload = {
        'schema_version': 2, 'generated_utc': datetime.now(timezone.utc).isoformat(),
        'setups_generated_utc': setups.get('generated_utc'),
        'source': 'Yahoo Finance OHLCV vía yfinance (no oficial, puede tener retraso)',
        'rules': {'entry': 'Solo rupturas: cierre > máximo de 30 sesiones con volumen >= 1,4x; no comprar > pivote +5%',
                  'exit': f'Stop por cierre; +{PARTIAL_R:g}R vender 1/3 y stop del resto a breakeven; runner configurable',
                  'risk': '1% por operación, 6% riesgo total, 20% peso máximo (editable en la app)'},
        'partial_r': PARTIAL_R,
        'entries_count': len(entries),
        'earnings_known_count': sum(bool(e['next_earnings_date']) for e in entries),
        'earnings_recent_count': sum(bool(e['last_earnings_date']) and not e['next_earnings_date'] for e in entries),
        'activated_count': sum(e['actionable'] for e in entries),
        'quotes_count': len(quotes), 'tracked_missing': missing, 'errors': errors[:20],
        'broker_connected': False, 'orders_enabled': False,
        'funnel': source,
        'entries': entries, 'quotes': quotes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Fuente', source['mode'], 'entradas', len(entries), 'activadas', payload['activated_count'],
          'cotizaciones', len(quotes))


if __name__ == '__main__':
    main()
