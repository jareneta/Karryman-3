"""Auditoría independiente del motor V24: cada indicador y regla se contrasta con una implementación de referencia
escrita aparte (bucles simples), no con el propio código del motor."""
import unittest

import numpy as np
import pandas as pd

import v24_engine as ve


def U(n=25, T=700, seed=11):
    return ve.synthetic_universe(n=n, T=T, seed=seed)


class Indicadores(unittest.TestCase):
    def setUp(self):
        self.p = U()
        self.cfg = ve.Cfg()
        self.mom, self.ema, self.atr = ve.indicators(self.p, self.cfg)

    def test_momentum_63(self):
        C = self.p['close'].to_numpy()
        ref = np.full_like(C, np.nan)
        for t in range(63, len(C)):
            ref[t] = C[t] / C[t - 63] - 1
        np.testing.assert_allclose(self.mom.to_numpy()[63:], ref[63:], rtol=1e-12)
        self.assertTrue(self.mom.iloc[:63].isna().all().all())

    def test_ema20_recursiva(self):
        C = self.p['close'].to_numpy()
        a = 2 / (20 + 1)
        ref = np.zeros_like(C)
        ref[0] = C[0]
        for t in range(1, len(C)):
            ref[t] = a * C[t] + (1 - a) * ref[t - 1]
        np.testing.assert_allclose(self.ema.to_numpy()[19:], ref[19:], rtol=1e-10)
        self.assertTrue(self.ema.iloc[:19].isna().all().all())

    def test_atr14_wilder(self):
        C, H, L = (self.p[k].to_numpy() for k in ('close', 'high', 'low'))
        tr = np.full_like(C, np.nan)
        for t in range(1, len(C)):
            tr[t] = np.maximum.reduce([H[t] - L[t], np.abs(H[t] - C[t - 1]), np.abs(L[t] - C[t - 1])])
        ref = np.full_like(C, np.nan)
        ref[1] = tr[1]
        for t in range(2, len(C)):
            ref[t] = (ref[t - 1] * 13 + tr[t]) / 14          # suavizado de Wilder sembrado con el primer TR
        np.testing.assert_allclose(self.atr.to_numpy()[14:], ref[14:], rtol=1e-9)
        # contra el ATR clásico (semilla = media simple de 14): la diferencia desaparece con el tiempo
        for j in range(C.shape[1]):
            seed = tr[1:15, j].mean()
            x = seed
            for t in range(15, len(C)):
                x = (x * 13 + tr[t, j]) / 14
            self.assertAlmostEqual(x / ref[-1, j], 1.0, delta=0.01)

    def test_indicadores_sin_futuro(self):
        q = {k: v.copy() for k, v in self.p.items()}
        t = 400
        for k in ('open', 'high', 'low', 'close'):
            q[k].iloc[t + 1:] *= 3.0
        m2, e2, a2 = ve.indicators(q, self.cfg)
        for a, b in ((self.mom, m2), (self.ema, e2), (self.atr, a2)):
            np.testing.assert_allclose(a.to_numpy()[:t + 1], b.to_numpy()[:t + 1], equal_nan=True)


class Seleccion(unittest.TestCase):
    N = 80

    def cfg(self, **k):
        return ve.Cfg(**k)

    def test_entra_top15_permanece_hasta_top45(self):
        c = self.cfg()
        rk = np.arange(1, self.N + 1, dtype=float)
        held = np.zeros(self.N, bool)
        cool = np.full(self.N, -10**9)
        sel = ve.select(rk, np.zeros(self.N, bool), held, cool, 100, c)
        self.assertEqual(sorted(sel), list(range(15)))                 # solo rangos 1..15
        held[sel] = True
        rk2 = rk.copy()
        rk2[0], rk2[44], rk2[45] = 45.0, 46.0, 1.0                      # uno en el límite 45, otro cae a 46
        rk2[44] = 46.0
        sel2 = ve.select(rk2, np.zeros(self.N, bool), held, cool, 101, c)
        self.assertIn(0, sel2)                                          # rango 45: permanece
        # el valor 14 (rango 15) baja a 46: sale
        rk3 = rk.copy()
        rk3[14] = 46.0
        sel3 = ve.select(rk3, np.zeros(self.N, bool), held, cool, 101, c)
        self.assertNotIn(14, sel3)

    def test_no_entra_rango_16_a_45(self):
        c = self.cfg()
        rk = np.arange(1, self.N + 1, dtype=float)
        held = np.zeros(self.N, bool)
        held[:5] = True
        cool = np.full(self.N, -10**9)
        sel = ve.select(rk, np.zeros(self.N, bool), held, cool, 100, c)
        self.assertTrue(all(j < 15 for j in sel))
        self.assertLessEqual(len(sel), c.max_pos)

    def test_maximo_15_posiciones(self):
        c = self.cfg(top_in=30, max_pos=15)
        rk = np.arange(1, self.N + 1, dtype=float)
        sel = ve.select(rk, np.zeros(self.N, bool), np.zeros(self.N, bool), np.full(self.N, -10**9), 100, c)
        self.assertEqual(len(sel), 15)

    def test_cooldown_exacto_10_sesiones(self):
        c = self.cfg()
        rk = np.arange(1, self.N + 1, dtype=float)
        held = np.zeros(self.N, bool)
        held[3] = True
        cool = np.full(self.N, -10**9)
        ext = np.zeros(self.N, bool)
        ext[3] = True
        ve.select(rk, ext, held, cool, 200, c)                            # salida por extensión en la sesión 200
        self.assertEqual(cool[3], 200)
        held[3] = False
        noext = np.zeros(self.N, bool)
        for day in range(201, 211):                                       # sesiones 201..210: espera
            self.assertNotIn(3, ve.select(rk, noext, held, cool, day, c), f'sesión {day}')
        self.assertIn(3, ve.select(rk, noext, held, cool, 211, c))        # 211: ya puede ser elegido

    def test_salida_por_extension_no_depende_del_ranking(self):
        c = self.cfg()
        rk = np.arange(1, self.N + 1, dtype=float)
        held = np.zeros(self.N, bool)
        held[0] = True
        ext = np.zeros(self.N, bool)
        ext[0] = True
        sel = ve.select(rk, ext, held, np.full(self.N, -10**9), 50, c)
        self.assertNotIn(0, sel)

    def test_ranking_mensual_no_reordena_entre_rebalanceos(self):
        c = self.cfg(rank_every=21)
        rk = np.arange(1, self.N + 1, dtype=float)
        held = np.zeros(self.N, bool)
        held[[60, 61]] = True                                             # fuera del top 45, pero en cartera
        cool = np.full(self.N, -10**9)
        sel = ve.select(rk, np.zeros(self.N, bool), held, cool, 105, c, rebalance=False)
        self.assertEqual(sorted(sel), [60, 61])                           # día intermedio: no cambia la cartera
        sel2 = ve.select(rk, np.zeros(self.N, bool), held, cool, 105, c, rebalance=True)
        self.assertNotIn(60, sel2)


