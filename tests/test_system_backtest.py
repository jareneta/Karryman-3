import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import system_backtest as sb  # noqa: E402


def make(closes, vols=None, spread=0.5, start='2020-01-01'):
    closes = np.asarray(closes, float)
    idx = pd.bdate_range(start, periods=len(closes))
    v = np.full(len(closes), 1_000_000.0) if vols is None else np.asarray(vols, float)
    return pd.DataFrame({'Open': closes, 'High': closes + spread, 'Low': closes - spread, 'Close': closes, 'Volume': v}, index=idx)


def uptrend_with_base(n_up=260, n_base=30):
    up = list(np.linspace(40, 100, n_up))
    base = [97 + 1.5 * np.sin(k) for k in range(n_base)]
    return up + base


class BacktestRules(unittest.TestCase):
    def setUp(self):
        self.spy = make(np.linspace(100, 110, 400)).Close  # SPY casi plano -> RS positiva

    def breakout_frame(self, after):
        closes = uptrend_with_base() + [101.0] + after
        vols = [1_000_000] * (len(closes) - len(after) - 1) + [2_000_000] + [1_000_000] * len(after)
        return sb.prepare(make(closes, vols), self.spy)

    def test_signal_and_no_lookahead(self):
        d1 = self.breakout_frame([101.0] * 5)
        d2 = self.breakout_frame([50.0] * 5)  # futuro distinto, misma señal
        s1 = sb.signals(d1, sb.Config(), sb.regime_series(make(np.linspace(100, 110, 400))))
        s2 = sb.signals(d2, sb.Config(), sb.regime_series(make(np.linspace(100, 110, 400))))
        self.assertTrue(any(k == 'ruptura' for _, k, *_ in s1))
        self.assertEqual([x[:4] for x in s1 if x[1] == 'ruptura'], [x[:4] for x in s2 if x[1] == 'ruptura'])

    def run_one(self, d, cfg=sb.Config()):
        sig = [x for x in sb.signals(d, cfg, sb.regime_series(make(np.linspace(100, 110, 400)))) if x[1] == 'ruptura'][0]
        t = sb.open_trade(d, 'X', sig, cfg)
        self.assertIsNotNone(t)
        for j in range(t.entry_i, len(d)):
            if sb.step(t, d, j, cfg):
                break
        return t, sb.finish(t, d)

    def test_stop_by_close_loses_about_1R(self):
        d = self.breakout_frame([101.0, 99.0, 90.0, 89.0, 88.0])
        t, r = self.run_one(d)
        # entra a 101 (+coste); cierra bajo el stop y sale a la apertura siguiente (89): pérdida > 1R por el hueco
        self.assertLess(r, -0.9)
        self.assertFalse(t.partial)

    def test_partial_at_2R_then_runner_trailing(self):
        d0 = self.breakout_frame([101.0])
        stop = float(d0.low10.iloc[-2])
        R = 101.0 * (1 + sb.COST) - stop
        path = [101.0, 101.0 + R * 0.5, 101.0 + R * 2.2, 101.0 + R * 3.0, 101.0 + R * 3.2] + [101.0 + R * 3.2 - 2 * k for k in range(1, 25)]
        d = self.breakout_frame(path)
        t, r = self.run_one(d)
        self.assertTrue(t.partial)
        self.assertGreater(r, 1.0)  # 1/3 a 2R + runner con ganancia
        self.assertAlmostEqual(t.fills[0][1], 1 / 3)

    def test_all_at_2R_variant(self):
        d0 = self.breakout_frame([101.0])
        stop = float(d0.low10.iloc[-2])
        R = 101.0 * (1 + sb.COST) - stop
        d = self.breakout_frame([101.0, 101.0 + R * 2 - 0.3, 101.0 + R * 2 - 0.3])
        t, r = self.run_one(d, sb.Config(partial_frac=1.0))
        self.assertAlmostEqual(r, 2.0, delta=0.1)

    def test_portfolio_smoke(self):
        d = self.breakout_frame([101.0 + k for k in range(30)])
        eq, n = sb.simulate_portfolio({'X': d}, sb.Config(), sb.regime_series(make(np.linspace(100, 110, 400))),
                                      d.index[0], d.index[-1])
        self.assertEqual(n, 1)
        self.assertGreater(eq.iloc[-1], 1.0)
        self.assertLessEqual(eq.max(), 1.5)

    def test_weekly_ma50_runner(self):
        # Subida larga y luego caída fuerte: el cierre semanal pierde la media de 50 semanas.
        closes = list(np.linspace(20, 100, 400)) + list(np.linspace(100, 40, 120))
        d = sb.prepare(make(closes), make(np.linspace(100, 110, 600)).Close)
        exits = np.flatnonzero(d.attrs['a']['w50_exit'] > 0)
        self.assertTrue(len(exits) > 0)
        self.assertTrue(all(i > 400 for i in exits))
        # Solo se marca el último día de cada semana
        self.assertTrue(all(d.index[i].weekday() == 4 or i == len(d) - 1 or d.index[i + 1].weekday() < d.index[i].weekday() for i in exits))

    def test_portfolio_exposure_and_sweep(self):
        d = self.breakout_frame([101.0 + k for k in range(30)])
        spy = pd.Series(np.linspace(100, 120, len(d)), index=d.index)
        reg = sb.regime_series(make(np.linspace(100, 110, 400)))
        eq, n, ex = sb.simulate_portfolio({'X': d}, sb.Config(), reg, d.index[0], d.index[-1],
                                          spy_close=spy, with_exposure=True)
        self.assertTrue(0 <= ex.max() <= 1)
        eq2, _, _ = sb.simulate_portfolio({'X': d}, sb.Config(), reg, d.index[0], d.index[-1],
                                          spy_close=spy, sweep=True, with_exposure=True)
        self.assertGreater(eq2.iloc[-1], eq.iloc[-1])  # el efectivo invertido en un SPY que sube suma
        self.assertEqual(sb.yearly(pd.Series([1.0, 1.1, 1.21], index=pd.to_datetime(['2020-01-02', '2020-12-31', '2021-12-31']))),
                         {'2020': 10.0, '2021': 10.0})

    def vcp_frame(self, after, vol_break=2_000_000):
        up = list(np.linspace(40, 100, 230))
        base = list(np.linspace(99, 86, 12)) + list(np.linspace(86, 96, 10)) + [97.5, 97.0, 97.8, 97.2, 97.6, 97.4, 97.9, 97.3, 97.7, 97.5]
        closes = up + base + [101.0] + after
        vols = [1_000_000] * (len(up) + len(base)) + [vol_break] + [1_000_000] * len(after)
        return sb.prepare(make(closes, vols), make(np.linspace(100, 110, 600)).Close)

    def test_vcp_base_signal(self):
        d = self.vcp_frame([101.0] * 3)
        reg = sb.regime_series(make(np.linspace(100, 110, 600)))
        cfg = sb.Config(pullback=False, entry='base')
        sig = sb.signals(d, cfg, reg)
        self.assertEqual(len(sig), 1)
        i, kind, pivot, stop, rs = sig[0]
        self.assertEqual(kind, 'base')
        self.assertEqual(i, 262)
        self.assertGreaterEqual(d.base_len.iloc[i], 25)
        # Sin volumen no hay señal
        self.assertEqual(sb.signals(self.vcp_frame([101.0] * 3, vol_break=1_000_000), cfg, reg), [])

    def test_climax_exit(self):
        jump = [101.0, 104.0] + [104.0 * 1.04 ** k for k in range(1, 15)]
        d = self.vcp_frame(jump)
        reg = sb.regime_series(make(np.linspace(100, 110, 600)))
        cfg = sb.Config(pullback=False, entry='base', partial_r=2.0, partial_frac=0.5, trail='w50', climax_ext=0.40)
        t = sb.open_trade(d, 'X', sb.signals(d, cfg, reg)[0], cfg)
        for j in range(t.entry_i, len(d)):
            if sb.step(t, d, j, cfg):
                break
        sb.finish(t, d)
        self.assertTrue(t.partial)
        self.assertTrue(t.climax)

    def test_stats(self):
        df = pd.DataFrame({'r': [2.0, -1.0, -1.0, 3.0], 'days': [5, 3, 2, 10], 'partial': [True, False, False, True]})
        s = sb.r_stats(df)
        self.assertEqual(s['expectancy_R'], 0.75)
        self.assertEqual(s['profit_factor'], 2.5)


if __name__ == '__main__':
    unittest.main()
