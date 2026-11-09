"""Karryman V24 · motor de simulación corregido (selección / riesgo / ejecución separados).

Investigación únicamente. No envía órdenes. Sin información futura: todas las señales se calculan con el cierre
del día i y las órdenes se ejecutan en la apertura del día i+1.

A. SELECCIÓN  (select): momentum de `mom_n` sesiones, entra el top `top_in`, permanece hasta salir del top
   `top_out`, máximo `max_pos` posiciones. Salida por extensión (cierre > EMA20 + 6 ATR) con espera REAL de
   `cooldown` sesiones. `rank_every`: 1 = ranking diario, 21 ≈ mensual (como el código histórico, documentado).
B. RIESGO     (Protection + exposición): volatilidad objetivo, protección progresiva con máquina de estados
   (niveles permitidos 35/50/75/100 %, bajada inmediata, subida de UN nivel tras `reentry_closes` cierres
   consecutivos cuyo drawdown permitiría un nivel superior), protección fija y guarda opcional de media móvil
   del patrimonio (ma100_guard, 25 %). Sin apalancamiento: exposición <= 100 % y efectivo >= 0.
C. EJECUCIÓN  (execute): comisión = max(fee_min, fee_per_share*acciones) limitada al 1 % del importe, slippage,
   acciones enteras o fraccionarias, importe mínimo por orden, banda de rebalanceo, límite de liquidez opcional,
   rechazos aleatorios opcionales. Las salidas obligatorias y las reducciones de riesgo NO se bloquean por
   importe mínimo ni por banda. Las posiciones viables: con capital pequeño el número de posiciones se limita a
   floor(exposición * patrimonio / importe mínimo) para que cada una alcance el mínimo (evita el bloqueo en
   efectivo que invalidó las simulaciones anteriores: 3.000 $ * 25 % / 15 = 50 $ < 100 $ de orden mínima).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

LEVELS = (0.35, 0.50, 0.75, 1.00)
DD_STEPS = ((0.12, 0.35), (0.08, 0.50), (0.04, 0.75))


@dataclass
class Cfg:
    capital: float = 3000.0
    mom_n: int = 63
    top_in: int = 15
    top_out: int = 45
    max_pos: int = 15
    rank_every: int = 1
    ema_n: int = 20
    atr_n: int = 14
    atr_mult: float = 6.0
    cooldown: int = 10
    vol_target: float = 0.15
    vol_n: int = 20
    protection: str = 'progressive'      # none | fixed | progressive
    fixed_dd: float = 0.08
    fixed_cap: float = 0.50
    reentry_closes: int = 5
    ma100_guard: bool = False
    ma_n: int = 100
    ma_cap: float = 0.25
    band: float = 0.0                     # banda relativa sobre el valor objetivo de cada posición
    min_order: float = 0.0
    fee_min: float = 0.0
    fee_per_share: float = 0.005
    fee_pct_max: float = 0.01
    slip_bps: float = 5.0
    fractional: bool = False
    adv_frac: float | None = None         # máximo % del volumen medio de 20 sesiones por orden
    reject_prob: float = 0.0
    seed: int = 1


def cap_from_dd(dd):
    for thr, cap in DD_STEPS:
        if dd >= thr:
            return cap
    return 1.0


class Protection:
    """Máquina de estados de la protección. `update(dd)` se llama con el cierre del día (sin futuro)."""

    def __init__(self, cfg):
        self.cfg, self.level, self.ok = cfg, 1.0, 0

    def update(self, dd):
        c = self.cfg
        if c.protection == 'none':
            return 1.0
        if c.protection == 'fixed':
            return c.fixed_cap if dd >= c.fixed_dd else 1.0
        raw = cap_from_dd(dd)
        if raw < self.level:
            self.level, self.ok = raw, 0
        elif raw > self.level:
            self.ok += 1
            if self.ok >= c.reentry_closes:
                self.level = min(l for l in LEVELS if l > self.level + 1e-12)
                self.ok = 0
        else:
            self.ok = 0
        return self.level


def indicators(p, cfg):
    C, H, L = p['close'], p['high'], p['low']
    prev = C.shift(1)
    tr = np.maximum(np.maximum((H - L).to_numpy(), (H - prev).abs().to_numpy()), (L - prev).abs().to_numpy())
    tr = pd.DataFrame(tr, index=C.index, columns=C.columns)
    atr = tr.ewm(alpha=1 / cfg.atr_n, adjust=False, min_periods=cfg.atr_n).mean()
    ema = C.ewm(span=cfg.ema_n, adjust=False, min_periods=cfg.ema_n).mean()
    mom = C / C.shift(cfg.mom_n) - 1
    return mom, ema, atr


def fee_of(q, px, cfg):
    f = max(cfg.fee_min, cfg.fee_per_share * q)
    return min(f, max(cfg.fee_min, cfg.fee_pct_max * q * px)) if cfg.fee_per_share > 0 else cfg.fee_min


def run(prices, cfg=None, member=None):
    """prices: dict de DataFrames fecha x ticker con open, high, low, close (y volume opcional).
    member: DataFrame booleano fecha x ticker con el universo vigente cada día (pertenencia histórica)."""
    cfg = cfg or Cfg()
    C, O = prices['close'].to_numpy(float), prices['open'].to_numpy(float)
    V = prices['volume'].to_numpy(float) if 'volume' in prices else None
    dates, cols = prices['close'].index, prices['close'].columns
    T, N = C.shape
    mom, ema, atr = indicators(prices, cfg)
    ext = (prices['close'] > ema + cfg.atr_mult * atr).to_numpy()
    elig = mom.notna() & prices['close'].notna()
    if member is not None:
        elig &= member.reindex(index=dates, columns=cols).fillna(False).astype(bool)
    rank = mom.where(elig).rank(axis=1, ascending=False, method='first').to_numpy()
    ret = prices['close'].pct_change().to_numpy()
    adv = (prices['volume'].rolling(20).mean().to_numpy() if V is not None else None)
    rng = np.random.default_rng(cfg.seed)

    cash, shares = cfg.capital, np.zeros(N)
    lastpx = np.where(np.isnan(C[0]), 0.0, C[0])
    held = np.zeros(N, bool)
    cool = np.full(N, -10**9)
    prot = Protection(cfg)
    peak, prev_exp = cfg.capital, 1.0
    eq = np.full(T, np.nan)
    expo = np.full(T, np.nan)
    trades = []
    i0 = max(cfg.mom_n, cfg.ema_n, cfg.atr_n, cfg.vol_n) + 2
    for i in range(T):
        px_c = np.where(np.isnan(C[i]), lastpx, C[i])
        lastpx = px_c
        eq[i] = cash + float((shares * px_c).sum())
        if i < i0 or i >= T - 1:
            expo[i] = np.nan
            continue
        peak = max(peak, eq[i])
        dd = 1 - eq[i] / peak
        # ---- A. selección con datos hasta el cierre i
        if i % cfg.rank_every == 0 or not held.any():
            rk = rank[i]
            keep = held & ~ext[i] & (rk <= cfg.top_out) & ~np.isnan(rk)
            for j in np.where(held & ~keep & ext[i])[0]:
                cool[j] = i
            cand = np.where((rk <= cfg.top_in) & ~held & ~ext[i] & (i > cool + cfg.cooldown))[0]
            cand = cand[np.argsort(rk[cand])]
            sel = list(np.where(keep)[0][np.argsort(rk[keep])])
            for j in cand:
                if len(sel) >= cfg.max_pos:
                    break
                sel.append(j)
        else:
            sel = [j for j in np.where(held)[0] if not ext[i][j]]
            for j in np.where(held & ext[i])[0]:
                cool[j] = i
        # ---- B. riesgo
        basket = np.nanmean(ret[i - cfg.vol_n + 1:i + 1][:, sel], axis=1) if sel else None
        vol = float(np.nanstd(basket, ddof=1) * np.sqrt(252)) if basket is not None and len(basket) > 2 else 0.0
        scale = min(1.0, cfg.vol_target / vol) if vol > 1e-9 else 1.0
        cap = prot.update(dd)
        if cfg.ma100_guard and i >= cfg.ma_n and eq[i] < np.nanmean(eq[i - cfg.ma_n + 1:i + 1]):
            cap = min(cap, cfg.ma_cap)
        exposure = min(scale, cap, 1.0)
        expo[i] = exposure
        risk_cut = exposure < prev_exp - 1e-9
        prev_exp = exposure
        n_slots = cfg.max_pos
        if cfg.min_order > 0:
            n_slots = max(1, min(cfg.max_pos, int(exposure * eq[i] // cfg.min_order)))
        targets = sel[:n_slots]
        per = exposure * eq[i] / n_slots
        # ---- C. ejecución en la apertura de i+1
        o = O[i + 1]
        tv = np.zeros(N)
        tv[targets] = per
        # posiciones sin precio mañana (deslistadas): liquidar al último cierre
        gone = held & np.isnan(o)
        for j in np.where(gone)[0]:
            cash += shares[j] * lastpx[j]
            trades.append((dates[i + 1], cols[j], 'DELIST', shares[j], lastpx[j], 0.0))
            shares[j], held[j] = 0.0, False
        orders = []
        for j in range(N):
            if np.isnan(o[j]):
                continue
            v = shares[j] * o[j]
            d = tv[j] - v
            if tv[j] == 0 and shares[j] > 0:
                orders.append((j, -shares[j], 'SELL_EXIT'))
            elif d < 0 and risk_cut:
                q = shares[j] * min(1.0, -d / v)
                orders.append((j, -(q if cfg.fractional else np.floor(q)), 'SELL_RISK'))
            elif tv[j] > 0 and shares[j] == 0:
                if tv[j] >= cfg.min_order:
                    orders.append((j, tv[j] / o[j], 'BUY_NEW'))
            elif tv[j] > 0 and abs(d) > cfg.band * tv[j] and abs(d) >= cfg.min_order:
                orders.append((j, d / o[j], 'BUY_ADD' if d > 0 else 'SELL_TRIM'))
        sells = [x for x in orders if x[1] < 0]
        buys = sorted([x for x in orders if x[1] > 0], key=lambda x: -x[1] * o[x[0]] / max(tv[x[0]], 1e-9))
        for j, q, kind in sells + buys:
            q = abs(q) if q < 0 else q
            if kind.startswith('SELL'):
                q = min(q, shares[j])
            if cfg.adv_frac and adv is not None and not np.isnan(adv[i, j]) and not kind.startswith('SELL_EXIT'):
                q = min(q, cfg.adv_frac * adv[i, j])
            q = q if cfg.fractional else float(np.floor(q))
            if q <= 0 or rng.random() < cfg.reject_prob:
                continue
            if kind.startswith('SELL'):
                px = o[j] * (1 - cfg.slip_bps / 1e4)
                f = fee_of(q, px, cfg)
                cash += q * px - f
                shares[j] -= q
                trades.append((dates[i + 1], cols[j], kind, q, px, f))
            else:
                px = o[j] * (1 + cfg.slip_bps / 1e4)
                q = _afford(q, px, cash, cfg)
                if q <= 0 or q * px < min(cfg.min_order, tv[j]) - 1e-9:
                    continue
                f = fee_of(q, px, cfg)
                cash -= q * px + f
                shares[j] += q
                trades.append((dates[i + 1], cols[j], kind, q, px, f))
            held[j] = shares[j] > 1e-12
    eqs = pd.Series(eq, index=dates)
    tr = pd.DataFrame(trades, columns=['date', 'ticker', 'kind', 'qty', 'price', 'fee'])
    return {'equity': eqs, 'exposure': pd.Series(expo, index=dates), 'trades': tr, 'cash_end': cash, 'cfg': cfg}


def _afford(q, px, cash, cfg):
    """Cantidad máxima <= q que cabe en el efectivo incluida la comisión (nunca efectivo negativo)."""
    while q > 0 and q * px + fee_of(q, px, cfg) > cash + 1e-9:
        q = q * 0.999 if cfg.fractional else q - 1
        if cfg.fractional and q * px < 1e-6:
            return 0.0
    return q


def metrics(res, start=None, end=None):
    """Métricas de todo el periodo o de un tramo [start, end] (para entrenamiento / validación / prueba)."""
    sl = slice(start, end)
    res = {**res, 'equity': res['equity'].loc[sl], 'exposure': res['exposure'].loc[sl],
           'trades': res['trades'][(res['trades'].date >= pd.Timestamp(start or '1900-01-01')) & (res['trades'].date <= pd.Timestamp(end or '2100-01-01'))]}
    e = res['equity'].dropna()
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 and e.iloc[-1] > 0 else -1.0
    dd = (e / e.cummax() - 1).min()
    ann = e.groupby(e.index.year).last()
    yret = ann.pct_change().dropna()
    tr = res['trades']
    return {'cagr_pct': round(cagr * 100, 2), 'max_dd_pct': round(dd * 100, 2),
            'sharpe': round(float(r.mean() / r.std() * np.sqrt(252)), 3) if r.std() > 0 else 0.0,
            'calmar': round(cagr / abs(dd), 2) if dd < 0 else np.nan,
            'vol_pct': round(float(r.std() * np.sqrt(252) * 100), 2),
            'orders': int(len(tr)), 'orders_per_day': round(len(tr) / max(len(e), 1), 3),
            'fees_usd': round(float(tr['fee'].sum()), 2), 'neg_years': int((yret < 0).sum()),
            'avg_exposure_pct': round(float(res['exposure'].mean() * 100), 1),
            'days_flat': int(((res['exposure'] > 0.05) & (res['equity'].diff() == 0)).sum())}


def fee_sensitivity(prices, base=None, fees=(0.35, 0.50, 1.00), min_order=100.0, member=None):
    base = base or Cfg()
    rows = []
    for f in fees:
        c = replace(base, fee_min=f, min_order=min_order)
        rows.append({'fee_min': f, 'min_order': min_order, **metrics(run(prices, c, member))})
    return pd.DataFrame(rows)


def synthetic_universe(n=60, T=1500, seed=7, start='2015-01-02'):
    """Universo sintético reproducible SOLO para probar el motor. No son datos reales."""
    r = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=T)
    mu = r.normal(0.0004, 0.0004, n)
    sg = r.uniform(0.012, 0.03, n)
    mkt = r.normal(0.0003, 0.008, T)
    rets = mu + 0.6 * mkt[:, None] + r.normal(0, 1, (T, n)) * sg
    close = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=[f'S{k:03d}' for k in range(n)])
    gap = r.normal(0, 0.004, (T, n))
    op = close.shift(1).fillna(close.iloc[0]) * (1 + gap)
    hi = np.maximum(close, op) * (1 + np.abs(r.normal(0, 0.006, (T, n))))
    lo = np.minimum(close, op) * (1 - np.abs(r.normal(0, 0.006, (T, n))))
    vol = pd.DataFrame(r.uniform(5e5, 5e6, (T, n)), index=idx, columns=close.columns)
    return {'open': op, 'high': hi, 'low': lo, 'close': close, 'volume': vol}


def main():
    ap = argparse.ArgumentParser(description='Motor V24 corregido. --demo usa datos SINTÉTICOS (solo prueba el motor).')
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args()
    if not a.demo:
        raise SystemExit('Pasa precios reales desde tu cargador (ver run()). Usa --demo para ver el motor con datos sintéticos.')
    p = synthetic_universe()
    print('DATOS SINTÉTICOS: estos números no son resultados de la estrategia.')
    print(fee_sensitivity(p).to_string(index=False))


if __name__ == '__main__':
    main()
