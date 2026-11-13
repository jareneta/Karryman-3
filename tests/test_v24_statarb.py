import unittest

import numpy as np
import pandas as pd

import v24_engine as ve
import v24_statarb as sa


def setup(T=900, n=60, seed=21):
    p = ve.synthetic_universe(n=n, T=T, seed=seed)
    mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
    elig = mem & p['close'].notna()
    return p, elig


class StatArb(unittest.TestCase):
    def test_pesos_dolar_neutrales(self):
        p, elig = setup()
        score = -(p['close'] / p['close'].shift(5) - 1)
        wl, ws = sa.weights(score, elig)
        ok = score.notna().any(axis=1)
        sl_, ss_ = wl.sum(axis=1)[ok], ws.sum(axis=1)[ok]
        self.assertTrue(((sl_ - 1).abs() < 1e-9).all() or ((sl_ - 1).abs() < 1e-9)[sl_ > 0].all())
        self.assertTrue((((wl > 0) & (ws > 0)).sum().sum()) == 0)       # ningún valor largo y corto a la vez
        # largos = los que más han caído; cortos = los que más han subido
        d = score.dropna(how='all').index[100]
        self.assertGreaterEqual(score.loc[d][wl.loc[d] > 0].min(), score.loc[d][ws.loc[d] > 0].max())

    def test_sin_costes_el_neto_es_el_bruto_y_los_costes_restan(self):
        p, elig = setup()
        score = -(p['close'] / p['close'].shift(5) - 1)
        fwd = sa.forward_returns(p['open'])
        n0, _, turn = sa.long_short(score, elig, fwd, cost=0.0, borrow=0.0)
        n1, _, _ = sa.long_short(score, elig, fwd, cost=0.001, borrow=0.0)
        np.testing.assert_allclose((n0 - n1).to_numpy(), (turn * 0.001).to_numpy(), atol=1e-12)
        n2, _, _ = sa.long_short(score, elig, fwd, cost=0.0, borrow=0.01)
        wl, ws = sa.weights(score, elig)
        np.testing.assert_allclose((n0 - n2).to_numpy(), (ws.sum(axis=1) * 0.01 / 252).to_numpy(), atol=1e-12)

    def test_sin_futuro(self):
        p, elig = setup()
        t = 500
        fwd = sa.forward_returns(p['open'])
        score = -(p['close'] / p['close'].shift(5) - 1)
        a, _, _ = sa.long_short(score, elig, fwd)
        q = {k: v.copy() for k, v in p.items()}
        for k in ('open', 'high', 'low', 'close'):
            q[k].iloc[t + 3:] *= 3.0
        fwd2 = sa.forward_returns(q['open'])
        score2 = -(q['close'] / q['close'].shift(5) - 1)
        b, _, _ = sa.long_short(score2, elig, fwd2)
        np.testing.assert_allclose(a.iloc[:t + 1].to_numpy(), b.iloc[:t + 1].to_numpy(), atol=1e-12)

    def test_senal_obsoleta_es_un_desplazamiento(self):
        p, elig = setup()
        score = -(p['close'] / p['close'].shift(5) - 1)
        s20 = score.shift(20)
        self.assertTrue(np.allclose(s20.iloc[100:].to_numpy(), score.iloc[80:-20].to_numpy(), equal_nan=True))

    def test_run_period_estructura(self):
        p, elig = setup(T=1300)
        mem = pd.DataFrame(True, index=p['close'].index, columns=p['close'].columns)
        bench = p['close'].mean(axis=1)
        idx = p['close'].index
        segs = [('a', (str(idx[300].date()), str(idx[800].date()))), ('b', (str(idx[801].date()), str(idx[-4].date())))]
        r = sa.run_period(p, mem, bench, segs, 0.99, sens=True)
        for k in ('J1_ic_media_mensual_neta', 'J2_sharpe_mayor_que_ambos_placebos_en_cada_tramo', 'esperanza_positiva_en_el_periodo', 'supera_a_spy_cagr_y_sharpe'):
            self.assertIn(k, r['criterios'])
        self.assertIn('solo_lado_largo_neto', r['sensibilidades_no_deciden'])
        self.assertEqual(set(r['placebos']), {'placebo_obsoleto_20', 'placebo_obsoleto_40'})


if __name__ == '__main__':
    unittest.main()
