"""The regression page's "exact prediction formula" explainer.

Partner ask: "explain the formula, like what is the exact predictions." The
page now renders, under the headline summary, the literal equation the model
evaluates —

    ŷ_fit = intercept + Σ βᵢ · (xᵢ − meanᵢ) / sdᵢ        (exp() if log target)

— a per-driver "+1 SD effect" table, and one worked example. These tests pin
the math (a one-SD move changes ŷ_fit by exactly βᵢ; multiplicative under a
log target) and the data contract (feat_mean / feat_std now ride on every
fitted coefficient so the equation can be reconstructed).
"""
from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd


def _synthetic_hcris(n: int = 420, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "name": [f"Hospital {i}" for i in range(n)],
        "state": rng.choice(
            ["CA", "NY", "TX", "FL", "OH", "PA", "MA", "IL", "GA", "WA"], n,
        ),
        "beds": rng.integers(20, 800, n),
        "occupancy_rate": rng.uniform(0.3, 0.95, n),
        "medicare_day_pct": rng.uniform(0.2, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.4, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "total_patient_days": rng.integers(1000, 250000, n),
    })
    df["net_patient_revenue"] = (
        df["operating_expenses"] * rng.uniform(0.85, 1.2, n)
        + rng.normal(0, 5e7, n)
    ).clip(lower=1e6)
    return df


def _log_result():
    return {
        "target": "net_patient_revenue",
        "log_target": True,
        "intercept": 18.30,
        "coefficients": [
            {"feature": "total_patient_days", "coefficient": 0.30,
             "feat_mean": 35000.0, "feat_std": 22000.0, "significance": "***"},
            {"feature": "medicare_day_pct", "coefficient": -0.12,
             "feat_mean": 0.42, "feat_std": 0.11, "significance": "**"},
            {"feature": "occupancy_rate", "coefficient": 0.05,
             "feat_mean": 0.63, "feat_std": 0.14, "significance": ""},
        ],
    }


class TestTargetUnitFmt(unittest.TestCase):
    def test_money_target(self):
        from rcm_mc.ui.regression_page import _rge_target_unit_fmt
        self.assertIn("M", _rge_target_unit_fmt(2.5e8, "net_patient_revenue"))

    def test_ratio_target_is_percent(self):
        from rcm_mc.ui.regression_page import _rge_target_unit_fmt
        self.assertEqual(_rge_target_unit_fmt(0.085, "operating_margin"), "8.5%")

    def test_count_target_plain(self):
        from rcm_mc.ui.regression_page import _rge_target_unit_fmt
        out = _rge_target_unit_fmt(12345.0, "total_patient_days")
        self.assertEqual(out, "12,345")


class TestFormulaExplainerLog(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.regression_page import _rge_formula_explainer
        self.html = _rge_formula_explainer(_log_result())

    def test_panel_and_equation_present(self):
        self.assertIn("The exact prediction formula", self.html)
        self.assertIn("rge-eq", self.html)
        # Log target → the equation is wrapped in exp(...).
        self.assertIn("exp(", self.html)

    def test_one_sd_effect_is_multiplicative(self):
        # +1 SD of the top driver moves log(target) by βᵢ = 0.30, so the
        # prediction is multiplied by exp(0.30) = 1.35 → +35.0%.
        pct = (math.exp(0.30) - 1.0) * 100.0
        self.assertAlmostEqual(pct, 34.986, places=2)
        self.assertIn("+35.0%", self.html)
        self.assertIn("×1.35", self.html)   # ×1.35

    def test_drivers_ranked_strongest_first(self):
        # total_patient_days (|0.30|) outranks medicare_day_pct (|0.12|).
        self.assertLess(
            self.html.index("Total Patient Days"),
            self.html.index("Medicare Day Pct"),
        )

    def test_worked_example_anchored_on_intercept(self):
        # Baseline = exp(intercept); the worked example states it.
        self.assertIn("Worked example", self.html)
        self.assertIn("average on every input", self.html)


class TestFormulaExplainerLinear(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.regression_page import _rge_formula_explainer
        res = _log_result()
        res["target"] = "operating_margin"
        res["log_target"] = False
        res["intercept"] = 0.085
        self.html = _rge_formula_explainer(res)

    def test_no_exp_wrapper(self):
        self.assertNotIn("exp(", self.html)

    def test_baseline_is_intercept_as_percent(self):
        # operating_margin is a ratio → baseline 0.085 shows as 8.5%.
        self.assertIn("8.5%", self.html)


class TestEmptyGuard(unittest.TestCase):
    def test_no_coefficients_returns_empty(self):
        from rcm_mc.ui.regression_page import _rge_formula_explainer
        self.assertEqual(_rge_formula_explainer({"coefficients": []}), "")


class TestFitCarriesFeatureMoments(unittest.TestCase):
    """Integration: a real fit must now carry feat_mean / feat_std on every
    coefficient, and the explainer must render off that fit."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.regression_page import _run_ols
        cls.result = _run_ols(
            _synthetic_hcris(),
            "net_patient_revenue",
            ["beds", "occupancy_rate", "medicare_day_pct",
             "operating_expenses", "total_patient_days"],
            log_target=True,
        )

    def test_every_coefficient_has_finite_moments(self):
        coefs = self.result["coefficients"]
        self.assertTrue(coefs)
        for c in coefs:
            self.assertIn("feat_mean", c)
            self.assertIn("feat_std", c)
            self.assertTrue(math.isfinite(c["feat_mean"]))
            self.assertTrue(math.isfinite(c["feat_std"]))
            self.assertGreater(c["feat_std"], 0.0)

    def test_explainer_renders_off_real_fit(self):
        from rcm_mc.ui.regression_page import _rge_formula_explainer
        html = _rge_formula_explainer(self.result)
        self.assertIn("The exact prediction formula", html)
        self.assertIn("rge-eq", html)
        self.assertIn("Worked example", html)


if __name__ == "__main__":
    unittest.main()
