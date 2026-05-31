"""Tests for the RNG-based samplers in core/distributions.

`rcm_mc/core/distributions.py` ships two RNG-driven helpers used by
the simulator for parametric draws:

  - sample_dirichlet(rng, base_shares, concentration) — sample a
    random share vector around the base mix with controllable
    spread (high concentration → tight, low → wide)
  - sample_sum_iid_as_gamma(rng, per_unit_spec, n, min_total) —
    approximate the sum of n IID variables as a gamma matched on
    mean/variance (avoids per-claim simulation while preserving
    variability that scales with volume)

Both had zero direct test coverage. Bugs here propagate into every
payer-mix sampler and every volume-scaling step. This file pins
each function's contract.
"""
from __future__ import annotations

import math
import unittest

import numpy as np

from rcm_mc.core.distributions import (
    DistributionError,
    sample_dirichlet,
    sample_sum_iid_as_gamma,
)


class SampleDirichletTests(unittest.TestCase):
    """``sample_dirichlet`` — random share vector around a base mix."""

    def test_returns_dict_with_same_keys(self):
        rng = np.random.default_rng(42)
        base = {"Medicare": 0.4, "Medicaid": 0.2, "Commercial": 0.4}
        out = sample_dirichlet(rng, base, concentration=100)
        self.assertEqual(set(out.keys()), set(base.keys()))

    def test_shares_sum_to_one(self):
        rng = np.random.default_rng(42)
        base = {"a": 0.5, "b": 0.3, "c": 0.2}
        out = sample_dirichlet(rng, base, concentration=50)
        self.assertAlmostEqual(sum(out.values()), 1.0, places=6)

    def test_shares_are_non_negative_floats(self):
        rng = np.random.default_rng(42)
        base = {"a": 0.5, "b": 0.3, "c": 0.2}
        out = sample_dirichlet(rng, base, concentration=20)
        for v in out.values():
            self.assertIsInstance(v, float)
            self.assertGreaterEqual(v, 0.0)

    def test_high_concentration_stays_near_base(self):
        # concentration=10000 → very tight around base shares.
        # Average over many draws should be ≈ base.
        rng = np.random.default_rng(123)
        base = {"Medicare": 0.4, "Medicaid": 0.2, "Commercial": 0.4}
        means = {k: 0.0 for k in base}
        n_draws = 200
        for _ in range(n_draws):
            d = sample_dirichlet(rng, base, concentration=10_000)
            for k, v in d.items():
                means[k] += v / n_draws
        for k, v in base.items():
            self.assertAlmostEqual(means[k], v, delta=0.005)

    def test_low_concentration_spreads_wider(self):
        # concentration=1 → much wider spread than concentration=1000
        rng = np.random.default_rng(7)
        base = {"a": 0.5, "b": 0.5}
        spreads = {1: [], 1000: []}
        for c in (1, 1000):
            for _ in range(200):
                d = sample_dirichlet(rng, base, concentration=c)
                spreads[c].append(d["a"])
        self.assertGreater(np.std(spreads[1]), np.std(spreads[1000]))

    def test_non_normalized_base_normalized_internally(self):
        # Base shares that don't sum to 1 are normalized.
        rng = np.random.default_rng(42)
        out = sample_dirichlet(
            rng,
            {"a": 4, "b": 2, "c": 4},  # sums to 10
            concentration=10_000,
        )
        # Mean over many draws should reflect normalized base
        # (0.4, 0.2, 0.4). Single draw with high concentration
        # is already very tight.
        self.assertAlmostEqual(out["a"], 0.4, delta=0.02)
        self.assertAlmostEqual(out["b"], 0.2, delta=0.02)
        self.assertAlmostEqual(out["c"], 0.4, delta=0.02)

    def test_negative_share_rejected(self):
        rng = np.random.default_rng(42)
        with self.assertRaises(DistributionError):
            sample_dirichlet(rng, {"a": 0.5, "b": -0.1}, concentration=10)

    def test_zero_sum_rejected(self):
        rng = np.random.default_rng(42)
        with self.assertRaises(DistributionError):
            sample_dirichlet(rng, {"a": 0.0, "b": 0.0}, concentration=10)

    def test_zero_or_negative_concentration_rejected(self):
        rng = np.random.default_rng(42)
        with self.assertRaises(DistributionError):
            sample_dirichlet(rng, {"a": 0.5, "b": 0.5}, concentration=0)
        with self.assertRaises(DistributionError):
            sample_dirichlet(rng, {"a": 0.5, "b": 0.5}, concentration=-5)

    def test_deterministic_with_seed(self):
        # Same seed + same call → identical output.
        base = {"a": 0.5, "b": 0.3, "c": 0.2}
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        self.assertEqual(
            sample_dirichlet(rng1, base, concentration=10),
            sample_dirichlet(rng2, base, concentration=10),
        )


