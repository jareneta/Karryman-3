import unittest

import numpy as np
import pandas as pd

import v24_engine as ve
import v24_screener as sc


def synth(T=1400, n=50, seed=17, with_div=True):
    p = ve.synthetic_universe(n=n, T=T, seed=seed)
    idx, cols = p['close'].index, p['close'].columns
    if with_div:
        dv = pd.DataFrame(0.0, index=idx, columns=cols)
        dv.iloc[300, :10] = 0.5                         # los 10 primeros pagan dividendo en la sesión 300
        p['dividends'] = dv
    mem = pd.DataFrame(True, index=idx, columns=cols)
    return p, mem


class Pantalla(unittest.TestCase):
    def test_matrices_contra_referencia_con_bucles(self):
        p, mem = synth()
        M = sc.screen_matrices(p, mem)
        C, H, V, D = (p[k].to_numpy() for k in ('close', 'high', 'volume', 'dividends'))
        checked = 0
        for t in range(260, 1400, 37):
            for j in range(0, 50, 7):
                c = C[:, j]
                vol50 = V[t - 49:t + 1, j].mean()
                ok = (c[t] >= 5 and vol50 > 500_000 and c[t] / c[t - 63] - 1 > 0.10 and c[t] / c[t - 21] - 1 > 0.01 and c[t] / c[t - 126] - 1 > 0 and c[t] / c[t - 252] - 1 > 0.01
                      and c[t] > c[t - 19:t + 1].mean() and c[t] > c[t - 49:t + 1].mean() and c[t] > c[t - 199:t + 1].mean() and c[t] / H[t - 251:t + 1, j].max() - 1 > -0.15
                      and D[t - 251:t + 1, j].sum() == 0)
                self.assertEqual(bool(M['screener_parcial'][t, j]), bool(ok), (t, j))
                self.assertEqual(bool(M['solo_tendencia'][t, j]), bool(c[t] >= 5 and vol50 > 500_000 and c[t] > c[t - 199:t + 1].mean()), (t, j))
                checked += 1
        self.assertGreater(checked, 100)
        self.assertGreater(M['screener_parcial'].sum(), 0)
        self.assertLessEqual(M['screener_parcial'].sum(), M['solo_tendencia'].sum())     # el screener parcial es más restrictivo

    def test_dividendo_excluye_durante_252_sesiones(self):
        p, mem = synth()
        M = sc.screen_matrices(p, mem)
        self.assertFalse(M['screener_parcial'][300:552, :10].any())                     # dividendo reciente: fuera
        base = sc.screen_matrices({k: v for k, v in p.items() if k != 'dividends'}, mem)
        self.assertGreaterEqual(base['screener_parcial'].sum(), M['screener_parcial'].sum())


class Simulacion(unittest.TestCase):
    def test_coste_y_ejecucion_a_la_apertura_siguiente(self):
        T = 8
        O = np.full((T, 1), 100.0)
        C = np.full((T, 1), 100.0)
        passes = np.zeros((T, 1), bool)
        passes[1:6, 0] = True                                      # cumple del cierre 1 al 5
        eq, st = sc.simulate_screen(O, C, passes, n_pos=1, cost=0.001, seed=1)
        self.assertAlmostEqual(eq[1], 1.0)                         # aún no hay posición: se compra en la apertura de la sesión 2
        self.assertAlmostEqual(eq[2], 1 / 1.001, places=9)         # compra con coste 0,1 %
        self.assertEqual(st['compras'], 1)
        self.assertEqual(st['ventas'], 1)                          # sale a la apertura de la sesión 6 (deja de cumplir en el cierre 5)
        self.assertAlmostEqual(eq[7], 1 / 1.001 * 0.999, places=9)
        self.assertAlmostEqual(st['efectivo_final'], 1 / 1.001 * 0.999, places=9)

    def test_nunca_mas_de_15_posiciones_y_vende_al_dejar_de_cumplir(self):
        p, mem = synth()
        M = sc.screen_matrices(p, mem)
        O, C = p['open'].to_numpy(), p['close'].to_numpy()
        eq, st = sc.simulate_screen(O, C, M['solo_tendencia'], seed=3)
        self.assertLessEqual(st['posiciones_medias'], 15)
        self.assertTrue((eq.dropna() > 0).all())
        self.assertGreater(st['compras'], 15)
        self.assertGreaterEqual(st['compras'], st['ventas'])

    def test_sin_futuro(self):
        p, mem = synth()
        M = sc.screen_matrices(p, mem)
        O, C = p['open'].to_numpy(), p['close'].to_numpy()
        t = 800
        a, _ = sc.simulate_screen(O, C, M['solo_tendencia'], seed=2)
        O2, C2 = O.copy(), C.copy()
        O2[t + 2:] *= 3.0
        C2[t + 2:] *= 3.0
        b, _ = sc.simulate_screen(O2, C2, M['solo_tendencia'], seed=2)       # las señales se mantienen: solo cambia el precio futuro
        np.testing.assert_allclose(a.iloc[:t + 1].to_numpy(), b.iloc[:t + 1].to_numpy(), rtol=1e-12)

    def test_azar_mensual_invierte_y_recompone(self):
        p, mem = synth()
        M = sc.screen_matrices(p, mem)
        O, C = p['open'].to_numpy(), p['close'].to_numpy()
        e = sc.simulate_random_monthly(O, C, M['liquidas'], seed=4)
        self.assertTrue((e.dropna() > 0).all())
        self.assertNotAlmostEqual(float(e.iloc[-1]), 1.0, places=2)

    def test_run_period_estructura_y_criterios(self):
        p, mem = synth(T=1500)
        bench = p['close'].mean(axis=1)
        idx = p['close'].index
        segs = [('a', (str(idx[400].date()), str(idx[900].date()))), ('b', (str(idx[901].date()), str(idx[-3].date())))]
        r = sc.run_period(p, mem, bench, segs, 0.99, n_seeds=2)
        for k in ('R1_supera_a_spy', 'R2_mejor_que_solo_tendencia_y_azar_en_cada_tramo', 'supera_al_sp500'):
            self.assertIn(k, r['criterios'])
        self.assertEqual(set(r), {'umbral', 'spy', 'igualponderada_miembros', 'screener_parcial', 'solo_tendencia', 'azar_mensual', 'criterios'})


if __name__ == '__main__':
    unittest.main()
