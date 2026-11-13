import unittest

import numpy as np
import pandas as pd

import v24_macro as mc


def data():
    idx = pd.bdate_range('1957-01-02', '2024-06-28')
    rg = np.random.default_rng(4)
    px = pd.Series(100 * np.cumprod(1 + rg.normal(0.0003, 0.01, len(idx))), index=idx)
    rate = pd.Series(0.03 + 0.02 * np.sin(np.arange(len(idx)) / 600.0), index=idx)
    return px, rate


class Macro(unittest.TestCase):
    def test_regimen_definicion(self):
        _, rate = data()
        t = mc.tightening(rate)
        ref = (rate - rate.shift(126)) > 0.005
        self.assertTrue((t == ref).all())

    def test_siempre_on_es_comprar_y_mantener(self):
        px, rate = data()
        import index_leverage as il
        e_on = mc.simulate_on(px, rate, pd.Series(True, index=px.index))
        ref = (1 + px.pct_change().fillna(0) + il.DIV_YIELD / 252).cumprod()
        # la señal se retrasa un día: el primer día está fuera; después coincide salvo el primer cambio
        r1 = e_on.pct_change().dropna().iloc[2:]
        r2 = ref.pct_change().dropna().iloc[2:]
        np.testing.assert_allclose(r1.to_numpy(), r2.to_numpy(), atol=1e-12)

    def test_senal_se_ejecuta_al_dia_siguiente(self):
        px, rate = data()
        on = ~mc.tightening(rate)
        a = mc.simulate_on(px.iloc[:4000], rate.iloc[:4000], on.iloc[:4000])
        px2 = px.iloc[:4000].copy()
        px2.iloc[-1] *= 0.4
        b = mc.simulate_on(px2, rate.iloc[:4000], on.iloc[:4000])
        np.testing.assert_allclose(a.iloc[:-1].to_numpy(), b.iloc[:-1].to_numpy())

    def test_bloqueo_y_criterios(self):
        px, rate = data()
        out = mc.run_all(px, rate, tnx=pd.Series(0.04 * 100, index=px.index))
        self.assertLessEqual(pd.Timestamp(out['ultimo_dia_usado']), pd.Timestamp('2020-12-31'))
        for k in ('M1_cagr_mayor_en_los_tres_periodos', 'M2_ic_exceso_mensual', 'M3_sharpe_no_peor', 'M4_caida_maxima_no_peor', 'supera_al_sp500'):
            self.assertIn(k, out['criterios'])
        self.assertAlmostEqual(out['criterios']['M2_ic_exceso_mensual']['nivel'], 1 - 0.05 / 14)
        self.assertIn('sens_curva_10a_menos_3m_positiva', out['metricas'])


if __name__ == '__main__':
    unittest.main()
