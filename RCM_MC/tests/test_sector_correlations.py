"""Cross-metric correlation layer over the six CMS verticals.

Locks the honesty contract: real pairwise-complete coefficients, n reported,
small-n suppression, association-not-causation framing, and metric-direction
exposure (never a value judgment).
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.data.sector_correlations import (
    CORR_CAVEATS, _MIN_N, _pearson, _spearman, metric_meta,
    sector_correlations, top_correlations,
)

_SECTORS = ("home-health", "hospice", "nursing-homes", "dialysis",
            "inpatient-rehab", "long-term-care-hospital")


class PureStatsTests(unittest.TestCase):
    def test_pearson_perfect_positive(self):
        self.assertEqual(_pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)

    def test_pearson_perfect_negative(self):
        self.assertEqual(_pearson([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

    def test_pearson_constant_column_is_none(self):
        self.assertIsNone(_pearson([1, 1, 1, 1], [1, 2, 3, 4]))

    def test_spearman_handles_ties_and_monotonic(self):
        # strictly monotonic but non-linear → Spearman should be 1.0
        rho = _spearman([1, 2, 3, 4, 5], [1, 4, 9, 16, 25])
        self.assertEqual(rho, 1.0)

    def test_coefficients_in_range(self):
        for sid in _SECTORS:
            for p in top_correlations(sid, k=50):
                self.assertGreaterEqual(p.pearson_r, -1.0)
                self.assertLessEqual(p.pearson_r, 1.0)
                if p.spearman_rho is not None:
                    self.assertGreaterEqual(p.spearman_rho, -1.0)
                    self.assertLessEqual(p.spearman_rho, 1.0)


class CorrelationContractTests(unittest.TestCase):
    def test_every_sector_produces_pairs(self):
        for sid in _SECTORS:
            sc = sector_correlations(sid)
            with self.subTest(sid=sid):
                self.assertIsNotNone(sc)
                self.assertGreater(len(sc.pairs), 0)
                self.assertGreater(sc.provider_n, 0)

    def test_pairs_sorted_by_abs_strength(self):
        sc = sector_correlations("nursing-homes")
        strengths = [abs(p.pearson_r) for p in sc.pairs]
        self.assertEqual(strengths, sorted(strengths, reverse=True))

    def test_small_n_is_suppressed(self):
        # Nothing below _MIN_N should ever surface.
        for sid in _SECTORS:
            for p in sector_correlations(sid).pairs:
                self.assertGreaterEqual(p.n, _MIN_N)

    def test_pairwise_complete_n_not_exceeding_universe(self):
        for sid in _SECTORS:
            sc = sector_correlations(sid)
            for p in sc.pairs:
                self.assertLessEqual(p.n, sc.provider_n)

    def test_direction_exposed_not_relabelled(self):
        sc = sector_correlations("nursing-homes")
        meta = dict((k, (lbl, d)) for k, lbl, d in sc.metrics)
        # turnover is lower-is-better; rn_hprd higher — directions must be honest
        self.assertEqual(meta["total_nurse_turnover_pct"][1], "lower")
        self.assertEqual(meta["rn_hprd"][1], "higher")

    def test_known_real_association_holds(self):
        # SNF fines and total penalties are strongly, positively associated.
        sc = sector_correlations("nursing-homes")
        hit = next(p for p in sc.pairs
                   if {p.key_a, p.key_b} == {"num_fines", "num_penalties"})
        self.assertGreater(hit.pearson_r, 0.5)
        self.assertGreater(hit.n, 1000)

    def test_caveats_are_association_not_causation(self):
        blob = " ".join(CORR_CAVEATS).lower()
        self.assertIn("association", blob)
        self.assertIn("not causation", blob)
        self.assertIn("not a forecast", blob)

    def test_unknown_sector_returns_none(self):
        self.assertIsNone(sector_correlations("not-a-sector"))

    def test_metric_meta_humanizes_unknown_key(self):
        label, direction = metric_meta("some_new_measure_key")
        self.assertEqual(label, "Some New Measure Key")
        self.assertEqual(direction, "neutral")


if __name__ == "__main__":
    unittest.main()
