"""Offline regression tests for screener. Run: python -m unittest discover -s tests."""
import unittest
import json
import tempfile
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import screener
from screener import evaluate

def candidate(**kwargs):
    x=dict(ticker="TEST",close=40,avg_volume=900000,market_cap=1e9,
        return_3m_pct=15,return_6m_pct=18,return_12m_pct=24,
        distance_high_pct=8,ma20=37,ma50=35,ma200=30,
        revenue_growth_pct=18,quarterly_revenue_growth_pct=16,
        eps_ttm=1,dividend_yield=0,finviz_proxy=False,score_preliminar=50)
    x.update(kwargs)
    return x

class ScreenerTests(unittest.TestCase):
    def test_missing_data_never_passes(self):
        x=evaluate(candidate(quarterly_revenue_growth_pct=None))
        self.assertEqual(x["stock_analysis_status"],"PENDIENTE_VERIFICACION")
        self.assertIn("quarterly_revenue_growth_over_10",x["unverified"])
    def test_bad_growth_excluded(self):
        x=evaluate(candidate(revenue_growth_pct=5))
        self.assertEqual(x["stock_analysis_status"],"DESCARTADA")
    def test_price_below_ma20_excluded(self):
        x=evaluate(candidate(ma20=41))
        self.assertEqual(x["stock_analysis_status"],"DESCARTADA")
    def test_finviz_does_not_override_rejection(self):
        x=evaluate(candidate(revenue_growth_pct=2,finviz_proxy=True))
        self.assertTrue(x["finviz_complement"])
        self.assertEqual(x["stock_analysis_status"],"DESCARTADA")
    def test_end_to_end_public_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"discovery.json").write_text(json.dumps({"generated_utc":"2026-11-02T00:00:00+00:00","scanned_this_run":2,"candidates":[candidate(),candidate(ticker="FAIL",revenue_growth_pct=2)]}),encoding="utf-8")
            with patch.object(screener,"DATA",root):
                screener.main()
            output=json.loads((root/"screener.json").read_text(encoding="utf-8"))
            self.assertEqual(output["primary_candidates"],1)
            self.assertEqual(output["candidates"][0]["ticker"],"TEST")
            self.assertFalse(output["orders_enabled"])
    def test_no_orders(self):
        self.assertFalse(evaluate(candidate())["order_enabled"])
if __name__=="__main__":unittest.main()
