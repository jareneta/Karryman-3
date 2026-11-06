import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import early_signals as es  # noqa: E402
import fundamental_study as fs  # noqa: E402
import system_backtest as sb  # noqa: E402


def mk(idx, c, vol=None):
    c = np.asarray(c, float)
    v = np.full(len(c), 2e6) if vol is None else vol
    return pd.DataFrame({'Open': c * 0.999, 'High': c * 1.01, 'Low': c * 0.99, 'Close': c, 'Volume': v}, index=idx)


def quarters(start_year, n, base_eps, growth):
    """Trimestres sintéticos con BPA creciente; presentado ~40 días después del cierre."""
    rows, eps, rev = [], base_eps, 100.0
    ends = pd.date_range(f'{start_year}-03-31', periods=n, freq='QE')
    for k, e in enumerate(ends):
        g = growth(k)
        eps, rev = eps * (1 + g / 4), rev * (1 + g / 4)
        f = (e + pd.Timedelta(days=40)).date().isoformat()
        rows.append({'end': e.date().isoformat(), 'eps': eps, 'eps_filed': f, 'rev': rev, 'rev_filed': f})
    return rows


class FundamentalStudyTests(unittest.TestCase):
    def test_pipeline_links_acceleration_to_winners(self):
        rng = np.random.default_rng(11)
        n = 3400
        idx = pd.bdate_range('2012-06-01', periods=n)
        spy = mk(idx, 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))))
        frames, fund = {}, {}
        # ganadoras plantadas: benefician de aceleración justo antes de la subida (año 5)
        for k in range(8):
            c = np.full(n, 25.0) + np.sin(np.arange(n) / 20 + k)
            c[1500:1800] = np.linspace(c[1500], c[1500] * 3.2, 300)
            c[1800:] = c[1800] * np.exp(-np.linspace(0, 0.5, n - 1800))
            frames[f'W{k}'] = mk(idx, c)
            fund[f'W{k}'] = {'rows': quarters(2012, 56, 1.0, lambda q: 0.05 if q < 21 else 0.6), 'sic': '73' + str(k % 3), 'sic_desc': 'Software'}
        for k in range(40):
            frames[f'R{k}'] = mk(idx, 30 * np.exp(np.cumsum(rng.normal(0.0002, 0.02, n))))
            fund[f'R{k}'] = {'rows': quarters(2012, 56, 1.0, lambda q: 0.05), 'sic': '28' + str(k % 4), 'sic_desc': 'Pharma'}
        flags_by, covered_by, group_by, sizes = fs.build_inputs(frames, fund, spy.Close)
        self.assertEqual(len(flags_by), 48)
        self.assertTrue(set(fs.GROUP_FLAGS) <= set(flags_by['W0']))
        up = sb.regime_series(spy)['spy_ma50_up']
        res = es.run_all(frames, spy.Close, up, flags_by, covered_by, group_by)
        start = res['winner_runs_at_start']
        self.assertGreater(start['with_fundamental_data'], 0)
        # al empezar la subida, las ganadoras plantadas aceleran más de lo habitual
        prev = res['baseline']['by_flag']['EPS +25% y acelera']['prevalence_pct']
        self.assertGreater(start['flags_pct']['EPS +25% y acelera'], prev)
        # cada señal trae su desglose por filtro y el control con el mismo filtro
        any_sig = next(iter(res['signals'].values()))
        self.assertIn('EPS +25% y acelera', any_sig['by_flag'])
        self.assertIn('control_R_with_flag', any_sig['by_flag']['EPS +25% y acelera'])

    def test_group_leaders_need_enough_members(self):
        idx = pd.bdate_range('2020-01-01', periods=400)
        frames, tk = {}, {}
        drifts = {'10 Oro': 0.6, '20 Comida': -0.1, '30 Tela': 0.0, '40 Gas': 0.05, '50 Agua': 0.1, '60 Papel': 0.02}
        for g, d in drifts.items():
            for k in range(11):
                frames[f'{g[:2]}_{k}'] = mk(idx, 20 * np.exp(np.linspace(0, d, 400)))
                tk[f'{g[:2]}_{k}'] = g
        for k in range(3):  # grupo demasiado pequeño: se ignora
            frames[f'70_{k}'] = mk(idx, 20 * np.exp(np.linspace(0, 0.9, 400)))
            tk[f'70_{k}'] = '70 Poco'
        lead, sizes = fs.leader_matrix(frames, tk, idx)
        self.assertNotIn('70 Poco', lead.columns)
        self.assertTrue(bool(lead['10 Oro'].iloc[-1]))
        self.assertFalse(bool(lead['20 Comida'].iloc[-1]))
        # con menos de 5 grupos no se puede ordenar: nadie es líder
        few = {t: g for t, g in tk.items() if g in ('10 Oro', '20 Comida')}
        lead2, _ = fs.leader_matrix({t: frames[t] for t in few}, few, idx)
        self.assertFalse(bool(lead2.to_numpy().any()))


if __name__ == '__main__':
    unittest.main()
