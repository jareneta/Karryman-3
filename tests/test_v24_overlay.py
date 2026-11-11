import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_dip as dip
import v24_overlay as ov
from tests.test_v24_dip import build


class Overlay(unittest.TestCase):
    def setUp(self):
        self.p, self.prep, self.reg = build(n=40, T=1300)
        idx = self.p['close'].index
        self.bench = pd.Series(100 * np.cumprod(1 + np.random.default_rng(2).normal(0.0004, 0.01, len(idx))), index=idx)
        self.start, self.end = idx[300], idx[-1]

    def test_sin_senales_la_cartera_es_exactamente_spy(self):
        cfg = replace(dip.CFG, dip_lo=0.90, dip_hi=0.95)               # umbral imposible: no hay operaciones
        eq, n = ov.sim(self.prep, self.reg, self.bench, cfg, self.start, self.end)
        self.assertEqual(n, 0)
        spy = self.bench[(self.bench.index >= self.start) & (self.bench.index <= self.end)]
        np.testing.assert_allclose((eq / eq.iloc[0]).to_numpy(), (spy / spy.iloc[0]).to_numpy(), rtol=1e-9)

    def test_efectivo_no_negativo_y_operaciones(self):
        eq, n = ov.sim(self.prep, self.reg, self.bench, dip.CFG, self.start, self.end)
        self.assertGreater(n, 3)
        self.assertTrue((eq > 0).all())

    def test_estructura_y_coste_se_restaura(self):
        idx = self.p['close'].index
        segs = [('a', (str(idx[300].date()), str(idx[800].date()))), ('b', (str(idx[801].date()), str(idx[-1].date())))]
        c0 = sb.COST
        r = ov.run_period(self.prep, self.reg, self.bench, segs, 0.99, sens=True, n_placebo=2)
        self.assertEqual(sb.COST, c0)
        for k in ('E1_supera_al_sp500', 'E2_mejor_que_placebo_en_cada_tramo', 'E3_sharpe_y_caida_no_peores', 'periodo_pasa'):
            self.assertIn(k, r['criterios'])
        self.assertIn('coste_0.2pct_por_lado', r['sensibilidades_no_deciden'])
        self.assertIn('riesgo_3pct', r['sensibilidades_no_deciden'])


if __name__ == '__main__':
    unittest.main()
