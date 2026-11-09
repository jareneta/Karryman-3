import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inst_features as inf  # noqa: E402


def frame(closes, vols, spread=0.01, close_pos=0.5, start='2020-01-01'):
    c = np.asarray(closes, float)
    idx = pd.bdate_range(start, periods=len(c))
    lo, hi = c * (1 - spread), c * (1 + spread)
    # cierre en la posición close_pos del rango: ajustamos máximos y mínimos alrededor del cierre
    lo = c - (c * spread) * 2 * close_pos
    hi = lo + c * spread * 2
    return pd.DataFrame({'Open': c, 'High': hi, 'Low': lo, 'Close': c, 'Volume': np.asarray(vols, float)}, index=idx)


class InstitutionalFeatureTests(unittest.TestCase):
    def test_distribution_and_accumulation_days(self):
        n = 120
        closes, vols = [100.0], [1e6]
        for k in range(1, n):
            if k >= 100 and k % 2 == 0:       # 10 días de distribución en 20 sesiones: cae un 1% con más volumen
                closes.append(closes[-1] * 0.99); vols.append(vols[-1] * 1.2)
            elif k >= 100:
                closes.append(closes[-1] * 1.0005); vols.append(vols[-1] * 0.8)   # sube poco y con menos volumen
            else:
                closes.append(closes[-1] * 1.005); vols.append(1e6 + (k % 2) * 1e5)  # sube un 0,5% (volumen alterno)
        d = inf.institutional_features(frame(closes, vols))
        self.assertEqual(d['dist_days_25'].iloc[-1], 10)      # sesiones pares 100,102,...,118: cae un 1% con más volumen
        self.assertGreater(d['dist_days_25'].iloc[-1], d['acc_days_25'].iloc[-1])
        self.assertLess(d['acc_net_50'].iloc[-1], d['acc_net_50'].iloc[95])

    def test_money_flow_signs_follow_the_close_position(self):
        n = 100
        up = frame(np.linspace(100, 130, n), np.full(n, 1e6), close_pos=0.9)      # cierra cerca del máximo del día
        dn = frame(np.linspace(100, 130, n), np.full(n, 1e6), close_pos=0.1)      # cierra cerca del mínimo
        self.assertGreater(inf.institutional_features(up)['cmf_20'].iloc[-1], 0.5)
        self.assertLess(inf.institutional_features(dn)['cmf_20'].iloc[-1], -0.5)
        self.assertGreater(inf.institutional_features(up)['ad_63'].iloc[-1], 0.3)

    def test_big_days_and_accumulation_divergence(self):
        n = 160
        c = np.full(n, 50.0) + np.sin(np.arange(n) / 8) * 0.3     # precio lateral
        v = np.full(n, 1e6)
        f = frame(c, v, close_pos=0.85)                           # pero cierra siempre en la parte alta (compra silenciosa)
        d = inf.institutional_features(f)
        self.assertEqual(d['accum_divergence'].iloc[-1], 1.0)     # A/D sube mientras el precio no
        # un día de compra masiva: volumen x3, sube y cierra arriba
        c2, v2 = c.copy(), v.copy()
        c2[150], v2[150] = c2[149] * 1.03, 3e6
        d2 = inf.institutional_features(frame(c2, v2, close_pos=0.9))
        self.assertGreaterEqual(d2['big_up_50'].iloc[155], 1)
        self.assertEqual(d2['big_dn_50'].iloc[155], 0)

    def test_no_lookahead(self):
        rng = np.random.default_rng(4)
        n = 500
        c = 40 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, n)))
        v = 1e6 * np.exp(rng.normal(0, 0.4, n))
        full = frame(c, v)
        short = full.iloc[:300]
        a, b = inf.institutional_features(full).iloc[:300], inf.institutional_features(short)
        pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9, atol=1e-12)
        s1, s2 = inf.stage_features(full, full.index[0]).iloc[:300], inf.stage_features(short, full.index[0])
        pd.testing.assert_frame_equal(s1, s2, check_exact=False, rtol=1e-9, atol=1e-12)

    def test_market_distribution(self):
        n = 80
        closes, vols = [100.0], [1e8]
        for k in range(1, n):
            closes.append(closes[-1] * (0.99 if k >= 60 else 1.001)); vols.append(vols[-1] * (1.1 if k >= 60 else 0.99))
        m = inf.market_distribution(frame(closes, vols))
        self.assertEqual(m['spy_dist_25'].iloc[-1], 20)
        self.assertEqual(m['spy_dist_ge5'].iloc[-1], 1.0)
        self.assertEqual(m['spy_dist_ge5'].iloc[59], 0.0)


class StageTests(unittest.TestCase):
    def test_weinstein_stages(self):
        c = np.r_[np.linspace(100, 40, 250), np.full(150, 40.0), np.linspace(40, 120, 200), np.linspace(120, 123, 300)]
        f = frame(c, np.full(len(c), 1e6))
        d = inf.stage_features(f, pd.Timestamp('2010-01-04'))
        st = d['stage']
        self.assertEqual(st.iloc[240], 4)                 # cayendo: precio < MA150 a la baja
        self.assertIn(st.iloc[380], (1, 4))               # lateral tras el suelo
        self.assertEqual(st.iloc[520], 2)                 # avance
        self.assertEqual(st.iloc[-1], 3)                  # techo lateral: precio > MA150 pero la MA150 ya no sube
        self.assertAlmostEqual(d['age_years'].iloc[0], (f.index[0] - pd.Timestamp('2010-01-04')).days / 365.25)
        self.assertLess(d['dd_3y'].iloc[300], -0.5)

    def test_unknown_first_date(self):
        f = frame(np.linspace(10, 20, 200), np.full(200, 1e6))
        self.assertTrue(inf.stage_features(f, None)['age_years'].isna().all())


if __name__ == '__main__':
    unittest.main()