class Ejecucion(unittest.TestCase):
    def test_comision(self):
        c = ve.Cfg(fee_min=1.0, fee_per_share=0.005, fee_pct_max=0.01)
        self.assertEqual(ve.fee_of(10, 100.0, c), 1.0)                     # mínimo
        self.assertAlmostEqual(ve.fee_of(1000, 100.0, c), 5.0)             # 0,005 $/acción
        self.assertAlmostEqual(ve.fee_of(1000, 0.2, c), 2.0)               # tope: 1 % de 200 $ = 2 $ (< 5 $ por acción)
        self.assertEqual(ve.fee_of(2, 1.0, c), 1.0)                        # el mínimo manda sobre el tope

    def test_precios_de_ejecucion_apertura_siguiente_con_slippage(self):
        p = U(T=600)
        c = ve.Cfg(slip_bps=10.0)
        r = ve.run(p, c)
        tr = r['trades']
        tr = tr[tr.kind != 'DELIST']
        self.assertGreater(len(tr), 0)
        for _, t in tr.head(200).iterrows():
            o = p['open'].loc[t.date, t.ticker]
            exp = o * (1 + c.slip_bps / 1e4) if t.kind.startswith('BUY') else o * (1 - c.slip_bps / 1e4)
            self.assertAlmostEqual(t.price, exp, places=9)

    def test_ninguna_orden_el_primer_dia_de_datos_y_siempre_tras_la_senal(self):
        p = U(T=600)
        r = ve.run(p, ve.Cfg())
        first = r['trades'].date.min()
        self.assertGreater(p['close'].index.get_loc(first), 64)            # tras el calentamiento de 63 sesiones

    def test_identidad_contable_efectivo(self):
        p = U(T=900)
        c = ve.Cfg(capital=5000, fee_min=0.5, min_order=50, slip_bps=7.0)
        r = ve.run(p, c)
        tr = r['trades']
        signed = np.where(tr.kind.str.startswith('BUY'), -1.0, 1.0) * tr.qty * tr.price
        cash = c.capital + signed.sum() - tr.fee.sum()
        self.assertAlmostEqual(cash, r['cash_end'], places=6)

    def test_patrimonio_final_coherente(self):
        p = U(T=900)
        r = ve.run(p, ve.Cfg(capital=5000))
        tr = r['trades']
        q = tr.assign(s=np.where(tr.kind.str.startswith('BUY'), 1.0, -1.0) * tr.qty).groupby('ticker')['s'].sum()
        last = p['close'].ffill().iloc[-1]
        val = r['cash_end'] + float((q * last[q.index]).sum())
        self.assertAlmostEqual(val, r['equity'].iloc[-1], delta=1e-6 * val)


class Riesgo(unittest.TestCase):
    def test_exposicion_nunca_supera_100_ni_cae_de_35_con_proteccion_progresiva(self):
        p = U(T=900)
        r = ve.run(p, ve.Cfg(protection='progressive'))
        e = r['exposure'].dropna()
        self.assertLessEqual(e.max(), 1.0 + 1e-12)
        self.assertTrue(((e >= 0.0) & (e > 0)).all())

    def test_volatilidad_objetivo_reduce_exposicion_en_alta_volatilidad(self):
        p = U(T=900)
        lo = ve.run(p, ve.Cfg(vol_target=0.05, protection='none'))['exposure'].mean()
        hi = ve.run(p, ve.Cfg(vol_target=0.50, protection='none'))['exposure'].mean()
        self.assertLess(lo, hi)


if __name__ == '__main__':
    unittest.main()
