import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(code, regimen):
    env = {**os.environ, 'V24_REGIMEN': regimen}
    r = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True)
    return r


class Regimen(unittest.TestCase):
    def test_legacy_mantiene_los_periodos_originales(self):
        r = run("import v24_regimen as rg, v24_h5 as h5, v24_lev as lv, v24_macro as mc; "
                "print(rg.ACTIVE, h5.ALL, h5.LEVEL, lv.FULL_KEY, mc.FULL_KEY, lv.LOCK_END)", 'legacy')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ['legacy', "('2010-01-01',", "'2020-12-31')", '0.95', 'todo_1960_2020', 'todo_1961_2020', '2020-12-31'])

    def test_2015_cambia_periodos_nivel_y_cierre(self):
        r = run("import v24_regimen as rg, v24_h5 as h5, v24_hipotesis as hp, v24_lev as lv, v24_macro as mc, v24_h7 as h7, v24_backtest as vb; "
                "pl = rg.period_list(((),), 14); print(rg.ACTIVE, h5.TRAIN, h5.VALID, h5.ALL, round(h5.LEVEL, 6), hp.K_HIPOTESIS, lv.LOCK_END, mc.FULL, lv.FULL_KEY, "
                "pl[0][0], pl[0][1], pl[0][2], round(pl[0][4], 6), sorted(vb.SEGS))", '2015')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        for frag in ("'2015-01-01', '2020-12-31'", "'2021-01-01', '2026-10-31'", '0.996429', '14', 'N_2015_2026', '2013-06-01', 'todo_2015_2026', "['2015_2020', '2021_2026', 'todo']"):
            self.assertIn(frag, out)

    def test_valor_no_valido_falla(self):
        r = run("import v24_regimen", 'x')
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
