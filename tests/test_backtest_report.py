import unittest
from backtest_report import buy_hold_return,independent_holdout,summarize

def bar(price):
    return {'open':price,'high':price*1.01,'low':price*.99,
            'close':price,'volume':1000000}

class ReportTests(unittest.TestCase):
    def test_summary_does_not_claim_portfolio_return(self):
        rows=[{'trade_count':2,'return_pct':4,'excess_vs_buy_hold_pct_points':-2,
               'holdout_30pct':{'baseline':{'trade_count':1}}},
              {'trade_count':0,'return_pct':-1,'excess_vs_buy_hold_pct_points':3,
               'holdout_30pct':None}]
        out=summarize(rows)
        self.assertEqual(out['symbols'],2)
        self.assertEqual(out['total_trades'],2)
        self.assertEqual(out['symbols_positive'],1)
        self.assertEqual(out['symbols_outperform_buy_hold'],1)
        self.assertEqual(out['holdout_symbols_with_trades'],1)
        self.assertNotIn('portfolio_return_pct',out)
    def test_buy_hold(self):
        self.assertEqual(buy_hold_return([bar(100),bar(125)]),25.0)
    def test_holdout_has_separate_equity(self):
        rows=[bar(100+i*.02) for i in range(500)]
        out=independent_holdout(rows)
        self.assertEqual(out['start_index'],350)
        self.assertEqual(out['sessions'],150)
        self.assertEqual(out['baseline']['initial_equity'],10000)
        self.assertEqual(out['baseline']['trade_count'],0)
    def test_holdout_requires_history(self):
        self.assertIsNone(independent_holdout([bar(100)]*240))

if __name__=='__main__':unittest.main()
