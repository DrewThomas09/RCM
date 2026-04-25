"""Tests for the ESG-HealthcarePacket."""
from __future__ import annotations

import unittest


class TestCarbon(unittest.TestCase):
    def test_hospital_scope_1_2_3(self):
        from rcm_mc.esg import (
            Facility, FacilityType, compute_scope_1_2_3,
        )
        f = Facility(
            facility_id="F1", name="Hosp 1",
            facility_type=FacilityType.HOSPITAL,
            state="TX", sq_ft=200_000,
            annual_kwh=8_000_000,
            annual_natgas_kwh=2_000_000,
            fleet_diesel_l=10_000,
            sevoflurane_kg=120,
            n2o_kg=400,
            procedures_per_year=15_000,
        )
        cf = compute_scope_1_2_3(f)
        # Scope 1: 2M × 0.18 + 10K × 2.68 + 120 × 130 + 400 × 298
        # = 360000 + 26800 + 15600 + 119200 = 521600
        self.assertAlmostEqual(cf.scope_1_kgco2e, 521600, delta=1)
        # Scope 2: 8M × 0.42 = 3,360,000
        self.assertAlmostEqual(cf.scope_2_kgco2e, 3_360_000,
                               delta=1)
        # Scope 3 = (s1 + s2) × 2.5
        self.assertAlmostEqual(
            cf.scope_3_kgco2e,
            (521600 + 3_360_000) * 2.5, delta=1,
        )
        # Total = sum
        self.assertAlmostEqual(
            cf.total_kgco2e,
            cf.scope_1_kgco2e + cf.scope_2_kgco2e
            + cf.scope_3_kgco2e, delta=1,
        )

    def test_state_grid_factor_sensitivity(self):
        """California grid is half the carbon of Texas grid → S2
        roughly halves."""
        from rcm_mc.esg import (
            Facility, FacilityType, compute_scope_1_2_3,
        )
        common = dict(
            facility_id="F", name="N",
            facility_type=FacilityType.HOSPITAL,
            sq_ft=100_000, annual_kwh=5_000_000,
        )
        tx = compute_scope_1_2_3(Facility(state="TX", **common))
        ca = compute_scope_1_2_3(Facility(state="CA", **common))
        self.assertGreater(tx.scope_2_kgco2e, ca.scope_2_kgco2e)


class TestDEI(unittest.TestCase):
    def test_computes_ratios(self):
        from rcm_mc.esg import compute_dei_metrics, WorkforceProfile
        dei = compute_dei_metrics(WorkforceProfile(
            total_headcount=1000,
            female_count=620, urm_count=200,
            female_in_management_count=45,
            management_count=100,
            board_members=8, board_female=3, board_urm=2,
            median_male_earnings=85000,
            median_female_earnings=80750,
            annual_voluntary_turnover_count=120,
        ))
        self.assertEqual(dei.pct_female, 0.62)
        self.assertEqual(dei.pct_urm, 0.20)
        self.assertEqual(dei.pct_female_in_management, 0.45)
        self.assertAlmostEqual(dei.pay_equity_ratio, 0.95, places=2)
        self.assertEqual(dei.annual_turnover_rate, 0.12)


class TestGovernance(unittest.TestCase):
    def test_undisclosed_cpom_drops_score(self):
        from rcm_mc.esg import score_governance, GovernanceProfile
        clean = score_governance(GovernanceProfile(
            has_cpom_msot_structure=True,
            cpom_structure_disclosed=True,
            board_total=8, board_independent=5,
            annual_third_party_audit=True,
            named_compliance_officer=True,
            anonymous_reporting_channel=True,
        ))
        opaque = score_governance(GovernanceProfile(
            has_cpom_msot_structure=True,
            cpom_structure_disclosed=False,
            board_total=8, board_independent=5,
            annual_third_party_audit=True,
            named_compliance_officer=True,
            anonymous_reporting_channel=True,
        ))
        self.assertGreater(clean.cpom_transparency,
                           opaque.cpom_transparency)
        self.assertGreater(clean.composite, opaque.composite)


class TestEDCIScorecard(unittest.TestCase):
    def test_aligned_band_requires_issb(self):
        from rcm_mc.esg import (
            Facility, FacilityType,
            compute_dei_metrics, WorkforceProfile,
            score_governance, GovernanceProfile,
            compute_edci_scorecard,
        )
        facilities = [Facility(
            facility_id="F1", name="N",
            facility_type=FacilityType.HOSPITAL,
            state="TX", annual_kwh=1_000_000,
            annual_natgas_kwh=500_000,
        )]
        dei = compute_dei_metrics(WorkforceProfile(
            total_headcount=500, female_count=300,
            urm_count=100, female_in_management_count=30,
            management_count=60, board_members=8,
            board_female=3, board_urm=2,
            median_male_earnings=80000,
            median_female_earnings=78000,
            annual_voluntary_turnover_count=50,
        ))
        gov = score_governance(GovernanceProfile(
            has_cpom_msot_structure=False,
            board_total=8, board_independent=5,
            annual_third_party_audit=True,
            named_compliance_officer=True,
            anonymous_reporting_channel=True,
        ))

        # Without ISSB attestation → Comprehensive
        sc = compute_edci_scorecard(
            "Test Co", facilities=facilities,
            dei=dei, governance=gov,
            issb_attested=False,
            cybersecurity_attested=True,
        )
        self.assertEqual(sc.maturity_band, "Comprehensive")

        # With ISSB attestation → Aligned
        sc2 = compute_edci_scorecard(
            "Test Co", facilities=facilities,
            dei=dei, governance=gov,
            issb_attested=True,
            cybersecurity_attested=True,
        )
        self.assertEqual(sc2.maturity_band, "Aligned")


class TestDisclosureRender(unittest.TestCase):
    def test_renders_markdown_with_required_sections(self):
        from rcm_mc.esg import (
            Facility, FacilityType,
            compute_dei_metrics, WorkforceProfile,
            score_governance, GovernanceProfile,
            compute_edci_scorecard, render_lp_disclosure,
        )
        facilities = [Facility(
            facility_id="F1", name="N",
            facility_type=FacilityType.HOSPITAL,
            state="TX", annual_kwh=1_000_000,
        )]
        dei = compute_dei_metrics(WorkforceProfile(
            total_headcount=500, female_count=275,
            urm_count=125,
            female_in_management_count=25,
            management_count=50,
            board_members=8, board_female=3, board_urm=2,
            median_male_earnings=85000,
            median_female_earnings=78000,
            annual_voluntary_turnover_count=70,
        ))
        gov = score_governance(GovernanceProfile(
            has_cpom_msot_structure=True,
            cpom_structure_disclosed=True,
            board_total=8, board_independent=5,
            annual_third_party_audit=True,
            named_compliance_officer=True,
            anonymous_reporting_channel=True,
        ))
        sc = compute_edci_scorecard(
            "Test Co", facilities=facilities,
            dei=dei, governance=gov,
            issb_attested=True, cybersecurity_attested=True,
        )
        md = render_lp_disclosure(sc)
        # Required sections present
        self.assertIn("## ESG Disclosure", md)
        self.assertIn("EDCI maturity band", md)
        self.assertIn("### Climate", md)
        self.assertIn("### Workforce", md)
        self.assertIn("### Governance", md)
        self.assertIn("Cybersecurity", md)


if __name__ == "__main__":
    unittest.main()
