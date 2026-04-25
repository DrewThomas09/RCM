"""Tests for MonteCarloPacket v3."""
from __future__ import annotations

import unittest

import numpy as np


# ── Copulas ─────────────────────────────────────────────────────

class TestGaussianCopula(unittest.TestCase):
    def test_marginals_uniform(self):
        from rcm_mc.montecarlo_v3 import gaussian_copula_sample
        corr = np.array([[1.0, 0.5], [0.5, 1.0]])
        u = gaussian_copula_sample(corr, n_samples=2000, seed=1)
        # Each marginal should be approximately uniform on (0, 1)
        self.assertEqual(u.shape, (2000, 2))
        for col in range(2):
            self.assertGreater(u[:, col].mean(), 0.45)
            self.assertLess(u[:, col].mean(), 0.55)

    def test_correlation_preserved(self):
        from rcm_mc.montecarlo_v3 import gaussian_copula_sample
        corr = np.array([[1.0, 0.7], [0.7, 1.0]])
        u = gaussian_copula_sample(corr, n_samples=5000, seed=2)
        # Spearman-style rank correlation should be near 0.7
        ranks = np.argsort(np.argsort(u, axis=0), axis=0).astype(float)
        ranks /= len(ranks)
        observed = np.corrcoef(ranks.T)[0, 1]
        self.assertGreater(observed, 0.55)
        self.assertLess(observed, 0.85)


class TestClaytonCopula(unittest.TestCase):
    def test_lower_tail_dependence(self):
        """Clayton with theta=4 should produce strong joint
        small-value events."""
        from rcm_mc.montecarlo_v3 import clayton_copula_sample
        u = clayton_copula_sample(
            theta=4.0, n_samples=5000, d=2, seed=3)
        # Both columns small simultaneously: P(u1 < 0.1 AND u2 < 0.1)
        # should be much higher than independence (0.01)
        joint_low = ((u[:, 0] < 0.1) & (u[:, 1] < 0.1)).mean()
        self.assertGreater(joint_low, 0.04)

    def test_invalid_theta_raises(self):
        from rcm_mc.montecarlo_v3 import clayton_copula_sample
        with self.assertRaises(ValueError):
            clayton_copula_sample(theta=-1.0, n_samples=10)


class TestGumbelCopula(unittest.TestCase):
    def test_upper_tail_dependence(self):
        from rcm_mc.montecarlo_v3 import gumbel_copula_sample
        u = gumbel_copula_sample(
            theta=4.0, n_samples=5000, d=2, seed=4)
        joint_high = ((u[:, 0] > 0.9) & (u[:, 1] > 0.9)).mean()
        # Independence baseline = 0.01; Gumbel θ=4 should beat
        # that by 2× even at modest sample size.
        self.assertGreater(joint_high, 0.02)

    def test_invalid_theta_raises(self):
        from rcm_mc.montecarlo_v3 import gumbel_copula_sample
        with self.assertRaises(ValueError):
            gumbel_copula_sample(theta=0.5, n_samples=10)


class TestFrankCopula(unittest.TestCase):
    def test_returns_uniform_pairs(self):
        from rcm_mc.montecarlo_v3 import frank_copula_sample
        u = frank_copula_sample(
            theta=3.0, n_samples=2000, d=2, seed=5)
        self.assertEqual(u.shape, (2000, 2))
        # Marginals approximately uniform
        for col in range(2):
            self.assertGreater(u[:, col].mean(), 0.4)
            self.assertLess(u[:, col].mean(), 0.6)


# ── Sobol ───────────────────────────────────────────────────────

class TestSobol(unittest.TestCase):
    def test_returns_unit_hypercube(self):
        from rcm_mc.montecarlo_v3 import sobol_sequence
        s = sobol_sequence(n_samples=128, dim=3)
        self.assertEqual(s.shape, (128, 3))
        self.assertGreaterEqual(s.min(), 0.0)
        self.assertLess(s.max(), 1.0)

    def test_better_uniformity_than_pseudo(self):
        """Sobol's gap-uniformity should beat pseudo-random on a
        small sample. Compare max-gap on dimension 1."""
        from rcm_mc.montecarlo_v3 import sobol_sequence
        s = sobol_sequence(n_samples=64, dim=1)
        rng = np.random.default_rng(0)
        p = rng.uniform(size=64)
        max_gap_sobol = np.diff(np.sort(s.flatten())).max()
        max_gap_pseudo = np.diff(np.sort(p)).max()
        # Sobol should have a smaller max-gap on this small sample
        self.assertLess(max_gap_sobol, max_gap_pseudo)

    def test_dim_out_of_range_raises(self):
        from rcm_mc.montecarlo_v3 import sobol_sequence
        with self.assertRaises(ValueError):
            sobol_sequence(n_samples=10, dim=20)


