"""Step 72: Property-based tests for distributions."""
import unittest
import numpy as np

from rcm_mc.core.distributions import sample_dist, dist_moments, DistributionError


class TestDistributionProperties(unittest.TestCase):

    def _test_bounds(self, spec, lo, hi, name=""):
        rng = np.random.default_rng(42)
        vals = sample_dist(rng, spec, size=5000)
        self.assertTrue(np.all(vals >= lo - 1e-9), f"{name}: values below {lo}")
        self.assertTrue(np.all(vals <= hi + 1e-9), f"{name}: values above {hi}")

    def test_beta_in_bounds(self):
        self._test_bounds({"dist": "beta", "mean": 0.5, "sd": 0.1}, 0, 1, "beta")

    def test_triangular_in_bounds(self):
        self._test_bounds({"dist": "triangular", "low": 5, "mode": 10, "high": 20}, 5, 20, "tri")

    def test_normal_trunc_in_bounds(self):
        self._test_bounds({"dist": "normal_trunc", "mean": 50, "sd": 10, "min": 20, "max": 80}, 20, 80, "ntrunc")

    def test_lognormal_positive(self):
        rng = np.random.default_rng(42)
        vals = sample_dist(rng, {"dist": "lognormal", "mean": 100, "sd": 30}, size=5000)
        self.assertTrue(np.all(vals > 0), "lognormal should be positive")

    def test_gamma_positive(self):
        rng = np.random.default_rng(42)
        vals = sample_dist(rng, {"dist": "gamma", "mean": 50, "sd": 15}, size=5000)
        self.assertTrue(np.all(vals > 0), "gamma should be positive")

    def test_fixed_constant(self):
        rng = np.random.default_rng(42)
        vals = sample_dist(rng, {"dist": "fixed", "value": 42}, size=100)
        self.assertTrue(np.all(vals == 42))

    def test_empirical_from_values(self):
        rng = np.random.default_rng(42)
        vals = sample_dist(rng, {"dist": "empirical", "values": [1, 2, 3]}, size=1000)
        self.assertTrue(set(vals.astype(int)).issubset({1, 2, 3}))

    def test_moments_nonnegative_variance(self):
        specs = [
            {"dist": "beta", "mean": 0.3, "sd": 0.05},
            {"dist": "gamma", "mean": 50, "sd": 10},
            {"dist": "lognormal", "mean": 100, "sd": 20},
            {"dist": "fixed", "value": 7},
            {"dist": "triangular", "low": 1, "mode": 5, "high": 10},
            {"dist": "normal_trunc", "mean": 50, "sd": 10, "min": 20, "max": 80},
        ]
        for spec in specs:
            mean, var = dist_moments(spec)
            self.assertGreaterEqual(var, 0, f"Negative variance for {spec['dist']}")


if __name__ == "__main__":
    unittest.main()
