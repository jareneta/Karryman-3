import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inst13f as i13  # noqa: E402


def make_zip(path, period, filings, holdings):
    """filings: [(acc, cik, tipo)] ; holdings: [(acc, cusip, shares, tipo_importe, putcall)]"""
    sub = pd.DataFrame([{'ACCESSION_NUMBER': a, 'FILING_DATE': '01-FEB-2024', 'SUBMISSIONTYPE': t, 'CIK': c, 'PERIODOFREPORT': period} for a, c, t in filings])
    info = pd.DataFrame([{'ACCESSION_NUMBER': a, 'INFOTABLE_SK': i, 'NAMEOFISSUER': 'X', 'CUSIP': cu, 'VALUE': '1', 'SSHPRNAMT': sh, 'SSHPRNAMTTYPE': ty, 'PUTCALL': pc}
                         for i, (a, cu, sh, ty, pc) in enumerate(holdings)])
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('SUBMISSION.tsv', sub.to_csv(sep='\t', index=False))
        zf.writestr('INFOTABLE.tsv', info.to_csv(sep='\t', index=False))
        zf.writestr('COVERPAGE.tsv', 'ACCESSION_NUMBER\tX\n')


class Holdings13FTests(unittest.TestCase):
    def test_read_filters_and_aggregates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = f'{tmp}/q.zip'
            make_zip(p, '31-DEC-2023', [('A1', '100', '13F-HR'), ('A2', '200', '13F-HR'), ('A3', '300', '13F-HR/A'), ('A4', '400', '13F-NT')],
                     [('A1', '037833100', 1000, 'SH', ''), ('A1', '037833100', 500, 'SH', ''),     # dos líneas del mismo gestor se suman
                      ('A1', '037833100', 9999, 'SH', 'Call'),                                       # opciones: fuera
                      ('A1', '594918104', 7, 'PRN', ''),                                              # bonos: fuera
                      ('A2', '037833100', 200, 'SH', ''), ('A3', '037833100', 5000, 'SH', ''),       # enmienda: fuera
                      ('A4', '037833100', 5000, 'SH', '')])
            h = i13.read_holdings(p)
        self.assertEqual(len(h), 2)
        apple = h.set_index('cik').loc['100', 'shares']
        self.assertEqual(apple, 1500)
        self.assertEqual(set(h.cik), {'100', '200'})
        self.assertEqual(h.period.iloc[0], pd.Timestamp('2023-12-31'))

    def test_quarter_movement(self):
        prev = pd.DataFrame({'cik': ['1', '2', '3', '4'], 'cusip': ['AAA'] * 4, 'shares': [100.0, 100.0, 100.0, 100.0]})
        cur = pd.DataFrame({'cik': ['1', '2', '3', '5', '6'], 'cusip': ['AAA'] * 5, 'shares': [150.0, 60.0, 100.0, 40.0, 10.0]})
        m = i13.quarter_metrics(cur, prev).set_index('cusip').loc['AAA']
        self.assertEqual(m['inst_holders'], 5)
        self.assertEqual(m['inst_shares'], 360)
        self.assertEqual(m['new_holders'], 2)       # 5 y 6
        self.assertEqual(m['closed_holders'], 1)    # 4
        self.assertEqual(m['added_holders'], 1)     # 1 sube
        self.assertEqual(m['reduced_holders'], 1)   # 2 baja
        self.assertEqual(m['net_shares'], -40)      # 360 - 400
        self.assertAlmostEqual(m['buyer_ratio'], 3 / 5)
        self.assertAlmostEqual(m['holders_chg_pct'], 5 / 4 - 1)
        self.assertAlmostEqual(m['shares_chg_pct'], -0.1)

    def test_availability_without_lookahead(self):
        self.assertEqual(i13.available_date('2023-12-31'), pd.Timestamp('2024-02-15'))


if __name__ == '__main__':
    unittest.main()
