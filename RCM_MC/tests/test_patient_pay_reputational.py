"""Patient-pay + reputational ESG regression tests (Prompt O)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.patient_pay import (
    benchmark_pos_collection, compute_medical_debt_overlay,
    segment_patient_pay_exposure,
)
from rcm_mc.diligence.reputational import (
    detect_bankruptcy_contagion, scan_media_mentions,
    state_ag_enforcement_heatmap,
)


class HDHPTests(unittest.TestCase):

    def test_high_hdhp_share_is_high_severity(self):
        r = segment_patient_pay_exposure(
            hdhp_member_share=0.55,
            total_patient_responsibility_usd=10_000_000,
        )
        self.assertEqual(r.severity, "HIGH")
        self.assertGreater(r.est_bad_debt_delta_usd, 0)

    def test_low_hdhp_share_is_low(self):
        r = segment_patient_pay_exposure(
            hdhp_member_share=0.05,
            total_patient_responsibility_usd=1_000_000,
        )
        self.assertEqual(r.severity, "LOW")


class POSCollectionTests(unittest.TestCase):

    def test_hospital_below_p25_is_high(self):
        r = benchmark_pos_collection(
            specialty="HOSPITAL", pos_collection_rate=0.05,
        )
        self.assertEqual(r.placement, "below_p25")
        self.assertEqual(r.severity, "HIGH")

    def test_asc_above_p75_is_low(self):
        r = benchmark_pos_collection(
            specialty="ASC", pos_collection_rate=0.80,
        )
        self.assertEqual(r.placement, "above_p75")
        self.assertEqual(r.severity, "LOW")

    def test_unknown_specialty_returns_none(self):
        self.assertIsNone(
            benchmark_pos_collection(
                specialty="ZZZ", pos_collection_rate=0.5,
            )
        )


class MedicalDebtOverlayTests(unittest.TestCase):

    def test_colorado_banned_is_high_uplift(self):
        out = compute_medical_debt_overlay(["CO"])
        self.assertEqual(out[0].status, "BANNED")
        self.assertAlmostEqual(out[0].bad_debt_uplift_pct, 0.03)
        self.assertEqual(out[0].severity, "HIGH")

    def test_unknown_state_is_none(self):
        out = compute_medical_debt_overlay(["TX"])
        self.assertEqual(out[0].status, "NONE")
        self.assertEqual(out[0].bad_debt_uplift_pct, 0.0)


class StateAGHeatmapTests(unittest.TestCase):

    def test_california_is_high(self):
        out = state_ag_enforcement_heatmap(["CA"])
        self.assertEqual(out[0].tier, "HIGH")
        self.assertGreater(out[0].recent_enforcement_count, 0)

    def test_unknown_state_is_low(self):
        out = state_ag_enforcement_heatmap(["NV"])
        self.assertEqual(out[0].tier, "LOW")


class BankruptcyContagionTests(unittest.TestCase):

    def test_hospital_with_mpt_fires_critical(self):
        r = detect_bankruptcy_contagion(
            target_specialty="HOSPITAL",
            target_landlord="Medical Properties Trust",
        )
        self.assertEqual(r.severity, "CRITICAL")
        self.assertIn("Steward Health Care", r.specialty_matches)
        self.assertIn("Steward Health Care", r.landlord_matches)

    def test_er_specialty_fires_high(self):
        r = detect_bankruptcy_contagion(
            target_specialty="EMERGENCY_MEDICINE",
        )
        self.assertEqual(r.severity, "HIGH")
        self.assertIn("Envision Healthcare", r.specialty_matches)

    def test_non_matching_specialty_is_low(self):
        r = detect_bankruptcy_contagion(
            target_specialty="VETERINARY",
        )
        self.assertEqual(r.severity, "LOW")


class MediaRiskScanTests(unittest.TestCase):

    def test_target_mention_with_risk_keyword_fires(self):
        findings = scan_media_mentions(
            target_name="Acme Health",
            articles=[
                {"source": "ProPublica",
                 "text": "Acme Health disclosed a lawsuit filed by the DOJ "
                         "over alleged kickbacks last quarter."},
                {"source": "STAT",
                 "text": "No mention of the target at all."},
                {"source": "KHN",
                 "text": "Acme Health expanded into a new market — clean."},
            ],
        )
        # Only ProPublica has target + risk keywords.
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].source, "ProPublica")
        self.assertGreater(findings[0].hit_count, 0)

    def test_no_target_mention_is_empty(self):
        findings = scan_media_mentions(
            target_name="NobodyCorp",
            articles=[{"source": "NYT",
                       "text": "Some other story about bankruptcy."}],
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
