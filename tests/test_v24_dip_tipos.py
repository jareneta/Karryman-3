import unittest

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_dip as dip
import v24_dip_tipos as tp
import v24_engine as ve
import v24_h5 as h5
from tests.test_v24_dip import build


class Tipos(unittest.TestCase):
    def test_grupos_son_una_particion_por_caracteristica(self):
        rg = np.random.default_rng(3)
        n = 3000
        T = pd.DataFrame({'dd': rg.uniform(-0.35, -0.15, n), 'ret5': rg.normal(-0.03, 0.06, n), 'dias_max': rg.integers(1, 61, n), 'vol_ratio': rg.uniform(0.2, 3, n),
                          'spy_up': rg.random(n) > 0.5, 'dist252': -rg.uniform(0.15, 0.6, n), 'gap': rg.normal(0, 0.03, n), 'sma200': rg.uniform(0, 0.6, n), 'r': rg.normal(0.05, 1, n)})
        for fam, names in tp.FAMILIES.items():
            masks = [fn(T).to_numpy(bool) for f, nm, fn in tp.GROUPS if f == fam]
            cover = np.sum(masks, axis=0)
            self.assertTrue((cover <= 1).all(), fam)                      # nunca en dos grupos a la vez
        for fam in ('profundidad', 'velocidad', 'volumen_señal', 'mercado', 'hueco_apertura'):
            masks = [fn(T).to_numpy(bool) for f, nm, fn in tp.GROUPS if f == fam]
            self.assertTrue((np.sum(masks, axis=0) == 1).all(), fam)       # y cubren todo
        self.assertEqual(len(tp.GROUPS), 21)

    def test_contraste_detecta_diferencia_plantada(self):
        rg = np.random.default_rng(4)
        n = 4000
        dd = rg.uniform(-0.35, -0.15, n)
        T = pd.DataFrame({'dd': dd, 'ret5': rg.normal(-0.03, 0.06, n), 'dias_max': rg.integers(1, 61, n), 'vol_ratio': rg.uniform(0.2, 3, n), 'spy_up': rg.random(n) > 0.5,
                          'dist252': -rg.uniform(0.15, 0.6, n), 'gap': rg.normal(0, 0.03, n), 'sma200': rg.uniform(0, 0.6, n)})
        T['r'] = rg.normal(0, 1, n) + np.where(dd < -0.25, 0.3, 0.0)         # las caídas de 25-35 % rinden +0,3 R
        c = tp.contrasts(T)
        self.assertGreater(c[('profundidad', '25-35%')]['dif_R'], 0.2)
        self.assertLess(c[('profundidad', '25-35%')]['p'], 0.001)
        self.assertGreater(c[('mercado', 'SPY>SMA200')]['p'], 0.001)

    def test_caracteristicas_de_las_operaciones_con_referencia(self):
        p, prep, reg = build(n=60, T=1500)
        bench = p['close'].mean(axis=1)
        tr = sb.simulate_independent(prep, dip.CFG, reg)
        self.assertGreater(len(tr), 10)
        F = tp.trade_features(tr, prep, bench)
        self.assertGreater(len(F), 5)
        for r in F.head(30).itertuples():
            d = prep[r.ticker]
            e = d.index.get_loc(r.entry_date)
            i = e - 1
            c = d.Close.to_numpy()
            self.assertAlmostEqual(r.dd, c[i] / c[i - 60:i].max() - 1, places=12)
            self.assertTrue(-0.35 - 1e-9 <= r.dd <= -0.15 + 1e-9)                       # la señal exige 15-35 %
            self.assertAlmostEqual(r.ret5, c[i] / c[i - 5] - 1, places=12)
            self.assertAlmostEqual(r.gap, d.Open.iloc[i] / c[i - 1] - 1, places=12)
            self.assertTrue(1 <= r.dias_max <= 60)


if __name__ == '__main__':
    unittest.main()
