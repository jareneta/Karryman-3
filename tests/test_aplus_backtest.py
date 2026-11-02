import unittest
from unittest.mock import patch
import pandas as pd
from aplus_backtest import run_aplus
from backtest import Config

def prices(n=260):
    idx=pd.date_range('2024-01-01',periods=n,freq='B')
    return pd.DataFrame({'Open':[100.]*n,'High':[102.]*n,
                         'Low':[98.]*n,'Close':[100.]*n,'Volume':[1000000.]*n},index=idx)

class APlusResearchTests(unittest.TestCase):
    def test_no_signals_no_trades(self):
        frame=prices()
        with patch('aplus_backtest.calculate',return_value=None):
            result=run_aplus(frame,frame.Close)
        self.assertEqual(result['trade_count'],0)
        self.assertEqual(result['final_equity'],10000)
    def test_signal_uses_only_history_and_fills_next_open(self):
        frame=prices()
        observed=[]
        def signal(t,hist,spy):
            observed.append((len(hist),len(spy)))
            return {'technical_a_plus':True,'status':'CONFIRMADA',
                    'stop_reference':95,'setup':'PULLBACK_EMA20'} if len(hist)==253 else None
        with patch('aplus_backtest.calculate',side_effect=signal):
            result=run_aplus(frame,frame.Close)
        self.assertEqual(result['trade_count'],1)
        self.assertEqual(result['trades'][0]['signal_index'],252)
        self.assertEqual(result['trades'][0]['entry_index'],253)
        self.assertTrue(all(a==b for a,b in observed))
    def test_invalid_risk_rejected(self):
        with self.assertRaises(ValueError):
            run_aplus(prices(),prices().Close,Config(risk_fraction=.05))

if __name__=='__main__':unittest.main()
