import unittest
from backtest import run,Config

def row(o=100,h=101,l=99,c=100,v=1000000):
    return {'open':o,'high':h,'low':l,'close':c,'volume':v}

class BacktestTests(unittest.TestCase):
    def test_no_trade_on_flat_prices(self):
        result=run([row() for _ in range(240)])
        self.assertEqual(result['trade_count'],0)
        self.assertEqual(result['final_equity'],10000)
    def test_signal_uses_previous_close_and_next_open(self):
        bars=[row(o=100+i*.1,h=101+i*.1,l=99+i*.1,c=100+i*.1) for i in range(201)]
        bars[200]=row(o=125,h=128,l=124,c=127,v=2000000)
        bars.append(row(o=130,h=131,l=129,c=130))
        bars.extend(row(o=130,h=132,l=128,c=130) for _ in range(21))
        result=run(bars)
        self.assertGreaterEqual(result['trade_count'],1)
        trade=result['trades'][0]
        self.assertEqual(trade['entry_index'],201)
        self.assertGreater(trade['entry'],130)
    def test_entry_day_stop_is_not_ignored(self):
        bars=[row(o=100+i*.1,h=101+i*.1,l=99+i*.1,c=100+i*.1) for i in range(201)]
        bars[200]=row(o=125,h=128,l=124,c=127,v=2000000)
        # Open above the breakout, then sell off through the calculated stop.
        bars.append(row(o=130,h=135,l=118,c=125))
        bars.extend(row(o=130,h=131,l=129,c=130) for _ in range(3))
        result=run(bars)
        self.assertGreaterEqual(result['trade_count'],1)
        trade=result['trades'][0]
        self.assertEqual(trade['entry_index'],201)
        self.assertEqual(trade['exit_index'],201)
        self.assertEqual(trade['exit_reason'],'entry_day_stop')
        self.assertLess(trade['pnl'],0)
    def test_no_same_day_reentry_after_exit(self):
        bars=[row(o=100+i*.1,h=101+i*.1,l=99+i*.1,c=100+i*.1) for i in range(201)]
        bars[200]=row(o=125,h=128,l=124,c=127,v=2000000)
        bars.append(row(o=130,h=135,l=118,c=125))
        result=run(bars)
        self.assertEqual(result['trade_count'],1)
    def test_bad_ohlcv_rejected(self):
        with self.assertRaises(ValueError):run([row(l=102)])
    def test_risk_over_one_percent_rejected(self):
        with self.assertRaises(ValueError):run([],Config(risk_fraction=.05))

if __name__=='__main__':unittest.main()
