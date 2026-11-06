import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan  # noqa: E402
import tracked  # noqa: E402
import trade_levels  # noqa: E402


def frame(closes, volumes=None, spread=0.5):
    closes = np.asarray(closes, dtype=float)
    idx = pd.bdate_range('2026-01-01', periods=len(closes))
    vol = np.full(len(closes), 1_000_000.0) if volumes is None else np.asarray(volumes, dtype=float)
    return pd.DataFrame({'Open': closes, 'High': closes + spread, 'Low': closes - spread,
                         'Close': closes, 'Volume': vol}, index=idx)


def base(n=120, level=100.0):
    up = np.linspace(70, level - 8, n - 30)
    flat = level - 3 + np.sin(np.arange(30)) * 1.5  # base de 30 sesiones bajo ~100
    return list(up) + list(flat)


class EntryPlanTests(unittest.TestCase):
    def test_waiting_below_pivot(self):
        p = trade_levels.entry_plan(frame(base()), 'BASE_6_SEMANAS')
        self.assertEqual(p['entry_status'], 'ESPERANDO')
        self.assertGreater(p['pivot'], p['close'])
        self.assertLess(p['stop_reference'], p['pivot'])
        self.assertAlmostEqual(p['target_2r'], p['entry_reference'] + 2 * p['risk_per_share'], places=1)

    def test_close_over_pivot_with_volume_activates(self):
        closes = base() + [101.0]
        vols = [1_000_000] * (len(closes) - 1) + [1_600_000]
        p = trade_levels.entry_plan(frame(closes, vols), 'BASE_6_SEMANAS')
        self.assertEqual(p['entry_status'], 'ACTIVADA')
        self.assertEqual(p['sessions_since_trigger'], 0)
        self.assertEqual(p['max_entry_price'], round(p['pivot'] * 1.05, 2))

    def test_breakout_without_volume_does_not_activate(self):
        closes = base() + [101.0]
        p = trade_levels.entry_plan(frame(closes), 'BASE_6_SEMANAS')
        self.assertNotEqual(p['entry_status'], 'ACTIVADA')

    def test_extended_and_failed(self):
        closes = base() + [101.0, 108.0]
        vols = [1_000_000] * (len(closes) - 2) + [1_600_000, 900_000]
        self.assertEqual(trade_levels.entry_plan(frame(closes, vols), 'BASE')['entry_status'], 'EXTENDIDA')
        closes = base() + [101.0, 97.0]
        self.assertEqual(trade_levels.entry_plan(frame(closes, vols), 'BASE')['entry_status'], 'FALLIDA')

    def test_short_history(self):
        self.assertEqual(trade_levels.entry_plan(frame([10] * 30))['entry_status'], 'SIN_DATOS')

    def test_quote_has_bars(self):
        q = trade_levels.quote(frame(base()), history=10)
        self.assertEqual(len(q['bars']), 10)
        self.assertIn('ema20', q)


class PlanBuildTests(unittest.TestCase):
    def test_build_marks_actionable_only_with_criteria(self):
        closes = base() + [101.0]
        vols = [1_000_000] * (len(closes) - 1) + [1_600_000]
        f = frame(closes, vols)
        good = {'ticker': 'AAA', 'setup': 'BASE_6_SEMANAS', 'trend_ok': True, 'near_high_ok': True,
                'rs_vs_spy_3m_pct': 5, 'fundamental_status': 'CUMPLE'}
        weak = {**good, 'ticker': 'BBB', 'fundamental_status': 'NO_VERIFICADO'}
        entries, quotes = plan.build([good, weak], {'AAA': f, 'BBB': f, 'POS': f}, ['POS'])
        by = {e['ticker']: e for e in entries}
        self.assertTrue(by['AAA']['actionable'])
        self.assertFalse(by['BBB']['actionable'])
        self.assertFalse(by['AAA']['order_enabled'])
        self.assertEqual(set(quotes), {'AAA', 'BBB', 'POS'})
        json.dumps(entries)

    def test_tracked_parse_rejects_junk(self):
        self.assertEqual(tracked.parse('aapl, msft;  ../x 123 brk.b'), ['AAPL', 'BRK.B', 'MSFT'])


if __name__ == '__main__':
    unittest.main()
