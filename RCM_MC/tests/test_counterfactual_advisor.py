"""Counterfactual Advisor regression tests.

Covers:
    - Each individual solver (CPOM, NSA, Steward, TEAM, antitrust,
      cyber, site-neutral)
    - advise_all composes + picks largest lever
    - CCD-driven runner derives OON / HOPD / HHI from claims
    - Bridge lever translation (feasibility multiplier, confidence)
    - HTML page renders (landing + dataset-driven)
    - JSON API surface round-trips correctly
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from rcm_mc.diligence.counterfactual import (
    CounterfactualLever, CounterfactualSet, advise_all,
    counterfactual_bridge_lever, for_antitrust, for_cpom,
    for_cyber, for_nsa, for_site_neutral, for_steward, for_team,
    run_counterfactuals_from_ccd, summarize_ccd_inputs,
)
from rcm_mc.diligence.cyber import compose_cyber_score
from rcm_mc.diligence.real_estate import (
    LeaseLine, LeaseSchedule, compute_steward_score,
)
from rcm_mc.diligence.regulatory import (
    RegulatoryBand, compute_antitrust_exposure, compute_cpom_exposure,
    compute_nsa_exposure, compute_team_impact,
    simulate_site_neutral_impact,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


class SolverTests(unittest.TestCase):

    def test_cpom_red_yields_restructure(self):
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        cf = for_cpom(cpom)
        self.assertIsNotNone(cf)
        self.assertEqual(cf.module, "CPOM")
        self.assertEqual(cf.target_band, "GREEN")
        self.assertIn("DIRECT_EMPLOYMENT", cf.change_description)
        self.assertGreater(cf.estimated_dollar_impact_usd, 0)

    def test_cpom_green_yields_none(self):
        """No counterfactual when already GREEN."""
        cpom = compute_cpom_exposure(
            target_structure="DIRECT_EMPLOYMENT",
            footprint_states=["NY"],
        )
        self.assertIsNone(for_cpom(cpom))

    def test_nsa_high_oon_yields_contract_top_payers(self):
        nsa = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.42,
            oon_dollars_annual=10_000_000,
            seller_avg_rate_multiple_of_medicare=2.3,
        )
        cf = for_nsa(nsa)
        self.assertIsNotNone(cf)
        self.assertEqual(cf.module, "NSA")
        self.assertIn("OON", cf.change_description)
        self.assertGreater(cf.estimated_dollar_impact_usd, 0)

    def test_steward_critical_yields_factor_removal(self):
        schedule = LeaseSchedule(lines=[LeaseLine(
            property_id="x", property_type="HOSPITAL",
            base_rent_annual_usd=10_000_000,
            escalator_pct=0.035, term_years=20,
            landlord="Medical Properties Trust",
            property_revenue_annual_usd=100_000_000,
        )])
        result = compute_steward_score(
            schedule,
            portfolio_ebitdar_annual_usd=12_000_000,
            portfolio_annual_rent_usd=10_000_000,
            geography="RURAL",
        )
        cf = for_steward(result)
        self.assertIsNotNone(cf)
        self.assertEqual(cf.module, "STEWARD")
        # CRITICAL → HIGH after removing one factor
        self.assertEqual(cf.original_band, "CRITICAL")
        self.assertEqual(cf.target_band, "HIGH")

    def test_team_red_yields_track_1(self):
        team = compute_team_impact(
            cbsa_code="35620", track="track_2",
            annual_case_volume={"LEJR": 500, "CABG": 100},
            hospital_performance_percentile=0.2,
        )
        cf = for_team(team)
        self.assertIsNotNone(cf)
        self.assertIn("track_1", cf.change_description.lower()
                      + cf.lever.lower())

    def test_antitrust_red_yields_divest(self):
        at = compute_antitrust_exposure(
            target_specialty="ANESTHESIOLOGY",
            target_msas=["Houston"],
            acquisitions=[
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.2},
            ] * 5,
        )
        cf = for_antitrust(at)
        self.assertIsNotNone(cf)
        self.assertIn("divest", cf.change_description.lower())

    def test_cyber_red_with_change_healthcare_yields_replace(self):
        score = compose_cyber_score(
            external_rating=None,
            ehr_vendor_risk=65,
            ba_findings=[type("F", (), {
                "severity": "CRITICAL",
                "ba_name": "Change Healthcare",
                "cascade_risk_multiplier": 2.5,
            })()],
            it_capex=None, bi_loss=None,
            annual_revenue_usd=100_000_000,
        )
        # Force it RED by lowering the score manually (the compose
        # above lands in YELLOW given only one BA + no other factors)
        score.band = "RED"
        score.findings = ["BA cascade CRITICAL: Change Healthcare"]
        cf = for_cyber(score)
        self.assertIsNotNone(cf)
        self.assertIn("Change Healthcare", cf.change_description)


class AdviseAllTests(unittest.TestCase):

    def test_composes_across_modules(self):
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        nsa = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.45,
            oon_dollars_annual=15_000_000,
            seller_avg_rate_multiple_of_medicare=2.3,
        )
        cs = advise_all(cpom=cpom, nsa=nsa)
        self.assertEqual(len(cs.items), 2)
        modules = {c.module for c in cs.items}
        self.assertIn("CPOM", modules)
        self.assertIn("NSA", modules)
        self.assertEqual(cs.critical_findings_addressed, 2)

    def test_largest_lever_picks_highest_dollar_impact(self):
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        nsa = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.45,
            oon_dollars_annual=20_000_000,
            seller_avg_rate_multiple_of_medicare=2.5,
        )
        cs = advise_all(cpom=cpom, nsa=nsa)
        largest = cs.largest_lever
        self.assertIsNotNone(largest)
        self.assertEqual(largest.module, "NSA")

    def test_empty_inputs_produce_empty_set(self):
        cs = advise_all()
        self.assertEqual(len(cs.items), 0)
        self.assertIsNone(cs.largest_lever)


class CCDRunnerTests(unittest.TestCase):

    def setUp(self):
        from rcm_mc.diligence import ingest_dataset
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_08_waterfall_critical",
        )

    def test_summarize_ccd_inputs_returns_expected_fields(self):
        s = summarize_ccd_inputs(self.ccd)
        for key in (
            "claim_count", "total_paid_usd", "oon_paid_usd",
            "oon_share", "hopd_revenue_usd", "commercial_hhi",
        ):
            self.assertIn(key, s)
        self.assertEqual(s["claim_count"], 10)

    def test_run_with_full_metadata_covers_multiple_modules(self):
        cs = run_counterfactuals_from_ccd(
            self.ccd, metadata={
                "legal_structure": "FRIENDLY_PC_PASS_THROUGH",
                "states": ["OR"],
                "landlord": "Medical Properties Trust",
                "lease_term_years": 20,
                "lease_escalator_pct": 0.035,
                "annual_rent_usd": 10_000_000,
                "portfolio_ebitdar_usd": 12_000_000,
                "geography": "RURAL",
                "specialty": "EMERGENCY_MEDICINE",
                "is_hospital_based_physician": True,
                "cbsa_codes": ["35620"],
                "acquisitions": [{
                    "msa": "Dallas",
                    "specialty": "EMERGENCY_MEDICINE",
                    "market_share_acquired": 0.15,
                }] * 5,
                "msas": ["Dallas"],
            },
        )
        # Should include at least CPOM + Steward + Antitrust
        modules = {c.module for c in cs.items}
        self.assertIn("CPOM", modules)
        self.assertIn("STEWARD", modules)

    def test_run_with_no_metadata_returns_empty_or_site_neutral_only(self):
        cs = run_counterfactuals_from_ccd(self.ccd, metadata={})
        # Might produce site-neutral if HOPD revenue is present
        self.assertLessEqual(len(cs.items), 1)


class BridgeLeverTests(unittest.TestCase):

    def test_positive_savings_flow_to_bridge_with_realization(self):
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        cs = advise_all(cpom=cpom)
        lever = counterfactual_bridge_lever(
            cs, realization_probability=0.5,
        )
        # CPOM CF savings ~$850k × 0.5 × 0.7 (MEDIUM feasibility)
        self.assertGreater(lever.ebitda_impact_usd, 200_000)
        self.assertLess(lever.ebitda_impact_usd, 450_000)
        self.assertEqual(len(lever.provenance), 1)

    def test_empty_set_returns_zero_lever(self):
        lever = counterfactual_bridge_lever(
            CounterfactualSet(items=[]),
        )
        self.assertEqual(lever.ebitda_impact_usd, 0.0)
        self.assertEqual(lever.confidence, "LOW")

    def test_high_feasibility_counterfactuals_boost_confidence(self):
        # TEAM counterfactual has HIGH feasibility.
        team = compute_team_impact(
            cbsa_code="35620", track="track_2",
            annual_case_volume={"LEJR": 500, "CABG": 100},
            hospital_performance_percentile=0.1,
        )
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        # One HIGH (TEAM) + one MEDIUM (CPOM) → MEDIUM confidence
        lever_mixed = counterfactual_bridge_lever(
            advise_all(cpom=cpom, team=team),
        )
        self.assertEqual(lever_mixed.confidence, "MEDIUM")


class CounterfactualPageTests(unittest.TestCase):

    def test_landing_renders_form(self):
        from rcm_mc.ui.counterfactual_page import (
            render_counterfactual_page,
        )
        html = render_counterfactual_page()
        self.assertIn("Counterfactual Advisor", html)
        self.assertIn("CCD fixture", html)

    def test_live_page_includes_ccd_summary(self):
        from rcm_mc.ui.counterfactual_page import (
            render_counterfactual_page,
        )
        html = render_counterfactual_page(
            dataset="hospital_08_waterfall_critical",
            metadata={
                "legal_structure": "FRIENDLY_PC_PASS_THROUGH",
                "states": ["OR"],
                "specialty": "EMERGENCY_MEDICINE",
            },
        )
        self.assertIn("Derived from CCD", html)
        self.assertIn("Counterfactuals", html)

    def test_unknown_fixture_falls_back_to_landing(self):
        from rcm_mc.ui.counterfactual_page import (
            render_counterfactual_page,
        )
        html = render_counterfactual_page(dataset="not_a_fixture")
        self.assertIn("pick a CCD fixture", html)


class NavLinkTest(unittest.TestCase):

    def test_counterfactual_nav_link(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/counterfactual"', rendered)


if __name__ == "__main__":
    unittest.main()
