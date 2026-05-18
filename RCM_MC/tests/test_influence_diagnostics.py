"""Tests for Phase-4B influence diagnostics.

Pins:
  - Leverage h_ii sums to p+1 (one per coefficient including intercept)
  - Cook's D is symmetric and finite for a clean fit
  - High-Cook's-D rows are correctly classified by segment
    (Academic / Flagship Specialty / Children's → "legitimate but
    different class", not "data issue")
  - Acquisition-target segments with high positive residuals get
    flagged as "possible_opportunity"
  - data_issue fires for big y-outliers with low leverage
  - in_band returned for rows below every threshold
"""
import unittest

import numpy as np

from rcm_mc.finance.influence import (
    classify_influence_point,
    compute_influence,
    influence_points,
    top_influential,
)


def _fit_ols(X, y):
    X_aug = np.column_stack([np.ones(len(X)), X])
    beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
    return beta, X_aug @ beta


class LeverageSumTests(unittest.TestCase):
    """For OLS with intercept, sum of h_ii = p + 1 (degrees of freedom
    used by the fit). Canonical identity — useful as a sanity check
    that the hat-matrix computation is correct.
    """

    def test_leverage_sums_to_p_plus_1(self):
        rng = np.random.default_rng(7)
        n, p = 200, 5
        X = rng.normal(0, 1, (n, p))
        y = rng.normal(0, 1, n)
        _, y_hat = _fit_ols(X, y)
        leverage, _, _ = compute_influence(X, y, y_hat)
        self.assertAlmostEqual(
            float(np.sum(leverage)), p + 1, places=4,
        )

    def test_leverage_in_zero_one(self):
        rng = np.random.default_rng(11)
        n, p = 300, 3
        X = rng.normal(0, 1, (n, p))
        y = rng.normal(0, 1, n)
        _, y_hat = _fit_ols(X, y)
        leverage, _, _ = compute_influence(X, y, y_hat)
        self.assertTrue((leverage >= 0).all())
        self.assertTrue((leverage <= 1 + 1e-9).all())


class CooksDistanceTests(unittest.TestCase):
    def test_finite_cooks_d_on_clean_fit(self):
        rng = np.random.default_rng(13)
        n, p = 200, 3
        X = rng.normal(0, 1, (n, p))
        y = 1 + X[:, 0] + 0.5 * X[:, 1] + rng.normal(0, 0.5, n)
        _, y_hat = _fit_ols(X, y)
        _, _, cooks = compute_influence(X, y, y_hat)
        self.assertTrue(np.all(np.isfinite(cooks)))
        # No row should be wildly influential on a clean fit
        self.assertTrue(cooks.max() < 0.5,
                        f"max Cook's = {cooks.max()}")

    def test_injected_outlier_dominates_cooks(self):
        # Inject a high-leverage + high-residual point — its Cook's
        # D should dwarf the rest.
        rng = np.random.default_rng(17)
        n, p = 100, 2
        X = rng.normal(0, 1, (n, p))
        y = X[:, 0] + 0.5 * X[:, 1] + rng.normal(0, 0.3, n)
        # Outlier at (x=10, x=10) with y=100 — far from any other row
        X[-1] = [10.0, 10.0]
        y[-1] = 100.0
        _, y_hat = _fit_ols(X, y)
        _, _, cooks = compute_influence(X, y, y_hat)
        # The injected point has by far the largest Cook's D
        self.assertEqual(int(np.argmax(cooks)), n - 1)
        self.assertGreater(cooks[-1], 10 * np.median(cooks))


class ClassificationTests(unittest.TestCase):
    """Map Cook's / leverage / residual / segment to a partner-facing
    classification."""

    def _classify(self, cooks=0.1, leverage=0.05,
                  stud=0.5, n=100, p=5, segment=None):
        return classify_influence_point(
            leverage, stud, cooks, n, p, segment=segment,
        )

    def test_high_cooks_academic_is_legitimate_but_different(self):
        # Cook's > 1, Academic segment → "legitimate but different class"
        cls, sev = self._classify(cooks=2.5, segment="Academic")
        self.assertEqual(cls, "legitimate_but_different_class")
        self.assertEqual(sev, "critical")

    def test_high_cooks_flagship_specialty_legitimate(self):
        cls, _ = self._classify(cooks=1.5, segment="Flagship Specialty")
        self.assertEqual(cls, "legitimate_but_different_class")

    def test_high_cooks_no_segment_is_high_influence(self):
        # Same Cook's but no segment info → fall back to high_influence
        cls, sev = self._classify(cooks=2.0, segment=None)
        self.assertEqual(cls, "high_influence")
        self.assertEqual(sev, "critical")

    def test_acquisition_target_big_positive_residual_is_opportunity(self):
        # Cook's > 1, Large Community segment, big positive resid
        cls, sev = self._classify(
            cooks=1.5, stud=4.5, segment="Large Community",
        )
        self.assertEqual(cls, "possible_opportunity")
        self.assertEqual(sev, "critical")

    def test_data_issue_for_low_leverage_big_residual(self):
        # Cook's > 1, low leverage, big residual, no special segment
        cls, _ = self._classify(
            cooks=1.5, leverage=0.01, stud=5.0, segment="Other",
        )
        self.assertEqual(cls, "data_issue")

    def test_warning_cooks_above_4_over_n(self):
        # Cook's > 4/n but < 1 → warning severity
        cls, sev = self._classify(cooks=0.08, n=100, segment=None)
        # 4/100 = 0.04, 0.08 > threshold
        self.assertIn(cls, ("high_influence", "data_issue"))
        self.assertEqual(sev, "warning")

    def test_in_band_for_clean_row(self):
        # Low Cook's, low leverage, normal residual → in_band
        cls, sev = self._classify(
            cooks=0.01, leverage=0.02, stud=0.5,
            n=100, p=3, segment="Large Community",
        )
        self.assertEqual(cls, "in_band")
        self.assertEqual(sev, "ok")

    def test_nan_inputs_return_unknown(self):
        cls, sev = self._classify(
            cooks=float("nan"), leverage=float("nan"),
        )
        self.assertEqual(cls, "unknown")
        self.assertEqual(sev, "info")


