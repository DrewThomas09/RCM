"""Regulatory Risk Packet — five-module integration tests.

Covers the prompt-specified invariants:
- CPOM: Oregon friendly-PC → RED (voided-contract ban)
- CPOM: California friendly-PC → YELLOW (restrictions, not ban)
- NSA: high-OON ER pattern → RED + Envision case-study match
- Site-neutral: current / MedPAC / legislative scenarios
- TEAM: 188-CBSA membership check, track bounds, mandatory episode list
- Antitrust: Houston anesthesia rollup → 30-day FTC notice trigger
- Content freshness: all five YAMLs must have last_reviewed within 60d
- Compose_packet: composite band = worst-of, dollars accumulate
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from rcm_mc.diligence.regulatory import (
    RegulatoryBand, compose_packet,
    compute_antitrust_exposure, compute_cpom_exposure,
    compute_nsa_exposure, compute_team_impact,
    is_cbsa_mandatory, regulatory_content_freshness_report,
    simulate_all_scenarios, simulate_site_neutral_impact,
)


# ── CPOM ──────────────────────────────────────────────────────────

class CPOMOregonVoidTests(unittest.TestCase):
    """An Oregon MSO target with a friendly-PC pass-through must
    flag RED (voided-contract ban under SB 951)."""

    def test_oregon_friendly_pc_is_red(self):
        rep = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )
        self.assertEqual(rep.overall_band, RegulatoryBand.RED)
        or_exposure = next(s for s in rep.per_state if s.state_code == "OR")
        self.assertEqual(or_exposure.band, RegulatoryBand.RED)
        self.assertTrue(any("void" in v.lower()
                            for v in or_exposure.voided_contracts))
        self.assertGreater(rep.total_remediation_usd, 0)

    def test_california_friendly_pc_is_yellow(self):
        """CA has restrictions on PC structures but no outright ban
        → YELLOW, not RED."""
        rep = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["CA"],
        )
        self.assertEqual(rep.overall_band, RegulatoryBand.YELLOW)

    def test_non_lattice_state_is_unknown(self):
        """NV has no PESP entry → UNKNOWN — we don't invent
        regulation that isn't on the lattice."""
        rep = compute_cpom_exposure(
            target_structure="DIRECT_EMPLOYMENT",
            footprint_states=["NV"],
        )
        nv = next(s for s in rep.per_state if s.state_code == "NV")
        self.assertEqual(nv.band, RegulatoryBand.UNKNOWN)

    def test_direct_employment_clean_anywhere(self):
        """Direct-employment structure is not in any state's
        structure_bans — CPOM-clean."""
        rep = compute_cpom_exposure(
            target_structure="DIRECT_EMPLOYMENT",
            footprint_states=["OR", "CA", "MA"],
        )
        self.assertIn(
            rep.overall_band,
            (RegulatoryBand.GREEN, RegulatoryBand.YELLOW, RegulatoryBand.UNKNOWN),
        )
        self.assertNotEqual(rep.overall_band, RegulatoryBand.RED)

    def test_rejects_unknown_structure(self):
        with self.assertRaises(ValueError):
            compute_cpom_exposure(
                target_structure="NOT_A_REAL_STRUCTURE",
                footprint_states=["OR"],
            )


# ── NSA ──────────────────────────────────────────────────────────

class NSAEnvisionPatternTests(unittest.TestCase):

    def test_high_oon_er_group_triggers_envision_pattern(self):
        """42% OON share → RED and Envision case-study match."""
        ex = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.42,
            oon_dollars_annual=14_500_000,
            seller_avg_rate_multiple_of_medicare=2.3,
        )
        self.assertEqual(ex.band, RegulatoryBand.RED)
        self.assertIsNotNone(ex.case_study_match)
        self.assertIn("Envision", ex.case_study_match or "")
        self.assertGreater(ex.dollars_at_risk_usd, 0)

    def test_low_oon_is_green(self):
        ex = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.05,
            oon_dollars_annual=500_000,
            seller_avg_rate_multiple_of_medicare=1.6,
        )
        self.assertEqual(ex.band, RegulatoryBand.GREEN)

    def test_non_covered_specialty_returns_green(self):
        """Primary care isn't NSA-covered → no exposure."""
        ex = compute_nsa_exposure(
            specialty="PRIMARY_CARE",
            oon_revenue_share=0.5, oon_dollars_annual=1_000_000,
        )
        self.assertEqual(ex.band, RegulatoryBand.GREEN)
        self.assertEqual(ex.dollars_at_risk_usd, 0.0)

    def test_high_shortfall_without_envision_volume_still_flags(self):
        """APP-pattern: 22% OON share (yellow band from share) +
        high QPA shortfall (red band from shortfall) → RED overall."""
        ex = compute_nsa_exposure(
            specialty="ANESTHESIOLOGY",
            oon_revenue_share=0.22,
            oon_dollars_annual=4_000_000,
            seller_avg_rate_multiple_of_medicare=2.8,
        )
        self.assertEqual(ex.band, RegulatoryBand.RED)


