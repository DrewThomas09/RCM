"""Quality + working capital + synergy regression tests (Prompt N)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.quality import project_vbp_hrrp
from rcm_mc.diligence.synergy import (
    check_cross_referral_claim, estimate_ehr_migration,
)
from rcm_mc.diligence.working_capital import (
    compute_normalized_peg, detect_pre_close_pull_forward,
    estimate_dnfb,
)


class VBPHRRPTests(unittest.TestCase):

    def test_five_star_with_low_readmit_is_positive(self):
        p = project_vbp_hrrp(
            star_rating=5,
            excess_readmission_ratios={"AMI": 0.95, "HF": 0.93},
            hac_worst_quartile=False,
            base_ms_drg_payments_annual_usd=200_000_000,
        )
        self.assertGreater(p.year1_dollar_impact_usd, 0)
        self.assertEqual(p.severity, "LOW")

    def test_one_star_bad_readmit_hac_is_critical(self):
        p = project_vbp_hrrp(
            star_rating=1,
            excess_readmission_ratios={"AMI": 1.30, "HF": 1.28,
                                        "PN": 1.25},
            hac_worst_quartile=True,
            base_ms_drg_payments_annual_usd=300_000_000,
        )
        self.assertLess(p.year1_dollar_impact_usd, -5_000_000)
        self.assertEqual(p.severity, "CRITICAL")


class PegComputationTests(unittest.TestCase):

    def test_flat_nwc_produces_flat_peg(self):
        months = [1_000_000] * 24
        r = compute_normalized_peg(months)
        self.assertAlmostEqual(
            r.seasonality_adjusted_peg_usd, 1_000_000, delta=100,
        )
        self.assertAlmostEqual(r.dispersion_pct, 0.0, delta=1e-6)

    def test_insufficient_data_returns_simple_mean(self):
        r = compute_normalized_peg([500_000, 600_000, 550_000])
        self.assertIn(
            "<12 months supplied — simple mean only", r.notes,
        )
        self.assertAlmostEqual(
            r.seasonality_adjusted_peg_usd, 550_000, delta=1,
        )


class DNFBTests(unittest.TestCase):

    def test_excessive_dnfb_flags_high(self):
        r = estimate_dnfb(
            discharged_not_billed_claim_count=800,
            avg_claim_value_usd=4_000,
            avg_daily_discharges=100,
        )
        self.assertEqual(r.dnfb_days, 8.0)
        self.assertEqual(r.severity, "HIGH")

    def test_healthy_dnfb_is_low(self):
        r = estimate_dnfb(
            discharged_not_billed_claim_count=250,
            avg_claim_value_usd=4_000,
            avg_daily_discharges=100,
        )
        self.assertEqual(r.dnfb_days, 2.5)
        self.assertEqual(r.severity, "LOW")


class PullForwardTests(unittest.TestCase):

    def test_heavy_pull_forward_critical(self):
        r = detect_pre_close_pull_forward(
            last_60_days_collections_usd=6_000_000,
            prior_12_monthly_collections_usd=[2_000_000] * 12,
        )
        # lift = 6M / (2M*2) = 1.5
        self.assertAlmostEqual(r.lift_ratio, 1.5, delta=0.01)
        self.assertEqual(r.severity, "CRITICAL")

    def test_normal_close_low(self):
        r = detect_pre_close_pull_forward(
            last_60_days_collections_usd=4_000_000,
            prior_12_monthly_collections_usd=[2_000_000] * 12,
        )
        self.assertEqual(r.severity, "LOW")


class IntegrationVelocityTests(unittest.TestCase):

    def test_epic_migration_cost_sums(self):
        v = estimate_ehr_migration(
            target_ehr="EPIC", provider_count=50, bed_count=200,
        )
        expected = 50 * 150_000 + 200 * 800_000
        self.assertAlmostEqual(v.estimated_cost_usd, expected)
        self.assertEqual(v.estimated_duration_months_low, 18)
        self.assertEqual(v.estimated_duration_months_high, 36)

    def test_unknown_ehr_returns_zero_cost(self):
        v = estimate_ehr_migration(
            target_ehr="BESPOKE_EHR", provider_count=5, bed_count=10,
        )
        self.assertEqual(v.estimated_cost_usd, 0.0)


class CrossReferralTests(unittest.TestCase):

    def test_credible_claim_high(self):
        r = check_cross_referral_claim(
            claimed_cross_referral_usd=1_000_000,
            pre_close_referral_pairs=[
                {"from": "A", "to": "B", "dollars_usd": 500_000},
                {"from": "B", "to": "C", "dollars_usd": 400_000},
                {"from": "A", "to": "Z", "dollars_usd": 200_000},  # external
            ],
            sister_practice_ids=["A", "B", "C"],
        )
        # actual = 500k+400k = 900k; 900k/1M = 90%
        self.assertEqual(r.credibility, "HIGH")

    def test_low_credibility_flag(self):
        r = check_cross_referral_claim(
            claimed_cross_referral_usd=2_000_000,
            pre_close_referral_pairs=[
                {"from": "A", "to": "B", "dollars_usd": 100_000},
            ],
            sister_practice_ids=["A", "B"],
        )
        self.assertEqual(r.credibility, "LOW")


if __name__ == "__main__":
    unittest.main()