class InfluencePointsIntegrationTests(unittest.TestCase):
    def test_full_pipeline_returns_per_row_records(self):
        rng = np.random.default_rng(23)
        n, p = 100, 3
        X = rng.normal(0, 1, (n, p))
        y = X[:, 0] + rng.normal(0, 0.3, n)
        _, y_hat = _fit_ols(X, y)
        # Tag every row with a segment
        segments = (["Academic"] * 10 +
                    ["Large Community"] * 60 +
                    ["Critical Access"] * 30)
        pts = influence_points(X, y, y_hat,
                               segment_per_row=segments)
        self.assertEqual(len(pts), n)
        # Every point should have all four numbers
        for pt in pts:
            self.assertTrue(np.isfinite(pt.leverage))
            self.assertTrue(np.isfinite(pt.cooks_d))
            self.assertIn(pt.severity,
                          {"critical", "warning", "info", "ok"})

    def test_top_influential_returns_sorted_subset(self):
        rng = np.random.default_rng(29)
        n, p = 50, 2
        X = rng.normal(0, 1, (n, p))
        y = X[:, 0] + rng.normal(0, 0.3, n)
        # Inject a clearly-influential row
        X[0] = [8.0, 8.0]
        y[0] = 50.0
        _, y_hat = _fit_ols(X, y)
        pts = influence_points(X, y, y_hat)
        top = top_influential(pts, limit=5)
        self.assertEqual(len(top), 5)
        # The injected row should be #1
        self.assertEqual(top[0].index, 0)
        # Sorted by Cook's D descending
        cooks_d_seq = [p.cooks_d for p in top]
        self.assertEqual(cooks_d_seq, sorted(cooks_d_seq, reverse=True))


class PerfectLeverageOverflowTests(unittest.TestCase):
    """User-reported bug: Cook's D rendered as 4,891,622,318,067,742
    (1e18) for a row whose leverage was ≈ 1.0. The divisor in the
    Cook's-D formula was clamped to 1e-9, producing exponentially
    large values. Rows with leverage > 0.99 now NaN out and
    classify as ``perfect_leverage`` instead.
    """

    def test_perfect_leverage_row_produces_nan_not_huge_number(self):
        # Inject a row whose features are far from all others
        rng = np.random.default_rng(7)
        n, p = 50, 3
        X = rng.normal(0, 1, (n, p))
        y = X[:, 0] + rng.normal(0, 0.3, n)
        X[0] = [50.0, 50.0, 50.0]  # geometrically isolated
        y[0] = 100.0
        _, y_hat = _fit_ols(X, y)
        leverage, stud, cooks = compute_influence(X, y, y_hat)
        # Row 0 should have leverage ≈ 1 → NaN'd cooks_d
        self.assertGreater(leverage[0], 0.99)
        self.assertTrue(np.isnan(cooks[0]))
        self.assertTrue(np.isnan(stud[0]))
        # No row anywhere should have a > 1000 Cook's D
        finite = cooks[np.isfinite(cooks)]
        if len(finite) > 0:
            self.assertLessEqual(float(finite.max()), 1000.0)

    def test_classifier_returns_perfect_leverage(self):
        # leverage > 0.99 → perfect_leverage classification, even
        # if cooks_d and stud_resid are NaN
        cls, sev = classify_influence_point(
            leverage=0.999, studentized_residual=float("nan"),
            cooks_d=float("nan"), n=100, p=5, segment="Small Community",
        )
        self.assertEqual(cls, "perfect_leverage")
        self.assertEqual(sev, "critical")

    def test_normal_leverage_unaffected(self):
        # Sanity: rows in normal leverage range still classify as before
        cls, _ = classify_influence_point(
            leverage=0.3, studentized_residual=4.0, cooks_d=2.0,
            n=100, p=5, segment="Academic",
        )
        self.assertEqual(cls, "legitimate_but_different_class")


if __name__ == "__main__":
    unittest.main()
