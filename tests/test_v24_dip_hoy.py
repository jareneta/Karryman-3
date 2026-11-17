import unittest

import numpy as np
import pandas as pd

import system_backtest as sb
import v24_dip as dip
import v24_dip_hoy as hoy
from tests.test_v24_dip import build


class Hoy(unittest.TestCase):
    def test_scan_coincide_con_la_senal_de_los_backtests(self):
        p, prep, reg = build(n=60, T=1500)
        res = hoy.scan(prep, reg, last_n=60)
        ref = [(tk, s[0]) for tk, d in prep.items() for s in sb.signals(d, dip.CFG, reg) if s[0] >= len(d) - 60]
        self.assertEqual(sorted((tk, i) for tk, i, _ in res), sorted(ref))
        for tk, i, ago in res:
            self.assertEqual(ago, len(prep[tk]) - 1 - i)

    def test_describe_campos(self):
        p, prep, reg = build(n=60, T=1500)
        res = hoy.scan(prep, reg, last_n=300)
        self.assertGreater(len(res), 0)
        tk, i, _ = res[0]
        r = hoy.describe(tk, prep[tk], i, True)
        self.assertTrue(-35.0 - 1e-6 <= r['caida_vs_max60_pct'] <= -15.0 + 1e-6)
        self.assertGreater(r['sobre_sma200_pct'], 0)
        self.assertAlmostEqual(r['stop_12pct_sobre_ultimo_cierre'], round(float(prep[tk].Close.iloc[-1] * 0.88), 2), places=2)


if __name__ == '__main__':
    unittest.main()