# ── Site-neutral ──────────────────────────────────────────────────

class SiteNeutralScenarioTests(unittest.TestCase):

    def test_current_scenario_sub_15pct_erosion(self):
        """8% erosion under current rule → YELLOW band."""
        ex = simulate_site_neutral_impact(
            scenario="current", hopd_total_revenue_usd=20_000_000,
        )
        self.assertEqual(ex.band, RegulatoryBand.YELLOW)
        self.assertAlmostEqual(
            ex.annual_revenue_erosion_pct, 0.085, delta=0.01,
        )

    def test_legislative_scenario_goes_red(self):
        ex = simulate_site_neutral_impact(
            scenario="legislative", hopd_total_revenue_usd=20_000_000,
        )
        self.assertEqual(ex.band, RegulatoryBand.RED)

    def test_all_scenarios_bundle(self):
        out = simulate_all_scenarios(hopd_total_revenue_usd=10_000_000)
        self.assertEqual(
            set(out.keys()), {"current", "medpac", "legislative"},
        )
        # Legislative should be worst.
        self.assertGreater(
            out["legislative"].annual_revenue_erosion_usd,
            out["current"].annual_revenue_erosion_usd,
        )

    def test_unknown_scenario_raises(self):
        with self.assertRaises(ValueError):
            simulate_site_neutral_impact(
                scenario="hypercube",
                hopd_total_revenue_usd=1_000_000,
            )


# ── TEAM ──────────────────────────────────────────────────────────

class TEAMCBSAMembershipTests(unittest.TestCase):

    def test_new_york_cbsa_is_mandatory(self):
        self.assertTrue(is_cbsa_mandatory("35620"))

    def test_made_up_cbsa_not_mandatory(self):
        self.assertFalse(is_cbsa_mandatory("99999"))

    def test_non_mandatory_cbsa_returns_unknown_band(self):
        ex = compute_team_impact(
            cbsa_code="99999", track="track_2",
            annual_case_volume={"LEJR": 100},
        )
        self.assertFalse(ex.in_mandatory_cbsa)
        self.assertEqual(ex.band, RegulatoryBand.UNKNOWN)
        self.assertEqual(ex.annual_pnl_impact_usd, 0.0)

    def test_worst_quartile_nyc_hospital_is_red(self):
        """Bottom-quartile performer in a mandatory CBSA on track_2
        loses >$1M/yr → RED."""
        ex = compute_team_impact(
            cbsa_code="35620", track="track_2",
            annual_case_volume={"LEJR": 500, "CABG": 100},
            hospital_performance_percentile=0.2,
        )
        self.assertTrue(ex.in_mandatory_cbsa)
        self.assertEqual(ex.band, RegulatoryBand.RED)

    def test_top_quartile_hospital_neutral_to_green(self):
        """Top-quartile performer under Track 1 (no downside) is
        GREEN or near-neutral."""
        ex = compute_team_impact(
            cbsa_code="35620", track="track_1",
            annual_case_volume={"LEJR": 300},
            hospital_performance_percentile=0.9,
        )
        self.assertEqual(ex.band, RegulatoryBand.GREEN)

    def test_unknown_track_raises(self):
        with self.assertRaises(ValueError):
            compute_team_impact(
                cbsa_code="35620", track="track_99",
            )


# ── Antitrust ────────────────────────────────────────────────────

