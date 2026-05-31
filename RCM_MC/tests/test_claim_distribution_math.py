"""Tests for the per-claim-size denial-pricing math.

`rcm_mc/rcm/claim_distribution.py` ships 4 pure-math public
functions used by the Monte Carlo simulator to model "denial rate
is higher for big claims" — a real RCM observation that lifts tail
risk. The integration test (test_claim_distribution.py) exercises
the whole simulator path; these tests cover each function directly.

  - lognormal_mu_sigma_from_mean_cv  (parameter conversion from CV)
  - build_lognormal_claim_buckets    (quantile-based discretization)
  - solve_alpha_for_target_mean      (bisection solver)
  - denial_rate_by_bucket            (logistic pricing curve)
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from rcm_mc.rcm.claim_distribution import (
    ClaimBucket,
    build_lognormal_claim_buckets,
    denial_rate_by_bucket,
    lognormal_mu_sigma_from_mean_cv,
    solve_alpha_for_target_mean,
)


class LognormalMuSigmaFromMeanCvTests(unittest.TestCase):
    """Different from the core/distributions version: this one takes
    coefficient-of-variation (sd/mean) instead of raw sd."""

    def test_back_compute_mean(self):
        # mean = exp(mu + sigma²/2). For lognormal with CV=k,
        # sigma² = log(k²+1), mu = log(mean) - sigma²/2.
        for mean, cv in [(100, 0.30), (50, 1.0), (1000, 0.10)]:
            mu, sigma = lognormal_mu_sigma_from_mean_cv(mean, cv)
            back_mean = math.exp(mu + sigma * sigma / 2)
            self.assertAlmostEqual(back_mean, mean, places=3,
                                    msg=f"mean={mean}, cv={cv}")

    def test_back_compute_cv(self):
        # CV = sd/mean; sd² = (e^σ² - 1) · e^(2μ+σ²)
        # so CV² = (e^σ² - 1) → σ² = log(CV²+1)
        for mean, cv in [(100, 0.30), (50, 1.0), (1000, 0.10)]:
            mu, sigma = lognormal_mu_sigma_from_mean_cv(mean, cv)
            back_cv = math.sqrt(math.exp(sigma * sigma) - 1)
            self.assertAlmostEqual(back_cv, cv, places=3,
                                    msg=f"mean={mean}, cv={cv}")

    def test_floors_against_underflow(self):
        # Code clamps mean→1e-9 and cv→1e-6 to avoid log(0).
        # Tiny inputs must not blow up.
        mu1, sigma1 = lognormal_mu_sigma_from_mean_cv(0, 0)
        self.assertTrue(math.isfinite(mu1))
        self.assertTrue(math.isfinite(sigma1))
        mu2, sigma2 = lognormal_mu_sigma_from_mean_cv(-1, -1)
        self.assertTrue(math.isfinite(mu2))
        self.assertTrue(math.isfinite(sigma2))

    def test_returns_python_floats(self):
        mu, sigma = lognormal_mu_sigma_from_mean_cv(100, 0.3)
        self.assertIsInstance(mu, float)
        self.assertIsInstance(sigma, float)


class BuildLognormalClaimBucketsTests(unittest.TestCase):
    """The simulator's quantile-based discretization of the
    lognormal claim-size distribution."""

    def test_returns_correct_bucket_count(self):
        # N quantile edges produce N-1 buckets.
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.5,
            quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
        )
        self.assertEqual(len(bks), 4)

    def test_each_bucket_is_a_claimbucket(self):
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.5, quantiles=[0.0, 0.5, 1.0],
        )
        for b in bks:
            self.assertIsInstance(b, ClaimBucket)
            self.assertGreaterEqual(b.share_claims, 0)
            self.assertGreaterEqual(b.share_dollars, 0)
            self.assertGreater(b.mean_amount, 0)

    def test_share_claims_sum_to_one(self):
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.5,
            quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
        )
        self.assertAlmostEqual(
            sum(b.share_claims for b in bks), 1.0, places=4)

    def test_share_dollars_sum_to_one(self):
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.5,
            quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
        )
        self.assertAlmostEqual(
            sum(b.share_dollars for b in bks), 1.0, places=4)

    def test_high_cv_top_bucket_holds_disproportionate_dollars(self):
        # Lognormal is right-skewed; high CV → top quartile holds
        # more than its 25% share of total dollars.
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=1.5,
            quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
        )
        top = bks[-1]
        self.assertEqual(top.q_low, 0.75)
        self.assertEqual(top.q_high, 1.0)
        # Top quartile of CLAIMS, but holds way more than 25% of
        # dollars under high CV.
        self.assertGreater(top.share_dollars, 0.50)

    def test_uniform_buckets_for_low_cv(self):
        # CV very small → distribution is nearly point-mass at mean
        # → share_dollars within each bucket ≈ share_claims.
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.01,
            quantiles=[0.0, 0.25, 0.50, 0.75, 1.0],
        )
        for b in bks:
            self.assertAlmostEqual(b.share_dollars, b.share_claims,
                                    delta=0.01)

    def test_mean_amounts_strictly_increasing(self):
        # Bucket means must be monotone non-decreasing in quantile.
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.8,
            quantiles=[0.0, 0.20, 0.40, 0.60, 0.80, 1.0],
        )
        means = [b.mean_amount for b in bks]
        self.assertEqual(means, sorted(means))

    def test_q_low_q_high_match_quantile_edges(self):
        qs = [0.0, 0.10, 0.50, 0.90, 1.0]
        bks = build_lognormal_claim_buckets(
            mean=1000, cv=0.5, quantiles=qs,
        )
        for i, b in enumerate(bks):
            self.assertAlmostEqual(b.q_low, qs[i])
            self.assertAlmostEqual(b.q_high, qs[i + 1])
            self.assertEqual(b.idx, i)

    def test_too_few_quantiles_raises(self):
        # Need ≥3 quantiles to define ≥2 buckets.
        with self.assertRaises(ValueError):
            build_lognormal_claim_buckets(
                mean=1000, cv=0.5, quantiles=[0.0, 1.0])

    def test_quantile_endpoints_required(self):
        with self.assertRaises(ValueError):
            build_lognormal_claim_buckets(
                mean=1000, cv=0.5, quantiles=[0.1, 0.5, 1.0])
        with self.assertRaises(ValueError):
            build_lognormal_claim_buckets(
                mean=1000, cv=0.5, quantiles=[0.0, 0.5, 0.9])

    def test_deterministic_for_same_seed(self):
        # Caching + fixed seed → identical buckets across calls.
        b1 = build_lognormal_claim_buckets(
            mean=1000, cv=0.5,
            quantiles=[0.0, 0.5, 1.0], seed=42)
        b2 = build_lognormal_claim_buckets(
            mean=1000, cv=0.5,
            quantiles=[0.0, 0.5, 1.0], seed=42)
        for x, y in zip(b1, b2):
            self.assertEqual(x.mean_amount, y.mean_amount)


class SolveAlphaForTargetMeanTests(unittest.TestCase):
    """Bisection: find α such that Σ wᵢ · sigmoid(α + β·xᵢ) = target."""

    def test_solves_to_target(self):
        # With β=0 the solution is α = logit(target). Verify:
        x = np.array([0.0, 1.0, 2.0])
        w = np.array([1.0, 1.0, 1.0])
        for target in [0.10, 0.30, 0.50, 0.80]:
            alpha = solve_alpha_for_target_mean(
                target=target, beta=0.0, x=x, w=w)
            achieved = float(np.mean(1.0 / (1.0 + np.exp(-alpha))))
            self.assertAlmostEqual(achieved, target, places=4,
                                    msg=f"target={target}")

    def test_solves_with_nonzero_beta(self):
        # Non-trivial slope on x; bisection should still converge.
        rng = np.random.default_rng(42)
        x = rng.standard_normal(50)
        w = np.ones(50) / 50
        alpha = solve_alpha_for_target_mean(
            target=0.25, beta=0.5, x=x, w=w)
        achieved = float(
            np.sum(w * (1.0 / (1.0 + np.exp(-(alpha + 0.5 * x))))))
        self.assertAlmostEqual(achieved, 0.25, places=3)

    def test_target_clamped_into_open_interval(self):
        # target ∈ {0, 1} would require α = ±∞; code clamps into
        # (1e-9, 1-1e-9). The solver should still return without
        # raising.
        x = np.array([0.0, 1.0])
        w = np.array([1.0, 1.0])
        alpha_lo = solve_alpha_for_target_mean(
            target=0.0, beta=0.0, x=x, w=w)
        alpha_hi = solve_alpha_for_target_mean(
            target=1.0, beta=0.0, x=x, w=w)
        # Saturation: lo → very negative α, hi → very positive α
        self.assertLess(alpha_lo, alpha_hi)

    def test_weights_normalized_internally(self):
        # The solver internally normalizes weights — passing
        # un-normalized weights must produce the same answer as
        # normalized.
        x = np.array([0.0, 1.0, 2.0])
        w_norm = np.array([0.333, 0.333, 0.333])
        w_un = np.array([10.0, 10.0, 10.0])
        alpha_a = solve_alpha_for_target_mean(
            target=0.25, beta=0.5, x=x, w=w_norm)
        alpha_b = solve_alpha_for_target_mean(
            target=0.25, beta=0.5, x=x, w=w_un)
        self.assertAlmostEqual(alpha_a, alpha_b, places=4)

    def test_zero_weights_safe(self):
        # All-zero weights → degenerate; solver dodges divide-by-zero
        # and returns SOMETHING (the mid of the search interval).
        # Must not raise.
        x = np.array([0.0, 1.0])
        w = np.array([0.0, 0.0])
        alpha = solve_alpha_for_target_mean(
            target=0.3, beta=0.0, x=x, w=w)
        self.assertTrue(math.isfinite(alpha))


class DenialRateByBucketTests(unittest.TestCase):
    """End-to-end pricing: bucket-level denial rates that average
    back to idr_base."""

    def test_weighted_average_recovers_idr_base(self):
        # The whole point: ΣWᵢ · denial_iᵢ ≈ idr_base.
        bucket_means = [500.0, 1500.0, 5000.0, 20_000.0]
        weights = [0.5, 0.30, 0.15, 0.05]
        rates = denial_rate_by_bucket(
            idr_base=0.10,
            bucket_mean_amounts=bucket_means,
            avg_claim=2_000.0,
            beta=0.5,
            bucket_weights=weights,
        )
        recovered = float(np.sum(np.array(weights) * rates))
        self.assertAlmostEqual(recovered, 0.10, places=3)

    def test_higher_beta_steeper_curve(self):
        # Larger β → bigger spread between low-bucket and
        # high-bucket denial rates.
        bucket_means = [500.0, 5000.0]
        weights = [0.5, 0.5]
        flat = denial_rate_by_bucket(
            idr_base=0.10, bucket_mean_amounts=bucket_means,
            avg_claim=2_000.0, beta=0.1,
            bucket_weights=weights,
        )
        steep = denial_rate_by_bucket(
            idr_base=0.10, bucket_mean_amounts=bucket_means,
            avg_claim=2_000.0, beta=1.5,
            bucket_weights=weights,
        )
        # Spread between buckets bigger when β bigger.
        flat_spread = abs(flat[1] - flat[0])
        steep_spread = abs(steep[1] - steep[0])
        self.assertGreater(steep_spread, flat_spread)

    def test_positive_beta_higher_for_big_claims(self):
        # With positive β + log-amount feature, bigger claims get
        # higher denial rates.
        bucket_means = [100.0, 10_000.0]
        weights = [0.5, 0.5]
        rates = denial_rate_by_bucket(
            idr_base=0.10, bucket_mean_amounts=bucket_means,
            avg_claim=1_000.0, beta=0.5,
            bucket_weights=weights,
        )
        # Bucket 1 (big claims) > bucket 0 (small claims)
        self.assertGreater(rates[1], rates[0])

    def test_rates_clipped_to_0_98(self):
        # Cap at 0.98 — never show a partner 'this claim has 100%
        # denial probability'.
        bucket_means = [1e9]  # extreme outlier
        weights = [1.0]
        rates = denial_rate_by_bucket(
            idr_base=0.50, bucket_mean_amounts=bucket_means,
            avg_claim=1_000.0, beta=10.0,
            bucket_weights=weights,
        )
        for r in rates:
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 0.98)

    def test_avg_claim_floored(self):
        # avg_claim=0 would crash log(0) — code floors at 1e-9.
        bucket_means = [100.0, 1000.0]
        weights = [0.5, 0.5]
        rates = denial_rate_by_bucket(
            idr_base=0.10, bucket_mean_amounts=bucket_means,
            avg_claim=0, beta=0.5,
            bucket_weights=weights,
        )
        for r in rates:
            self.assertTrue(math.isfinite(r))


if __name__ == "__main__":
    unittest.main()
