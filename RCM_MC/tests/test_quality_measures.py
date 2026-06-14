"""Tests for HEDIS/CQM-style quality-measure gap analysis."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.quality_measures import (
    QUALITY_MEASURES,
    MeasureVerdict,
    evaluate_measure,
    get_measure,
    score_quality,
)


class LibraryTests(unittest.TestCase):

    def test_core_measures_present(self):
        ids = {m.measure_id for m in QUALITY_MEASURES}
        for mid in ("HBA1C_CONTROL", "BP_CONTROL", "BREAST_SCREEN",
                    "PLAN_ALL_READMIT"):
            self.assertIn(mid, ids)

    def test_benchmarks_are_rates(self):
        for m in QUALITY_MEASURES:
            self.assertGreaterEqual(m.national_benchmark, 0.0)
            self.assertLessEqual(m.national_benchmark, 1.0)


class EvaluateHigherIsBetterTests(unittest.TestCase):

    def test_below_benchmark_has_gap(self):
        m = get_measure("HBA1C_CONTROL")        # bench 0.72
        r = evaluate_measure(m, numerator=600, denominator=1000)  # 0.60
        self.assertEqual(r.verdict, MeasureVerdict.BELOW_BENCHMARK)
        self.assertGreater(r.gap_to_benchmark, 0)
        # Need ~120 patients to reach 0.72.
        self.assertEqual(r.gap_count, 120)

    def test_above_benchmark_no_gap(self):
        m = get_measure("HBA1C_CONTROL")
        r = evaluate_measure(m, numerator=800, denominator=1000)  # 0.80
        self.assertEqual(r.verdict, MeasureVerdict.ABOVE_BENCHMARK)
        self.assertEqual(r.gap_count, 0)

    def test_at_benchmark_band(self):
        m = get_measure("HBA1C_CONTROL")        # 0.72
        r = evaluate_measure(m, numerator=725, denominator=1000)  # 0.725
        self.assertEqual(r.verdict, MeasureVerdict.AT_BENCHMARK)


class EvaluateLowerIsBetterTests(unittest.TestCase):

    def test_high_readmit_is_below_benchmark(self):
        m = get_measure("PLAN_ALL_READMIT")     # bench 0.14, lower better
        r = evaluate_measure(m, numerator=200, denominator=1000)  # 0.20
        self.assertEqual(r.verdict, MeasureVerdict.BELOW_BENCHMARK)
        self.assertGreater(r.gap_count, 0)
        # Performance score should be lower than a good performer.
        good = evaluate_measure(m, numerator=80, denominator=1000)  # 0.08
        self.assertGreater(good.performance_score, r.performance_score)
        self.assertEqual(good.verdict, MeasureVerdict.ABOVE_BENCHMARK)

    def test_peer_percentile_inverted_for_lower_better(self):
        m = get_measure("PLAN_ALL_READMIT")
        # Our rate 0.08 is better (lower) than most peers → high percentile.
        r = evaluate_measure(m, 80, 1000, peer_rates=[0.12, 0.15, 0.18, 0.20])
        self.assertGreater(r.percentile_vs_peers, 0.9)


class ScorecardTests(unittest.TestCase):

    def test_composite_and_stars(self):
        results = [
            evaluate_measure(get_measure("HBA1C_CONTROL"), 800, 1000),
            evaluate_measure(get_measure("BP_CONTROL"), 700, 1000),
            evaluate_measure(get_measure("PLAN_ALL_READMIT"), 100, 1000),
        ]
        sc = score_quality(results)
        self.assertEqual(sc.n_measures, 3)
        self.assertGreaterEqual(sc.star_equivalent, 1.0)
        self.assertLessEqual(sc.star_equivalent, 5.0)
        self.assertGreaterEqual(sc.composite_score, 0.0)
        self.assertLessEqual(sc.composite_score, 100.0)

    def test_weakest_measures_surfaced(self):
        results = [
            evaluate_measure(get_measure("HBA1C_CONTROL"), 950, 1000),  # great
            evaluate_measure(get_measure("BP_CONTROL"), 300, 1000),     # poor
        ]
        sc = score_quality(results)
        self.assertEqual(sc.weakest_measures[0], "BP_CONTROL")

    def test_weights_applied(self):
        results = [
            evaluate_measure(get_measure("HBA1C_CONTROL"), 950, 1000),
            evaluate_measure(get_measure("BP_CONTROL"), 300, 1000),
        ]
        # Heavily weight the strong measure → higher composite.
        sc_weighted = score_quality(results, weights={"HBA1C_CONTROL": 9.0})
        sc_equal = score_quality(results)
        self.assertGreater(sc_weighted.composite_score, sc_equal.composite_score)

    def test_total_gap_sums(self):
        results = [
            evaluate_measure(get_measure("HBA1C_CONTROL"), 600, 1000),  # gap 120
            evaluate_measure(get_measure("BP_CONTROL"), 560, 1000),     # gap 100
        ]
        sc = score_quality(results)
        self.assertEqual(sc.total_gap_patients, 220)

    def test_empty(self):
        sc = score_quality([])
        self.assertEqual(sc.n_measures, 0)

    def test_dict_and_headline(self):
        sc = score_quality([evaluate_measure(get_measure("HBA1C_CONTROL"), 700, 1000)])
        self.assertTrue(sc.headline)
        self.assertEqual(sc.to_dict()["citation_key"], "QM1")

    def test_zero_denominator_raises(self):
        with self.assertRaises(ValueError):
            evaluate_measure(get_measure("HBA1C_CONTROL"), 0, 0)


if __name__ == "__main__":
    unittest.main()
