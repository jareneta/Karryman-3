import unittest

import numpy as np
import pandas as pd

import v24_exposure as ex


def mk(n=700, seed=1):
    idx = pd.bdate_range('2015-01-01', periods=n)
    r = np.random.default_rng(seed).normal(0.0004, 0.01, n)
    spy = pd.Series(100 * np.cumprod(1 + r), index=idx)
    close = pd.DataFrame({f'T{i}': spy * (1 + 0.1 * np.random.default_rng(i).normal(size=n).cumsum() / 50) for i in range(20)}, index=idx)
    return spy, close, pd.DataFrame(True, index=idx, columns=close.columns)


class Exposure(unittest.TestCase):
    def test_sin_mirar_al_futuro(self):
        spy, close, mem = mk()
        a = ex.indicators(spy, close, mem)
        spy2, close2 = spy.copy(), close.copy()
        spy2.iloc[500:] *= 3
        close2.iloc[500:] *= 3
        b = ex.indicators(spy2, close2, mem)
        pd.testing.assert_frame_equal(a.iloc[:500], b.iloc[:500])

    def test_mapeo_de_exposicion(self):
        idx = pd.bdate_range('2020-01-01', periods=4)
        ind = pd.DataFrame(False, index=idx, columns=list(ex.IND))
        ind.iloc[1, :3] = True
        ind.iloc[2, :5] = True
        ind.iloc[3, :] = True
        self.assertEqual(list(ex.exposure(ind)), [0.0, 0.5, 1.0, 1.0])
        self.assertEqual(list(ex.exposure(ind, 'dos_estados')), [0.0, 1.0, 1.0, 1.0])

    def test_exposicion_total_sin_coste_es_spy_con_retraso(self):
        spy, _, _ = mk()
        eq = ex.equity(spy, pd.Series(1.0, index=spy.index), fee=0.0)
        r = spy.pct_change().fillna(0.0)
        np.testing.assert_allclose(eq.iloc[10:].pct_change().dropna().to_numpy(), r.iloc[10:].iloc[1:].to_numpy(), atol=1e-12)

    def test_cero_exposicion_es_efectivo(self):
        spy, _, _ = mk()
        eq = ex.equity(spy, pd.Series(0.0, index=spy.index))
        self.assertAlmostEqual(float(eq.iloc[-1]), 1.0)
        self.assertGreater(float(ex.equity(spy, pd.Series(0.0, index=spy.index), cash_rate=0.02).iloc[-1]), 1.0)

    def test_la_senal_se_aplica_dos_cierres_despues(self):
        spy, _, _ = mk(50)
        e = pd.Series(0.0, index=spy.index)
        e.iloc[20:] = 1.0
        eq = ex.equity(spy, e, fee=0.0)
        r = spy.pct_change()
        self.assertAlmostEqual(float(eq.iloc[21] / eq.iloc[20] - 1), 0.0)
        self.assertAlmostEqual(float(eq.iloc[22] / eq.iloc[21] - 1), float(r.iloc[22]))

    def test_coste_por_cambio(self):
        spy, _, _ = mk(50)
        e = pd.Series(0.0, index=spy.index)
        e.iloc[20:] = 1.0
        a, b = ex.equity(spy, e, fee=0.0), ex.equity(spy, e, fee=0.01)
        ra, rb = a.pct_change(), b.pct_change()
        d = (ra - rb).abs()
        self.assertAlmostEqual(float(d.iloc[22]), 0.01, places=9)       # el coste cae solo el día del cambio
        self.assertAlmostEqual(float(d.drop(d.index[22]).iloc[1:].max()), 0.0, places=9)

    def test_run_period_estructura_y_placebo(self):
        spy, close, mem = mk(900)
        segs = [('S1', ('2016-06-01', '2017-06-30')), ('S2', ('2017-07-01', '2018-06-30'))]
        res = ex.run_period(spy, close, mem, segs, 0.99, sens=True, n_shift=50)
        self.assertIn('R2_reduce_riesgo', res['criterios'])
        self.assertTrue(0 < res['placebo_p_valor_todo'] <= 1)
        self.assertEqual(set(res['mezcla_constante']), {'S1', 'S2', 'todo'})


if __name__ == '__main__':
    unittest.main()
