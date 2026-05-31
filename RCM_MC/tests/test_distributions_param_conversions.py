"""Tests for the parameter-conversion functions in core/distributions.

`rcm_mc/core/distributions.py` exposes 4 method-of-moments parameter
conversions used by every Monte Carlo run:

- ``beta_alpha_beta_from_mean_sd(mean, sd) → (a, b)``
- ``lognormal_mu_sigma_from_mean_sd(mean, sd) → (mu, sigma)``
- ``gamma_shape_scale_from_mean_sd(mean, sd) → (shape, scale)``
- ``triangular_mean_var(low, mode, high) → (mean, var)``

The high-level ``sample_dist`` and ``dist_moments`` are covered by
the property tests, but the underlying math conversions had no
direct unit tests. Bugs here would propagate silently into every
Monte Carlo result (wrong shape parameters → wrong distribution →
wrong tail risk). This file pins each conversion against textbook
identities + the explicit feasibility/clamping behavior the code
documents.
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from rcm_mc.core.distributions import (
    DistributionError,
    beta_alpha_beta_from_mean_sd,
    gamma_shape_scale_from_mean_sd,
    lognormal_mu_sigma_from_mean_sd,
    triangular_mean_var,
)


class BetaAlphaBetaFromMeanSdTests(unittest.TestCase):
    """Beta method-of-moments: mean = a/(a+b),
    var = a·b / ((a+b)²·(a+b+1))."""

    def test_recovers_mean(self):
        # For any valid (mean, sd) inside the feasibility region, the
        # back-computed mean a/(a+b) must equal the input mean.
        for mean, sd in [(0.5, 0.1), (0.2, 0.05), (0.8, 0.05),
                          (0.1, 0.02)]:
            a, b = beta_alpha_beta_from_mean_sd(mean, sd)
            recovered = a / (a + b)
            self.assertAlmostEqual(recovered, mean, places=5,
                                    msg=f"input mean={mean}")

    def test_recovers_variance_when_feasible(self):
        # If sd² < mean(1-mean) the variance is feasible; the
        # back-computed variance should equal sd² (not the clamp).
        for mean, sd in [(0.5, 0.1), (0.3, 0.05)]:
            a, b = beta_alpha_beta_from_mean_sd(mean, sd)
            recovered_var = (a * b) / ((a + b) ** 2 * (a + b + 1))
            self.assertAlmostEqual(recovered_var, sd * sd, places=5,
                                    msg=f"input sd={sd}")

    def test_alpha_and_beta_strictly_positive(self):
        # The numerical guard floors both at 1e-6 — guarantees the
        # returned shapes can be sampled.
        a, b = beta_alpha_beta_from_mean_sd(0.5, 0.4)
        self.assertGreater(a, 0)
        self.assertGreater(b, 0)

    def test_infeasible_variance_clamped(self):
        # sd² > mean(1-mean) is infeasible — code clamps to 0.95 ×
        # max_var to keep the run alive (validator warns upstream).
        mean = 0.5
        # max_var = 0.25; pick sd^2 way above (sd=1.0 → var=1.0)
        a, b = beta_alpha_beta_from_mean_sd(mean, 1.0)
        # Recovered variance is the clamp (0.95 × 0.25 = 0.2375),
        # not the user input.
        recovered_var = (a * b) / ((a + b) ** 2 * (a + b + 1))
        self.assertAlmostEqual(recovered_var, 0.95 * 0.25, places=5)
        # And mean is still recovered.
        self.assertAlmostEqual(a / (a + b), mean, places=5)

    def test_mean_at_or_below_zero_rejected(self):
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(0.0, 0.1)
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(-0.1, 0.1)

    def test_mean_at_or_above_one_rejected(self):
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(1.0, 0.1)
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(1.5, 0.1)

    def test_zero_or_negative_sd_rejected(self):
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(0.5, 0.0)
        with self.assertRaises(DistributionError):
            beta_alpha_beta_from_mean_sd(0.5, -0.1)


class LognormalMuSigmaFromMeanSdTests(unittest.TestCase):
    """Lognormal: parametrized by μ + σ of the underlying normal.
    mean = exp(μ + σ²/2); var = (exp(σ²) - 1) · exp(2μ + σ²)."""

    def test_recovers_mean_and_variance(self):
        # For each (mean, sd), back-compute and check identities.
        for mean, sd in [(100, 30), (50, 10), (1000, 100), (1, 0.1)]:
            mu, sigma = lognormal_mu_sigma_from_mean_sd(mean, sd)
            # Back-compute mean = exp(mu + sigma^2 / 2)
            back_mean = math.exp(mu + sigma * sigma / 2)
            self.assertAlmostEqual(back_mean, mean, places=4,
                                    msg=f"mean={mean}, sd={sd}")
            # Back-compute variance
            back_var = ((math.exp(sigma * sigma) - 1)
                        * math.exp(2 * mu + sigma * sigma))
            self.assertAlmostEqual(back_var, sd * sd, places=2,
                                    msg=f"var for mean={mean}, sd={sd}")

    def test_returns_python_floats(self):
        # Used in JSON / YAML config round-trips → must be plain
        # float, not numpy scalar (which json.dumps would reject).
        mu, sigma = lognormal_mu_sigma_from_mean_sd(100, 30)
        self.assertIsInstance(mu, float)
        self.assertIsInstance(sigma, float)

    def test_zero_or_negative_mean_rejected(self):
        # Lognormal is positive-support; mean<=0 is undefined.
        with self.assertRaises(DistributionError):
            lognormal_mu_sigma_from_mean_sd(0, 1)
        with self.assertRaises(DistributionError):
            lognormal_mu_sigma_from_mean_sd(-1, 1)

    def test_zero_or_negative_sd_rejected(self):
        with self.assertRaises(DistributionError):
            lognormal_mu_sigma_from_mean_sd(100, 0)
        with self.assertRaises(DistributionError):
            lognormal_mu_sigma_from_mean_sd(100, -1)

    def test_high_cv_produces_high_sigma(self):
        # Lognormal sigma grows with CV (coefficient of variation =
        # sd/mean). A very-spread sample has sigma>1.
        _, sigma_low = lognormal_mu_sigma_from_mean_sd(100, 5)   # CV 0.05
        _, sigma_high = lognormal_mu_sigma_from_mean_sd(100, 200)  # CV 2.0
        self.assertGreater(sigma_high, sigma_low)
        self.assertGreater(sigma_high, 1.0)


class GammaShapeScaleFromMeanSdTests(unittest.TestCase):
    """Gamma method-of-moments:
    mean = shape · scale; var = shape · scale²."""

    def test_recovers_mean_and_variance(self):
        for mean, sd in [(50, 15), (100, 30), (1000, 200), (1, 0.2)]:
            shape, scale = gamma_shape_scale_from_mean_sd(mean, sd)
            self.assertAlmostEqual(shape * scale, mean, places=5,
                                    msg=f"mean={mean}, sd={sd}")
            self.assertAlmostEqual(shape * scale * scale, sd * sd,
                                    places=4,
                                    msg=f"var for mean={mean}, sd={sd}")

    def test_returns_python_floats(self):
        shape, scale = gamma_shape_scale_from_mean_sd(100, 30)
        self.assertIsInstance(shape, float)
        self.assertIsInstance(scale, float)

    def test_zero_or_negative_mean_rejected(self):
        with self.assertRaises(DistributionError):
            gamma_shape_scale_from_mean_sd(0, 1)
        with self.assertRaises(DistributionError):
            gamma_shape_scale_from_mean_sd(-50, 1)

    def test_zero_or_negative_sd_rejected(self):
        with self.assertRaises(DistributionError):
            gamma_shape_scale_from_mean_sd(100, 0)
        with self.assertRaises(DistributionError):
            gamma_shape_scale_from_mean_sd(100, -10)

    def test_lower_cv_higher_shape(self):
        # As CV → 0 the gamma approaches a Dirac at the mean, with
        # shape → ∞. Verify the relationship qualitatively.
        shape_low_cv, _ = gamma_shape_scale_from_mean_sd(100, 1)     # CV 0.01
        shape_high_cv, _ = gamma_shape_scale_from_mean_sd(100, 50)   # CV 0.5
        self.assertGreater(shape_low_cv, shape_high_cv)


class TriangularMeanVarTests(unittest.TestCase):
    """Triangular: mean = (a+b+c)/3,
    var = (a² + b² + c² - ab - ac - bc) / 18."""

    def test_recovers_textbook_identities(self):
        # Symmetric triangle (mode = midpoint): mean = midpoint,
        # var = (high - low)² / 24
        mean, var = triangular_mean_var(0, 5, 10)
        self.assertAlmostEqual(mean, 5.0)
        self.assertAlmostEqual(var, 100 / 24, places=5)

    def test_degenerate_point_mass_has_zero_variance(self):
        # low == mode == high → variance = 0
        mean, var = triangular_mean_var(5, 5, 5)
        self.assertAlmostEqual(mean, 5.0)
        self.assertAlmostEqual(var, 0.0)

    def test_asymmetric_distribution(self):
        # Left-skewed triangle: mode at the low end.
        mean, var = triangular_mean_var(0, 0, 10)
        self.assertAlmostEqual(mean, 10 / 3, places=5)
        # Closed-form: var = (a² + b² + c² - ab - ac - bc) / 18
        # = (0 + 0 + 100 - 0 - 0 - 0) / 18 = 5.555...
        self.assertAlmostEqual(var, 100 / 18, places=5)

    def test_low_greater_than_mode_rejected(self):
        # The contract requires low <= mode <= high.
        with self.assertRaises(DistributionError):
            triangular_mean_var(10, 5, 20)

    def test_mode_greater_than_high_rejected(self):
        with self.assertRaises(DistributionError):
            triangular_mean_var(0, 15, 10)

    def test_low_greater_than_high_rejected(self):
        # Implicit: if low > mode > high or any reorder violates
        # the bound, DistributionError.
        with self.assertRaises(DistributionError):
            triangular_mean_var(10, 5, 0)

    def test_variance_invariant_under_translation(self):
        # Triangular variance only depends on (high-low) and the
        # relative position of mode. Translating all three by the
        # same offset shifts the mean by that offset but leaves
        # variance unchanged.
        m1, v1 = triangular_mean_var(0, 3, 10)
        m2, v2 = triangular_mean_var(100, 103, 110)
        self.assertAlmostEqual(m2 - m1, 100.0)
        self.assertAlmostEqual(v1, v2, places=5)


class CrossDistributionConsistencyTests(unittest.TestCase):
    """Sanity: parameters fed into the distribution generator
    actually produce samples whose moments match the inputs (this
    is what the conversion functions exist for)."""

    def test_beta_sample_moments_match(self):
        rng = np.random.default_rng(seed=42)
        mean, sd = 0.30, 0.10
        a, b = beta_alpha_beta_from_mean_sd(mean, sd)
        samples = rng.beta(a, b, size=20_000)
        # Empirical mean within 1% of target on 20k draws
        self.assertAlmostEqual(float(samples.mean()), mean, delta=0.005)
        self.assertAlmostEqual(float(samples.std()), sd, delta=0.005)

    def test_lognormal_sample_moments_match(self):
        rng = np.random.default_rng(seed=42)
        mean, sd = 100.0, 30.0
        mu, sigma = lognormal_mu_sigma_from_mean_sd(mean, sd)
        samples = rng.lognormal(mu, sigma, size=50_000)
        # Lognormal tail makes sample moments wobble more; loose deltas.
        self.assertAlmostEqual(
            float(samples.mean()), mean, delta=mean * 0.02)
        self.assertAlmostEqual(
            float(samples.std()), sd, delta=sd * 0.06)

    def test_gamma_sample_moments_match(self):
        rng = np.random.default_rng(seed=42)
        mean, sd = 50.0, 15.0
        shape, scale = gamma_shape_scale_from_mean_sd(mean, sd)
        samples = rng.gamma(shape, scale, size=20_000)
        self.assertAlmostEqual(
            float(samples.mean()), mean, delta=mean * 0.01)
        self.assertAlmostEqual(
            float(samples.std()), sd, delta=sd * 0.03)


if __name__ == "__main__":
    unittest.main()
