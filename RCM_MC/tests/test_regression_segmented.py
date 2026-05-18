"""Tests for the Phase-1 regression extensions:

- ``log_transform_target`` — fits ln(y), reports error metrics on raw scale.
- ``compute_vif`` — collinearity detection.
- ``run_segmented_regression`` — per-segment + baseline side-by-side.

These pin down the new contracts the regression page (Phase 2 PR)
will rely on so we can iterate the UI without re-litigating the
maths every refactor.
"""
import unittest

import numpy as np
import pandas as pd

from rcm_mc.finance.regression import (
    compute_vif,
    run_regression,
    run_segmented_regression,
)


class LogTransformTargetTests(unittest.TestCase):
    """When the target spans 6+ orders of magnitude (CAH $300K through
    academic $9B), raw-dollar OLS gives the largest hospitals
    overwhelming weight on the loss. Log-transform makes the
    question about percentage differences, which is the regime
    where rural-vs-academic comparisons make sense.
    """

    def setUp(self):
        # y = exp(2 + 0.3*x1 + 0.2*x2) + noise — perfectly fit by
        # OLS in log space, poorly fit in raw space.
        rng = np.random.default_rng(seed=42)
        n = 200
        x1 = rng.uniform(0, 10, n)
        x2 = rng.uniform(0, 5, n)
        y_log = 2.0 + 0.3 * x1 + 0.2 * x2 + rng.normal(0, 0.05, n)
        y = np.exp(y_log)
        self.df = pd.DataFrame({"y": y, "x1": x1, "x2": x2})

    def test_log_target_yields_higher_r_squared_than_raw(self):
        raw = run_regression(self.df, "y", ["x1", "x2"])
        logged = run_regression(self.df, "y", ["x1", "x2"],
                                log_transform_target=True)
        # Log fit should explain effectively all the variance
        self.assertGreater(logged.r_squared, 0.95)
        # And it should beat (or at least match) raw fit
        self.assertGreaterEqual(logged.r_squared, raw.r_squared)

    def test_log_target_recovers_known_semi_elasticities(self):
        res = run_regression(self.df, "y", ["x1", "x2"],
                             log_transform_target=True)
        coeffs = {c.variable: c.coefficient for c in res.coefficients}
        # Coefficients should be near the data-generating slopes
        self.assertAlmostEqual(coeffs["x1"], 0.3, places=2)
        self.assertAlmostEqual(coeffs["x2"], 0.2, places=2)

    def test_error_metrics_reported_in_fit_space_when_log(self):
        # When the fit is in log space, RMSE/MAE/target_mean are
        # reported in log space too — the naive exp() back-transform
        # is biased (Jensen's inequality) and quotes catastrophic-
        # looking dollar numbers that don't reflect actual prediction
        # quality. UI code computes raw-dollar mean off the frame.
        res = run_regression(self.df, "y", ["x1", "x2"],
                             log_transform_target=True)
        self.assertTrue(res.target_was_log_transformed)
        # target_mean should be the mean of LOG(y) in fit space
        self.assertAlmostEqual(
            res.target_mean,
            float(np.mean(np.log(self.df["y"]))),
            places=2,
        )
        self.assertGreater(res.rmse, 0)
        self.assertTrue(np.isfinite(res.rmse))
        # Sanity: log-space RMSE should be small (we set noise sd=0.05)
        self.assertLess(res.rmse, 0.1)

    def test_log_target_drops_nonpositive_rows(self):
        # Add a row with target = 0 — log_transform should drop it
        df = self.df.copy()
        df.loc[len(df)] = [0.0, 5.0, 2.5]
        res = run_regression(df, "y", ["x1", "x2"],
                             log_transform_target=True)
        # Drop the zero row; everything else still fits
        self.assertEqual(res.n_observations, len(self.df))


class VIFTests(unittest.TestCase):
    """The current portfolio regression page reports VIFs of 999 for
    medicare/medicaid/commercial day-pct (they sum to 100, so any
    one is determined by the other two) and 143 for beds vs
    bed_days_available. compute_vif should surface both cases.
    """

    def test_perfect_collinearity_returns_inf(self):
        # x3 = x1 + x2 exactly
        n = 100
        rng = np.random.default_rng(7)
        x1 = rng.uniform(0, 10, n)
        x2 = rng.uniform(0, 5, n)
        x3 = x1 + x2
        df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
        vifs = compute_vif(df)
        self.assertTrue(np.isinf(vifs["x3"]) or vifs["x3"] > 1e6,
                        f"expected near-infinite VIF for x3, got {vifs['x3']}")

    def test_uncorrelated_features_have_vif_near_one(self):
        rng = np.random.default_rng(11)
        n = 500
        df = pd.DataFrame({
            "a": rng.normal(0, 1, n),
            "b": rng.normal(0, 1, n),
            "c": rng.normal(0, 1, n),
        })
        vifs = compute_vif(df)
        for v in vifs.values():
            self.assertLess(v, 1.5, f"unexpectedly high VIF: {vifs}")

    def test_high_but_finite_correlation_yields_high_vif(self):
        # x2 = x1 + small noise → tight but not perfect collinearity
        rng = np.random.default_rng(13)
        n = 200
        x1 = rng.normal(0, 1, n)
        x2 = x1 + rng.normal(0, 0.05, n)
        x3 = rng.normal(0, 1, n)
        df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3})
        vifs = compute_vif(df)
        # x1 and x2 should have VIF >> 10; x3 should be near 1
        self.assertGreater(vifs["x1"], 10)
        self.assertGreater(vifs["x2"], 10)
        self.assertLess(vifs["x3"], 2)

    def test_empty_or_singleton_returns_empty(self):
        self.assertEqual(compute_vif(pd.DataFrame()), {})
        self.assertEqual(compute_vif(pd.DataFrame({"a": [1, 2, 3]})), {})


