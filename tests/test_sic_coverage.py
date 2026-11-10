import unittest

import sic_coverage as sc


class Sic(unittest.TestCase):
    def test_base_ticker(self):
        self.assertEqual(sc.base_ticker('A-197701'), 'A')
        self.assertEqual(sc.base_ticker('AAMRQ-201312'), 'AAMRQ')
        self.assertEqual(sc.base_ticker('AAPL'), 'AAPL')
        self.assertEqual(sc.base_ticker('BRK-B'), 'BRK-B')          # no es sufijo de fecha

    def test_tecnologicas(self):
        for s in ('3571', '3674', '3661', '7372', '7370', '7379', 7374):
            self.assertTrue(sc.is_tech_sic(s), s)
        for s in ('2834', '6021', '', None, 'abc', '3580', '7380'):
            self.assertFalse(sc.is_tech_sic(s), s)


if __name__ == '__main__':
    unittest.main()
