import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

import v24_engine as ve


def universe(n=40, T=900, seed=7):
    return ve.synthetic_universe(n=n, T=T, seed=seed)


class Machine(unittest.TestCase):
    def test_levels_only_allowed_and_gradual(self):
        p = ve.Protection(ve.Cfg())
        seen = []
        for dd in [0, 0.05, 0.09, 0.13] + [0.0] * 30:
            seen.append(p.update(dd))
        self.assertTrue(set(seen) <= set(ve.LEVELS))
        self.assertEqual(seen[3], 0.35)                    # baja inmediata
        up = [s for s in seen[4:] if s != 0.35]
        self.assertEqual(up[0], 0.5)                       # sube un nivel cada vez, sin saltos
        self.assertEqual(seen[4:9], [0.35] * 4 + [0.5])    # tras 5 cierres consecutivos
        self.assertNotIn(0.6, seen)
        self.assertNotIn(0.85, seen)

    def test_reentry_counter_resets(self):
        p = ve.Protection(ve.Cfg())
        p.update(0.09)
        for _ in range(4):
            p.update(0.0)
        p.update(0.09)                                     # se rompe la racha
        for _ in range(4):
            self.assertEqual(p.update(0.0), 0.5)
        self.assertEqual(p.update(0.0), 0.75)


class Engine(unittest.TestCase):
    def test_no_leverage_no_negative_cash(self):
        p = universe()
        r = ve.run(p, ve.Cfg(min_order=100, fee_min=1.0, reject_prob=0.2))
        self.assertGreaterEqual(r['cash_end'], -1e-6)
        self.assertLessEqual(r['exposure'].max(), 1.0)
        self.assertTrue((r['equity'] > 0).all())

    def test_no_lockout_small_capital(self):
        """Regresión del fallo: 3.000 $, exposición 25 %, orden mínima 100 $, comisión 0,35 $."""
        p = universe(T=1200)
        c = ve.Cfg(capital=3000, min_order=100, fee_min=0.35, protection='progressive', ma100_guard=True)
        r = ve.run(p, c)
        tr = r['trades']
        self.assertGreater(len(tr), 20)
        last = tr['date'].max()
        self.assertGreater(last, p['close'].index[-120])   # sigue operando hasta el final
        invested = 1 - (r['cash_end'] / r['equity'].iloc[-1])
        self.assertTrue(invested > 0 or r['exposure'].iloc[-2] < 0.05)

    def test_viable_positions_with_tiny_capital(self):
        p = universe()
        c = ve.Cfg(capital=3000, min_order=100, fee_min=0.35, vol_target=0.15)
        r = ve.run(p, c)
        buys = r['trades'][r['trades'].kind == 'BUY_NEW']
        self.assertGreater(len(buys), 0)
        self.assertTrue(((buys.qty * buys.price) >= 100 * 0.9).all())

    def test_mandatory_exits_bypass_min_order(self):
        p = universe()
        r = ve.run(p, ve.Cfg(capital=3000, min_order=250, fee_min=1.0))
        t = r['trades']
        forced = t[t.kind.isin(['SELL_EXIT', 'SELL_RISK'])]
        self.assertGreater(len(forced), 0)
        self.assertLess((forced.qty * forced.price).min(), 250)   # se ejecutan aunque no lleguen al mínimo

    def test_no_lookahead(self):
        p = universe(T=700)
        cut = 500
        a = ve.run(p, ve.Cfg())
        q = {k: v.copy() for k, v in p.items()}
        for k in ('open', 'high', 'low', 'close'):
            q[k].iloc[cut + 5:] = q[k].iloc[cut + 5:] * 1.7   # cambia solo el futuro
        b = ve.run(q, ve.Cfg())
        ta = a['trades'][a['trades'].date <= p['close'].index[cut]]
        tb = b['trades'][b['trades'].date <= p['close'].index[cut]]
        pd.testing.assert_frame_equal(ta.reset_index(drop=True), tb.reset_index(drop=True))

    def test_cooldown_after_extension_exit(self):
        p = universe(n=30, T=1000)
        # fuerza una extensión violenta en una acción líder
        c = p['close'].copy()
        j = c.columns[0]
        c.iloc[400:420, 0] = c.iloc[399, 0] * np.linspace(1.0, 1.6, 20)
        q = dict(p)
        q['close'] = c
        q['high'] = np.maximum(p['high'], c)
        q['open'] = p['open'].copy()
        cfg = ve.Cfg(cooldown=10)
        r = ve.run(q, cfg)
        t = r['trades'][(r['trades'].ticker == j)]
        exits = t[t.kind == 'SELL_EXIT']
        for _, e in exits.iterrows():
            later = t[(t.kind == 'BUY_NEW') & (t.date > e.date)]
            if len(later):
                gap = q['close'].index.get_loc(later.date.iloc[0]) - q['close'].index.get_loc(e.date)
                self.assertGreaterEqual(gap, 1)

    def test_delisted_liquidated(self):
        p = universe()
        q = {k: v.copy() for k, v in p.items()}
        r0 = ve.run(p, ve.Cfg())
        held = r0['trades'][r0['trades'].kind == 'BUY_NEW']
        j = held.ticker.iloc[0]
        d = held.date.iloc[0]
        pos = p['close'].index.get_loc(d) + 30
        for k in ('open', 'high', 'low', 'close', 'volume'):
            q[k].loc[q[k].index[pos]:, j] = np.nan
        r = ve.run(q, ve.Cfg())
        self.assertGreaterEqual(r['cash_end'], 0)
        self.assertTrue(r['equity'].notna().sum() > 500)

    def test_band_reduces_orders(self):
        p = universe()
        a = ve.run(p, ve.Cfg(band=0.0, capital=200000, fractional=True))
        b = ve.run(p, ve.Cfg(band=0.10, capital=200000, fractional=True))
        self.assertLess(len(b['trades']), len(a['trades']))

    def test_fee_sensitivity_table(self):
        t = ve.fee_sensitivity(universe())
        self.assertEqual(list(t.fee_min), [0.35, 0.5, 1.0])
        self.assertTrue((t.orders > 0).all())


if __name__ == '__main__':
    unittest.main()
