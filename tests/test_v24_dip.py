import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_dip as dip
import v24_engine as ve
import v24_h5 as h5


def build(seed=13, n=60, T=1500):
    p = ve.synthetic_universe(n=n, T=T, seed=seed)
    mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
    fr = h5.frames_from_wide(p, mem, list(p['close'].columns))
    bench = p['close'].mean(axis=1)
    reg = sb.regime_series(pd.DataFrame({'Close': bench}))
    prep = {}
    for t, (f, m) in fr.items():
        d = sb.prepare(f, bench)
        d['member'] = m.reindex(d.index).fillna(False).astype(bool)
        prep[t] = d
    return p, prep, reg


class Dip(unittest.TestCase):
    def test_senal_contra_referencia_con_bucles(self):
        p, prep, reg = build()
        total = 0
        for tk, d in prep.items():
            c = d.Close.to_numpy()
            got = {s[0] for s in sb.signals(d, dip.CFG, reg)}
            ref = set()
            for i in range(62, len(c)):
                hi = c[i - 60:i].max()
                dd = c[i] / hi - 1
                hi_prev = c[i - 61:i - 1].max()
                dd_prev = c[i - 1] / hi_prev - 1
                liq = c[i] >= 5 and d.vol50.iloc[i] >= 500_000
                ma200 = d.ma200.iloc[i]
                if liq and np.isfinite(ma200) and c[i] > ma200 and -0.35 <= dd <= -0.15 and dd_prev > -0.15:
                    ref.add(i)
            self.assertEqual(got, ref, tk)
            total += len(got)
        self.assertGreater(total, 5)

    def test_sin_futuro(self):
        p, prep, reg = build(T=1100)
        t = 800
        a = {(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, dip.CFG, reg) if s[0] <= t}
        p2 = {k: v.copy() for k, v in p.items()}
        for k in ('open', 'high', 'low', 'close'):
            p2[k].iloc[t + 2:] *= 0.5
        mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
        fr = h5.frames_from_wide(p2, mem, list(p2['close'].columns))
        bench = p['close'].mean(axis=1)
        reg2 = sb.regime_series(pd.DataFrame({'Close': bench}))
        b = set()
        for tk, (f, m) in fr.items():
            d = sb.prepare(f, bench)
            d['member'] = m.reindex(d.index).fillna(False).astype(bool)
            b |= {(tk, s[0]) for s in sb.signals(d, dip.CFG, reg2) if s[0] <= t}
        self.assertEqual(a, b)

    def test_stop_12_y_salidas(self):
        p, prep, reg = build()
        tr = sb.simulate_independent(prep, dip.CFG, reg)
        self.assertGreater(len(tr), 10)
        self.assertLessEqual(tr.risk_pct.max(), 12.2)                  # stop fijo del 12 % (+ costes)
        self.assertGreaterEqual(tr.risk_pct.min(), 11.0)
        self.assertLessEqual(tr.days.max(), 21)                        # máximo 20 sesiones (+ ejecución de la salida)

    def test_salida_por_sma20_y_tiempo(self):
        # serie sintética: caída fuerte y rebote que cruza la SMA20 → la salida ocurre pronto
        T = 400
        idx = pd.bdate_range('2015-01-02', periods=T)
        c = np.concatenate([np.linspace(50, 100, 300), np.linspace(100, 80, 10), np.linspace(80, 95, 90)])
        f = pd.DataFrame({'Open': c, 'High': c * 1.005, 'Low': c * 0.995, 'Close': c, 'Volume': 2e6}, index=idx)
        bench = pd.Series(np.linspace(100, 150, T), index=idx)
        d = sb.prepare(f, bench)
        d['member'] = True
        reg = sb.regime_series(pd.DataFrame({'Close': bench}))
        tr = sb.simulate_independent({'X': d}, dip.CFG, reg)
        self.assertEqual(len(tr), 1)
        self.assertLessEqual(tr.days.iloc[0], 20)
        sin_sma = sb.simulate_independent({'X': d}, replace(dip.CFG, exit_above_sma20=False, max_hold=20), reg)
        self.assertGreaterEqual(sin_sma.days.iloc[0], tr.days.iloc[0])


if __name__ == '__main__':
    unittest.main()
