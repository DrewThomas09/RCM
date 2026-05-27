"""Shapley / LMG decomposition of regression R² into per-driver shares.

The defining property is exact additivity: the per-feature shares must sum to
the full-model R². We also check the two qualitative properties a partner
relies on — correlated drivers with equal effect split their shared variance
evenly (no double-counting), and an irrelevant feature gets ~0 — plus the
feature cap and degenerate safety. No scipy; OLS via lstsq.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.regression import (
    _subset_r2,
    shapley_r2_decomposition,
)
from rcm_mc.ui.regression_page import _run_ols


class ShapleyR2(unittest.TestCase):
    def test_shares_sum_to_full_r2(self):
        rng = np.random.default_rng(1)
        n = 1500
        x1 = rng.normal(0, 1, n)
        x2 = rng.normal(0, 1, n)
        x3 = rng.normal(0, 1, n)
        X = np.column_stack([x1, x2, x3])
        y = 1.0 * x1 + 2.0 * x2 + 0.5 * x3 + rng.normal(0, 1, n)
        dec = shapley_r2_decomposition(X, y, ["x1", "x2", "x3"])
        full = _subset_r2(X, y)
        self.assertIsNotNone(dec)
        self.assertAlmostEqual(sum(d["r2_share"] for d in dec), full, places=6)
        self.assertAlmostEqual(sum(d["pct_of_r2"] for d in dec), 100.0, places=2)

    def test_all_shares_nonnegative(self):
        rng = np.random.default_rng(2)
        n = 800
        X = rng.normal(0, 1, (n, 4))
        y = X @ np.array([1.0, -1.0, 0.5, 2.0]) + rng.normal(0, 1, n)
        dec = shapley_r2_decomposition(X, y, ["a", "b", "c", "d"])
        for d in dec:
            self.assertGreaterEqual(d["r2_share"], -1e-9, f"{d['feature']} negative")

    def test_correlated_equal_drivers_split_evenly(self):
        # x1 and x2 are noisy copies of a latent z with equal true effect →
        # their shares should be close (the no-double-counting property),
        # whereas a univariate r would credit each nearly fully.
        rng = np.random.default_rng(3)
        n = 4000
        z = rng.normal(0, 1, n)
        x1 = z + rng.normal(0, 0.5, n)
        x2 = z + rng.normal(0, 0.5, n)
        X = np.column_stack([x1, x2])
        y = 1.0 * x1 + 1.0 * x2 + rng.normal(0, 1, n)
        dec = {d["feature"]: d["r2_share"] for d in
               shapley_r2_decomposition(X, y, ["x1", "x2"])}
        self.assertAlmostEqual(dec["x1"], dec["x2"], delta=0.05)

    def test_irrelevant_feature_gets_near_zero(self):
        rng = np.random.default_rng(4)
        n = 2000
        x1 = rng.normal(0, 1, n)
        noise = rng.normal(0, 1, n)
        X = np.column_stack([x1, noise])
        y = 2.0 * x1 + rng.normal(0, 1, n)        # noise has no true effect
        dec = {d["feature"]: d["pct_of_r2"] for d in
               shapley_r2_decomposition(X, y, ["x1", "noise"])}
        self.assertGreater(dec["x1"], 90.0)
        self.assertLess(dec["noise"], 10.0)

    def test_sorted_descending(self):
        rng = np.random.default_rng(5)
        n = 600
        X = rng.normal(0, 1, (n, 3))
        y = X @ np.array([0.3, 3.0, 1.0]) + rng.normal(0, 1, n)
        dec = shapley_r2_decomposition(X, y, ["a", "b", "c"])
        shares = [d["r2_share"] for d in dec]
        self.assertEqual(shares, sorted(shares, reverse=True))

    def test_feature_cap_returns_none(self):
        rng = np.random.default_rng(6)
        n = 400
        X = rng.normal(0, 1, (n, 9))
        y = rng.normal(0, 1, n)
        self.assertIsNone(
            shapley_r2_decomposition(X, y, [f"f{i}" for i in range(9)],
                                     max_features=8))

    def test_degenerate_safe(self):
        rng = np.random.default_rng(7)
        self.assertIsNone(shapley_r2_decomposition(
            np.empty((10, 0)), rng.normal(0, 1, 10), []))
        # mismatched names
        self.assertIsNone(shapley_r2_decomposition(
            rng.normal(0, 1, (10, 2)), rng.normal(0, 1, 10), ["only_one"]))


class RunOLSExposesShapley(unittest.TestCase):
    def test_result_carries_shapley(self):
        rng = np.random.default_rng(7)
        n = 300
        x = rng.normal(100, 20, n)
        df = pd.DataFrame({
            "beds": x,
            "operating_expenses": x * 1000 + rng.normal(0, 4000, n),
            "net_patient_revenue": x * 900 + rng.normal(0, 8000, n),
        })
        res = _run_ols(df, "net_patient_revenue", ["beds", "operating_expenses"])
        self.assertIsNotNone(res)
        self.assertIn("shapley_r2", res)
        self.assertIsNotNone(res["shapley_r2"])
        self.assertAlmostEqual(
            sum(d["r2_share"] for d in res["shapley_r2"]), res["r2"], places=5)


if __name__ == "__main__":
    unittest.main()
