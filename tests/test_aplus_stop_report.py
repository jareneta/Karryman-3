import unittest
from aplus_stop_report import summarize,compare_frames

class APlusComparisonTests(unittest.TestCase):
    def test_summary_empty_is_not_fabricated(self):
        result=summarize([])
        for mode in ("intraday","close_next_open"):
            self.assertEqual(result[mode]["total_trades"],0)
            self.assertIsNone(result[mode]["win_rate_pct"])
            self.assertIsNone(result[mode]["profit_factor"])
    def test_summary_uses_trade_pnl_not_symbol_returns(self):
        data=[{"intraday":{"trades":[{"pnl":10},{"pnl":-5}]},
               "close_next_open":{"trades":[{"pnl":-2}]}}]
        s=summarize(data)
        self.assertEqual(s["intraday"]["profit_factor"],2)
        self.assertEqual(s["intraday"]["mean_pnl_usd_per_trade"],2.5)
        self.assertEqual(s["close_next_open"]["win_rate_pct"],0)
        self.assertIsNone(s["close_next_open"]["profit_factor"])

if __name__=="__main__":unittest.main()
