import unittest

import numpy as np
import pandas as pd

import v24_backtest as vb
import v24_engine as ve


def make():
    idx = pd.bdate_range('2009-06-01', periods=400)
    rows, mem = [], []
    for k, t in enumerate(['AAA', 'BBB', 'DEAD', 'SPY']):
        end = len(idx) if t != 'DEAD' else 250          # DEAD desaparece del conjunto
        c = 50 * np.exp(np.cumsum(np.random.default_rng(k).normal(0.0005, 0.01, end)))
        for i in range(end):
            f = 0.5 if (t == 'AAA' and i < 100) else 1.0   # factor de ajuste de dividendos: adj_close = close * f
            rows.append((idx[i], t, c[i], c[i] * 1.01, c[i] * 0.99, c[i], 1e6, c[i] * f, 0.0, 0.0, 'yahoo'))
            if t != 'SPY':
                mem.append((idx[i], t))
    return (pd.DataFrame(rows, columns=['date', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'dividends', 'stock_splits', 'source']),
            pd.DataFrame(mem, columns=['date', 'ticker']))


class Cargador(unittest.TestCase):
    def test_ajuste_pertenencia_y_deslistadas(self):
        p, m = make()
        w, mem, bench, info = vb.build_universe(p, m, start='2009-06-01')
        self.assertNotIn('SPY', w['close'].columns)                       # el benchmark no entra en el universo
        self.assertGreater(len(bench), 300)
        self.assertIn('DEAD', w['close'].columns)                         # la deslistada se conserva
        self.assertTrue(w['close']['DEAD'].iloc[260:].isna().all())       # y deja de tener precio
        self.assertFalse(mem['DEAD'].iloc[260:].any())
        # ajuste: close ajustado = adj_close; open/high/low se escalan con adj_close/close
        ratio = (w['high']['AAA'] / w['close']['AAA']).dropna()
        np.testing.assert_allclose(ratio, 1.01, rtol=1e-9)
        a0 = p[(p.ticker == 'AAA')].sort_values('date').iloc[0]
        self.assertAlmostEqual(w['close']['AAA'].dropna().iloc[0], a0.adj_close, places=9)
        self.assertAlmostEqual(w['open']['AAA'].dropna().iloc[0], a0.open * 0.5, places=9)   # factor 0,5 de ajuste
        self.assertEqual(info['series'], 3)

    def test_motor_corre_con_deslistadas_sin_bloqueo(self):
        p, m = make()
        w, mem, bench, _ = vb.build_universe(p, m)
        r = ve.run(w, ve.Cfg(top_in=2, top_out=3, max_pos=2, capital=10000), mem)
        self.assertGreaterEqual(r['cash_end'], 0)
        self.assertTrue((r['equity'].dropna() > 0).all())
        self.assertGreater(len(r['trades']), 0)


if __name__ == '__main__':
    unittest.main()
