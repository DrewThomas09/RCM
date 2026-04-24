"""Cyber posture + BI loss regression tests (Prompt K).

- EHR vendor risk lookups
- BA cascade: Change Healthcare → CRITICAL + 2.5x multiplier
- BI loss Monte Carlo: mean increases with revenue/day + downtime
- IT capex: overdue EHR + staffing gap → CRITICAL severity
- CyberScore composite: Change-Healthcare-BA target → RED +
  block_packet_build flag
- Bridge reserve: GREEN 0% / YELLOW 1.5% / RED 5%
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.cyber import (
    assess_business_associates, compose_cyber_score,
    cyber_bridge_reserve_pct, detect_deferred_it_capex,
    ehr_vendor_risk_score, list_ehr_vendors, simulate_bi_loss,
)


class EHRVendorRiskTests(unittest.TestCase):

    def test_lists_six_expected_vendors(self):
        vendors = list_ehr_vendors()
        for v in ("EPIC", "ORACLE_CERNER", "ATHENAHEALTH",
                  "ECLINICALWORKS", "NEXTGEN", "MEDITECH"):
            self.assertIn(v, vendors)

    def test_cerner_score_higher_than_meditech(self):
        """Oracle Cerner carries more incident history than Meditech
        in public records."""
        self.assertGreater(
            ehr_vendor_risk_score("ORACLE_CERNER"),
            ehr_vendor_risk_score("MEDITECH"),
        )

    def test_unknown_vendor_returns_none(self):
        self.assertIsNone(ehr_vendor_risk_score("BESPOKE_EHR"))


class BACascadeTests(unittest.TestCase):

    def test_change_healthcare_is_critical(self):
        findings = assess_business_associates([
            "Change Healthcare",
            "In-House Clearinghouse",
        ])
        self.assertEqual(len(findings), 2)
        ch = next(f for f in findings
                  if f.matched_catastrophe == "Change Healthcare")
        self.assertEqual(ch.severity, "CRITICAL")
        self.assertGreaterEqual(ch.cascade_risk_multiplier, 2.0)

    def test_alias_matching_works(self):
        """The YAML 'aka' list catches common name variants."""
        findings = assess_business_associates([
            "Optum / Change", "ChangeHealthcare",
        ])
        self.assertTrue(all(
            f.matched_catastrophe == "Change Healthcare"
            for f in findings
        ))

    def test_unknown_ba_is_low(self):
        findings = assess_business_associates(["Bespoke Vendor LLC"])
        self.assertEqual(findings[0].severity, "LOW")
        self.assertIsNone(findings[0].matched_catastrophe)


class BILossModelTests(unittest.TestCase):

    def test_higher_revenue_per_day_produces_higher_expected_loss(self):
        small = simulate_bi_loss(
            revenue_per_day_baseline_usd=50_000,
            incident_probability_per_year=0.10,
            n_runs=500, seed=1,
        )
        large = simulate_bi_loss(
            revenue_per_day_baseline_usd=500_000,
            incident_probability_per_year=0.10,
            n_runs=500, seed=1,
        )
        self.assertGreater(
            large.expected_loss_usd, small.expected_loss_usd * 5,
        )

    def test_cascade_multiplier_scales_loss(self):
        base = simulate_bi_loss(
            revenue_per_day_baseline_usd=100_000,
            incident_probability_per_year=0.10,
            cascade_risk_multiplier=1.0,
            n_runs=500, seed=7,
        )
        cascaded = simulate_bi_loss(
            revenue_per_day_baseline_usd=100_000,
            incident_probability_per_year=0.10,
            cascade_risk_multiplier=2.5,
            n_runs=500, seed=7,
        )
        self.assertGreater(
            cascaded.expected_loss_usd, base.expected_loss_usd * 2,
        )

    def test_zero_probability_zero_loss(self):
        result = simulate_bi_loss(
            revenue_per_day_baseline_usd=100_000,
            incident_probability_per_year=0.0,
            n_runs=200,
        )
        self.assertEqual(result.expected_loss_usd, 0.0)


class ITCapexTests(unittest.TestCase):

    def test_epic_overdue_plus_staffing_gap_is_critical(self):
        f = detect_deferred_it_capex(
            ehr_vendor="EPIC",
            years_since_ehr_implementation=13,      # 4y overdue
            annual_revenue_usd=500_000_000,
            it_fte_count=20,                          # expected ~55
        )
        self.assertEqual(f.severity, "CRITICAL")
        self.assertGreater(f.estimated_replacement_cost_usd, 0)
        self.assertIn("EPIC", f.narrative)

    def test_within_benchmark_is_low(self):
        f = detect_deferred_it_capex(
            ehr_vendor="EPIC",
            years_since_ehr_implementation=5,
            annual_revenue_usd=100_000_000,
            it_fte_count=12,
        )
        self.assertEqual(f.severity, "LOW")
        self.assertEqual(f.estimated_replacement_cost_usd, 0.0)


class CyberScoreCompositeTests(unittest.TestCase):

    def test_change_healthcare_ba_plus_low_ehr_pushes_red(self):
        ba_findings = assess_business_associates(["Change Healthcare"])
        capex = detect_deferred_it_capex(
            ehr_vendor="ORACLE_CERNER",
            years_since_ehr_implementation=12,
            annual_revenue_usd=200_000_000,
            it_fte_count=12,
        )
        bi = simulate_bi_loss(
            revenue_per_day_baseline_usd=550_000,
            incident_probability_per_year=0.15,
            cascade_risk_multiplier=2.5,
            n_runs=500,
        )
        score = compose_cyber_score(
            external_rating=None,
            ehr_vendor_risk=ehr_vendor_risk_score("ORACLE_CERNER"),
            ba_findings=ba_findings,
            it_capex=capex,
            bi_loss=bi,
            annual_revenue_usd=200_000_000,
        )
        self.assertEqual(score.band, "RED")
        self.assertTrue(score.block_packet_build)
        self.assertGreaterEqual(score.ba_critical_count, 1)

    def test_clean_target_is_green(self):
        # No BA findings + clean vendor + no capex overdue
        score = compose_cyber_score(
            external_rating=35,                  # below baseline 50
            ehr_vendor_risk=ehr_vendor_risk_score("MEDITECH"),
            ba_findings=[],
            it_capex=None,
            bi_loss=None,
            annual_revenue_usd=100_000_000,
        )
        self.assertEqual(score.band, "GREEN")
        self.assertFalse(score.block_packet_build)

    def test_bridge_reserve_pcts(self):
        self.assertEqual(cyber_bridge_reserve_pct("GREEN"), 0.0)
        self.assertAlmostEqual(
            cyber_bridge_reserve_pct("YELLOW"), 0.015,
        )
        self.assertAlmostEqual(cyber_bridge_reserve_pct("RED"), 0.05)


if __name__ == "__main__":
    unittest.main()
