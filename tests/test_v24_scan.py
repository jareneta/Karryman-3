import unittest

import numpy as np
import pandas as pd

import v24_calendar as cal
import v24_engine as ve
import v24_scan as sc


def panel(T=700, n=40, seed=31):
    p = ve.synthetic_universe(n=n, T=T, seed=seed)
    mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
    return p, mem


class Scan(unittest.TestCase):
    def test_lista_de_45_variables(self):
        p, _ = panel()
        F = sc.features(p)
        self.assertEqual(len(F), 45)
        expected = ('r1 r2 r3 r5 r10 r21 r63 r126 r252 r126m21 r252m21 vol10 vol21 vol63 atr14pct dvol63 skew63 max21 min21 beta126 ivol63 dh252 dl252 dh20 dh50 c_sma10 c_sma20 c_sma50 c_sma200 '
                    'sma50_200 logp vratio1_50 vratio5_50 logdv amihud63 obv21 gap intraday clv1 clv5 nr7 inside run rev5_x_vol21 mom126m21_x_lowvol').split()
        self.assertEqual(set(F), set(expected))

    def test_formulas_contra_referencia(self):
        p, _ = panel()
        F = sc.features(p)
        C, H, L, V = (p[k].to_numpy() for k in ('close', 'high', 'low', 'volume'))
        t = 400
        self.assertAlmostEqual(F['r5'].iloc[t, 3], C[t, 3] / C[t - 5, 3] - 1, places=12)
        self.assertAlmostEqual(F['r252m21'].iloc[t, 3], C[t - 21, 3] / C[t - 252, 3] - 1, places=12)
        self.assertAlmostEqual(F['dh252'].iloc[t, 5], C[t, 5] / H[t - 251:t + 1, 5].max() - 1, places=12)
        self.assertAlmostEqual(F['c_sma50'].iloc[t, 7], C[t, 7] / C[t - 49:t + 1, 7].mean() - 1, places=12)
        self.assertAlmostEqual(F['vol21'].iloc[t, 2], np.std(np.diff(C[t - 21:t + 1, 2]) / C[t - 21:t, 2], ddof=1), places=12)
        # run con signo: bucle de referencia
        r = np.sign(np.diff(C[:, 4], prepend=np.nan))
        r[np.isnan(r)] = 0
        run = 0.0
        for i in range(1, t + 1):
            run = run + r[i] if r[i] * r[i - 1] > 0 else r[i]
        self.assertAlmostEqual(F['run'].iloc[t, 4], run, places=12)

    def test_features_sin_futuro(self):
        p, _ = panel()
        t = 450
        a = sc.features(p)
        q = {k: v.copy() for k, v in p.items()}
        for k in q:
            q[k].iloc[t + 1:] *= 2.5
        b = sc.features(q)
        for k in a:
            np.testing.assert_allclose(a[k].iloc[:t + 1].to_numpy(), b[k].iloc[:t + 1].to_numpy(), rtol=1e-9, atol=1e-12, equal_nan=True, err_msg=k)

    def test_ic_detecta_una_senal_plantada_y_no_ruido(self):
        rg = np.random.default_rng(5)
        T, n = 400, 120
        idx = pd.bdate_range('2015-01-02', periods=T)
        cols = [f'S{i}' for i in range(n)]
        F = pd.DataFrame(rg.normal(size=(T, n)), index=idx, columns=cols)
        R = 0.3 * F + pd.DataFrame(rg.normal(size=(T, n)), index=idx, columns=cols)
        ic, _ = sc.row_ic(F, R)
        self.assertGreater(ic.mean(), 0.15)
        noise = pd.DataFrame(rg.normal(size=(T, n)), index=idx, columns=cols)
        ic2, _ = sc.row_ic(F, noise)
        n_, m_, t_, p_ = sc.tstat(ic2)
        self.assertGreater(p_, 0.01)

    def test_bh(self):
        p = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216, 0.222, 0.251, 0.269, 0.275, 0.34, 0.341, 0.384, 0.569, 0.594, 0.696]
        rej = sc.bh(p, 0.05)
        self.assertEqual(int(rej.sum()), 1)                      # umbrales 0,05·k/20: solo p=0,001 (≤ 0,0025); 0,008 > 0,005
        self.assertTrue(rej[0] and not rej[1])
        self.assertEqual(int(sc.bh([0.001, 0.004, 0.2], 0.05).sum()), 2)   # umbrales 0,0167 / 0,033 / 0,05
        self.assertEqual(int(sc.bh([0.03, 0.9, 0.01, 0.02], 0.05).sum()), 3)   # umbrales 0,0125/0,025/0,0375/0,05; el orden de entrada no importa
        self.assertEqual(int(sc.bh([0.5, 0.6, 0.7], 0.05).sum()), 0)

    def test_muestreo_sin_solapamiento_y_analyze(self):
        p, mem = panel(T=900, n=90)
        idx = p['close'].index
        res = sc.analyze(p, mem, (str(idx[300].date()), str(idx[800].date())))
        self.assertEqual(len(res), 45 * 3)
        n1, n21 = res[('r5', 1)]['n'], res[('r5', 21)]['n']
        self.assertGreater(n1, 15 * n21 / 1.5)                      # el horizonte de 21 sesiones usa ~1/21 de las fechas


class Calendario(unittest.TestCase):
    def test_grupos_y_bloqueo(self):
        idx = pd.bdate_range('1950-01-03', '2024-06-28')
        px = pd.Series(100 * np.cumprod(1 + np.random.default_rng(2).normal(0.0003, 0.01, len(idx))), index=idx)
        out = cal.run_all(px)
        self.assertLessEqual(pd.Timestamp(out['ultimo_dia_usado']), pd.Timestamp('2020-12-31'))
        self.assertEqual(out['resumen']['pruebas'], 5 + 12 + 1 + 1 + 1)
        g = cal.groups(idx[:300])
        self.assertEqual(int(g.loc[:, 'dia_lun'].sum()), int((idx[:300].weekday == 0).sum()))
        self.assertEqual(int(g.iloc[:, 5:17].sum(axis=1).max()), 1)   # cada sesión pertenece a un único mes


if __name__ == '__main__':
    unittest.main()
