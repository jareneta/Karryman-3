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
    trail: str = 'ema20'          # ema10 | ema20 | ma50 | none
    trail_from_start: bool = False
    intraday_stop: bool = False
    time_stop: int = 0            # sesiones sin llegar a +1R -> salir (0 = no)
    regime: str = 'none'          # none | spy_ma200 | spy_ma50
    rs_min: float = 0.0
    near_high: float = 0.85
    placebo: bool = False


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
    d.attrs['a'] = {k: d[k].to_numpy(dtype=float) for k in ('Open', 'High', 'Low', 'Close', 'ema10', 'ema20', 'ma50')}
    return d


def regime_series(spy):
    c = spy.Close
    return pd.DataFrame({'spy_ma200': c > c.rolling(200).mean(), 'spy_ma50': c > c.rolling(50).mean()})


def signals(d, cfg, regime, rng=None):
    """Señales al cierre del día i; la compra se intenta en la apertura de i+1."""
    c, v = d.Close, d.Volume
    base = ((c >= 5) & (d.vol50 >= 500_000) & (c > d.ma50) & (d.ma50 > d.ma200) & (d.ma200 > d.ma200_prev)
            & (c >= cfg.near_high * d.hi252) & (d.rs > cfg.rs_min))
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
    if c <= t.stop:
        t.pending = True
    elif trail_on and c < a[cfg.trail][j]:
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
                         'partial': t.partial})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- cartera
def simulate_portfolio(prepared, cfg, regime, start, end, seed=7, risk_pct=0.01, total_risk=0.06, max_weight=0.20):
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
    for dt in dates:
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
            open_risk += q2 * t2.rem * max(0.0, last - t2.stop)
        for tk, sig in cands:
            if tk in pos:
                continue
            d = prepared[tk]
            t = open_trade(d, tk, sig, cfg)
            if not t or d.index[t.entry_i] != dt:
                continue
            per = t.entry - t.stop0
            budget = min(equity_open * risk_pct, max(0.0, equity_open * total_risk - open_risk))
            q = min(budget / per, equity_open * max_weight / t.entry, max(0.0, cash) / t.entry)
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
        equity_curve.append((dt, cash + mark('Close')))
    eq = pd.Series([v for _, v in equity_curve], index=[x for x, _ in equity_curve])
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


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=700)
    ap.add_argument('--start', default='2013-06-01')
    ap.add_argument('--split', default='2021-01-01')
    ap.add_argument('--output', default='data/system_backtest.json')
    ap.add_argument('--seed', type=int, default=42)
    a = ap.parse_args()
    t0 = time.time()
    names = universe()
    random.Random(a.seed).shuffle(names)
    sample = names[:a.symbols]
    frames = download(['SPY'] + sample, a.start)
    spy = frames.pop('SPY')
    regime = regime_series(spy)
    prepared = {tk: prepare(f, spy.Close) for tk, f in frames.items()}
    split = pd.Timestamp(a.split)
    eval_start = pd.Timestamp(a.start) + pd.Timedelta(days=400)
    end = spy.index[-1]
    print(f'Universo: {len(names)} · muestra {len(sample)} · con datos {len(prepared)} · {time.time()-t0:.0f}s')
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
