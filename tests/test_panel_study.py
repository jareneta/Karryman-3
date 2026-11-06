import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fundamental_study as fs  # noqa: E402
import inst_features as inf  # noqa: E402
import panel_study as ps  # noqa: E402
import sec_fundamentals as sec  # noqa: E402
import system_backtest as sb  # noqa: E402


def mk(idx, c):
    c = np.asarray(c, float)
    return pd.DataFrame({'Open': c * 0.999, 'High': c * 1.01, 'Low': c * 0.99, 'Close': c, 'Volume': np.full(len(c), 2e6)}, index=idx)


def rows_for(start_year, n, growth):
    """Trimestres con ventas/margen/BPA coherentes; presentado ~40 días después del cierre."""
    out, rev, eps = [], 100.0, 1.0
    for k, e in enumerate(pd.date_range(f'{start_year}-03-31', periods=n, freq='QE')):
        g = growth(k)
        rev, eps = rev * (1 + g / 4), eps * (1 + g / 4)
        f = (e + pd.Timedelta(days=40)).date().isoformat()
        out.append({'end': e.date().isoformat(), 'rev': rev, 'rev_filed': f, 'eps': eps, 'eps_filed': f,
                    'gp': rev * 0.4, 'gp_filed': f, 'oi': rev * 0.1, 'oi_filed': f, 'ni': rev * 0.08, 'ni_filed': f,
                    'cfo': rev * 0.09, 'cfo_filed': f, 'sh': 50.0, 'sh_filed': f, 'assets': 900.0, 'assets_filed': f,
                    'liab': 400.0, 'liab_filed': f, 'equity': 500.0, 'equity_filed': f, 'cash': 100.0, 'cash_filed': f})
    return out


class StatsTests(unittest.TestCase):
    def test_ic_and_quintiles_detect_a_real_effect_and_not_noise(self):
        rng = np.random.default_rng(0)
        months = pd.period_range('2015-01', periods=60, freq='M').astype(str)
        rows = []
        for m in months:
            x, noise = rng.normal(size=300), rng.normal(size=300)
            exc = 0.3 * x + noise * 0.5 + 0.0
            rows.append(pd.DataFrame({'month': m, 'signal': x, 'noise': rng.normal(size=300), 'fwd_exc_252': exc,
                                      'hit2': (exc > 1.0).astype(float), 'flag': (x > 0.5).astype(float)}))
        p = pd.concat(rows, ignore_index=True)
        real, junk = ps.month_ic(p, 'signal', 'fwd_exc_252'), ps.month_ic(p, 'noise', 'fwd_exc_252')
        self.assertGreater(real['t'], 10)
        self.assertLess(abs(junk['t']), 3)
        rng2 = np.random.default_rng(1)
        q = ps.quintile_stats(p, 'signal', rng2)
        self.assertEqual(q['groups'], 5)
        self.assertGreater(q['spread_hit2_pp'], 5)
        self.assertGreater(q['spread_hit2_ci'][0], 0)           # el IC95 no contiene el 0
        qj = ps.quintile_stats(p, 'noise', rng2)
        self.assertLessEqual(qj['spread_hit2_ci'][0], 0.0)      # sin efecto real, el IC95 contiene el 0
        self.assertGreaterEqual(qj['spread_hit2_ci'][1], 0.0)
        qb = ps.quintile_stats(p, 'flag', rng2)
        self.assertEqual(qb['groups'], 2)
        self.assertGreater(qb['spread_hit2_pp'], 0)

    def test_segments_share_and_ci(self):
        rng = np.random.default_rng(2)
        rows = []
        for m in pd.period_range('2015-01', periods=40, freq='M').astype(str):
            seg = rng.random(400) < 0.2
            hit = (rng.random(400) < np.where(seg, 0.30, 0.08)).astype(float)
            rows.append(pd.DataFrame({'month': m, 'seg': seg, 'hit2': hit, 'fwd_exc_252': hit * 0.5 - 0.1}))
        p = pd.concat(rows, ignore_index=True)
        out = ps.segment_table(p, {'S': p['seg']}, rng)
        self.assertAlmostEqual(out['S']['share_all_pct'], 20, delta=2)
        self.assertGreater(out['S']['share_of_doublers_pct'], 40)   # concentra a las que doblan
        self.assertGreater(out['S']['hit2_vs_rest_ci'][0], 10)
        self.assertGreater(out['S']['lift_vs_all'], 1.8)