class SampleSumIidAsGammaTests(unittest.TestCase):
    """``sample_sum_iid_as_gamma`` — gamma approximation of a sum
    of N IID variables, matched on mean and variance."""

    def test_returns_float(self):
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 30}
        out = sample_sum_iid_as_gamma(rng, spec, n=10)
        self.assertIsInstance(out, float)

    def test_sample_mean_approaches_n_times_mu(self):
        # Average over many draws of the sum should be ≈ n × mu.
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 30}
        n = 100
        draws = [sample_sum_iid_as_gamma(rng, spec, n=n)
                 for _ in range(500)]
        # Expected sum mean = 100 × 100 = 10_000
        empirical = float(np.mean(draws))
        self.assertAlmostEqual(empirical, n * 100,
                                delta=0.02 * n * 100)

    def test_sample_variance_scales_with_n(self):
        # var(sum) = n × var(unit); std(sum) = sqrt(n) × sd(unit).
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 30}
        for n in (10, 100, 1000):
            draws = [sample_sum_iid_as_gamma(rng, spec, n=n)
                     for _ in range(300)]
            empirical_std = float(np.std(draws))
            expected_std = math.sqrt(n) * 30
            # Loose delta: lognormal tail + small N inflates wobble.
            self.assertAlmostEqual(
                empirical_std, expected_std,
                delta=0.30 * expected_std)

    def test_zero_n_returns_zero_or_min(self):
        # n=0 → mean_sum=0 → returns 0 (or min_total, if higher).
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 30}
        self.assertEqual(sample_sum_iid_as_gamma(rng, spec, n=0), 0.0)
        # min_total floor applies.
        self.assertEqual(
            sample_sum_iid_as_gamma(rng, spec, n=0, min_total=50.0),
            50.0)

    def test_negative_n_treated_as_zero(self):
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 30}
        # n=-5 → max(n, 0) → 0 → returns 0.
        self.assertEqual(
            sample_sum_iid_as_gamma(rng, spec, n=-5), 0.0)

    def test_fixed_distribution_returns_exact_n_times_mean(self):
        # fixed value has zero variance → no gamma sampling, just
        # return n × mean directly.
        rng = np.random.default_rng(42)
        spec = {"dist": "fixed", "value": 42.0}
        for n in (1, 5, 100):
            out = sample_sum_iid_as_gamma(rng, spec, n=n)
            self.assertAlmostEqual(out, n * 42.0)

    def test_min_total_floor_applied(self):
        # Even with sampling, if the gamma draw < min_total, the
        # floor takes effect.
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 10, "sd": 1}
        # n=1 → mean_sum=10; min_total=1000 → should be ≥1000.
        for _ in range(10):
            out = sample_sum_iid_as_gamma(
                rng, spec, n=1, min_total=1000.0)
            self.assertGreaterEqual(out, 1000.0)

    def test_returns_non_negative(self):
        # Gamma is positive-support; the function must never return
        # a negative number.
        rng = np.random.default_rng(42)
        spec = {"dist": "lognormal", "mean": 100, "sd": 50}
        for _ in range(20):
            self.assertGreaterEqual(
                sample_sum_iid_as_gamma(rng, spec, n=10), 0.0)


if __name__ == "__main__":
    unittest.main()
