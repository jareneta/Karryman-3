"""Karryman · backtest del sistema completo y variantes de optimización.

Replica sin lookahead las reglas de la app:
- Filtros (al cierre de la señal): precio >= 5, volumen medio 50 >= 500k,
  cierre > MA50 > MA200 con MA200 subiendo (20 sesiones), cierre >= 85% del
  máximo de 52 semanas, rentabilidad 63 sesiones mejor que SPY.
- Entrada: cierre > pivote con volumen (base: máximo 30 sesiones previas, vol >= 1,4x;
  pullback tras tocar la EMA20: máximo 5 sesiones previas, vol >= 1,1x), primer cruce.
  Compra a la apertura siguiente si no supera pivote +5%. Stop: mínimo de 10 (base)
  o 5 (pullback) sesiones previas; riesgo <= 12%.
- Salida: stop por cierre (sale a la apertura siguiente); +2R vende 1/3 y sube el stop
  a breakeven; el resto (runner) sale con cierre bajo la EMA20.
- Costes: 0,10% por lado (comisión + deslizamiento).
- Cartera: 1% de riesgo por operación, 6% de riesgo abierto total, 20% de peso máximo,
  exposición <= 100% del patrimonio; prioridad por fuerza relativa.

Limitaciones (se imprimen con los resultados): universo actual (sesgo de
supervivencia), sin fundamentales ni fechas de resultados históricas, datos de Yahoo.
Investigación únicamente: no envía órdenes.
"""
import argparse
import io
import json
import math
import random
import time
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

COST = 0.001  # por lado


@dataclass(frozen=True)
class Config:
    name: str = 'base'
    breakout: bool = True
    pullback: bool = True
    vol_breakout: float = 1.4
    vol_pullback: float = 1.1
    max_chase: float = 0.05
    max_risk: float = 0.12
    partial_r: float = 2.0
    partial_frac: float = 1 / 3
    be_after_partial: bool = True
    be_at_1r: bool = False
    trail: str = 'ema20'          # ema10 | ema20 | ma50 | w50 (media 50 semanas) | none
    trail_from_start: bool = False
    intraday_stop: bool = False
    time_stop: int = 0            # sesiones sin llegar a +1R -> salir (0 = no)
    regime: str = 'none'          # none | spy_ma200 | spy_ma50
    rs_min: float = 0.0
    near_high: float = 0.85
    placebo: bool = False
    entry: str = 'pivot30'        # pivot30 | base (VCP/asa, disparo diario) | base_weekly (cierre semanal)
    min_base_weeks: int = 5
    max_base_depth: float = 0.35
    min_prior_advance: float = 0.30
    max_tight: float = 0.12       # rango de las 2 últimas semanas / cierre
    climax_ext: float = 0.0       # 0 = sin salida por clímax; p. ej. 0.40 = 40% sobre la MA50
    climax_run: float = 0.25      # subida mínima en 15 sesiones para considerar clímax
    rs_rank_min: float = 0.0      # rango RS (percentil IBD) mínimo, 0 = sin filtro
    max_positions: int = 0        # 0 = sin límite de posiciones activas (los runners no cuentan)


VARIANTS = [
    Config(),
    Config(name='salida_todo_2R', partial_frac=1.0),
    Config(name='runner_EMA10', trail='ema10'),
    Config(name='runner_MA50', trail='ma50'),
    Config(name='mitad_en_2R', partial_frac=0.5),
    Config(name='parcial_en_3R', partial_r=3.0),
    Config(name='breakeven_en_1R', be_at_1r=True),
    Config(name='stop_intradia', intraday_stop=True),
    Config(name='stop_tiempo_10', time_stop=10),
    Config(name='mercado_SPY>MA200', regime='spy_ma200'),
    Config(name='mercado_SPY>MA50', regime='spy_ma50'),
    Config(name='riesgo_max_8', max_risk=0.08),
    Config(name='solo_rupturas', pullback=False),
    Config(name='solo_pullbacks', breakout=False),
    Config(name='volumen_2x', vol_breakout=2.0, vol_pullback=1.5),
    Config(name='persecucion_max_2', max_chase=0.02),
    Config(name='RS_>10pp', rs_min=10.0),
    Config(name='rupturas+parcial_3R', pullback=False, partial_r=3.0),
    Config(name='rupturas+runner_MA50', pullback=False, trail='ma50'),
    Config(name='rupturas+3R+MA50', pullback=False, partial_r=3.0, trail='ma50'),
    Config(name='R+2R+MA50sem', pullback=False, partial_r=2.0, trail='w50'),
    Config(name='R+3R+MA50sem', pullback=False, partial_r=3.0, trail='w50'),
    Config(name='R+4R+EMA20', pullback=False, partial_r=4.0),
    Config(name='R+4R+MA50', pullback=False, partial_r=4.0, trail='ma50'),
    Config(name='R+4R+MA50sem', pullback=False, partial_r=4.0, trail='w50'),
    Config(name='R+5R+MA50sem', pullback=False, partial_r=5.0, trail='w50'),
    Config(name='R+sin_parcial+MA50sem', pullback=False, partial_r=0.0, trail='w50', trail_from_start=False),
    Config(name='placebo_aleatorio', placebo=True),
]


