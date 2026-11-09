import unittest

import pandas as pd

import v24_engine as ve
import v24_h6 as h6


class H6(unittest.TestCase):
    def test_run_period_estructura_y_criterios(self):
        p = ve.synthetic_universe(n=40, T=900, seed=2)
        mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
        bench = p['close'].mean(axis=1)
        idx = p['close'].index
        r = h6.run_period(p, mem, bench, {'a': (str(idx[300].date()), str(idx[600].date())), 'b': (str(idx[601].date()), str(idx[-1].date())), 'todo': None}, 0.99, 'A')
        self.assertIn('h6', r)
        self.assertEqual(set(r['placebos']), {'a', 'b', 'todo'})
        self.assertIn('pasa', r['criterios'])
        self.assertEqual(r['h6']['todo']['avg_exposure_pct'] > 90, True)     # sin protecciones: casi siempre invertida


if __name__ == '__main__':
    unittest.main()
