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


def fact_ytd(start, end, val, filed):
    return {'start': start, 'end': end, 'val': val, 'filed': filed}


def inst(end, val, filed):
    return {'end': end, 'val': val, 'filed': filed}


def companyfacts_full():
    """2 años: ingresos 100->130 (+30%), margen bruto 40->45%, operativo -10%->+5%, BPA pasa de -0.2 a +0.1,
    caja operativa solo acumulada (YTD) y balance."""
    g = {}
    def put(tag, unit, entries):
        g.setdefault(tag, {'units': {}})['units'].setdefault(unit, []).extend(entries)
    q22 = [('2022-01-01', '2022-03-31', '2022-05-01'), ('2022-04-01', '2022-06-30', '2022-08-01'), ('2022-07-01', '2022-09-30', '2022-11-01')]
    q23 = [('2023-01-01', '2023-03-31', '2023-05-01'), ('2023-04-01', '2023-06-30', '2023-08-01'), ('2023-07-01', '2023-09-30', '2023-11-01')]
    put('Revenues', 'USD', [fact(s, e, 100, f) for s, e, f in q22] + [fact('2022-01-01', '2022-12-31', 400, '2023-02-20')] + [fact(s, e, 130, f) for s, e, f in q23])
    put('GrossProfit', 'USD', [fact(s, e, 40, f) for s, e, f in q22] + [fact('2022-01-01', '2022-12-31', 160, '2023-02-20')] + [fact(s, e, 58.5, f) for s, e, f in q23])
    put('OperatingIncomeLoss', 'USD', [fact(s, e, -10, f) for s, e, f in q22] + [fact('2022-01-01', '2022-12-31', -40, '2023-02-20')] + [fact(s, e, 6.5, f) for s, e, f in q23])
    put('EarningsPerShareDiluted', 'USD/shares', [fact(s, e, -0.2, f) for s, e, f in q22] + [fact('2022-01-01', '2022-12-31', -0.8, '2023-02-20')] + [fact(s, e, 0.1, f) for s, e, f in q23])
    put('NetIncomeLoss', 'USD', [fact(s, e, -12, f) for s, e, f in q22] + [fact('2022-01-01', '2022-12-31', -48, '2023-02-20')] + [fact(s, e, 8, f) for s, e, f in q23])
    # caja operativa: solo el primer trimestre y acumulados de 6/9/12 meses
    put('NetCashProvidedByUsedInOperatingActivities', 'USD', [
        fact_ytd('2022-01-01', '2022-03-31', 5, '2022-05-01'), fact_ytd('2022-01-01', '2022-06-30', 12, '2022-08-01'),
        fact_ytd('2022-01-01', '2022-09-30', 21, '2022-11-01'), fact_ytd('2022-01-01', '2022-12-31', 30, '2023-02-20'),
        fact_ytd('2023-01-01', '2023-03-31', 10, '2023-05-01'), fact_ytd('2023-01-01', '2023-06-30', 22, '2023-08-01'),
        fact_ytd('2023-01-01', '2023-09-30', 36, '2023-11-01')])
    put('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', [fact(s, e, 60, f) for s, e, f in q22] + [fact(s, e, 66, f) for s, e, f in q23])
    put('Assets', 'USD', [inst('2022-12-31', 1000, '2023-02-20'), inst('2023-09-30', 1200, '2023-11-01')])
    put('Liabilities', 'USD', [inst('2022-12-31', 600, '2023-02-20'), inst('2023-09-30', 480, '2023-11-01')])
    put('StockholdersEquity', 'USD', [inst('2022-12-31', 400, '2023-02-20'), inst('2023-09-30', 720, '2023-11-01')])
    return {'facts': {'us-gaap': g}}


