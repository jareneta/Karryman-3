import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_engine as ve
import v24_h5 as h5


def build(seed=5, n=25, T=1400, nonmember_first_half=5):
    p = ve.synthetic_universe(n=n, T=T, seed=seed)
    mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
    mem.iloc[:T // 2, :nonmember_first_half] = False
    fr = h5.frames_from_wide(p, mem, list(p['close'].columns))
    bench = p['close'].mean(axis=1)
    reg = sb.regime_series(pd.DataFrame({'Close': bench}))
    prep = {}
    for t, (f, m) in fr.items():
        d = sb.prepare(f, bench)
        d['member'] = m.reindex(d.index).fillna(False).astype(bool)
        prep[t] = d
    return p, prep, reg, T


class H5(unittest.TestCase):
    def test_solo_cuentan_los_dias_de_pertenencia(self):
        p, prep, reg, T = build()
        cfg = replace(sb.FINAL, name='t')
        tr = sb.simulate_independent(prep, cfg, reg)
        self.assertGreater(len(tr), 20)
        first = list(p['close'].columns[:5])
        early = tr[tr.ticker.isin(first) & (tr.entry_date <= p['close'].index[T // 2])]
        self.assertEqual(len(early), 0)

    def test_placebo_respeta_la_pertenencia(self):
        p, prep, reg, T = build()
        cfg = replace(sb.FINAL, name='t', placebo=True)
        tr = sb.simulate_independent(prep, cfg, reg, seed=3)
        first = list(p['close'].columns[:5])
        self.assertEqual(len(tr[tr.ticker.isin(first) & (tr.entry_date <= p['close'].index[T // 2])]), 0)

    def test_sin_futuro_en_las_senales(self):
        p, prep, reg, T = build(T=1100)
        cfg = replace(sb.FINAL, name='t')
        t = 800
        a = [(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, cfg, reg) if s[0] <= t]
        p2 = {k: v.copy() for k, v in p.items()}
        for k in ('open', 'high', 'low', 'close'):
            p2[k].iloc[t + 2:] *= 2.0
        mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
        mem.iloc[:T // 2, :5] = False
        fr = h5.frames_from_wide(p2, mem, list(p2['close'].columns))
        bench = p2['close'].mean(axis=1)
        bench.iloc[:t + 2] = p['close'].mean(axis=1).iloc[:t + 2]
        reg2 = sb.regime_series(pd.DataFrame({'Close': bench}))
        b = []
        for tk, (f, m) in fr.items():
            d = sb.prepare(f, bench)
            d['member'] = m.reindex(d.index).fillna(False).astype(bool)
            b += [(tk, s[0]) for s in sb.signals(d, cfg, reg2) if s[0] <= t]
        self.assertEqual(sorted(a), sorted(b))

    def test_estadisticos(self):
        r = h5.rstats([1.0, -1.0, 2.0, -0.5] * 100)
        self.assertEqual(r['trades'], 400)
        self.assertAlmostEqual(r['expectancy_R'], 0.375, places=6)
        lo, hi, mean = h5.diff_ci(np.full(200, 1.0) + np.random.default_rng(0).normal(0, .1, 200), np.zeros(200) + np.random.default_rng(1).normal(0, .1, 200))
        self.assertGreater(lo, 0)


if __name__ == '__main__':
    unittest.main()
