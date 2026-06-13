"""Tests for the Benford's-law billing-integrity screen."""
from __future__ import annotations

import math
import unittest

import numpy as np

from rcm_mc.diligence.integrity import (
    BenfordVerdict,
    benford_first_digit,
)


def _benford_sample(n, seed=0):
    """Draw n values that follow Benford's law: 10**U, U~Uniform(0,k)."""
    rng = np.random.default_rng(seed)
    return (10 ** (rng.uniform(0, 5, n))).tolist()


class BenfordTests(unittest.TestCase):

    def test_benford_distributed_data_conforms(self):
        res = benford_first_digit(_benford_sample(5000, seed=1))
        self.assertIn(res.verdict,
                      (BenfordVerdict.CONFORMING, BenfordVerdict.MARGINAL))
        self.assertLess(res.mad, 0.015)
        # Leading digit 1 should dominate (~30%).
        self.assertAlmostEqual(res.observed_proportions[0], 0.301, delta=0.03)

    def test_fabricated_uniform_digits_flagged(self):
        # Uniform first digits (each ~11%) badly violate Benford.
        rng = np.random.default_rng(2)
        # Construct values whose leading digit is uniform 1..9.
        lead = rng.integers(1, 10, 3000)
        mant = rng.uniform(0, 1, 3000)
        vals = (lead + mant) * (10 ** rng.integers(0, 4, 3000))
        res = benford_first_digit(vals.tolist())
        self.assertEqual(res.verdict, BenfordVerdict.NONCONFORMING)
        self.assertGreater(res.mad, 0.015)

    def test_small_sample_insufficient(self):
        res = benford_first_digit([123, 456, 789], min_n=100)
        self.assertEqual(res.verdict, BenfordVerdict.INSUFFICIENT)
        self.assertIn("unreliable", res.advisory.lower())

    def test_narrow_spread_insufficient(self):
        # All values in [50, 60): < 1 order of magnitude spread.
        rng = np.random.default_rng(3)
        vals = rng.uniform(50, 60, 500).tolist()
        res = benford_first_digit(vals)
        self.assertEqual(res.verdict, BenfordVerdict.INSUFFICIENT)
        self.assertLess(res.spread_orders, 1.0)

    def test_filters_zero_and_nonfinite(self):
        vals = _benford_sample(500, seed=4) + [0.0, -0.0, float("nan"),
                                               float("inf")]
        res = benford_first_digit(vals)
        self.assertEqual(res.n, 500)

    def test_expected_proportions_are_benford(self):
        res = benford_first_digit(_benford_sample(200, seed=5))
        for d in range(1, 10):
            self.assertAlmostEqual(
                res.expected_proportions[d - 1], math.log10(1 + 1 / d),
            )

    def test_chi_square_p_in_unit_interval(self):
        res = benford_first_digit(_benford_sample(2000, seed=6))
        self.assertGreaterEqual(res.chi_square_p, 0.0)
        self.assertLessEqual(res.chi_square_p, 1.0)

    def test_empty(self):
        res = benford_first_digit([])
        self.assertEqual(res.verdict, BenfordVerdict.INSUFFICIENT)
        self.assertEqual(res.n, 0)

    def test_headline_and_dict(self):
        res = benford_first_digit(_benford_sample(1000, seed=7))
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "IN-BEN")


class ChiSquareClosedFormTests(unittest.TestCase):

    def test_even_df_closed_form_matches_known_value(self):
        from rcm_mc.diligence.integrity.benford import _chi2_sf_even_df
        # For df=8, the 0.05 critical value is 15.507 → sf ≈ 0.05.
        self.assertAlmostEqual(_chi2_sf_even_df(15.507, 8), 0.05, delta=0.002)
        # sf(0) = 1, decreasing in x.
        self.assertEqual(_chi2_sf_even_df(0.0, 8), 1.0)
        self.assertGreater(_chi2_sf_even_df(5, 8), _chi2_sf_even_df(20, 8))


if __name__ == "__main__":
    unittest.main()
