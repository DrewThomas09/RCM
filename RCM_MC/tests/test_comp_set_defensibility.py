"""Comparable-set defensibility — how much the comp-implied median
can be trusted as an IC anchor.

Pure function of benchmark_deal's output: set size, match closeness,
and MOIC dispersion. The band must step down as any leg weakens, and
a thin set must never read as STRONG.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.comparable_outcomes import assess_comp_set


def _result(scores, moic):
    return {
        "comparables": [{"match_score": s} for s in scores],
        "outcome_distribution": {"moic": moic},
    }


class CompSetDefensibilityTests(unittest.TestCase):
    def test_thin_set_is_thin(self):
        a = assess_comp_set(_result([80, 75, 70],
                                    {"median": 2.5, "p25": 2.4, "p75": 2.6}))
        self.assertEqual(a["band"], "THIN")
        self.assertEqual(a["n"], 3)

    def test_close_tight_set_is_strong(self):
        a = assess_comp_set(_result(
            [80, 78, 75, 72, 70],
            {"median": 2.5, "p25": 2.3, "p75": 2.9}))  # IQR 0.6/2.5=24%
        self.assertEqual(a["band"], "STRONG")
        self.assertLessEqual(a["moic_dispersion"], 0.30)

    def test_loose_scattered_set_is_weak(self):
        a = assess_comp_set(_result(
            [40, 38, 35, 30, 28, 25],
            {"median": 2.0, "p25": 1.0, "p75": 3.5}))  # IQR 125%
        self.assertEqual(a["band"], "WEAK")

    def test_moderate_middle(self):
        a = assess_comp_set(_result(
            [60, 55, 52, 50, 48],
            {"median": 2.5, "p25": 2.0, "p75": 3.3}))  # IQR 52%
        self.assertEqual(a["band"], "MODERATE")

    def test_median_match_is_true_median(self):
        a = assess_comp_set(_result(
            [50, 60, 70, 80, 90],
            {"median": 2.5, "p25": 2.4, "p75": 2.6}))
        self.assertEqual(a["median_match"], 70.0)
        self.assertEqual(a["n_close"], 4)   # 60,70,80,90 >= 60

    def test_empty_is_thin(self):
        a = assess_comp_set({"comparables": [], "outcome_distribution": {}})
        self.assertEqual(a["band"], "THIN")
        self.assertEqual(a["n"], 0)
        self.assertIsNone(a["moic_dispersion"])

    def test_missing_moic_does_not_crash(self):
        a = assess_comp_set(_result([70, 70, 70, 70, 70], {}))
        self.assertIn(a["band"], ("MODERATE", "WEAK"))
        self.assertIsNone(a["moic_dispersion"])

    def test_real_benchmark_and_page(self):
        import os
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        from rcm_mc.diligence.comparable_outcomes import benchmark_deal
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        c = DealsCorpus("/tmp/test_comp_defensibility.db")
        c.seed(skip_if_populated=True)
        res = benchmark_deal(
            c, {"sector": "hospital", "ev_mm": 500, "year": 2020,
                "buyer": ""}, top_n=10)
        a = assess_comp_set(res)
        self.assertEqual(a["n"], len(res["comparables"]))
        os.environ["RCM_MC_DB"] = "/tmp/test_comp_defensibility.db"
        h = render_comparable_outcomes_page({
            "sector": "hospital", "ev_mm": "500", "year": "2020"})
        self.assertIn("COMP SET", h)


if __name__ == "__main__":
    unittest.main()
