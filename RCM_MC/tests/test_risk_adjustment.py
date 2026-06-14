"""Tests for the CMS-HCC risk-adjustment + risk-adjusted benchmarking module."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.risk_adjustment import (
    HCC_FACTORS,
    Demographics,
    RiskVerdict,
    apply_hierarchies,
    compute_raf,
    demographic_factor,
    map_condition_to_hcc,
    risk_adjust_metric,
    score_panel,
)


class HCCLibraryTests(unittest.TestCase):

    def test_library_covers_core_conditions(self):
        ids = {f.hcc for f in HCC_FACTORS}
        for canonical in (
            "DIAB_CHRONIC", "DIAB_NOCOMP", "CHF", "COPD",
            "CANCER_METASTATIC", "ESRD_DIALYSIS", "DEMENTIA",
            "SCHIZOPHRENIA", "VASCULAR",
        ):
            self.assertIn(canonical, ids, f"missing {canonical}")

    def test_coefficients_are_positive(self):
        for f in HCC_FACTORS:
            self.assertGreater(f.coefficient, 0.0, f.hcc)

    def test_demographic_factor_monotone_in_age(self):
        # Older bands carry higher demographic weight, same sex.
        self.assertLess(
            demographic_factor("F", 67), demographic_factor("F", 87),
        )
        self.assertLess(
            demographic_factor("M", 67), demographic_factor("M", 87),
        )

    def test_under_65_is_disabled_band(self):
        self.assertGreater(demographic_factor("F", 50), 0.0)
        self.assertEqual(
            demographic_factor("F", 50), demographic_factor("F", 40),
        )

    def test_unknown_sex_falls_back_to_female(self):
        self.assertEqual(
            demographic_factor("X", 70), demographic_factor("F", 70),
        )


class CrosswalkTests(unittest.TestCase):

    def test_icd10_longest_prefix_wins(self):
        # E1165 (diabetes w/o comp) should beat the generic E11 keyword.
        self.assertEqual(map_condition_to_hcc("E11.65"), "DIAB_NOCOMP")
        self.assertEqual(map_condition_to_hcc("E11.42"), "DIAB_CHRONIC")

    def test_keyword_mapping(self):
        self.assertEqual(map_condition_to_hcc("Congestive heart failure"), "CHF")
        self.assertEqual(map_condition_to_hcc("metastatic disease"),
                         "CANCER_METASTATIC")
        self.assertEqual(map_condition_to_hcc("on dialysis"), "ESRD_DIALYSIS")

    def test_unmapped_returns_none(self):
        self.assertIsNone(map_condition_to_hcc("sprained ankle"))
        self.assertIsNone(map_condition_to_hcc(""))


class HierarchyTests(unittest.TestCase):

    def test_severe_trumps_mild_within_family(self):
        # Both diabetes HCCs present → only the chronic one survives.
        survivors = apply_hierarchies(["DIAB_NOCOMP", "DIAB_CHRONIC"])
        self.assertIn("DIAB_CHRONIC", survivors)
        self.assertNotIn("DIAB_NOCOMP", survivors)

    def test_cancer_hierarchy(self):
        survivors = apply_hierarchies(
            ["CANCER_LOCAL", "CANCER_METASTATIC", "CANCER_OTHER"],
        )
        self.assertEqual(survivors, ["CANCER_METASTATIC"])

    def test_standalone_hccs_all_survive(self):
        survivors = apply_hierarchies(["CHF", "COPD", "VASCULAR"])
        self.assertEqual(set(survivors), {"CHF", "COPD", "VASCULAR"})

    def test_unknown_hcc_dropped(self):
        self.assertEqual(apply_hierarchies(["NOT_A_REAL_HCC"]), [])


class RafScoringTests(unittest.TestCase):

    def test_demographic_only_when_no_conditions(self):
        s = compute_raf(Demographics(age=72, sex="M"), [])
        self.assertAlmostEqual(s.raf, demographic_factor("M", 72))
        self.assertEqual(s.disease_component, 0.0)

    def test_disease_adds_to_raf(self):
        healthy = compute_raf(Demographics(72, "M"), [])
        sick = compute_raf(Demographics(72, "M"), ["CHF", "COPD"])
        self.assertGreater(sick.raf, healthy.raf)
        self.assertGreater(sick.disease_component, 0.0)

    def test_interaction_applied(self):
        s = compute_raf(Demographics(72, "M"), ["E11.42", "I50.9"])
        # diabetes-chronic + CHF triggers the documented interaction.
        self.assertGreater(s.interaction_component, 0.0)
        self.assertTrue(s.interactions)

    def test_hierarchy_prevents_double_count(self):
        both = compute_raf(Demographics(72, "M"),
                           ["DIAB_NOCOMP", "DIAB_CHRONIC"])
        only_chronic = compute_raf(Demographics(72, "M"), ["DIAB_CHRONIC"])
        self.assertAlmostEqual(both.disease_component,
                               only_chronic.disease_component)

    def test_unmapped_conditions_surfaced(self):
        s = compute_raf(Demographics(72, "M"), ["sprained ankle", "CHF"])
        self.assertIn("sprained ankle", s.unmapped_conditions)
        self.assertIn("CHF", s.hccs)

    def test_to_dict_round_trips(self):
        s = compute_raf(Demographics(80, "F"), ["CHF"])
        d = s.to_dict()
        self.assertIn("raf", d)
        self.assertEqual(d["citation_key"], "RA1")


class PanelScoringTests(unittest.TestCase):

    def test_panel_rollup(self):
        panel = [
            (Demographics(72, "M"), ["CHF"]),
            (Demographics(80, "F"), ["E11.42", "I50.9"]),
            (Demographics(68, "F"), []),
        ]
        ps = score_panel(panel)
        self.assertEqual(ps.n_beneficiaries, 3)
        self.assertGreater(ps.mean_raf, 0.0)
        self.assertIn("CHF", ps.hcc_prevalence)

    def test_empty_panel(self):
        ps = score_panel([])
        self.assertEqual(ps.n_beneficiaries, 0)
        self.assertEqual(ps.mean_raf, 0.0)


class RiskAdjustedBenchmarkTests(unittest.TestCase):

    def test_sicker_panel_not_punished(self):
        # Target costs more raw, but is sicker by exactly the same ratio
        # → O/E should be ~1.0, verdict IN_LINE.
        peer_values = [100.0, 110.0, 90.0, 105.0]
        peer_rafs = [1.0, 1.0, 1.0, 1.0]
        b = risk_adjust_metric(
            "cost_pmpm", target_value=130.0, target_raf=1.3,
            peer_values=peer_values, peer_rafs=peer_rafs,
            lower_is_better=True,
        )
        self.assertAlmostEqual(b.oe_ratio, 1.0, delta=0.05)
        self.assertEqual(b.verdict, RiskVerdict.IN_LINE)
        self.assertGreater(b.raw_ratio, 1.2)   # raw it looks expensive
        self.assertAlmostEqual(b.case_mix_effect, 1.3, places=2)

    def test_true_outlier_flagged(self):
        peer_values = [100.0, 100.0, 100.0, 100.0]
        peer_rafs = [1.0, 1.0, 1.0, 1.0]
        b = risk_adjust_metric(
            "cost_pmpm", target_value=140.0, target_raf=1.0,
            peer_values=peer_values, peer_rafs=peer_rafs,
            lower_is_better=True,
        )
        self.assertEqual(b.verdict, RiskVerdict.OUTLIER)
        self.assertGreater(b.oe_ratio, 1.25)

    def test_efficient_operator(self):
        peer_values = [100.0, 100.0, 100.0, 100.0]
        peer_rafs = [1.0, 1.0, 1.0, 1.0]
        b = risk_adjust_metric(
            "cost_pmpm", target_value=80.0, target_raf=1.0,
            peer_values=peer_values, peer_rafs=peer_rafs,
        )
        self.assertEqual(b.verdict, RiskVerdict.EFFICIENT)

    def test_higher_is_better_polarity(self):
        # Quality-stars: lower O/E is bad, not good.
        peer_values = [4.0, 4.0, 4.0, 4.0]
        peer_rafs = [1.0, 1.0, 1.0, 1.0]
        b = risk_adjust_metric(
            "quality_stars", target_value=3.0, target_raf=1.0,
            peer_values=peer_values, peer_rafs=peer_rafs,
            lower_is_better=False,
        )
        self.assertIn(b.verdict, (RiskVerdict.ELEVATED, RiskVerdict.OUTLIER))

    def test_percentile_and_headline(self):
        b = risk_adjust_metric(
            "cost_pmpm", target_value=100.0, target_raf=1.0,
            peer_values=[80.0, 90.0, 100.0, 120.0],
            peer_rafs=[1.0, 1.0, 1.0, 1.0],
        )
        self.assertGreaterEqual(b.percentile_vs_peers, 0.0)
        self.assertLessEqual(b.percentile_vs_peers, 1.0)
        self.assertTrue(b.headline)

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            risk_adjust_metric("m", 1.0, 1.0, [], [])
        with self.assertRaises(ValueError):
            risk_adjust_metric("m", 1.0, 1.0, [1.0], [1.0, 2.0])
        with self.assertRaises(ValueError):
            risk_adjust_metric("m", 1.0, -1.0, [1.0], [1.0])


if __name__ == "__main__":
    unittest.main()