class AnticipationTests(unittest.TestCase):
    def test_event_study_sees_price_move_before_the_filing(self):
        n = 3000
        idx = pd.bdate_range('2012-06-01', periods=n)
        spy = pd.Series(100 * np.exp(np.cumsum(np.full(n, 0.0002))), index=idx)
        # BPA pasa de pérdidas a beneficios en 2020-02; el precio sube un 60% en los 9 meses ANTES
        c = np.full(n, 20.0)
        filing = pd.Timestamp('2020-05-15')
        p = idx.searchsorted(filing)
        c[p - 190:p - 5] = np.linspace(20, 32, 185)
        c[p - 5:] = 32.0
        f = mk(idx, c)
        rows = []
        for k, e in enumerate(pd.date_range('2018-03-31', periods=12, freq='QE')):
            eps = -0.3 if e < pd.Timestamp('2020-03-01') else 0.2
            fl = (e + pd.Timedelta(days=45)).date().isoformat()
            rows.append({'end': e.date().isoformat(), 'eps': eps, 'eps_filed': fl, 'rev': 100.0, 'rev_filed': fl})
        qt = sec.quarter_table(rows)
        self.assertGreater(qt['ev_eps_turn'].sum(), 0)
        store = {}
        ps.event_study_stock(f, spy, qt, store)
        out = ps.summarize_events(dict(store, **{k: v * 40 for k, v in store.items()}))
        self.assertIn('ev_eps_turn', store)
        ev = out['ev_eps_turn']
        self.assertGreater(ev['pre_9m_median_pct'], 20)              # el mercado ya había subido antes del dato
        self.assertLess(abs(ev['post_12m_median_pct']), 10)          # y después no queda recorrido

    def test_winner_timing(self):
        n = 3400
        idx = pd.bdate_range('2012-06-01', periods=n)
        c = np.full(n, 25.0) + np.sin(np.arange(n) / 20)
        c[1500:1800] = np.linspace(c[1500], c[1500] * 3.2, 300)
        c[1800:] = c[1800] * np.exp(-np.linspace(0, 0.5, n - 1800))
        f = mk(idx, c)
        # ventas aceleran DESPUÉS de empezar la subida (trimestre ~25 -> 2018-06)
        rows = rows_for(2012, 56, lambda q: 0.05 if q < 25 else 0.8)
        ff, valid = sec.fund_features(rows, idx)
        store = {}
        ps.winner_timing_stock(f, ff, valid, store)
        res = ps.summarize_timing(store)
        r = res['Ventas +25% interanual']
        self.assertEqual(r['runs'], 1)
        self.assertEqual(r['true_at_start_pct'], 0.0)
        self.assertGreater(r['median_days_until_on'], 60)            # la cifra llega meses después
        self.assertGreater(r['median_pct_of_run_done_when_on'], 10)


