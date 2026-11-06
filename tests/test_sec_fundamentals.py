import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sec_fundamentals as sf  # noqa: E402


def fact(start, end, val, filed):
    return {'start': start, 'end': end, 'val': val, 'filed': filed, 'form': '10-Q'}


def companyfacts():
    # Ingresos: año 2022 trimestral 100, 100, 100 y anual 440 (-> Q4 = 440 - 300 = 140); 2023 crece un 30%
    rev = [fact('2022-01-01', '2022-03-31', 100, '2022-05-01'), fact('2022-04-01', '2022-06-30', 100, '2022-08-01'),
           fact('2022-07-01', '2022-09-30', 100, '2022-11-01'), fact('2022-01-01', '2022-09-30', 300, '2022-11-01'),
           fact('2022-01-01', '2022-12-31', 440, '2023-02-20'),
           fact('2023-01-01', '2023-03-31', 130, '2023-05-01'), fact('2023-04-01', '2023-06-30', 140, '2023-08-01'),
           fact('2023-07-01', '2023-09-30', 160, '2023-11-01'), fact('2023-01-01', '2023-09-30', 430, '2023-11-01'),
           # reexpresión posterior del Q1 2023 (no debe usarse: se toma el primer valor presentado)
           {'start': '2023-01-01', 'end': '2023-03-31', 'val': 999, 'filed': '2024-05-01', 'form': '10-Q'}]
    eps = [fact('2022-01-01', '2022-03-31', 1.0, '2022-05-01'), fact('2022-04-01', '2022-06-30', 1.0, '2022-08-01'),
           fact('2022-07-01', '2022-09-30', 1.0, '2022-11-01'), fact('2022-01-01', '2022-09-30', 3.0, '2022-11-01'),
           fact('2022-01-01', '2022-12-31', 4.0, '2023-02-20'),
           fact('2023-01-01', '2023-03-31', 1.3, '2023-05-01'), fact('2023-04-01', '2023-06-30', 1.6, '2023-08-01'),
           fact('2023-07-01', '2023-09-30', 2.0, '2023-11-01')]
    return {'facts': {'us-gaap': {'Revenues': {'units': {'USD': rev}},
                                  'EarningsPerShareDiluted': {'units': {'USD/shares': eps}}}}}


class SecTests(unittest.TestCase):
    def test_parse_and_q4(self):
        rows = {r['end']: r for r in sf.parse_companyfacts(companyfacts())}
        self.assertEqual(rows['2022-12-31']['rev'], 140)       # Q4 derivado: 440 - 300
        self.assertEqual(rows['2022-12-31']['rev_filed'], '2023-02-20')
        self.assertEqual(rows['2023-03-31']['rev'], 130)       # primer valor presentado, no el reexpresado
        self.assertAlmostEqual(rows['2022-12-31']['eps'], 1.0)

    def test_growth_and_acceleration(self):
        rows = sf.parse_companyfacts(companyfacts())
        g = {f: (a, b) for f, a, b in sf.growth_points(rows, 'rev')}
        self.assertAlmostEqual(g['2023-05-01'][0], 0.30)       # 130/100 - 1
        self.assertAlmostEqual(g['2023-08-01'][0], 0.40)
        self.assertAlmostEqual(g['2023-08-01'][1], 0.30)       # g previo
        eg = {f: a for f, a, b in sf.growth_points(rows, 'eps', eps=True)}
        self.assertAlmostEqual(eg['2023-11-01'], 1.0)

    def test_point_in_time_alignment(self):
        rows = sf.parse_companyfacts(companyfacts())
        idx = pd.bdate_range('2023-04-01', '2024-03-29')
        fl, cov = sf.daily_flags(rows, idx)
        pos = lambda d: idx.get_loc(pd.Timestamp(d))
        # antes de presentar el 2.º trimestre (2023-08-01) la aceleración no puede conocerse
        self.assertFalse(fl['Ingresos +20% y aceleran'][pos('2023-07-31')])
        self.assertTrue(fl['Ingresos +20% y aceleran'][pos('2023-08-03')])     # +40% tras +30%
        self.assertTrue(fl['EPS +25% y acelera'][pos('2023-08-03')])
        self.assertTrue(cov[pos('2023-08-03')])
        # los datos caducan: sin presentaciones nuevas, tras 140 días no hay cobertura
        self.assertFalse(cov[pos('2024-03-28')])

    def test_turnaround_and_negative(self):
        rows = [{'end': '2022-03-31', 'eps': -0.5, 'eps_filed': '2022-05-01', 'rev': None, 'rev_filed': None},
                {'end': '2023-03-31', 'eps': 0.2, 'eps_filed': '2023-05-01', 'rev': None, 'rev_filed': None},
                {'end': '2024-03-31', 'eps': -0.1, 'eps_filed': '2024-05-01', 'rev': None, 'rev_filed': None},
                {'end': '2025-03-31', 'eps': -0.3, 'eps_filed': '2025-05-01', 'rev': None, 'rev_filed': None}]
        g = [a for _, a, _ in sf.growth_points(rows, 'eps', eps=True)]
        self.assertEqual(g[1], 9.99)   # de pérdidas a beneficios
        self.assertAlmostEqual(g[2], -1.5)   # de +0,2 a -0,1: cae un 150%
        self.assertEqual(g[3], -1.0)   # pérdidas sobre pérdidas


if __name__ == '__main__':
    unittest.main()
