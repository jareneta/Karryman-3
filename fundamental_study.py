"""Karryman · opción 4: ¿mejoran los fundamentales y los grupos líderes la detección temprana?

Combina las señales tempranas (early_signals.py) con:
- aceleración de beneficios (BPA) e ingresos trimestrales (SEC EDGAR, con fecha de presentación);
- liderazgo del grupo de industria (SIC de 2 dígitos: mediana de rentabilidad a 6 meses entre las
  mejores 20% de los grupos).
Mide, por señal y por filtro, precisión (x2 en 12 meses), lift frente a la población con ese filtro,
R de operar la señal frente a un control al azar con el mismo filtro, y qué porcentaje de las
ganadoras (tramos x2) cumplía cada filtro AL EMPEZAR la subida frente a la prevalencia general.
Investigación únicamente. Sesgo de supervivencia: solo acciones que cotizan hoy.
"""
import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import early_signals as es
import sec_fundamentals as sec
import system_backtest as sb

GROUP_FLAGS = ('Grupo líder', 'Grupo líder + EPS acelera', 'Grupo líder + doble aceleración')


def group_names(fund):
    """SIC de 2 dígitos -> nombre (la descripción más frecuente) y ticker -> grupo."""
    by = {}
    for t, d in fund.items():
        sic = (d.get('sic') or '')[:2]
        if sic:
            by.setdefault(sic, []).append((t, d.get('sic_desc') or sic))
    names = {sic: pd.Series([x[1] for x in v]).mode().iloc[0] for sic, v in by.items()}
    tk = {t: f'{sic} {names[sic]}' for sic, v in by.items() for t, _ in v}
    return tk


def leader_matrix(frames, tk_group, index, min_members=10, top=0.2):
    """DataFrame (días x grupo) con True si el grupo está en el 20% mejor por rentabilidad a 6 meses."""
    ret = pd.DataFrame({t: f.Close / f.Close.shift(126) - 1 for t, f in frames.items() if t in tk_group}).reindex(index)
    groups = pd.Series(tk_group)
    sizes = groups.value_counts()
    keep = [g for g, n in sizes.items() if n >= min_members]
    med = pd.DataFrame({g: ret[[t for t in groups.index[groups == g] if t in ret.columns]].median(axis=1) for g in keep})
    rank = med.rank(axis=1, pct=True)
    return (rank >= 1 - top) & (med.notna().sum(axis=1).to_numpy()[:, None] >= 5), sizes


def build_inputs(frames, fund, spy_close):
    tk_group = group_names(fund)
    leaders, sizes = leader_matrix(frames, tk_group, spy_close.index)
    flags_by, covered_by, group_by = {}, {}, {}
    for t, f in frames.items():
        rows = (fund.get(t) or {}).get('rows') or []
        if not rows:
            continue
        fl, covered = sec.daily_flags(rows, f.index)
        g = tk_group.get(t)
        if g in leaders.columns:
            lead = leaders[g].reindex(f.index).ffill().fillna(False).to_numpy(bool)
        else:
            lead = np.zeros(len(f), dtype=bool)
        fl['Grupo líder'] = lead
        fl['Grupo líder + EPS acelera'] = lead & fl['EPS +25% y acelera']
        fl['Grupo líder + doble aceleración'] = lead & fl['Doble aceleración (EPS e ingresos)']
        flags_by[t], covered_by[t], group_by[t] = fl, covered, g
    return flags_by, covered_by, group_by, sizes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbols', type=int, default=2500)
    ap.add_argument('--start', default='2012-06-01')
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--output', default='data/fundamental_study.json')
    a = ap.parse_args()
    t0 = time.time()
    names = sb.universe()
    random.Random(a.seed).shuffle(names)
    lim = sec.RateLimiter(8)
    cmap = sec.cik_map(lim)
    cand = [t for t in names if t in cmap][:a.symbols]
    print(f'Universo {len(names)} · con CIK {sum(t in cmap for t in names)} · muestra {len(cand)}', flush=True)
    frames = sb.download(['SPY'] + cand, a.start)
    spy = frames.pop('SPY')
    up = sb.regime_series(spy)['spy_ma50_up']
    print(f'Precios de {len(frames)} acciones en {time.time()-t0:.0f}s', flush=True)
    fund, _ = sec.fetch_many(list(frames))
    with_rows = sum(1 for d in fund.values() if d['rows'])
    print(f'Fundamentales SEC: {with_rows}/{len(frames)} acciones con trimestres · {time.time()-t0:.0f}s', flush=True)
    flags_by, covered_by, group_by, sizes = build_inputs(frames, fund, spy.Close)
    res = es.run_all(frames, spy.Close, up, flags_by, covered_by, group_by)
    res['group_sizes'] = {g: int(n) for g, n in sizes.head(40).items()}
    res['coverage'] = {'stocks_with_prices': len(frames), 'stocks_with_fundamentals': len(flags_by)}
    res['seconds'] = round(time.time() - t0)
    res['generated_utc'] = datetime.now(timezone.utc).isoformat()
    print('RESUMEN_FUNDAMENTALES ' + json.dumps(res, ensure_ascii=False, default=str))
    Path(a.output).parent.mkdir(exist_ok=True)
    Path(a.output).write_text(json.dumps(res, ensure_ascii=False, default=str, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