class PipelineTests(unittest.TestCase):
    def setup_universe(self, n=3300, stocks=14):
        rng = np.random.default_rng(3)
        idx = pd.bdate_range('2012-06-01', periods=n)
        spy = mk(idx, 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))))
        spy['Volume'] = 1e8 * np.exp(rng.normal(0, 0.1, n))
        frames, fund, first = {}, {}, {}
        for k in range(stocks):
            frames[f'S{k}'] = mk(idx, 30 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n))))
            fund[f'S{k}'] = {'rows': rows_for(2012, 55, lambda q: 0.08 + 0.01 * (k % 5)), 'sic': f'{20 + k % 6}00', 'sic_desc': 'X'}
            first[f'S{k}'] = pd.Timestamp('1995-01-02') if k % 2 else pd.Timestamp('2011-06-01')   # maduras y jóvenes
        up = sb.regime_series(spy)['spy_ma50_up']
        tk_group = fs.group_names(fund)
        grank, _ = ps.group_rank_matrix(frames, tk_group, spy.Close.index, min_members=2)
        return frames, fund, first, spy, up, tk_group, grank

    def test_panel_has_no_lookahead_in_features_and_labels_are_forward(self):
        frames, fund, first, spy, up, tk_group, grank = self.setup_universe()
        panel, ev, tm, winners = ps.collect(frames, fund, spy.Close, up, tk_group, grank, inf.market_distribution(spy), first)
        self.assertGreater(len(panel), 500)
        row = panel[panel.ticker == 'S3'].iloc[40]
        f = frames['S3']
        i = f.index.get_loc(row['date'])
        # etiqueta futura: usa precios posteriores; variable pasada: solo anteriores
        self.assertAlmostEqual(row['fwd_ret_252'], f.Close.iloc[i + 252] / f.Close.iloc[i] - 1, places=3)
        self.assertAlmostEqual(row['ret_63'], f.Close.iloc[i] / f.Close.iloc[i - 63] - 1, places=3)
        self.assertEqual(row['hit2'], float(f.Close.iloc[i + 1:i + 253].max() >= 2 * f.Close.iloc[i]))
        need = {'rev_yoy', 'gm_chg', 'eps_turn', 'dil_chg', 'log_mcap', 'rs_rank', 'group_rank', 'fwd_exc_252', 'age_years', 'stage',
                'dist_days_25', 'cmf_63', 'ad_63', 'big_net_50', 'pocket_20', 'spy_dist_25', 'dd_3y'}
        self.assertTrue(need <= set(panel.columns), need - set(panel.columns))
        self.assertAlmostEqual(row['age_years'], (row['date'] - first['S3']).days / 365.25, places=3)
        res = ps.analyze(panel, ev, tm, winners)
        self.assertIn('eps', res['segments'])
        self.assertIn('estadio', res['segments'])
        self.assertIn('huellas', res['segments'])
        self.assertGreater(res['meta']['observations'], 300)

    def test_winners_profile_distinguishes_young_small_winners(self):
        rng = np.random.default_rng(8)
        pop = pd.DataFrame({'age_years': rng.uniform(1, 40, 3000), 'log_mcap': rng.uniform(8, 11.5, 3000), 'stage': rng.choice([1, 2, 3, 4, 5], 3000),
                            'ni_pos': rng.choice([0.0, 1.0], 3000), 'rev_yoy': rng.normal(0.1, 0.3, 3000), 'eps_turn': 0.0, 'oi_turn': 0.0,
                            'dd_3y': rng.uniform(-0.8, 0, 3000), 'acc_net_50': rng.integers(-10, 10, 3000), 'cmf_63': rng.normal(0, .1, 3000),
                            'accum_divergence': 0.0, 'big_net_50': rng.integers(-3, 3, 3000), 'pocket_20': rng.integers(0, 4, 3000),
                            'dist_days_25': rng.integers(0, 10, 3000), 'spy_dist_ge5': 0.0, 'rs_rank': rng.uniform(0, 100, 3000)})
        win = pd.DataFrame({'age_years': rng.uniform(1, 6, 300), 'log_mcap': rng.uniform(8, 9.3, 300), 'stage': 1,
                            'ni_pos': 0.0, 'rev_yoy': rng.normal(0.4, 0.2, 300), 'eps_turn': 0.0, 'oi_turn': 0.0, 'dd_3y': rng.uniform(-0.9, -0.5, 300),
                            'acc_net_50': rng.integers(0, 10, 300), 'cmf_63': rng.normal(0.1, .1, 300), 'accum_divergence': 1.0,
                            'big_net_50': rng.integers(0, 3, 300), 'pocket_20': rng.integers(1, 4, 300), 'dist_days_25': rng.integers(0, 4, 300),
                            'spy_dist_ge5': 0.0, 'rs_rank': rng.uniform(40, 100, 300), 'gain_x': rng.uniform(2, 6, 300), 'days_to_peak': 120})
        out = ps.winners_profile(pop, win)
        young = out['segments']['Edad < 3 años (salida a bolsa reciente)']
        self.assertGreater(young['ratio'], 1.5)
        self.assertGreater(out['segments']['Ángel caído (caída 3 años < -40%)']['ratio'], 1.3)
        self.assertGreater(out['segments']['Etapa 1: base (precio < MA150 plana)']['ratio'], 2)
        self.assertLess(out['segments'].get('Tamaño > 10 B$ (grande)', {'ratio': 0})['ratio'], 0.2)
        self.assertGreater(out['features']['acc_net_50']['percentile_of_winners_median_in_population'], 55)
        self.assertGreater(out['features']['age_years']['median_population'], out['features']['age_years']['median_winners'])


if __name__ == '__main__':
    unittest.main()
