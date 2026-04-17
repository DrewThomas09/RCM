"""Tests for demand analysis: disease density, stickiness, elasticity, tailwinds."""
from __future__ import annotations

import unittest

from rcm_mc.analytics.demand_analysis import (
    DemandProfile,
    compute_disease_density_index,
    compute_price_elasticity,
    compute_stickiness_score,
    compute_tailwind_score,
    _empty_profile,
)
from rcm_mc.data.drg_weights import (
    CONDITION_ACUITY_WEIGHTS,
    CHRONIC_STICKY_CONDITIONS,
    DRG_WEIGHTS,
    classify_drg,
    get_drg_weight,
    is_sticky_drg,
)


class TestDiseaseeDensityIndex(unittest.TestCase):

    def test_empty_returns_50(self):
        idx, conditions = compute_disease_density_index([])
        self.assertEqual(idx, 50.0)
        self.assertEqual(conditions, [])

    def test_high_prevalence_scores_high(self):
        records = [
            {"condition": "Heart Failure", "prevalence_pct": 25, "national_avg_pct": 15},
            {"condition": "Diabetes", "prevalence_pct": 30, "national_avg_pct": 20},
            {"condition": "COPD", "prevalence_pct": 18, "national_avg_pct": 12},
        ]
        idx, conditions = compute_disease_density_index(records)
        self.assertGreater(idx, 50)
        self.assertLessEqual(idx, 100)
        self.assertEqual(len(conditions), 3)

    def test_conditions_sorted_by_weighted_score(self):
        records = [
            {"condition": "Other", "prevalence_pct": 50, "national_avg_pct": 50},
            {"condition": "Heart Failure", "prevalence_pct": 20, "national_avg_pct": 15},
        ]
        _, conditions = compute_disease_density_index(records)
        self.assertEqual(conditions[0]["condition"], "Heart Failure")

    def test_delta_calculated(self):
        records = [{"condition": "Diabetes", "prevalence_pct": 25, "national_avg_pct": 20}]
        _, conditions = compute_disease_density_index(records)
        self.assertAlmostEqual(conditions[0]["delta_pct"], 5.0)


class TestStickinessScore(unittest.TestCase):

    def test_range_0_to_100(self):
        score, breakdown = compute_stickiness_score(80, 0, 60)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_monopoly_high_when_no_competitors(self):
        _, breakdown = compute_stickiness_score(50, 0, 30)
        self.assertEqual(breakdown["geographic_monopoly"], 33.0)

    def test_monopoly_low_when_many_competitors(self):
        _, breakdown = compute_stickiness_score(50, 15, 30)
        self.assertEqual(breakdown["geographic_monopoly"], 0)

    def test_high_chronicity_scores_high(self):
        _, breakdown = compute_stickiness_score(100, 5, 50)
        self.assertGreater(breakdown["chronicity"], 30)

    def test_breakdown_sums_to_total(self):
        score, breakdown = compute_stickiness_score(60, 3, 45)
        component_sum = sum(breakdown.values())
        self.assertAlmostEqual(score, component_sum, delta=0.2)


class TestPriceElasticity(unittest.TestCase):

    def test_empty_returns_default(self):
        elas, detail = compute_price_elasticity([])
        self.assertEqual(elas, -0.3)
        self.assertEqual(detail, [])

    def test_sticky_drgs_more_inelastic(self):
        records = [
            {"drg_code": "291", "total_discharges": 100,
             "average_covered_charges": 50000, "average_total_payments": 15000,
             "drg_description": "Heart Failure"},
        ]
        elas, detail = compute_price_elasticity(records)
        self.assertLess(elas, 0)
        self.assertGreater(elas, -1)

    def test_returns_negative(self):
        records = [
            {"drg_code": "470", "total_discharges": 200,
             "average_covered_charges": 80000, "average_total_payments": 20000,
             "drg_description": "Joint Replacement"},
        ]
        elas, _ = compute_price_elasticity(records)
        self.assertLess(elas, 0)


class TestTailwindScore(unittest.TestCase):

    def test_empty_returns_zero(self):
        score, detail = compute_tailwind_score([])
        self.assertEqual(score, 0)

    def test_positive_delta_gives_tailwind(self):
        records = [
            {"condition": "Heart Failure", "prevalence_pct": 20,
             "national_avg_pct": 14, "delta_pct": 6},
        ]
        score, detail = compute_tailwind_score(records)
        self.assertGreater(score, 0)

    def test_negative_delta_gives_headwind(self):
        records = [
            {"condition": "Diabetes", "prevalence_pct": 10,
             "national_avg_pct": 18, "delta_pct": -8},
        ]
        score, detail = compute_tailwind_score(records)
        self.assertLess(score, 0)

    def test_score_clamped(self):
        huge = [
            {"condition": f"Cond{i}", "prevalence_pct": 50,
             "national_avg_pct": 5, "delta_pct": 45}
            for i in range(20)
        ]
        score, _ = compute_tailwind_score(huge)
        self.assertLessEqual(score, 50)


class TestDemandProfile(unittest.TestCase):

    def test_to_dict(self):
        profile = _empty_profile("010001")
        d = profile.to_dict()
        self.assertEqual(d["ccn"], "010001")
        self.assertIn("disease_density_index", d)
        self.assertIn("stickiness_score", d)
        self.assertIn("price_elasticity", d)
        self.assertIn("tailwind_score", d)


class TestDrgWeights(unittest.TestCase):

    def test_acuity_weights_exist(self):
        self.assertIn("Heart Failure", CONDITION_ACUITY_WEIGHTS)
        self.assertGreater(CONDITION_ACUITY_WEIGHTS["Heart Failure"], 1)

    def test_classify_drg(self):
        result = classify_drg("291")
        self.assertIsInstance(result, str)

    def test_get_drg_weight(self):
        weight = get_drg_weight("470")
        self.assertIsInstance(weight, float)
        self.assertGreater(weight, 0)

    def test_is_sticky_drg(self):
        self.assertIsInstance(is_sticky_drg("291"), bool)

    def test_chronic_conditions_set(self):
        self.assertIsInstance(CHRONIC_STICKY_CONDITIONS, (set, frozenset))
        self.assertTrue(len(CHRONIC_STICKY_CONDITIONS) > 0)


class TestDemandPage(unittest.TestCase):

    def test_renders(self):
        from rcm_mc.ui.demand_page import render_demand_analysis
        profile = {
            "ccn": "010001",
            "hospital_name": "Test Hospital",
            "county": "Jefferson",
            "state": "AL",
            "disease_density_index": 72.5,
            "stickiness_score": 68.0,
            "price_elasticity": -0.35,
            "tailwind_score": 12.5,
            "top_conditions": [
                {"condition": "Heart Failure", "prevalence_pct": 15.2,
                 "national_avg_pct": 12.0, "delta_pct": 3.2, "acuity_weight": 3.0},
            ],
            "stickiness_breakdown": {"chronicity": 28, "geographic_monopoly": 22, "switching_cost": 18},
            "competitor_count": 5,
            "elasticity_detail": [],
            "tailwind_detail": [],
            "explanations": {"density": "High", "stickiness": "Good", "elasticity": "Low", "tailwind": "Positive"},
        }
        html = render_demand_analysis(profile)
        self.assertIn("SeekingChartis", html)
        self.assertIn("Disease Density", html)
        self.assertIn("Stickiness", html)
        self.assertIn("Heart Failure", html)
        self.assertIn("Jefferson", html)


if __name__ == "__main__":
    unittest.main()
