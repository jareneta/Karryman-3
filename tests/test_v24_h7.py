import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_engine as ve
import v24_h5 as h5
import v24_h7 as h7


def build(seed=4, n=30, T=1500):
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
    return p, mem, prep, reg


class H7(unittest.TestCase):
    def test_trend_template_solo_restringe(self):
        p, mem, prep, reg = build()
        base = replace(h7.CFG, template=False, rs_rank_min=0.0)
        tmpl = replace(h7.CFG, template=True, rs_rank_min=0.0)
        a = {(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, base, reg)}
        b = {(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, tmpl, reg)}
        self.assertTrue(b <= a)

    def test_columnas_del_template_con_referencia(self):
        p, mem, prep, reg = build()
        t = list(prep)[0]
        d = prep[t]
        c, lo = d.Close, d.Low
        np.testing.assert_allclose(d.ma150.dropna().to_numpy(), c.rolling(150).mean().dropna().to_numpy())
        np.testing.assert_allclose(d.lo252.dropna().to_numpy(), lo.rolling(252).min().dropna().to_numpy())

    def test_stop_no_supera_el_8_por_ciento(self):
        p, mem, prep, reg = build()
        cfg = replace(h7.CFG, rs_rank_min=0.0, template=False, min_prior_advance=0.0, max_tight=1.0, max_base_depth=1.0)
        tr = sb.simulate_independent(prep, cfg, reg)
        self.assertGreater(len(tr), 5)
        self.assertLessEqual(tr.risk_pct.max(), 8.1)               # 8 % + costes de entrada

    def test_rs_rank_solo_entre_miembros(self):
        p, mem, prep, reg = build(n=20, T=700)
        mem2 = mem.copy()
        mem2.iloc[:, :10] = False
        h7.rs_rank_members(prep, mem2, p['close'].index)
        d0 = prep[p['close'].columns[0]]
        self.assertTrue(d0.rs_rank.isna().all())                   # no miembros: sin rango
        d15 = prep[p['close'].columns[15]]
        v = d15.rs_rank.dropna()
        self.assertTrue((v > 0).all() and (v <= 100).all())


if __name__ == '__main__':
    unittest.main()
