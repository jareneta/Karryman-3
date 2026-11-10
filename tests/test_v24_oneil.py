import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_oneil as on

ENTRY_I = 100


def make_d(highs, closes=None, T=260):
    """DataFrame preparado con precios controlados a partir de la sesión de entrada."""
    idx = pd.bdate_range('2015-01-02', periods=T)
    c = np.full(T, 100.0)
    h = np.full(T, 100.5)
    lo = np.full(T, 99.5)
    for k, v in highs.items():
        h[ENTRY_I + k] = v
        c[ENTRY_I + k] = v * 0.99
    if closes:
        for k, v in closes.items():
            c[ENTRY_I + k] = v
            lo[ENTRY_I + k] = min(lo[ENTRY_I + k], v)
    f = pd.DataFrame({'Open': c, 'High': np.maximum(h, c), 'Low': np.minimum(lo, c), 'Close': c, 'Volume': 2e6}, index=idx)
    d = sb.prepare(f, pd.Series(np.linspace(100, 120, T), index=idx))
    return d


def run(d, cfg):
    t = sb.Trade('X', 'base', ENTRY_I, 100.0 * (1 + sb.COST), 92.0, 0.0)
    t.stop = 92.0
    for j in range(ENTRY_I, len(d)):
        if sb.step(t, d, j, cfg):
            break
    return t


class Oneil(unittest.TestCase):
    def test_beneficio_en_mas_25(self):
        d = make_d({30: 126.0})                      # máximo +26 % en la sesión 30, sin haber tocado +20 % antes
        t = run(d, on.CFG)
        self.assertFalse(t.hold8)
        self.assertEqual(t.exit_i, ENTRY_I + 30)
        self.assertAlmostEqual(t.fills[-1][2], 100.0 * (1 + sb.COST) * 1.25 * (1 - sb.COST), places=6)   # límite en +25 % sobre la entrada (con coste) menos coste de venta

    def test_regla_de_8_semanas(self):
        d = make_d({5: 121.0, 20: 131.0})            # +21 % en la sesión 5 (< 15) → se mantiene
        t = run(d, on.CFG)
        self.assertTrue(t.hold8)
        self.assertEqual(t.exit_i, ENTRY_I + 40)     # salida en la sesión 40 (apertura de la 41ª sesión = índice entrada+40)

    def test_sin_regla_si_el_20_llega_tarde(self):
        d = make_d({20: 121.0, 25: 126.0})           # +21 % en la sesión 20 (> 15) → no hay mantenimiento
        t = run(d, on.CFG)
        self.assertFalse(t.hold8)
        self.assertEqual(t.exit_i, ENTRY_I + 25)

    def test_stop_fijo_8_por_ciento_por_cierre(self):
        d = make_d({}, closes={10: 91.0})            # cierre por debajo de 92 en la sesión 10 → salida en la apertura siguiente
        t = run(d, on.CFG)
        self.assertEqual(t.exit_i, ENTRY_I + 11)
        self.assertLess(t.realized / t.R, 0)

    def test_open_trade_stop_exacto_8(self):
        d = make_d({})
        d['member'] = True
        sig = (ENTRY_I - 1, 'base', float(d.Close.iloc[ENTRY_I - 1]), 1e-6, 0.0)
        t = sb.open_trade(d, 'X', sig, on.CFG)
        self.assertIsNotNone(t)
        self.assertAlmostEqual(t.stop0 / d.Open.iloc[ENTRY_I], 0.92, places=6)

    def test_condiciones_de_base(self):
        rng = np.random.default_rng(3)
        T = 1500
        idx = pd.bdate_range('2012-01-02', periods=T)
        for k in range(8):
            c = 50 * np.exp(np.cumsum(rng.normal(0.0006, 0.015, T)))
            f = pd.DataFrame({'Open': c, 'High': c * 1.01, 'Low': c * 0.99, 'Close': c, 'Volume': rng.uniform(1e6, 3e6, T)}, index=idx)
            d = sb.prepare(f, pd.Series(np.linspace(100, 200, T), index=idx))
            d['member'] = True
            d['rs_rank'] = 90.0
            reg = sb.regime_series(pd.DataFrame({'Close': pd.Series(np.linspace(100, 200, T), index=idx)}))
            for (i, kind, pivot, stop, rs) in sb.signals(d, on.CFG, reg):
                self.assertGreaterEqual(d.vol50.iloc[i] and d.Volume.iloc[i] / d.vol50.iloc[i], 1.5 - 1e-9)
                self.assertTrue(d.base_len.iloc[i] >= 35 or d.base_depth.iloc[i] <= 0.15 + 1e-12)
                self.assertLessEqual(d.base_depth.iloc[i], 0.33 + 1e-12)
                self.assertGreaterEqual(d.prior_adv.iloc[i], 0.30)
                self.assertEqual(stop, 1e-6)


if __name__ == '__main__':
    unittest.main()