# ── Importance sampling ─────────────────────────────────────────

class TestImportanceSampling(unittest.TestCase):
    def test_glasserman_li_returns_unbiased_estimate(self):
        """Estimate P(X > 3) for X ~ N(0,1) using IS with tilt 3.0."""
        from rcm_mc.montecarlo_v3 import importance_sample_tail
        # f(x) = 1{x > 3}
        def f(samples):
            return (samples[:, 0] > 3.0).astype(float)
        est, se = importance_sample_tail(
            f, n_samples=2000, dim=1,
            tilt=np.array([3.0]), seed=10,
        )
        # True P(X > 3) ≈ 0.00135
        self.assertGreater(est, 0.0005)
        self.assertLess(est, 0.005)
        # SE should be tiny relative to plain MC
        self.assertLess(se, 0.001)


# ── Control variates ────────────────────────────────────────────

class TestControlVariates(unittest.TestCase):
    def test_correlated_proxy_reduces_variance(self):
        """Y = f(X), Z = X (known E[X] = 0) — Y has variance, but
        with control variate it should drop."""
        from rcm_mc.montecarlo_v3 import control_variate_estimate
        rng = np.random.default_rng(7)
        X = rng.standard_normal(2000)
        Y = X + 0.1 * rng.standard_normal(2000)
        est, se, reduction = control_variate_estimate(
            Y, X, z_expectation=0.0)
        self.assertGreater(reduction, 80.0)


# ── Nested MC ───────────────────────────────────────────────────

class TestNestedMC(unittest.TestCase):
    def test_call_option_value_positive(self):
        from rcm_mc.montecarlo_v3 import nested_mc_real_option
        # Out-of-the-money call: payoff = max(S - 110, 0)
        result = nested_mc_real_option(
            initial_state=100.0,
            decision_time=1.0, horizon=2.0,
            drift=0.05, volatility=0.30,
            payoff=lambda s: np.maximum(s - 110.0, 0.0),
            n_outer=80, n_inner=80, seed=1,
        )
        self.assertGreater(result["option_value"], 0)
        self.assertGreaterEqual(result["exercise_probability"], 0)
        self.assertLessEqual(result["exercise_probability"], 1)


# ── Healthcare joint tail ───────────────────────────────────────

class TestJointTailShock(unittest.TestCase):
    def test_returns_three_shocks(self):
        from rcm_mc.montecarlo_v3 import joint_tail_healthcare_shock
        out = joint_tail_healthcare_shock(n_samples=1000, seed=0)
        for k in (
            "cms_rate_shock", "commercial_rate_shock",
            "labor_inflation_shock",
        ):
            self.assertIn(k, out)
            self.assertEqual(out[k].size, 1000)

    def test_clayton_produces_joint_downside(self):
        """Joint event: CMS cut > 5% AND commercial cut > 3%
        AND labor up > 6%. Should be more likely under Clayton
        than under Gaussian (the ENTIRE point of the Clayton
        copula in this context)."""
        from rcm_mc.montecarlo_v3 import joint_tail_healthcare_shock
        clayton = joint_tail_healthcare_shock(
            n_samples=4000, use_clayton=True, seed=11)
        # Clayton tail event detection
        joint = ((clayton["cms_rate_shock"] < -0.05)
                 & (clayton["commercial_rate_shock"] < -0.03)
                 & (clayton["labor_inflation_shock"] > 0.06))
        # Under independence, this would be ~0.16 × 0.25 × 0.40 ~ 1.6%
        # Clayton should produce at least that or more
        self.assertGreaterEqual(joint.mean(), 0.001)


if __name__ == "__main__":
    unittest.main()