class ExtendedFeatureTests(unittest.TestCase):
    def test_cumulative_cash_flow_becomes_quarterly(self):
        rows = {r['end']: r for r in sf.parse_companyfacts(companyfacts_full())}
        self.assertEqual(rows['2022-03-31']['cfo'], 5)
        self.assertEqual(rows['2022-06-30']['cfo'], 7)     # 12 - 5
        self.assertEqual(rows['2022-09-30']['cfo'], 9)     # 21 - 12
        self.assertEqual(rows['2022-12-31']['cfo'], 9)     # 30 - 21
        self.assertEqual(rows['2023-09-30']['cfo'], 14)    # 36 - 22
        self.assertEqual(rows['2022-12-31']['rev'], 100)   # 400 - 300 (Q4 derivado)
        self.assertEqual(rows['2023-09-30']['equity'], 720)

    def test_quarter_features(self):
        qt = sf.quarter_table(sf.parse_companyfacts(companyfacts_full())).set_index('end')
        r = qt.loc['2023-09-30']
        self.assertAlmostEqual(r['rev_yoy'], 0.30)
        self.assertAlmostEqual(r['gm'], 0.45)
        self.assertAlmostEqual(r['gm_chg'], 5.0)            # 40% -> 45%
        self.assertAlmostEqual(r['om'], 0.05)
        self.assertAlmostEqual(r['om_chg'], 15.0)           # -10% -> +5%
        self.assertEqual(r['oi_turn'], 1.0)
        self.assertEqual(r['eps_turn'], 1.0)                # de -0.2 a +0.1: giro a beneficios
        self.assertEqual(r['eps_neg'], 0.0)
        self.assertEqual(r['eps_g25'], 0.0)                 # no es "crecimiento" de beneficio previo positivo
        self.assertAlmostEqual(r['dil_chg'], 0.10)
        self.assertEqual(r['equity_pos'], 1.0)
        self.assertAlmostEqual(r['lev'], 0.4)
        self.assertEqual(r['ev_eps_turn'], 0.0)            # no es el primer trimestre rentable (ya lo fue el 2.º)
        self.assertEqual(qt.loc['2023-03-31', 'ev_eps_turn'], 1.0)   # sí: primer BPA positivo tras pérdidas
        # un año antes: pérdidas
        r0 = qt.loc['2022-09-30']
        self.assertEqual(r0['eps_neg'], 1.0)
        self.assertEqual(r0['eps_turn'], 0.0)

    def test_eps_segments_are_exclusive(self):
        rows = [{'end': '2022-03-31', 'eps': 1.0, 'eps_filed': '2022-05-01'}, {'end': '2023-03-31', 'eps': 1.5, 'eps_filed': '2023-05-01'},
                {'end': '2024-03-31', 'eps': 1.6, 'eps_filed': '2024-05-01'}, {'end': '2025-03-31', 'eps': 1.0, 'eps_filed': '2025-05-01'},
                {'end': '2026-03-31', 'eps': -0.5, 'eps_filed': '2026-05-01'}]
        qt = sf.quarter_table(rows).set_index('end')
        seg = ['eps_neg', 'eps_turn', 'eps_g25', 'eps_low', 'eps_fall']
        self.assertEqual(qt.loc['2023-03-31', seg].tolist(), [0, 0, 1, 0, 0])   # +50%
        self.assertEqual(qt.loc['2024-03-31', seg].tolist(), [0, 0, 0, 1, 0])   # +6.7%
        self.assertEqual(qt.loc['2025-03-31', seg].tolist(), [0, 0, 0, 0, 1])   # cae
        self.assertEqual(qt.loc['2026-03-31', seg].tolist(), [1, 0, 0, 0, 0])   # pérdidas

    def test_daily_features_point_in_time(self):
        rows = sf.parse_companyfacts(companyfacts_full())
        idx = pd.bdate_range('2023-04-01', '2024-03-29')
        df, valid = sf.fund_features(rows, idx)
        # antes de presentar el primer trimestre de 2023 (2023-05-01) solo se conocen los de 2022
        self.assertEqual(df.loc['2023-04-28', 'n_quarters'], 4.0)
        self.assertTrue(np.isnan(df.loc['2023-04-28', 'rev_yoy']))           # sin 2021 no hay crecimiento interanual
        self.assertEqual(df.loc['2023-05-03', 'n_quarters'], 5.0)
        self.assertAlmostEqual(df.loc['2023-05-03', 'rev_yoy'], 0.30)
        self.assertAlmostEqual(df.loc['2023-11-03', 'om_chg'], 15.0)
        self.assertEqual(df.loc['2023-11-03', 'n_quarters'], 7.0)
        self.assertFalse(valid[-1])                                          # datos caducados a final de marzo 2024


if __name__ == '__main__':
    unittest.main()
