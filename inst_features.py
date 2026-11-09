"""Karryman · huellas institucionales en precio y volumen, y estadio de la empresa.

Variables diarias, todas calculadas SOLO con datos hasta cada fecha:
- Acumulación / distribución: días de acumulación y distribución (cierre +-0,2% con volumen mayor que el día
  anterior, definición de O'Neil), flujo de dinero de Chaikin, línea A/D y OBV normalizados, días de compra
  o venta masiva (volumen >= 2x la media con cierre en la parte alta/baja del rango), pocket pivots y gaps
  alcistas con volumen.
- Mercado: días de distribución del índice en 25 sesiones (regla de >= 5).
- Estadio: edad desde la primera cotización, etapa de Weinstein sobre la media de 150 sesiones (30 semanas),
  caída desde el máximo de 3 años y rentabilidad previa de 2 años.
"""
import numpy as np
import pandas as pd

INST_COLS = ['dist_days_25', 'acc_days_25', 'acc_net_50', 'cmf_20', 'cmf_63', 'ad_63', 'ad_126', 'obv_63', 'big_up_50',
             'big_dn_50', 'big_net_50', 'pocket_20', 'gapup_60', 'accum_divergence']
STAGE_COLS = ['age_years', 'ma150_slope', 'stage', 'dd_3y', 'ret_504']
STAGE_NAMES = {1: 'Etapa 1: base (precio < MA150 plana)', 2: 'Etapa 2: avance (precio > MA150 que sube)',
               3: 'Etapa 3: techo/lateral (precio > MA150 plana o a la baja)', 4: 'Etapa 4: declive (precio < MA150 a la baja)',
               5: 'Corrección en etapa 2 (precio < MA150 que sube)'}


def institutional_features(f):
    c, h, lo, o, v = f.Close, f.High, f.Low, f.Open, f.Volume.astype(float)
    prev, vprev = c.shift(1), v.shift(1)
    chg = c / prev - 1
    dist_day = ((chg <= -0.002) & (v > vprev)).astype(float)
    acc_day = ((chg >= 0.002) & (v > vprev)).astype(float)
    rng = (h - lo).replace(0, np.nan)
    clv = ((c - lo) - (h - c)) / rng
    mfv = (clv * v).fillna(0)
    adl = mfv.cumsum()
    obv = (np.sign(chg.fillna(0)) * v).cumsum()
    vol50 = v.shift(1).rolling(50).mean()
    big_up = ((chg > 0) & (v >= 2 * vol50) & (clv > 0)).astype(float)
    big_dn = ((chg < 0) & (v >= 2 * vol50) & (clv < 0)).astype(float)
    maxdown = v.where(chg < 0, 0).shift(1).rolling(10).max()
    pocket = ((chg > 0) & (v > maxdown) & (maxdown > 0) & (c > c.rolling(10).mean())).astype(float)
    gap = o / prev - 1
    d = pd.DataFrame(index=f.index)
    d['dist_days_25'], d['acc_days_25'] = dist_day.rolling(25).sum(), acc_day.rolling(25).sum()
    d['acc_net_50'] = acc_day.rolling(50).sum() - dist_day.rolling(50).sum()
    d['cmf_20'] = mfv.rolling(20).sum() / v.rolling(20).sum()
    d['cmf_63'] = mfv.rolling(63).sum() / v.rolling(63).sum()
    d['ad_63'] = (adl - adl.shift(63)) / v.rolling(63).sum()
    d['ad_126'] = (adl - adl.shift(126)) / v.rolling(126).sum()
    d['obv_63'] = (obv - obv.shift(63)) / v.rolling(63).sum()
    d['big_up_50'], d['big_dn_50'] = big_up.rolling(50).sum(), big_dn.rolling(50).sum()
    d['big_net_50'] = d['big_up_50'] - d['big_dn_50']
    d['pocket_20'] = pocket.rolling(20).sum()
    d['gapup_60'] = ((gap >= 0.04) & (v >= 2 * vol50) & (c >= o)).astype(float).rolling(60).sum()
    ret63 = c / c.shift(63) - 1
    d['accum_divergence'] = ((d['ad_63'] >= 0.10) & (ret63 <= 0.05)).astype(float).where(d['ad_63'].notna())
    return d.replace([np.inf, -np.inf], np.nan)


def market_distribution(spy):
    """Días de distribución/acumulación del índice en 25 sesiones (cierre -0,2%/+0,2% con más volumen)."""
    c, v = spy.Close, spy.Volume.astype(float)
    chg = c / c.shift(1) - 1
    dist = ((chg <= -0.002) & (v > v.shift(1))).astype(float).rolling(25).sum()
    acc = ((chg >= 0.002) & (v > v.shift(1))).astype(float).rolling(25).sum()
    return pd.DataFrame({'spy_dist_25': dist, 'spy_acc_25': acc, 'spy_dist_ge5': (dist >= 5).astype(float).where(dist.notna())})


def stage_features(f, first_date):
    c = f.Close
    ma150 = c.rolling(150).mean()
    slope = ma150 / ma150.shift(20) - 1
    above = c > ma150
    stage = pd.Series(np.nan, index=f.index)
    flat = slope.abs() < 0.02
    stage[above & (slope >= 0.02)] = 2
    stage[~above & (slope >= 0.02)] = 5
    stage[above & (slope < 0.02)] = 3
    stage[~above & flat] = 1
    stage[~above & (slope <= -0.02)] = 4
    stage[ma150.isna() | slope.isna()] = np.nan
    d = pd.DataFrame(index=f.index)
    d['age_years'] = (f.index - pd.Timestamp(first_date)).days / 365.25 if first_date is not None else np.nan
    d['ma150_slope'], d['stage'] = slope, stage
    d['dd_3y'] = c / c.rolling(756, min_periods=250).max() - 1
    d['ret_504'] = c / c.shift(504) - 1
    return d


def first_trade_dates(tickers, batch=50):
    """Primera cotización de cada acción (barras mensuales del histórico completo)."""
    import time
    import yfinance as yf
    out = {}
    for k in range(0, len(tickers), batch):
        part = tickers[k:k + batch]
        try:
            data = yf.download(part, period='max', interval='1mo', auto_adjust=False, progress=False, threads=True, group_by='ticker', timeout=60)
        except Exception:
            continue
        for t in part:
            try:
                s = (data[t] if isinstance(data.columns, pd.MultiIndex) else data)['Close'].dropna()
                if len(s):
                    out[t] = s.index[0]
            except Exception:
                pass
        time.sleep(1)
    return out
