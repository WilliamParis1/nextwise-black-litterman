"""Offline regression checks; synthetic returns do not validate market data."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'nextwise - asset allocation' / 'nextwise'))
from config import PORTFOLIO, CONVICTION_EXCESS, CONVICTION_CONFIDENCE, DEFAULT_PARAMS, TICKER_FALLBACKS
from models import build_views_from_convictions, run_full_pipeline
from backtest import run_backtest


class PortfolioTests(unittest.TestCase):
    def test_requested_universe(self):
        expected = {'ADYEN', 'ASM', 'ASML', 'CRL', 'AM', 'ERA', 'FOHW', 'GL9', 'ISAE', 'ITWN', 'BATT', 'LR', 'LDO', '3AAP', 'WHCA', 'NEX', 'PRY', 'SU', 'WCOS', 'SPIE', 'TE', 'HO', 'NUCL'}
        self.assertEqual({a['symbol'] for a in PORTFOLIO}, expected)
        self.assertEqual(len(PORTFOLIO), 23)
        self.assertEqual(len({a['ticker'] for a in PORTFOLIO}), 23)
        self.assertEqual(TICKER_FALLBACKS, {})
        for asset in PORTFOLIO:
            self.assertIn(asset['action'], CONVICTION_EXCESS)
            self.assertTrue(0 < asset['confidence'] <= 1)

    def test_individual_confidence_reaches_views(self):
        assets = [{'name': 'A', 'action': 'Renforcer', 'confidence': .42},
                  {'name': 'B', 'action': 'Renforcer'},
                  {'name': 'C', 'action': 'Maintien', 'confidence': .9}]
        p, q, confidence, indices = build_views_from_convictions(assets, np.zeros(3), CONVICTION_EXCESS, CONVICTION_CONFIDENCE, 3)
        np.testing.assert_allclose(confidence, [.42, CONVICTION_CONFIDENCE['Renforcer']])
        self.assertEqual(indices, [0, 1])
        self.assertEqual(p.shape, (2, 3))
        np.testing.assert_allclose(q, [.03, .03])
        for invalid in [0, -1, 1.1, float('nan')]:
            with self.assertRaises(ValueError):
                build_views_from_convictions([{'action': 'Renforcer', 'confidence': invalid}], np.zeros(1), CONVICTION_EXCESS, CONVICTION_CONFIDENCE, 1)

    def test_pipeline_and_backtest(self):
        rng = np.random.default_rng(73)
        n = len(PORTFOLIO)
        factors = rng.normal(0, .006, (756, 1))
        returns = pd.DataFrame(factors + rng.normal(0, np.linspace(.006, .025, n), (756, n)), index=pd.bdate_range('2021-01-01', periods=756), columns=[a['name'] for a in PORTFOLIO])
        result = run_full_pipeline(returns, PORTFOLIO, CONVICTION_EXCESS, CONVICTION_CONFIDENCE, DEFAULT_PARAMS)
        w = result['ucits_weights']
        self.assertTrue(np.isfinite(w).all())
        self.assertTrue((w >= 0).all())
        self.assertAlmostEqual(w.sum(), 1)
        self.assertTrue(result['ucits_report']['all_pass'], result['ucits_report'])
        self.assertEqual(result['n_assets'], 23)
        bt = run_backtest(returns, w, transaction_cost=DEFAULT_PARAMS['transaction_cost'])
        self.assertTrue(np.isfinite(bt['ann_return']))
        self.assertEqual(len(bt['daily_returns']), len(returns))
        self.assertTrue(np.isfinite(bt['daily_returns']).all())
        self.assertGreater(bt['n_rebalances'], 0)
        self.assertGreater(bt['total_cost'], 0)


if __name__ == '__main__':
    unittest.main()
