"""Data-science tests for the regression multicollinearity diagnostics.

These pin the textbook behaviour a partner relies on: the condition number
and VIF must flag a collinear design, stepwise pruning must return an
interpretable feature set, and the verdict must escalate severity — so a
high-R²/high-F model built on inter-correlated predictors is never presented
as if its coefficients were trustworthy.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.regression import (
    compute_vif,
    condition_number,
    f_pvalue,
    multicollinearity_verdict,
    prune_collinear,
    run_regression,
)


class FPValueTests(unittest.TestCase):
    def test_known_critical_values(self):
        # F at the 5% critical value should return p ~ 0.05.
        self.assertAlmostEqual(f_pvalue(4.96, 1, 10), 0.05, places=2)
        self.assertAlmostEqual(f_pvalue(1.0, 10, 10), 0.5, places=2)

    def test_large_f_is_tiny_p(self):
        self.assertLess(f_pvalue(1000.0, 7, 200), 1e-20)

    def test_degenerate_is_one(self):
        self.assertEqual(f_pvalue(0.0, 5, 30), 1.0)
        self.assertEqual(f_pvalue(-1.0, 5, 30), 1.0)


def _frames(seed: int = 0):
    rng = np.random.default_rng(seed)
    n = 300
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    # x3 is (almost) a linear combination of x1 + x2 — textbook collinearity,
    # like medicare% + medicaid% + commercial% summing to 100.
    x3 = x1 + x2 + rng.normal(scale=1e-3, size=n)
    collinear = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
    independent = pd.DataFrame({
        "a": rng.normal(size=n), "b": rng.normal(size=n),
        "c": rng.normal(size=n),
    })
    return collinear, independent


class ConditionNumberTests(unittest.TestCase):
    def test_low_for_independent_features(self):
        _, indep = _frames()
        self.assertLess(condition_number(indep), 30.0)

    def test_high_for_collinear_features(self):
        collinear, _ = _frames()
        self.assertGreater(condition_number(collinear), 100.0)

    def test_degenerate_input_is_safe(self):
        self.assertEqual(condition_number(pd.DataFrame()), 1.0)
        self.assertEqual(condition_number(pd.DataFrame({"x": [1.0]})), 1.0)


class PruneTests(unittest.TestCase):
    def test_pruning_removes_collinearity(self):
        collinear, _ = _frames()
        kept, dropped = prune_collinear(collinear, max_vif=10.0)
        self.assertTrue(dropped, "should drop at least one collinear feature")
        # The surviving set must itself be low-VIF and interpretable.
        kept_vifs = compute_vif(collinear[kept])
        self.assertTrue(all(v <= 10.0 for v in kept_vifs.values()),
                        f"kept set still collinear: {kept_vifs}")

    def test_independent_set_kept_intact(self):
        _, indep = _frames()
        kept, dropped = prune_collinear(indep, max_vif=10.0)
        self.assertEqual(set(kept), set(indep.columns))
        self.assertEqual(dropped, [])


class VerdictTests(unittest.TestCase):
    def test_severity_escalates(self):
        self.assertEqual(multicollinearity_verdict(2.0, 5.0)["severity"], "low")
        self.assertEqual(
            multicollinearity_verdict(12.0, 20.0)["severity"], "moderate")
        self.assertEqual(
            multicollinearity_verdict(999.0, 500.0)["severity"], "severe")

    def test_severe_warns_against_individual_effects(self):
        v = multicollinearity_verdict(999.0, 500.0)
        self.assertIn("individual", v["message"].lower())
        self.assertIn("optimized", v["recommendation"].lower())


class EndToEndTests(unittest.TestCase):
    def test_collinear_fit_is_flagged_then_fixed(self):
        # A model on collinear predictors fits well (high R²) but the
        # diagnostics must catch it, and pruning must yield a clean fit.
        collinear, _ = _frames()
        collinear = collinear.copy()
        collinear["y"] = 2 * collinear["x1"] - collinear["x2"] + \
            np.random.default_rng(1).normal(scale=0.1, size=len(collinear))
        res = run_regression(collinear, "y", ["x1", "x2", "x3"])
        self.assertGreater(res.r_squared, 0.9)            # fits well
        self.assertGreater(res.condition_number, 100.0)   # but ill-conditioned
        self.assertEqual(
            multicollinearity_verdict(
                max(res.vifs.values()), res.condition_number)["severity"],
            "severe")
        kept, dropped = prune_collinear(collinear[["x1", "x2", "x3"]])
        self.assertTrue(dropped)
        clean = run_regression(collinear, "y", kept)
        self.assertLess(clean.condition_number, 100.0)


class PageBannerTests(unittest.TestCase):
    def test_severe_collinearity_surfaces_to_the_user(self):
        # The exact failure mode the regression tab must catch: a fit on
        # mechanically-collinear HCRIS columns (beds ≈ bed_days ≈ patient_days)
        # must show a Severe banner + the optimized feature set, never present
        # the inflated fit as trustworthy.
        from tests.test_regression_page_phase2 import _synthetic_hcris
        import rcm_mc.ui.regression_page as rp
        df = _synthetic_hcris(150).copy()
        df["bed_days_available"] = df["beds"] * 250.0
        df["total_patient_days"] = df["beds"] * 200.0 + \
            np.random.default_rng(1).normal(scale=5, size=len(df))
        feats = ["beds", "bed_days_available", "total_patient_days"]
        res = rp._run_ols(rp._add_computed_features(df),
                          "net_patient_revenue", feats)
        self.assertEqual(res["verdict"]["severity"], "severe")
        self.assertTrue(res["optimized_dropped"])
        html = rp.render_regression_page(hcris_df=df, features=feats)
        self.assertIn("Severe multicollinearity", html)
        self.assertIn("Optimized feature set", html)
        self.assertIn("Condition #", html)
        # The optimized set is one click away.
        self.assertIn("optimized=1", html)
        self.assertIn("Apply the optimized model", html)

    def test_optimized_toggle_refits_and_offers_full(self):
        from tests.test_regression_page_phase2 import _synthetic_hcris
        import rcm_mc.ui.regression_page as rp
        df = _synthetic_hcris(150).copy()
        df["bed_days_available"] = df["beds"] * 250.0
        df["total_patient_days"] = df["beds"] * 200.0 + \
            np.random.default_rng(1).normal(scale=5, size=len(df))
        feats = ["beds", "bed_days_available", "total_patient_days"]
        html = rp.render_regression_page(
            hcris_df=df, features=feats, optimized=True)
        # Applied state: confirms the de-collinearized fit + a way back.
        self.assertIn("Optimized model applied", html)
        self.assertIn("View the full", html)

    def test_f_pvalue_shown(self):
        from tests.test_regression_page_phase2 import _synthetic_hcris
        import rcm_mc.ui.regression_page as rp
        html = rp.render_regression_page(hcris_df=_synthetic_hcris(80))
        self.assertRegex(html, r"p (&lt;|=) ")


if __name__ == "__main__":
    unittest.main()
