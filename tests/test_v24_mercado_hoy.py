import unittest

import numpy as np
import pandas as pd

import v24_mercado_hoy as mh


class Mercado(unittest.TestCase):
    def setUp(self):
        idx = pd.bdate_range('2020-01-01', periods=400)
        up = pd.DataFrame({'A': np.linspace(10, 20, 400), 'B': np.linspace(20, 10, 400)}, index=idx)
        self.c, self.m = up, pd.DataFrame(True, index=idx, columns=up.columns)

    def test_amplitud(self):
        b = mh.breadth(self.c, self.m, 50)
        self.assertAlmostEqual(float(b.iloc[-1]), 50.0)

    def test_cerca_max_y_min(self):
        self.assertAlmostEqual(float(mh.share_near(self.c, self.m, True).iloc[-1]), 50.0)
        self.assertAlmostEqual(float(mh.share_near(self.c, self.m, False).iloc[-1]), 50.0)

    def test_top10_con_pocos_valores_es_100(self):
        v = pd.DataFrame(1000.0, index=self.c.index, columns=self.c.columns)
        self.assertAlmostEqual(float(mh.top10_share(self.c, v, self.m).iloc[-1]), 100.0)

    def test_igual_ponderado_no_usa_pertenencia_futura(self):
        m = self.m.copy()
        m.loc[m.index[100]:, 'B'] = False
        e1 = mh.ew_index(self.c, m)
        c2 = self.c.copy()
        c2.iloc[200:] *= 5
        e2 = mh.ew_index(c2, m)
        pd.testing.assert_series_equal(e1.iloc[:200], e2.iloc[:200])

    def test_forward(self):
        s = pd.Series(np.arange(1, 400, dtype=float), index=self.c.index)
        f = mh.forward(s, s, s.index[10])
        self.assertIn('12m', f)


if __name__ == '__main__':
    unittest.main()
