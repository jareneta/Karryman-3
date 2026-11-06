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
        self.assertTrue(any('Fundamentales' in b for b in by['BBB']['blockers']))
        self.assertIn('pivote', by['AAA']['status_reason'])
        json.dumps(entries)

    def test_near_earnings_blocks_entry(self):
        from datetime import datetime, timedelta, timezone
        closes = base() + [101.0]
        vols = [1_000_000] * (len(closes) - 1) + [1_600_000]
        good = {'ticker': 'AAA', 'setup': 'BASE_6_SEMANAS', 'trend_ok': True, 'near_high_ok': True,
                'rs_vs_spy_3m_pct': 5, 'fundamental_status': 'CUMPLE'}
        soon = (datetime.now(timezone.utc).date() + timedelta(days=5)).isoformat()
        entries, _ = plan.build([good], {'AAA': frame(closes, vols)}, [], earnings_lookup=lambda t: soon)
        self.assertFalse(entries[0]['actionable'])
        self.assertEqual(entries[0]['days_to_earnings'], 5)
        self.assertIn('Resultados', entries[0]['blockers'][0])
        later = (datetime.now(timezone.utc).date() + timedelta(days=40)).isoformat()
        entries, _ = plan.build([good], {'AAA': frame(closes, vols)}, [], earnings_lookup=lambda t: later)
        self.assertTrue(entries[0]['actionable'])

    def test_recent_earnings_history_is_reported(self):
        from datetime import datetime, timedelta, timezone
        closes = base() + [101.0]
        vols = [1_000_000] * (len(closes) - 1) + [1_600_000]
        good = {'ticker': 'AAA', 'setup': 'BASE_6_SEMANAS', 'trend_ok': True, 'near_high_ok': True,
                'rs_vs_spy_3m_pct': 5, 'fundamental_status': 'CUMPLE'}
        past = (datetime.now(timezone.utc).date() - timedelta(days=8)).isoformat()
        entries, _ = plan.build([good], {'AAA': frame(closes, vols)}, [],
                                earnings_lookup=lambda t: {'next': None, 'last': past})
        self.assertEqual(entries[0]['last_earnings_date'], past)
        self.assertTrue(entries[0]['actionable'])
        self.assertTrue(any('Publicó resultados' in w for w in entries[0]['warnings']))

    def test_as_date(self):
        import pandas as pd
        self.assertEqual(plan._as_date(pd.Timestamp('2026-11-12 16:00', tz='America/New_York')).isoformat(), '2026-11-12')
        self.assertEqual(plan._as_date('2026-11-12').isoformat(), '2026-11-12')
        self.assertIsNone(plan._as_date(None))

    def test_every_status_has_reason(self):
        for closes, vols in [(base(), None), (base() + [101.0, 108.0], [1_000_000] * 120 + [1_600_000, 900_000]),
                             (base() + [101.0, 97.0], [1_000_000] * 120 + [1_600_000, 900_000])]:
            p = trade_levels.entry_plan(frame(closes, vols), 'BASE')
            self.assertTrue(p['status_reason'], p)

    def test_tracked_parse_rejects_junk(self):
        self.assertEqual(tracked.parse('aapl, msft;  ../x 123 brk.b'), ['AAPL', 'BRK.B', 'MSFT'])


if __name__ == '__main__':
    unittest.main()


class PlanMainTests(unittest.TestCase):
    def test_main_end_to_end_offline(self):
        import tempfile
        from unittest import mock
        closes = base() + [101.0]
        vols = [1_000_000] * (len(closes) - 1) + [1_600_000]
        f = frame(closes, vols)
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            good = {'ticker': 'AAA', 'setup': 'BASE_6_SEMANAS', 'trend_ok': True, 'near_high_ok': True,
                    'rs_vs_spy_3m_pct': 5, 'fundamental_status': 'CUMPLE'}
            (data / 'setups.json').write_text(json.dumps({'generated_utc': 'x', 'candidates': [good]}))
            (data / 'tracked.json').write_text(json.dumps({'tickers': ['POS']}))
            (data / 'discovery.json').write_text(json.dumps({'scanned_this_run': 10, 'filter_counts': {
                'pasa filtro técnico': 2, 'precio/liquidez': 8}, 'candidates': [
                {'ticker': 'DIV', 'close': 50, 'avg_volume': 1e6, 'market_cap': 1e9, 'dividend_yield': 2}]}))
            with mock.patch.object(plan, 'DATA', data), mock.patch.object(plan, 'OUT', data / 'plan.json'), \
                    mock.patch.object(plan, 'download', return_value=({'AAA': f, 'POS': f}, [])), \
                    mock.patch.object(plan, 'earnings_info', return_value={'next': None, 'last': None}):
                plan.main()
            out = json.loads((data / 'plan.json').read_text())
        self.assertEqual(out['entries_count'], 1)
        self.assertIn('POS', out['quotes'])
        self.assertFalse(out['orders_enabled'])
        self.assertEqual(out['funnel']['discovery_filter_counts'], {'precio/liquidez': 8})
        self.assertIn('paga dividendo', out['funnel']['screener_discards'][0]['reasons'])
