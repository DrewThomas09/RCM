"""Regression statistical-soundness guards.

Two fixes driven by a partner report that the page showed nonsense:

1. Net patient revenue must NOT be predicted from operating_expenses. The two
   are P&L lines that scale together with hospital size, so opex is a circular
   quasi-leakage predictor that inflates R² without independent signal AND
   breaks for academic / safety-net hospitals (high expenses, low/negative
   margin from uncompensated care). It's dropped from the curated NPR set.

2. A negative R² (out-of-sample headline, or a per-cohort fit) means the model
   predicts WORSE than the mean — an unusable model, not a weak one. The page
   now flags those as inconclusive instead of presenting "-287%" as a number a
   partner might act on.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


class TestNoOpexPredictor(unittest.TestCase):
    def test_npr_curated_set_excludes_operating_expenses(self):
        from rcm_mc.ui.regression_page import _CURATED_DEFAULTS
        feats = _CURATED_DEFAULTS["net_patient_revenue"]
        self.assertNotIn("operating_expenses", feats)
        # The structural drivers it SHOULD use are present.
        for f in ("total_patient_days", "medicare_day_pct", "medicaid_day_pct"):
            self.assertIn(f, feats)

    def test_collinear_pairs_excludes_pl_lines_for_npr(self):
        from rcm_mc.ui.regression_page import _COLLINEAR_PAIRS
        excl = _COLLINEAR_PAIRS["net_patient_revenue"]
        self.assertIn("operating_expenses", excl)
        self.assertIn("net_income", excl)


class TestInconclusiveGuard(unittest.TestCase):
    def _res(self):
        return {"r2": 0.556, "condition_number": 9.4, "rmse": 0.99,
                "y_std": 1.0, "residual_summary": {"p80_abs": 0.5}}

    def test_negative_oos_flags_inconclusive(self):
        from rcm_mc.ui.regression_page import _rge_headline_strip
        cv = SimpleNamespace(mean_test_r2=-2.87, k=5, overfit_gap=3.4,
                             pi_coverage=None, target_was_log_transformed=True,
                             folds=[])
        html = _rge_headline_strip(self._res(), cv, True)
        self.assertIn("Inconclusive", html)
        self.assertIn("does not beat the mean", html)
        self.assertIn("WORSE THAN MEAN", html)
        self.assertIn("OVERFIT", html)        # in-sample tile flagged

    def test_positive_oos_no_banner(self):
        from rcm_mc.ui.regression_page import _rge_headline_strip
        cv = SimpleNamespace(mean_test_r2=0.563, k=5, overfit_gap=0.003,
                             pi_coverage=None, target_was_log_transformed=True,
                             folds=[])
        html = _rge_headline_strip(self._res(), cv, True)
        self.assertNotIn("Inconclusive", html)
        self.assertIn("56.3%", html)

    def test_negative_cohort_r2_shows_inconclusive(self):
        from rcm_mc.ui.regression_page import _rge_cohort_grids
        result = {
            "r2": 0.55,
            "cohort_r2_by_segment": [
                {"bucket": "Academic", "r2": -2.87, "n": 41,
                 "delta_vs_headline": -3.4},
                {"bucket": "Community", "r2": 0.61, "n": 900,
                 "delta_vs_headline": 0.06},
            ],
        }
        html = _rge_cohort_grids(result)
        self.assertIn("inconclusive", html)
        self.assertNotIn("-287%", html)       # never the raw nonsense number
        self.assertIn("61%", html)            # the healthy cohort still shows


if __name__ == "__main__":
    unittest.main()
