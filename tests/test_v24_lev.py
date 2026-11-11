import unittest

import numpy as np
import pandas as pd

import index_leverage as il
import v24_lev as lev


class Lev(unittest.TestCase):
    def setUp(self):
        idx = pd.bdate_range('1955-01-03', '2024-06-30')
        rg = np.random.default_rng(1)
        self.px = pd.Series(100 * np.cumprod(1 + rg.normal(0.0003, 0.01, len(idx))), index=idx)
        self.rate = pd.Series(0.03, index=idx)

    def test_bloqueo_y_referencia_1x(self):
        out = lev.run_all(self.px, self.rate)
        self.assertLessEqual(pd.Timestamp(out['ultimo_dia_usado']), pd.Timestamp('2020-12-31'))
        # referencia 1x: rentabilidad diaria del índice + 2 %/año de dividendo, sin comisión
        px = self.px[self.px.index <= '2020-12-31']
        eq = (1 + px.pct_change().fillna(0) + il.DIV_YIELD / 252).cumprod()
        w = out['metricas']['B_1x_comprar_y_mantener']['todo_1960_2020']
        e = eq.loc['1960-01-01':'2020-12-31']
        e = e / e.iloc[0]
        self.assertAlmostEqual(w['final_multiple'], float(e.iloc[-1]), places=2)

    def test_criterios_y_sensibilidades(self):
        out = lev.run_all(self.px, self.rate)
        for k in ('L1_cagr_mayor_en_los_tres_periodos', 'L2_ic_exceso_mensual', 'L3_sharpe_no_peor', 'L4_caida_maxima_no_peor', 'supera_al_sp500'):
            self.assertIn(k, out['criterios'])
        self.assertEqual(set(out['metricas']), {'B_1x_comprar_y_mantener', 'S_2x_filtro_MA200', 'sens_2x_sin_filtro', 'sens_3x_filtro_MA200', 'sens_2x_filtro_10_meses', 'sens_1x_filtro_MA200'})
        self.assertAlmostEqual(out['criterios']['L2_ic_exceso_mensual']['nivel'], 1 - 0.05 / 12)

    def test_senal_se_ejecuta_al_dia_siguiente(self):
        # el filtro desplaza la señal un día: cambiar el último precio no altera el valor de ayer
        a = il.simulate(self.px.iloc[:3000], self.rate.iloc[:3000], 2, 'ma200')
        px2 = self.px.iloc[:3000].copy()
        px2.iloc[-1] *= 0.5
        b = il.simulate(px2, self.rate.iloc[:3000], 2, 'ma200')
        np.testing.assert_allclose(a.iloc[:-1].to_numpy(), b.iloc[:-1].to_numpy())


if __name__ == '__main__':
    unittest.main()