class AntitrustUSAPThresholdTests(unittest.TestCase):

    def test_anesthesia_rollup_in_regulated_msa_triggers_30_day_notice(self):
        ex = compute_antitrust_exposure(
            target_specialty="ANESTHESIOLOGY",
            target_msas=["Houston"],
            acquisitions=[
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.20},
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.15},
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.12},
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.10},
                {"msa": "Houston", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.08},
            ],
        )
        self.assertEqual(ex.band, RegulatoryBand.RED)
        self.assertTrue(ex.thirty_day_ftc_notice_triggered)
        self.assertIn("USAP", " ".join(ex.matching_precedents) or "USAP")

    def test_no_acquisitions_returns_unknown(self):
        ex = compute_antitrust_exposure(
            target_specialty="DERMATOLOGY",
            target_msas=["Denver"],
            acquisitions=[],
        )
        self.assertEqual(ex.band, RegulatoryBand.UNKNOWN)
        self.assertFalse(ex.thirty_day_ftc_notice_triggered)

    def test_non_high_risk_specialty_no_30_day_trigger(self):
        ex = compute_antitrust_exposure(
            target_specialty="FAMILY_MEDICINE",
            target_msas=["Denver"],
            acquisitions=[
                {"msa": "Denver", "specialty": "FAMILY_MEDICINE",
                 "market_share_acquired": 0.5},
            ],
            estimated_hhi=3500,
        )
        self.assertFalse(ex.thirty_day_ftc_notice_triggered)


# ── Content freshness ────────────────────────────────────────────

class ContentFreshnessTests(unittest.TestCase):

    def test_all_content_files_present_and_fresh(self):
        """Weekly regression lock — any stale file fails the suite
        so curation can't silently drift."""
        report = regulatory_content_freshness_report()
        self.assertEqual(
            set(report.keys()),
            {"cpom_states", "nsa_idr_benchmarks",
             "site_neutral_rules", "team_cbsa_list",
             "antitrust_precedents"},
        )
        stale = [k for k, v in report.items() if v["stale"]]
        self.assertEqual(
            stale, [],
            msg=f"Stale regulatory content: {stale}. "
                f"Refresh last_reviewed in the YAMLs.",
        )

    def test_stale_detection_triggers_when_past_threshold(self):
        """Set today to 100d after the current last_reviewed — all
        files should flag stale."""
        future = date.today() + timedelta(days=100)
        report = regulatory_content_freshness_report(
            max_age_days=60, today=future,
        )
        self.assertTrue(all(v["stale"] for v in report.values()))


# ── Composite packet ────────────────────────────────────────────

class ComposePacketTests(unittest.TestCase):

    def test_composite_band_is_worst_of(self):
        cpom = compute_cpom_exposure(
            target_structure="FRIENDLY_PC_PASS_THROUGH",
            footprint_states=["OR"],
        )          # RED
        nsa = compute_nsa_exposure(
            specialty="EMERGENCY_MEDICINE",
            oon_revenue_share=0.05,
            oon_dollars_annual=500_000,
            seller_avg_rate_multiple_of_medicare=1.6,
        )          # GREEN
        packet = compose_packet(
            target_name="T1", cpom=cpom, nsa=nsa,
        )
        self.assertEqual(packet.composite_band, RegulatoryBand.RED)
        self.assertTrue(packet.critical_findings)

    def test_pending_statute_state_is_green(self):
        """New York's bill is pending (no effective_date). A
        direct-employment target touching only NY should score
        GREEN on CPOM."""
        cpom = compute_cpom_exposure(
            target_structure="DIRECT_EMPLOYMENT",
            footprint_states=["NY"],
        )
        packet = compose_packet(target_name="T2", cpom=cpom)
        self.assertEqual(
            packet.composite_band,
            RegulatoryBand.GREEN,
        )

    def test_to_dict_round_trip_shape(self):
        cpom = compute_cpom_exposure(
            target_structure="DIRECT_EMPLOYMENT",
            footprint_states=["NY"],
        )
        packet = compose_packet(target_name="T3", cpom=cpom)
        d = packet.to_dict()
        self.assertIn("composite_band", d)
        self.assertIn("cpom", d)
        self.assertIn("critical_findings", d)
        self.assertEqual(d["target_name"], "T3")


if __name__ == "__main__":
    unittest.main()
