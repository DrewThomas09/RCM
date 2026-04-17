"""Tests for Quant Lab and Bayesian calibration pages."""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _sample_hcris(n=100):
    rng = np.random.RandomState(42)
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY"], n),
        "county": ["County"] * n,
        "beds": rng.randint(20, 600, n).astype(float),
        "net_patient_revenue": rng.uniform(1e7, 5e9, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "gross_patient_revenue": rng.uniform(5e7, 1e10, n),
        "total_patient_days": rng.randint(1000, 100000, n).astype(float),
        "bed_days_available": rng.randint(5000, 200000, n).astype(float),
        "medicare_day_pct": rng.uniform(0.1, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.3, n),
    })


class TestQuantLabPage(unittest.TestCase):

    def test_renders(self):
        from rcm_mc.ui.quant_lab_page import render_quant_lab
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris(200))
        html = render_quant_lab(df)
        self.assertIn("SeekingChartis", html)
        self.assertIn("Quant Lab", html)
        self.assertIn("Efficiency Frontier", html)
        self.assertIn("Market Intelligence", html)
        self.assertIn("Queueing", html)
        self.assertIn("Bayesian", html)

    def test_has_stack_summary(self):
        from rcm_mc.ui.quant_lab_page import render_quant_lab
        from rcm_mc.ui.regression_page import _add_computed_features
        df = _add_computed_features(_sample_hcris(100))
        html = render_quant_lab(df)
        self.assertIn("Quant Stack", html)
        self.assertIn("ECONOMETRICS", html)
        self.assertIn("OPERATIONS RESEARCH", html)


class TestBayesianPage(unittest.TestCase):

    def test_renders_with_data(self):
        from rcm_mc.ui.bayesian_page import render_bayesian_profile
        html = render_bayesian_profile(
            "010001", "Test Hospital", 200, "AL",
            {"denial_rate": 0.12, "days_in_ar": 45, "claims_volume": 500})
        self.assertIn("Bayesian", html)
        self.assertIn("Posterior", html)
        self.assertIn("Shrinkage", html)

    def test_renders_with_no_data(self):
        from rcm_mc.ui.bayesian_page import render_bayesian_profile
        html = render_bayesian_profile("010001", "Test", 200, "AL", {})
        self.assertIn("Missing Data is Informative", html)
        self.assertIn("Prior Only", html)

    def test_suspicious_values_flagged(self):
        from rcm_mc.ui.bayesian_page import render_bayesian_profile
        html = render_bayesian_profile(
            "010001", "Test", 200, "AL",
            {"denial_rate": 0.001, "claims_volume": 100})
        self.assertIn("Suspicious", html)


if __name__ == "__main__":
    unittest.main()
