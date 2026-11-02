import unittest
from strategy_comparison import classify

def bars(n=260):
    return [{'open':100+i*.1,'high':101+i*.1,'low':99+i*.1,
             'close':100+i*.1,'volume':1000000} for i in range(n)]

class StrategyComparisonTests(unittest.TestCase):
    def test_insufficient_history_blocks(self):
        r=classify(bars(200))
        self.assertFalse(r['minervini_proxy'])
        self.assertFalse(r['kell_proxy'])
    def test_flat_prices_do_not_trigger(self):
        x=[{'open':100,'high':101,'low':99,'close':100,'volume':1000000} for _ in range(260)]
        r=classify(x)
        self.assertFalse(r['minervini_proxy'])
        self.assertFalse(r['kell_proxy'])
    def test_output_explicitly_marks_proxy(self):
        r=classify(bars())
        self.assertIn('RS rank unavailable',r['note'])
        self.assertIn('minervini_trend',r)

if __name__=='__main__':unittest.main()