class SegmentedRegressionTests(unittest.TestCase):
    """The core Phase-1 contract: per-segment fits surface that
    different hospital regimes have different slopes. A synthetic
    two-regime dataset should produce a baseline R² lower than
    either segment's R² (segmentation buys explanatory power).
    """

    def setUp(self):
        rng = np.random.default_rng(seed=42)
        n_per = 200
        # Regime A: y = 10 + 2*x + noise
        xa = rng.uniform(0, 10, n_per)
        ya = 10 + 2.0 * xa + rng.normal(0, 0.5, n_per)
        # Regime B: y = 50 + 0.5*x + noise (much smaller slope on x)
        xb = rng.uniform(0, 10, n_per)
        yb = 50 + 0.5 * xb + rng.normal(0, 0.5, n_per)
        self.df = pd.DataFrame({
            "y": np.concatenate([ya, yb]),
            "x": np.concatenate([xa, xb]),
            "segment_label": ["A"] * n_per + ["B"] * n_per,
        })

    def test_baseline_and_per_segment_results_returned(self):
        res = run_segmented_regression(self.df, "y", ["x"])
        self.assertIsNotNone(res.baseline)
        self.assertIn("A", res.by_segment)
        self.assertIn("B", res.by_segment)
        self.assertEqual(res.segment_counts["A"], 200)
        self.assertEqual(res.segment_counts["B"], 200)

    def test_per_segment_r_squared_beats_baseline(self):
        res = run_segmented_regression(self.df, "y", ["x"])
        # The core contract: segmenting buys explanatory power.
        # Regime A has slope 2 (huge signal-to-noise) so its R²
        # is near-perfect; regime B has slope 0.5 (slope ≈ noise
        # scale) so its R² is moderate. Both should comfortably
        # beat the baseline that's trying to explain two different
        # regimes with one slope.
        self.assertGreater(res.by_segment["A"].r_squared, 0.95)
        self.assertGreater(res.by_segment["B"].r_squared, 0.85)
        self.assertLess(res.baseline.r_squared,
                        min(res.by_segment["A"].r_squared,
                            res.by_segment["B"].r_squared))

    def test_per_segment_coefficients_differ(self):
        res = run_segmented_regression(self.df, "y", ["x"])
        coef_a = res.by_segment["A"].coefficients[0].coefficient
        coef_b = res.by_segment["B"].coefficients[0].coefficient
        self.assertAlmostEqual(coef_a, 2.0, places=1)
        self.assertAlmostEqual(coef_b, 0.5, places=1)

    def test_small_segments_skipped_but_counted(self):
        # Add a "tiny" segment with only 5 rows
        small = pd.DataFrame({"y": [1, 2, 3, 4, 5],
                              "x": [1, 2, 3, 4, 5],
                              "segment_label": ["tiny"] * 5})
        df = pd.concat([self.df, small], ignore_index=True)
        res = run_segmented_regression(df, "y", ["x"], min_segment_rows=30)
        self.assertNotIn("tiny", res.by_segment)
        # But row count is still reported so the UI can show
        # "tiny: 5 rows, fit skipped"
        self.assertEqual(res.segment_counts["tiny"], 5)

    def test_missing_segment_column_raises(self):
        df = pd.DataFrame({"y": [1, 2, 3], "x": [4, 5, 6]})
        with self.assertRaises(ValueError):
            run_segmented_regression(df, "y", ["x"])

    def test_log_target_propagates_to_per_segment_fits(self):
        # Same data but as multiplicative regimes
        rng = np.random.default_rng(99)
        n = 200
        xa = rng.uniform(1, 10, n)
        ya = np.exp(1 + 0.3 * xa + rng.normal(0, 0.05, n))
        xb = rng.uniform(1, 10, n)
        yb = np.exp(3 + 0.1 * xb + rng.normal(0, 0.05, n))
        df = pd.DataFrame({
            "y": np.concatenate([ya, yb]),
            "x": np.concatenate([xa, xb]),
            "segment_label": ["A"] * n + ["B"] * n,
        })
        res = run_segmented_regression(df, "y", ["x"],
                                       log_transform_target=True)
        self.assertTrue(res.target_was_log_transformed)
        self.assertTrue(res.baseline.target_was_log_transformed)
        self.assertTrue(res.by_segment["A"].target_was_log_transformed)


if __name__ == "__main__":
    unittest.main()
