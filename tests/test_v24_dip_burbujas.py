import unittest

import numpy as np
import pandas as pd

import v24_dip_burbujas as db


class Burbujas(unittest.TestCase):
    def test_buckets(self):
        self.assertEqual([db.bucket(x) for x in (0.0, -0.05, -0.07, -0.11, -0.15, -0.21, -0.3)],
                         ['mayor_-5', 'mayor_-5', '-5_a_-10', '-10_a_-20', '-10_a_-20', 'menor_-20', 'menor_-20'])

    def test_ic_incluye_cero_si_no_hay_diferencia(self):
        rng = np.random.default_rng(0)
        r1, r0 = rng.normal(0, 1, 400), rng.normal(0, 1, 400)
        m = pd.period_range('2000-01', periods=40, freq='M')
        d = db.month_boot_diff(r1, m[rng.integers(0, 40, 400)], r0, m[rng.integers(0, 40, 400)])
        self.assertLess(d['ic95'][0], 0)
        self.assertGreater(d['ic95'][1], 0)

    def test_ic_excluye_cero_con_diferencia_grande(self):
        rng = np.random.default_rng(1)
        r1, r0 = rng.normal(1, 0.3, 400), rng.normal(0, 0.3, 400)
        m = pd.period_range('2000-01', periods=40, freq='M')
        d = db.month_boot_diff(r1, m[rng.integers(0, 40, 400)], r0, m[rng.integers(0, 40, 400)])
        self.assertGreater(d['ic95'][0], 0)

    def test_niveles_por_n(self):
        mk = lambda n: pd.DataFrame({'r': np.ones(n), 'entry_date': pd.Timestamp('2001-01-02')}, index=range(n))
        pl = pd.DataFrame({'r': [0.0, 0.0], 'entry_date': pd.Timestamp('2001-01-02'), 'seed': [1, 2]})
        self.assertEqual(db.summarize(mk(50), pl)['nivel'], 'no_concluyente')
        self.assertEqual(db.summarize(mk(150), pl)['nivel'], 'indicativo')
        self.assertEqual(db.summarize(mk(350), pl)['nivel'], 'evaluable')
        self.assertEqual(db.summarize(mk(0), pl)['n'], 0)

    def test_dd_usa_sesion_anterior(self):
        idx = pd.bdate_range('2020-01-01', periods=300)
        s = pd.Series(100.0, index=idx)
        s.iloc[-1] = 50.0
        self.assertAlmostEqual(float(db.spy_dd_at(s, pd.DatetimeIndex([idx[-1]]))[0]), 0.0)


if __name__ == '__main__':
    unittest.main()
