"""Tests for hierarchical (partial-pooling) benchmarking."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.hierarchical_bench import (
    partial_pool,
    partial_pool_nested,
)


class PartialPoolTests(unittest.TestCase):

    def test_noisy_unit_shrinks_more(self):
        # Two units equally far from the mean, one precise one noisy.
        # The noisy one should shrink harder (smaller B, closer to mean).
        res = partial_pool(
            units=["precise_high", "noisy_high", "anchor1", "anchor2",
                   "anchor3", "anchor4"],
            estimates=[1.5, 1.5, 1.0, 1.0, 1.0, 1.0],
            standard_errors=[0.05, 0.50, 0.05, 0.05, 0.05, 0.05],
        )
        by = {u.unit: u for u in res.units}
        self.assertGreater(by["precise_high"].shrinkage_factor,
                           by["noisy_high"].shrinkage_factor)
        # Noisy unit's shrunken estimate is closer to the grand mean.
        self.assertLess(
            abs(by["noisy_high"].shrunken - res.grand_mean),
            abs(by["precise_high"].shrunken - res.grand_mean),
        )

    def test_shrunken_between_raw_and_mean(self):
        res = partial_pool(
            ["a", "b", "c", "d"],
            [2.0, 0.5, 1.0, 1.1],
            [0.2, 0.2, 0.2, 0.2],
        )
        for u in res.units:
            lo, hi = sorted([u.raw, res.grand_mean])
            self.assertGreaterEqual(u.shrunken, lo - 1e-9)
            self.assertLessEqual(u.shrunken, hi + 1e-9)

    def test_zero_heterogeneity_collapses_to_mean(self):
        # All units equal up to noise → τ²≈0 → everything pooled to mean.
        rng = np.random.default_rng(0)
        n = 30
        est = (1.0 + rng.normal(0, 0.01, n)).tolist()
        se = [0.3] * n
        res = partial_pool([f"u{i}" for i in range(n)], est, se)
        self.assertLess(res.tau_squared, 0.01)
        for u in res.units:
            self.assertAlmostEqual(u.shrunken, res.grand_mean, delta=0.05)

    def test_true_outlier_survives_shrinkage(self):
        # A precise, far-from-mean unit among precise peers stays flagged.
        res = partial_pool(
            ["outlier", "p1", "p2", "p3", "p4", "p5"],
            [3.0, 1.0, 1.05, 0.95, 1.0, 1.02],
            [0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
        )
        by = {u.unit: u for u in res.units}
        self.assertTrue(by["outlier"].is_outlier)

    def test_phantom_outlier_demoted(self):
        # A tiny-n unit with a wild estimate should NOT remain top-ranked
        # after shrinkage, and should not be flagged an outlier.
        res = partial_pool(
            ["phantom", "p1", "p2", "p3", "p4", "p5"],
            [5.0, 1.0, 1.05, 0.95, 1.0, 1.02],
            [3.0, 0.05, 0.05, 0.05, 0.05, 0.05],   # phantom is very noisy
        )
        by = {u.unit: u for u in res.units}
        self.assertFalse(by["phantom"].is_outlier)
        # It shrinks hard: tiny trust in its own data, estimate collapses
        # toward the grand mean (the raw 5.0 does not survive).
        self.assertLess(by["phantom"].shrinkage_factor, 0.2)
        self.assertLess(abs(by["phantom"].shrunken - res.grand_mean),
                        0.25 * abs(by["phantom"].raw - res.grand_mean))

    def test_ranks_are_permutations(self):
        res = partial_pool(
            ["a", "b", "c"], [1.0, 2.0, 3.0], [0.1, 0.1, 0.1],
        )
        self.assertEqual(sorted(u.rank_raw for u in res.units), [1, 2, 3])
        self.assertEqual(sorted(u.rank_shrunken for u in res.units), [1, 2, 3])

    def test_empty(self):
        res = partial_pool([], [], [])
        self.assertEqual(res.n_units, 0)

    def test_headline_and_dict(self):
        res = partial_pool(["a", "b"], [1.0, 2.0], [0.1, 0.5])
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "HB1")


class NestedPoolTests(unittest.TestCase):

    def test_nested_runs_and_populates_groups(self):
        units = ["p1", "p2", "p3", "p4", "p5", "p6"]
        groups = ["mktA", "mktA", "mktA", "mktB", "mktB", "mktB"]
        est = [1.2, 1.1, 1.3, 0.8, 0.9, 0.7]
        se = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        res = partial_pool_nested(units, groups, est, se)
        self.assertEqual(res.n_units, 6)
        for u in res.units:
            self.assertIn(u.group, ("mktA", "mktB"))

    def test_nested_shrinks_toward_group_not_grand(self):
        # Two well-separated markets; a unit shrinks toward its OWN
        # market mean, so high-market units stay above low-market units.
        units = ["a1", "a2", "a3", "b1", "b2", "b3"]
        groups = ["A", "A", "A", "B", "B", "B"]
        est = [2.0, 2.1, 1.9, 0.1, 0.0, 0.2]
        se = [0.3, 0.3, 0.3, 0.3, 0.3, 0.3]
        res = partial_pool_nested(units, groups, est, se)
        by = {u.unit: u for u in res.units}
        a_mean = np.mean([by[u].shrunken for u in ("a1", "a2", "a3")])
        b_mean = np.mean([by[u].shrunken for u in ("b1", "b2", "b3")])
        self.assertGreater(a_mean, b_mean + 1.0)

    def test_empty_nested(self):
        res = partial_pool_nested([], [], [], [])
        self.assertEqual(res.n_units, 0)


if __name__ == "__main__":
    unittest.main()
