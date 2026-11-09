import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_engine as ve
import v24_h5 as h5
import v24_kell as kell


def build(seed=9, n=80, T=1600):
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


CFGT = replace(kell.CFG, rs_rank_min=0.0)      # sin rango RS en la prueba sintética (no hay rango calculado)


class Kell(unittest.TestCase):
    def test_cada_senal_cumple_las_definiciones_del_registro(self):
        p, prep, reg = build()
        checked = {'wedge_pop': 0, 'crossback': 0}
        for tk, d in prep.items():
            sigs = sb.signals(d, CFGT, reg)
            c, o, h, lo, v = (d[x].to_numpy() for x in ('Close', 'Open', 'High', 'Low', 'Volume'))
            e10, e20 = d.ema10.to_numpy(), d.ema20.to_numpy()
            for (i, kind, pivot, stop, rs) in sigs:
                self.assertGreaterEqual(i, 60)
                self.assertAlmostEqual(pivot, c[i])
                # filtro común
                self.assertTrue(c[i] >= 5 and d.vol50.iloc[i] >= 500_000 and c[i] > d.ma50.iloc[i] > d.ma200.iloc[i] and d.ma200.iloc[i] > d.ma200_prev.iloc[i])
                if kind == 'wedge_pop':
                    self.assertLessEqual((h[i - 5:i].max() - lo[i - 5:i].min()) / c[i - 1], 0.10 + 1e-12)
                    self.assertLessEqual(abs(e10[i - 1] / e20[i - 1] - 1), 0.02 + 1e-12)
                    self.assertTrue(c[i - 1] <= max(e10[i - 1], e20[i - 1]) and c[i] > e10[i] and c[i] > e20[i])
                    self.assertGreaterEqual(v[i], 1.2 * v[i - 50:i].mean() - 1e-6)
                    self.assertTrue(c[i] > o[i] and c[i] >= lo[i] + 0.5 * (h[i] - lo[i]) - 1e-12)
                    self.assertAlmostEqual(stop, lo[i])
                else:
                    self.assertGreater(e20[i], e20[i - 5])
                    self.assertGreaterEqual(h[i - 14:i + 1].max(), 0.98 * h[i - 50:i].max() - 1e-9)
                    self.assertLessEqual(lo[i - 2:i + 1].min(), 1.01 * e20[i] + 1e-9)
                    self.assertTrue(c[i - 1] <= e10[i - 1] and c[i] > e10[i] and c[i] > o[i] and c[i] > h[i - 1])
                    self.assertAlmostEqual(stop, lo[i - 2:i + 1].min())
                checked[kind] += 1
        self.assertGreater(sum(checked.values()), 20, checked)

    def test_senales_sin_futuro(self):
        p, prep, reg = build(T=1300)
        t = 900
        a = {(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, CFGT, reg) if s[0] <= t}
        p2 = {k: v.copy() for k, v in p.items()}
        for k in ('open', 'high', 'low', 'close'):
            p2[k].iloc[t + 2:] *= 1.8
        mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
        fr = h5.frames_from_wide(p2, mem, list(p2['close'].columns))
        bench = p['close'].mean(axis=1)
        reg2 = sb.regime_series(pd.DataFrame({'Close': bench}))
        b = set()
        for tk, (f, m) in fr.items():
            d = sb.prepare(f, bench)
            d['member'] = m.reindex(d.index).fillna(False).astype(bool)
            b |= {(tk, s[0]) for s in sb.signals(d, CFGT, reg2) if s[0] <= t}
        self.assertEqual(a, b)

    def test_operaciones_y_stop_maximo_10_por_ciento(self):
        p, prep, reg = build()
        tr = sb.simulate_independent(prep, CFGT, reg)
        self.assertGreater(len(tr), 10)
        self.assertLessEqual(tr.risk_pct.max(), 10.2)


if __name__ == '__main__':
    unittest.main()
