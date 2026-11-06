"""Karryman: niveles de entrada (pivote) y cotizaciones para gestionar posiciones.

Reglas del usuario:
- Entrada: CIERRE por encima del pivote con volumen >= 1,4x la media de 50 sesiones
  (pullbacks: >= 1,1x, porque su volumen de giro suele ser menor).
- Pivote de base: máximo de las 30 sesiones previas. Pivote de pullback: máximo
  de las 5 sesiones previas (el "lower high" del retroceso).
- Stop: mínimo de las 10 sesiones previas al disparo (base) o de las 5 (pullback).
- No perseguir: si el cierre supera el pivote en más de un 5 %, queda EXTENDIDA.
Funciones puras sobre OHLCV diario; sin red ni órdenes.
"""
import math

import pandas as pd

BREAKOUT_VOLUME = 1.4
PULLBACK_VOLUME = 1.1
MAX_CHASE_PCT = 5.0
MAX_RISK_PCT = 12.0
LOOKBACK_TRIGGER = 5  # sesiones en las que se busca un disparo reciente
PULLBACK_SETUPS = {'PULLBACK_EMA20', 'PULLBACK_FORMACION'}


def _r(x, digits=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, digits) if math.isfinite(v) else None


def clean(df):
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(-1)
    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if any(c not in df.columns for c in cols):
        return None
    d = df[cols].dropna()
    return d if len(d) else None


def entry_plan(df, setup='TENDENCIA'):
    """Devuelve pivote, stop, objetivos y estado de la entrada para la última sesión."""
    d = clean(df)
    if d is None or len(d) < 60:
        return {'entry_status': 'SIN_DATOS'}
    kind = 'PULLBACK' if setup in PULLBACK_SETUPS else 'BASE'
    pivot_window, stop_window = (5, 5) if kind == 'PULLBACK' else (30, 10)
    min_vol = PULLBACK_VOLUME if kind == 'PULLBACK' else BREAKOUT_VOLUME
    h, lo, c, v = d.High, d.Low, d.Close, d.Volume
    ma50 = c.rolling(50).mean()
    n = len(d)

    def levels(i):
        """Pivote y stop tal como se conocían ANTES de la sesión i (sin lookahead)."""
        pivot = float(h.iloc[i - pivot_window:i].max())
        stop = float(lo.iloc[i - stop_window:i].min())
        avg = float(v.iloc[max(0, i - 50):i].mean())
        return pivot, stop, avg

    trigger = None
    for i in range(n - LOOKBACK_TRIGGER, n):
        pivot, stop, avg = levels(i)
        if avg > 0 and float(c.iloc[i]) > pivot and float(v.iloc[i]) >= min_vol * avg:
            trigger = (i, pivot, stop, float(v.iloc[i]) / avg)
    last = n - 1
    close = float(c.iloc[last])
    out = {'entry_kind': kind, 'trigger_rule': f'Cierre > pivote con volumen >= {min_vol}x media 50',
           'last_session': str(d.index[last].date()), 'close': _r(close)}
    if trigger:
        i, pivot, stop, volratio = trigger
        # Si compras ahora, la referencia realista es el último cierre (orden a la apertura).
        entry = close
        out['trigger_close'] = _r(c.iloc[i])
        sessions_ago = last - i
        extension = (close / pivot - 1) * 100
        day = str(d.index[i].date())
        if close <= pivot:
            status = 'FALLIDA'  # volvió a cerrar bajo el pivote
            reason = f'Rompió el pivote {pivot:.2f} el {day} pero ha vuelto a cerrar por debajo ({close:.2f})'
        elif close <= stop:
            status = 'INVALIDADA'
            reason = f'Cierre {close:.2f} en o bajo el stop {stop:.2f}'
        elif extension > MAX_CHASE_PCT:
            status = 'EXTENDIDA'
            reason = f'Cierre {close:.2f} un {extension:.1f}% sobre el pivote {pivot:.2f} (máximo {MAX_CHASE_PCT:.0f}%): no perseguir'
        else:
            status = 'ACTIVADA'
            reason = f'Cerró sobre el pivote {pivot:.2f} el {day} con volumen {volratio:.1f}x'
        out.update({'trigger_session': str(d.index[i].date()), 'sessions_since_trigger': sessions_ago,
                    'trigger_volume_ratio': _r(volratio)})
    else:
        pivot, stop, _ = levels(n)  # niveles vigentes para la próxima sesión
        entry = pivot
        extension = (close / pivot - 1) * 100
        m50 = float(ma50.iloc[last])
        if close <= stop:
            status, reason = 'INVALIDADA', f'Cierre {close:.2f} en o bajo el stop {stop:.2f} (mínimo de {stop_window} sesiones)'
        elif close < m50:
            status, reason = 'INVALIDADA', f'Cierre {close:.2f} por debajo de la MA50 {m50:.2f}: tendencia rota'
        else:
            status, reason = 'ESPERANDO', f'Falta un cierre sobre {pivot:.2f} ({-extension:.1f}% más arriba) con volumen >= {min_vol}x'
    risk = entry - stop
    risk_pct = risk / entry * 100 if entry > 0 else None
    if risk <= 0:
        status, reason = 'INVALIDADA', 'El stop no queda por debajo del precio de entrada'
    elif risk_pct > MAX_RISK_PCT and status in ('ESPERANDO', 'ACTIVADA'):
        status = 'RIESGO_ALTO'
        reason = (f'Stop {stop:.2f} a un {risk_pct:.1f}% de la entrada {entry:.2f} '
                  f'(máximo {MAX_RISK_PCT:.0f}%)')
    out.update({'entry_status': status, 'status_reason': reason, 'pivot': _r(pivot), 'entry_reference': _r(entry),
                'max_entry_price': _r(pivot * (1 + MAX_CHASE_PCT / 100)),
                'stop_reference': _r(stop) if risk > 0 else None,
                'risk_per_share': _r(risk) if risk > 0 else None,
                'risk_pct': _r(risk_pct) if risk > 0 else None,
                'target_1r': _r(entry + risk) if risk > 0 else None,
                'target_2r': _r(entry + 2 * risk) if risk > 0 else None,
                'distance_to_pivot_pct': _r(-extension)})
    return out


def quote(df, history=90):
    """Cotización e indicadores para gestionar posiciones en el navegador."""
    d = clean(df)
    if d is None or len(d) < 21:
        return None
    c = d.Close
    tail = d.iloc[-history:]
    return {'last_session': str(d.index[-1].date()), 'open': _r(d.Open.iloc[-1]),
            'high': _r(d.High.iloc[-1]), 'low': _r(d.Low.iloc[-1]), 'close': _r(c.iloc[-1]),
            'ema10': _r(c.ewm(span=10, adjust=False).mean().iloc[-1]),
            'ema20': _r(c.ewm(span=20, adjust=False).mean().iloc[-1]),
            'ma50': _r(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else None,
            # [fecha, máximo, mínimo, cierre] para medir +2R desde la fecha de entrada
            'bars': [[str(ix.date()), _r(r.High), _r(r.Low), _r(r.Close)] for ix, r in tail.iterrows()]}