# ---------------------------------------------------------------- datos
def universe():
    names = set()
    for market, url in [('nasdaq', 'https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt'),
                        ('other', 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt')]:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8-sig')
        df = pd.read_csv(io.StringIO(raw), sep='|', dtype=str)
        col = 'Symbol' if market == 'nasdaq' else 'ACT Symbol'
        for _, row in df.iterrows():
            t = str(row.get(col, '')).strip()
            if row.get('Test Issue') == 'N' and row.get('ETF') == 'N' and t.isascii() and t.isalpha() and 1 <= len(t) <= 5:
                names.add(t)
    return sorted(names)


def download(tickers, start):
    import yfinance as yf
    frames = {}
    for k in range(0, len(tickers), 40):
        batch = tickers[k:k + 40]
        for attempt in range(3):
            try:
                data = yf.download(batch, start=start, interval='1d', auto_adjust=True, progress=False,
                                   threads=True, group_by='ticker', timeout=60)
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            continue
        for t in batch:
            try:
                f = data[t] if isinstance(data.columns, pd.MultiIndex) else data
                f = f[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                if len(f) >= 260:
                    frames[t] = f
            except Exception:
                pass
        time.sleep(1)
    return frames


# ---------------------------------------------------------------- indicadores
def prepare(df, spy_close):
    d = df.copy()
    c, h, lo, v = d.Close, d.High, d.Low, d.Volume
    d['ma50'] = c.rolling(50).mean()
    d['ma200'] = c.rolling(200).mean()
    d['ma200_prev'] = d['ma200'].shift(20)
    d['ema10'] = c.ewm(span=10, adjust=False).mean()
    d['ema20'] = c.ewm(span=20, adjust=False).mean()
    d['ema21'] = c.ewm(span=21, adjust=False).mean()
    d['hi252'] = h.rolling(252).max()
    d['vol50'] = v.shift(1).rolling(50).mean()
    d['piv30'] = h.shift(1).rolling(30).max()
    d['piv5'] = h.shift(1).rolling(5).max()
    d['low10'] = lo.shift(1).rolling(10).min()
    d['low5'] = lo.shift(1).rolling(5).min()
    touch = (lo <= d['ema20'] * 1.02).astype(float)
    d['touch'] = touch.shift(1).rolling(5).max() > 0
    spy = spy_close.reindex(d.index).ffill()
    d['rs'] = ((c / c.shift(63)) - (spy / spy.shift(63))) * 100
    # Media de 50 semanas: cierre semanal (último día de cada semana) por debajo de su SMA50 semanal.
    week = d.index.to_period('W-FRI')
    wk_close = c.groupby(week).last()
    wk_ma = wk_close.rolling(50).mean()
    below = (wk_close < wk_ma)
    last_of_week = pd.Series(week, index=d.index) != pd.Series(week, index=d.index).shift(-1)
    d['w50_exit'] = (last_of_week & pd.Series(week, index=d.index).map(below).fillna(False).astype(bool)).astype(float)
    below10 = (wk_close < wk_close.rolling(10).mean())
    d['w10_exit'] = (last_of_week & pd.Series(week, index=d.index).map(below10).fillna(False).astype(bool)).astype(float)
    d['rs_rank'] = np.nan
    # Bases (VCP / taza con asa): máximo previo de 52 semanas como pivote, sesiones desde ese máximo,
    # profundidad de la base, subida previa y estrechez del lado derecho. Todo con datos hasta ayer.
    hs, ls = h.shift(1), lo.shift(1)
    bh = hs.rolling(252, min_periods=60).max()
    is_new = (hs >= bh) & bh.notna()
    n = len(d)
    last_pos = pd.Series(np.where(is_new.values, np.arange(n), np.nan), index=d.index).ffill()
    d['base_high'] = bh
    d['base_len'] = np.arange(n) - last_pos
    seg = is_new.cumsum()
    d['base_low'] = ls.groupby(seg).cummin()
    d['base_depth'] = 1 - d['base_low'] / bh
    d['prior_adv'] = bh / lo.rolling(252, min_periods=60).min() - 1
    d['tight'] = (hs.rolling(10).max() - ls.rolling(10).min()) / c
    d['ret15'] = c / c.shift(15) - 1
    wk = pd.Series(week, index=d.index)
    d['last_of_week'] = last_of_week
    d['week_pivot'] = bh.groupby(wk).transform('first')
    d['week_base_len'] = d['base_len'].groupby(wk).transform('first')
    d['week_depth'] = d['base_depth'].groupby(wk).transform('first')
    wvol = v.groupby(wk).transform('sum')
    wk_vol = v.groupby(week).sum()
    d['week_vol_ratio'] = wvol / wk.map(wk_vol.shift(1).rolling(10).mean())
    d.attrs['a'] = {k: d[k].to_numpy(dtype=float) for k in ('Open', 'High', 'Low', 'Close', 'ema10', 'ema20', 'ema21', 'ma50',
                                                            'w50_exit', 'w10_exit', 'ret15')}
    return d


def regime_series(spy):
    c = spy.Close
    ma50 = c.rolling(50).mean()
    return pd.DataFrame({'spy_ma200': c > c.rolling(200).mean(), 'spy_ma50': c > ma50,
                         'spy_ma50_up': (c > ma50) & (ma50 > ma50.shift(10)),
                         'spy_ema21': c > c.ewm(span=21, adjust=False).mean()})


def attach_rs_rank(prepared, index):
    """Rango RS tipo IBD (40% 3m + 20% 6, 9 y 12 meses) en percentil sobre las acciones líquidas."""
    def score(c):
        r = lambda n: c / c.shift(n) - 1
        return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)
    sc = pd.DataFrame({t: score(d.Close) for t, d in prepared.items()}).reindex(index)
    liq = pd.DataFrame({t: (d.Close >= 5) & (d.vol50 >= 300_000) for t, d in prepared.items()}).reindex(index).fillna(False)
    rank = sc.where(liq).rank(axis=1, pct=True) * 100
    for t, d in prepared.items():
        d['rs_rank'] = rank[t].reindex(d.index)


def signals(d, cfg, regime, rng=None):
    """Señales al cierre del día i; la compra se intenta en la apertura de i+1."""
    c, v = d.Close, d.Volume
    base = ((c >= 5) & (d.vol50 >= 500_000) & (c > d.ma50) & (d.ma50 > d.ma200) & (d.ma200 > d.ma200_prev)
            & (c >= cfg.near_high * d.hi252) & (d.rs > cfg.rs_min))
    if cfg.rs_rank_min > 0:
        base &= d.rs_rank.fillna(0) >= cfg.rs_rank_min
    if cfg.regime != 'none':
        base &= regime[cfg.regime].reindex(d.index).fillna(False).astype(bool)
    out = []
    if cfg.placebo:
        # Control: mismos filtros de liquidez, fecha aleatoria, mismo stop y salidas.
        liquid = (c >= 5) & (d.vol50 >= 500_000) & d.low10.notna() & d.ma200.notna()
        idx = np.flatnonzero(liquid.values)
        if len(idx) and rng is not None:
            for i in rng.choice(idx, size=max(1, len(idx) // 120), replace=False):
                out.append((int(i), 'placebo', float(c.iloc[i]) * (1 + cfg.max_chase), float(d.low10.iloc[i]), 0.0))
        return out
    if cfg.entry in ('base', 'base_weekly'):
        common = (base & (d.prior_adv >= cfg.min_prior_advance))
        if cfg.entry == 'base':
            sig = (common & (d.base_len >= 5 * cfg.min_base_weeks) & (d.base_depth <= cfg.max_base_depth)
                   & (d.tight <= cfg.max_tight) & (c > d.base_high) & (c.shift(1) <= d.base_high.shift(1))
                   & (v >= cfg.vol_breakout * d.vol50))
            piv = d.base_high
        else:
            sig = (common & d.last_of_week & (d.week_base_len >= 5 * cfg.min_base_weeks)
                   & (d.week_depth <= cfg.max_base_depth) & (c > d.week_pivot)
                   & (d.week_vol_ratio >= cfg.vol_breakout) & (d.tight <= cfg.max_tight * 1.5))
            piv = d.week_pivot
        for i in np.flatnonzero(sig.fillna(False).values):
            out.append((int(i), 'base', float(piv.iloc[i]), float(d.low10.iloc[i]),
                        float(d.rs_rank.iloc[i]) if d.rs_rank.notna().iloc[i] else float(d.rs.iloc[i])))
        return out
    if cfg.breakout:
        brk = base & (c > d.piv30) & (v >= cfg.vol_breakout * d.vol50) & (c.shift(1) <= d.piv30.shift(1))
        for i in np.flatnonzero(brk.fillna(False).values):
            out.append((int(i), 'ruptura', float(d.piv30.iloc[i]), float(d.low10.iloc[i]), float(d.rs.iloc[i])))
    if cfg.pullback:
        pb = base & d.touch & (c > d.piv5) & (v >= cfg.vol_pullback * d.vol50) & (c.shift(1) <= d.piv5.shift(1))
        if cfg.breakout:
            pb &= ~((c > d.piv30) & (v >= cfg.vol_breakout * d.vol50))
        for i in np.flatnonzero(pb.fillna(False).values):
            out.append((int(i), 'pullback', float(d.piv5.iloc[i]), float(d.low5.iloc[i]), float(d.rs.iloc[i])))
    return out


# ---------------------------------------------------------------- operación
@dataclass
class Trade:
    ticker: str
    kind: str
    entry_i: int
    entry: float
    stop0: float
    rs: float
    stop: float = 0.0
    rem: float = 1.0
    partial: bool = False
    pending: bool = False
    realized: float = 0.0        # suma de fracción * (precio_salida - entrada)
    costs: float = 0.0
    exit_i: int = -1
    climax: bool = False
    hi: float = 0.0
    fills: list = field(default_factory=list)

    @property
    def R(self):
        return self.entry - self.stop0


def open_trade(d, ticker, sig, cfg):
    i, kind, pivot, stop, rs = sig
    if i + 1 >= len(d) or not (stop > 0):
        return None
    a = d.attrs['a']
    close = a['Close'][i]
    if (close - stop) / close > cfg.max_risk or close <= stop:
        return None
    if not cfg.placebo and close > pivot * (1 + cfg.max_chase):
        return None
    o = a['Open'][i + 1]
    if o > pivot * (1 + cfg.max_chase) or o <= stop:
        return None
    t = Trade(ticker, kind, i + 1, o * (1 + COST), stop, rs)
    t.stop = stop
    t.costs = COST
    return t


def step(t, d, j, cfg):
    """Avanza la operación un día (j). Devuelve True si queda cerrada."""
    a = d.attrs['a']
    o, h, lo, c = a['Open'][j], a['High'][j], a['Low'][j], a['Close'][j]
    def sell(frac, price):
        px = price * (1 - COST)
        t.realized += frac * (px - t.entry)
        t.fills.append((j, frac, px))
        t.rem -= frac
    if t.pending:
        sell(t.rem, o); t.exit_i = j; return True
    if cfg.intraday_stop and lo <= t.stop:
        sell(t.rem, min(o, t.stop)); t.exit_i = j; return True
    R = t.R
    if cfg.be_at_1r and h >= t.entry + R:
        t.stop = max(t.stop, t.entry)
    if not t.partial and cfg.partial_r > 0 and h >= t.entry + cfg.partial_r * R:
        frac = min(t.rem, cfg.partial_frac)
        sell(frac, max(o, t.entry + cfg.partial_r * R))
        t.partial = True
        if cfg.be_after_partial:
            t.stop = max(t.stop, t.entry)
        if t.rem <= 1e-9:
            t.exit_i = j; return True
    trail_on = cfg.trail != 'none' and (t.partial or cfg.trail_from_start)
    t.hi = max(t.hi, c)
    if cfg.climax_ext > 0 and a['ma50'][j] > 0 and c >= a['ma50'][j] * (1 + cfg.climax_ext) and a['ret15'][j] >= cfg.climax_run:
        t.pending = True  # clímax: subida vertical muy extendida sobre la MA50 -> vender todo
        t.climax = True
    elif c <= t.stop:
        t.pending = True
    elif trail_on and cfg.trail in ('w50', 'w10') and a[cfg.trail + '_exit'][j] > 0:
        t.pending = True
    elif trail_on and cfg.trail.startswith('tr') and c <= t.hi * (1 - int(cfg.trail[2:]) / 100):
        t.pending = True
    elif trail_on and cfg.trail not in ('w50', 'w10') and not cfg.trail.startswith('tr') and c < a[cfg.trail][j]:
        t.pending = True
    elif cfg.time_stop and not t.partial and j - t.entry_i >= cfg.time_stop and c < t.entry + R:
        t.pending = True
    return False


def finish(t, d):
    if t.rem > 1e-9:
        px = d.attrs['a']['Close'][-1]
        t.realized += t.rem * (px - t.entry)
        t.rem = 0
        t.exit_i = len(d) - 1
    return t.realized / t.R if t.R > 0 else 0.0


def simulate_independent(prepared, cfg, regime, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for tk, d in prepared.items():
        for sig in signals(d, cfg, regime, rng):
            t = open_trade(d, tk, sig, cfg)
            if not t:
                continue
            for j in range(t.entry_i, len(d)):
                if step(t, d, j, cfg):
                    break
            r = finish(t, d)
            rows.append({'ticker': tk, 'kind': t.kind, 'entry_date': d.index[t.entry_i], 'exit_date': d.index[t.exit_i],
                         'r': r, 'days': t.exit_i - t.entry_i, 'risk_pct': t.R / t.entry * 100, 'rs': t.rs,
                         'partial': t.partial, 'climax': t.climax})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- cartera
def simulate_portfolio(prepared, cfg, regime, start, end, seed=7, risk_pct=0.01, total_risk=0.06, max_weight=0.20,
                       spy_close=None, sweep=False, with_exposure=False, risk_basis='price', leverage=1.0,
                       margin_rate=0.06):
    rng = np.random.default_rng(seed)
    by_date = {}
    for tk, d in prepared.items():
        for sig in signals(d, cfg, regime, rng):
            i = sig[0]
            if i + 1 < len(d):
                by_date.setdefault(d.index[i + 1], []).append((tk, sig))
    dates = sorted(set().union(*[set(d.index) for d in prepared.values()]))
    dates = [x for x in dates if start <= x <= end]
    pos = {}
    cash, equity_curve = 1.0, []
    pos_idx = {tk: {dt: k for k, dt in enumerate(d.index)} for tk, d in prepared.items()}
    trades = 0
    exposure = []
    spy_px = spy_close.reindex(dates).ffill() if spy_close is not None else None
    prev_dt = None
    for dt in dates:
        # Efectivo sin usar invertido en SPY (si sweep): crece con el SPY del día anterior a hoy.
        if sweep and spy_px is not None and prev_dt is not None and cash > 0:
            cash *= float(spy_px.loc[dt]) / float(spy_px.loc[prev_dt])
        if cash < 0 and prev_dt is not None:
            cash *= 1 + margin_rate * (dt - prev_dt).days / 365.0  # intereses del margen
        prev_dt = dt
        # valor de mercado y riesgo abierto a la apertura
        def mark(field='Close', at=None):
            val = 0.0
            for tk, (t, q) in pos.items():
                k = pos_idx[tk].get(dt)
                px = prepared[tk].attrs['a'][field][k] if k is not None else t.entry
                val += q * t.rem * px
            return val
        equity_open = cash + mark('Open')
        # salidas pendientes y gestión diaria de posiciones
        for tk in list(pos):
            t, q = pos[tk]
            k = pos_idx[tk].get(dt)
            if k is None or k < t.entry_i:
                continue
            before = t.rem
            closed = step(t, prepared[tk], k, cfg) if k >= t.entry_i else False
            sold = before - t.rem
            if sold > 0:
                cash += q * sum(frac * px for (jj, frac, px) in t.fills if jj == k)
            if closed:
                del pos[tk]
        # entradas a la apertura (ya filtradas por el día de la señal)
        cands = by_date.get(dt, [])
        cands.sort(key=lambda x: -x[1][4])
        open_risk = 0.0
        for tk2, (t2, q2) in pos.items():
            k2 = pos_idx[tk2].get(dt)
            last = prepared[tk2].attrs['a']['Close'][(k2 if k2 is not None else t2.entry_i + 1) - 1]
            base_px = last if risk_basis == 'price' else min(last, t2.entry)
            open_risk += q2 * t2.rem * max(0.0, base_px - t2.stop)
        for tk, sig in cands:
            if tk in pos:
                continue
            if cfg.max_positions and sum(1 for (tt_, _) in pos.values() if not tt_.partial) >= cfg.max_positions:
                break
            d = prepared[tk]
            t = open_trade(d, tk, sig, cfg)
            if not t or d.index[t.entry_i] != dt:
                continue
            per = t.entry - t.stop0
            budget = min(equity_open * risk_pct, max(0.0, equity_open * total_risk - open_risk))
            gross = mark('Open')
            room = max(0.0, equity_open * leverage - gross) if leverage > 1 else max(0.0, cash)
            q = min(budget / per, equity_open * max_weight / t.entry, room / t.entry)
            if q * t.entry < equity_open * 0.01:
                continue
            cash -= q * t.entry
            open_risk += q * per
            pos[tk] = (t, q)
            trades += 1
            k = pos_idx[tk][dt]
            before = t.rem
            closed = step(t, d, k, cfg)
            if before - t.rem > 0:
                cash += q * sum(frac * px for (jj, frac, px) in t.fills if jj == k)
            if closed:
                del pos[tk]
        invested = mark('Close')
        equity_curve.append((dt, cash + invested))
        exposure.append(invested / (cash + invested) if cash + invested > 0 else 0)
        if cash + invested <= 0:
            break  # ruina (margen)
    eq = pd.Series([v for _, v in equity_curve], index=[x for x, _ in equity_curve])
    if with_exposure:
        return eq, trades, pd.Series(exposure, index=eq.index)
    return eq, trades


def curve_stats(eq):
    if len(eq) < 2:
        return {}
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
    dd = (eq / eq.cummax() - 1).min()
    rets = eq.pct_change().dropna()
    sharpe = rets.mean() / rets.std() * math.sqrt(252) if rets.std() > 0 else 0
    return {'cagr_pct': round(cagr * 100, 2), 'max_dd_pct': round(dd * 100, 2), 'sharpe': round(float(sharpe), 2),
            'final_multiple': round(float(eq.iloc[-1] / eq.iloc[0]), 3)}


def r_stats(df):
    if df is None or not len(df):
        return {'trades': 0}
    r = df.r
    wins, losses = r[r > 0], r[r <= 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else float('inf')
    boot = np.random.default_rng(1).choice(r.values, size=(1000, len(r)), replace=True).mean(axis=1)
    return {'trades': int(len(r)), 'expectancy_R': round(float(r.mean()), 3),
            'ci95_R': [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
            'win_rate_pct': round(float((r > 0).mean() * 100), 1),
            'avg_win_R': round(float(wins.mean()), 2) if len(wins) else 0,
            'avg_loss_R': round(float(losses.mean()), 2) if len(losses) else 0,
            'profit_factor': round(float(pf), 2) if math.isfinite(pf) else None,
            'median_days': int(df.days.median()), 'reached_2R_pct': round(float(df.partial.mean() * 100), 1)}


# ---------------------------------------------------------------- rotación de líderes
def simulate_rotation(prepared, regime, start, end, top_n=10, min_rank=90.0, min_dollar_vol=20e6,
                      regime_key='spy_ma50_up', exit_ma='ma50', trailing=0.0):
    """Cada viernes: mantener las top_n acciones con mayor rango RS que cumplen la plantilla de tendencia
    y liquidez; fuera de régimen alcista, liquidez. Entre rebalanceos, venta si cierra bajo exit_ma
    o cae un `trailing` desde su máximo. Pesos iguales, compra/venta a la apertura siguiente, 0,10% por lado."""
    dates = pd.DatetimeIndex([x for x in regime.index if start <= x <= end])
    tickers = list(prepared)
    P = lambda f: pd.DataFrame({t: f(d) for t, d in prepared.items()}).reindex(dates).to_numpy(float)
    O, C, EX, RK = P(lambda d: d.Open), P(lambda d: d.Close), P(lambda d: d[exit_ma]), P(lambda d: d.rs_rank)
    EL = pd.DataFrame({t: ((d.Close > d.ma50) & (d.ma50 > d.ma200) & (d.ma200 > d.ma200_prev) & (d.Close >= 0.75 * d.hi252)
                           & ((d.Close * d.vol50) >= min_dollar_vol) & (d.rs_rank >= min_rank))
                       for t, d in prepared.items()}).reindex(dates).fillna(False).to_numpy(bool)
    reg = regime[regime_key].reindex(dates).fillna(False).to_numpy(bool)
    wk = dates.to_period('W-FRI')
    rebal = np.r_[wk[1:] != wk[:-1], True]
    cash, pos, hi, eq = 1.0, {}, {}, np.empty(len(dates))
    sell, buy, trades = set(), [], 0
    for k in range(len(dates)):
        for j in list(sell):
            if j in pos and not np.isnan(O[k, j]):
                cash += pos.pop(j) * O[k, j] * (1 - COST); hi.pop(j, None); sell.discard(j)
            elif j not in pos:
                sell.discard(j)
        if buy:
            equity = cash + sum(q * (O[k, j] if not np.isnan(O[k, j]) else C[k - 1, j]) for j, q in pos.items())
            slot = equity / top_n
            for j in buy:
                if j in pos or len(pos) >= top_n or np.isnan(O[k, j]):
                    continue
                amt = min(slot, cash)
                if amt <= equity * 0.02:
                    continue
                px = O[k, j] * (1 + COST)
                pos[j] = amt / px; cash -= amt; hi[j] = px; trades += 1
            buy = []
        value = 0.0
        for j, q in pos.items():
            c = C[k, j]
            if np.isnan(c):
                c = C[k - 1, j] if k else 0.0
                value += q * c
                continue
            value += q * c
            hi[j] = max(hi.get(j, c), c)
            if (not np.isnan(EX[k, j]) and c < EX[k, j]) or (trailing and c <= hi[j] * (1 - trailing)):
                sell.add(j)
        eq[k] = cash + value
        if rebal[k]:
            if not reg[k]:
                sell |= set(pos)
                continue
            cand = np.flatnonzero(EL[k])
            order = cand[np.argsort(-RK[k, cand])]
            keep = set(order[:top_n * 2].tolist())
            for j in pos:
                if j not in keep:
                    sell.add(j)
            free = top_n - (len(pos) - len([j for j in pos if j in sell]))
            buy = [j for j in order[:top_n].tolist() if j not in pos][:max(0, free)]
    return pd.Series(eq, index=dates), trades


# ---------------------------------------------------------------- comparación con el SPY
FINAL = Config(name='reglas_finales', pullback=False, partial_r=4.0, trail='w50')
ANTERIOR = Config(name='reglas_anteriores')


def yearly(eq):
    y = eq.groupby(eq.index.year).last()
    first = eq.iloc[0]
    out, prev = {}, first
    for year, val in y.items():
        out[str(year)] = round((val / prev - 1) * 100, 1)
        prev = val
    return out


def benchmark(prepared, regime, spy, start, end, split, a, universe_size, sample, t0):
    spy_eval = spy.Close[(spy.Close.index >= start) & (spy.Close.index <= end)]
    spy_eq = spy_eval / spy_eval.iloc[0]
    rows = {'SPY comprar y mantener': {**curve_stats(spy_eq), 'exposure_pct': 100.0, 'trades': 0,
                                       'in_sample': curve_stats(spy_eq[spy_eq.index < split]),
                                       'out_of_sample': curve_stats(spy_eq[spy_eq.index >= split]), 'yearly': yearly(spy_eq)}}
    def L(name, **kw):
        base = dict(pullback=False, entry='base', partial_r=2.0, partial_frac=1 / 3, trail='tr25',
                    rs_rank_min=80, regime='spy_ma50_up', climax_ext=0.50, climax_run=0.25)
        base.update(kw)
        return Config(name=name, **base)
    a_tr25 = L('A líderes VCP · trailing 25%')
    a_w50 = L('A líderes VCP · MA50 sem', trail='w50')
    a_tr15 = L('A líderes VCP · trailing 15%', trail='tr15')
    a_piv = L('A líderes pivote30 · trailing 25%', entry='pivot30')
    a_noreg = L('A líderes VCP · sin filtro mercado', regime='none')
    b_conc = L('B concentrada 5 pos · trailing 25%', max_positions=5)
    print('--- Por operación (sin límites de cartera) ---')
    for cfg in (a_tr25, a_w50, a_tr15, a_piv, a_noreg, ANTERIOR):
        tr = simulate_independent(prepared, cfg, regime)
        tr = tr[tr.entry_date >= start] if len(tr) else tr
        st, ins, oos = r_stats(tr), r_stats(tr[tr.entry_date < split]), r_stats(tr[tr.entry_date >= split])
        print(f"{cfg.name:36s} n={st.get('trades')} ops/año={round(st.get('trades',0)/((end-start).days/365.25),1)} "
              f"E={st.get('expectancy_R')}R IC95={st.get('ci95_R')} IS={ins.get('expectancy_R')} OOS={oos.get('expectancy_R')} "
              f"acierto={st.get('win_rate_pct')}% PF={st.get('profit_factor')}", flush=True)
    scenarios = [('A líderes VCP · tr25 · 1%', a_tr25, 0.01, False, 'entry', 1.0),
                 ('A líderes VCP · MA50sem · 1%', a_w50, 0.01, False, 'entry', 1.0),
                 ('A líderes VCP · tr15 · 1%', a_tr15, 0.01, False, 'entry', 1.0),
                 ('A líderes pivote30 · tr25 · 1%', a_piv, 0.01, False, 'entry', 1.0),
                 ('A sin filtro mercado · tr25 · 1%', a_noreg, 0.01, False, 'entry', 1.0),
                 ('B concentrada 5 pos · 2%', b_conc, 0.02, False, 'entry', 1.0),
                 ('A líderes VCP · tr25 · 1% + SPY', a_tr25, 0.01, True, 'entry', 1.0),
                 ('Anteriores 1% (referencia)', ANTERIOR, 0.01, False, 'price', 1.0)]
    for label, kw in (('C rotación top10 RS≥90 · MA50', dict(top_n=10, min_rank=90, exit_ma='ma50')),
                      ('C rotación top10 RS≥90 · EMA21', dict(top_n=10, min_rank=90, exit_ma='ema21')),
                      ('C rotación top5 RS≥95 · MA50', dict(top_n=5, min_rank=95, exit_ma='ma50')),
                      ('C rotación top10 · tr25 · sin mercado', dict(top_n=10, min_rank=90, exit_ma='ma50', trailing=0.25,
                                                                      regime_key='spy_ma200'))):
        eq, n = simulate_rotation(prepared, regime, start, end, **kw)
        years = (eq.index[-1] - eq.index[0]).days / 365.25
        rows[label] = {**curve_stats(eq), 'exposure_pct': None, 'trades': n, 'trades_per_year': round(n / years, 1),
                       'in_sample': curve_stats(eq[eq.index < split]), 'out_of_sample': curve_stats(eq[eq.index >= split]),
                       'yearly': yearly(eq), 'spy_same_exposure': {}}
        r = rows[label]
        print(f"{label:38s} CAGR={r['cagr_pct']:6}% DD={r['max_dd_pct']:7}% Sharpe={r['sharpe']:5} "
              f"x{r['final_multiple']:6} ops/año={r['trades_per_year']:5}", flush=True)
    for label, cfg, risk, sweep, basis, lev in scenarios:
        eq, n, ex = simulate_portfolio(prepared, cfg, regime, start, end, risk_pct=risk, total_risk=6 * risk,
                                       spy_close=spy.Close, sweep=sweep, with_exposure=True, risk_basis=basis,
                                       leverage=lev)
        years = (eq.index[-1] - eq.index[0]).days / 365.25
        rows[label] = {**curve_stats(eq), 'exposure_pct': round(float(ex.mean()) * 100, 1),
                       'trades': n, 'trades_per_year': round(n / years, 1),
                       'in_sample': curve_stats(eq[eq.index < split]),
                       'out_of_sample': curve_stats(eq[eq.index >= split]), 'yearly': yearly(eq)}
        # SPY con la misma exposición media (resto en efectivo sin interés): comparación de riesgo equivalente
        e = float(ex.mean())
        mix = (1 + spy_eval.pct_change().fillna(0) * e).cumprod()
        rows[label]['spy_same_exposure'] = curve_stats(mix)
        r = rows[label]
        print(f"{label:38s} CAGR={r['cagr_pct']:6}% DD={r['max_dd_pct']:7}% Sharpe={r['sharpe']:5} "
              f"x{r['final_multiple']:6} expos={r['exposure_pct']:5}% ops/año={r['trades_per_year']:5} "
              f"| SPY a igual exposición CAGR={r['spy_same_exposure']['cagr_pct']}% DD={r['spy_same_exposure']['max_dd_pct']}%",
              flush=True)
    s = rows['SPY comprar y mantener']
    print(f"{'SPY comprar y mantener':38s} CAGR={s['cagr_pct']:6}% DD={s['max_dd_pct']:7}% Sharpe={s['sharpe']:5} x{s['final_multiple']:6}")
    years = sorted(s['yearly'])
    print('AÑO   ' + ' '.join(f'{y:>6}' for y in years))
    for label, r in rows.items():
        print(f"{label[:30]:30s} " + ' '.join(f"{r['yearly'].get(y, 0):6}" for y in years))
    for label, r in rows.items():
        print(f"{label[:38]:38s} IS CAGR={r['in_sample'].get('cagr_pct')}% DD={r['in_sample'].get('max_dd_pct')}% | "
              f"OOS CAGR={r['out_of_sample'].get('cagr_pct')}% DD={r['out_of_sample'].get('max_dd_pct')}%")
    payload = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'mode': 'benchmark', 'universe_size': universe_size,
               'sample': sample, 'with_data': len(prepared), 'start': str(start.date()), 'end': str(end.date()),
               'split': a.split, 'rows': rows, 'seconds': round(time.time() - t0)}
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding='utf-8')


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=700)
    ap.add_argument('--start', default='2013-06-01')
    ap.add_argument('--split', default='2021-01-01')
    ap.add_argument('--output', default='data/system_backtest.json')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--benchmark', action='store_true', help='Comparar solo las reglas finales y anteriores con el SPY')
    a = ap.parse_args()
    t0 = time.time()
    names = universe()
    random.Random(a.seed).shuffle(names)
    sample = names[:a.symbols]
    frames = download(['SPY'] + sample, a.start)
    spy = frames.pop('SPY')
    regime = regime_series(spy)
    prepared = {tk: prepare(f, spy.Close) for tk, f in frames.items()}
    attach_rs_rank(prepared, spy.index)
    split = pd.Timestamp(a.split)
    eval_start = pd.Timestamp(a.start) + pd.Timedelta(days=400)
    end = spy.index[-1]
    print(f'Universo: {len(names)} · muestra {len(sample)} · con datos {len(prepared)} · {time.time()-t0:.0f}s')
    if a.benchmark:
        return benchmark(prepared, regime, spy, eval_start, end, split, a, len(names), len(sample), t0)
    results = {}
    for cfg in VARIANTS:
        tr = simulate_independent(prepared, cfg, regime)
        if len(tr):
            tr = tr[tr.entry_date >= eval_start]
        ins = tr[tr.entry_date < split] if len(tr) else tr
        oos = tr[tr.entry_date >= split] if len(tr) else tr
        res = {'all': r_stats(tr), 'in_sample': r_stats(ins), 'out_of_sample': r_stats(oos)}
        if len(tr):
            res['by_year'] = {str(y): round(float(g.r.mean()), 3) for y, g in tr.groupby(tr.entry_date.dt.year)}
            res['by_kind'] = {k: r_stats(g) for k, g in tr.groupby('kind')}
            res['by_regime'] = {}
            reg = regime.spy_ma200.reindex(tr.entry_date).values
            for lbl, mask in (('SPY>MA200', reg == True), ('SPY<MA200', reg == False)):  # noqa: E712
                res['by_regime'][lbl] = r_stats(tr[mask])
        if not cfg.placebo:
            eq, n = simulate_portfolio(prepared, cfg, regime, eval_start, end)
            res['portfolio'] = {**curve_stats(eq), 'trades': n,
                                'in_sample': curve_stats(eq[eq.index < split]),
                                'out_of_sample': curve_stats(eq[eq.index >= split])}
        results[cfg.name] = res
        s = res['all']
        print(f"{cfg.name:20s} n={s.get('trades',0):5d} E={s.get('expectancy_R','-')!s:>6}R "
              f"IS={res['in_sample'].get('expectancy_R','-')!s:>6} OOS={res['out_of_sample'].get('expectancy_R','-')!s:>6} "
              f"win={s.get('win_rate_pct','-')}% PF={s.get('profit_factor','-')} "
              f"cartera CAGR={res.get('portfolio',{}).get('cagr_pct','-')}% DD={res.get('portfolio',{}).get('max_dd_pct','-')}%",
              flush=True)
    spy_eval = spy.Close[spy.Close.index >= eval_start]
    payload = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'universe_size': len(names),
               'sample': len(sample), 'with_data': len(prepared), 'start': str(eval_start.date()), 'end': str(end.date()),
               'split': a.split, 'cost_per_side_pct': COST * 100,
               'spy_buy_hold': {**curve_stats(spy_eval), 'in_sample': curve_stats(spy_eval[spy_eval.index < split]),
                                'out_of_sample': curve_stats(spy_eval[spy_eval.index >= split])},
               'limitations': ['Universo de acciones cotizadas hoy: sesgo de supervivencia (sobrestima resultados).',
                               'Sin filtros fundamentales ni fechas de resultados históricas.',
                               'Datos diarios de Yahoo ajustados; ejecución a la apertura con 0,10% de coste por lado.',
                               'Muestra aleatoria del universo; resultados con incertidumbre (ver IC 95%).'],
               'variants': results, 'seconds': round(time.time() - t0)}
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print('SPY comprar y mantener:', json.dumps(payload['spy_buy_hold']))
    print('RESUMEN_JSON ' + json.dumps({k: {'all': v['all'], 'is': v['in_sample'].get('expectancy_R'),
                                            'oos': v['out_of_sample'].get('expectancy_R'),
                                            'pf': v.get('portfolio')} for k, v in results.items()}, default=str))


if __name__ == '__main__':
    main()
