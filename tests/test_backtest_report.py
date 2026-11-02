import unittest
from backtest_report import buy_hold_return,independent_holdout

def bar(price):
    return {'open':price,'high':price*1.01,'low':price*.99,
            'close':price,'volume':1000000}

class ReportTests(unittest.TestCase):
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
