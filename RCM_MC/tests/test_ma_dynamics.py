"""MA V28 + payer-mix dynamics regression tests (Prompt L)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.ma_dynamics import (
    analyze_coding_intensity, compute_commercial_concentration,
    compute_v28_recalibration,
    detect_payer_behavior_signals,
    estimate_medicaid_unwind_impact, load_code_map,
    project_risk_contract,
)


class V28RecalibrationTests(unittest.TestCase):

    def test_load_code_map_nonempty(self):
        m = load_code_map()
        self.assertGreater(len(m), 5)
        # Atherosclerosis code is removed under V28
        self.assertIn("I7020", m)
        self.assertIsNone(m["I7020"].v28_hcc)

    def test_removed_code_reduces_risk_score(self):
        """Member with I7020 + E119: V24 has both HCCs; V28 loses
        the atherosclerosis HCC → lower risk score."""
        res = compute_v28_recalibration(
            [{"member_id": "M1",
              "diagnosis_codes": ["I7020", "E119"]}],
        )
        self.assertEqual(res.members_scored, 1)
        self.assertGreater(res.aggregate_v24_score,
                           res.aggregate_v28_score)
        self.assertLess(res.aggregate_revenue_impact_usd, 0)
        self.assertIn("I7020", res.removed_codes_observed)

    def test_empty_member_list_handles_gracefully(self):
        res = compute_v28_recalibration([])
        self.assertEqual(res.members_scored, 0)
        self.assertEqual(res.aggregate_v24_score, 0.0)

    def test_member_with_no_matching_codes_skipped(self):
        res = compute_v28_recalibration([
            {"member_id": "M1",
             "diagnosis_codes": ["Z9999", "X0000"]},
        ])
        # Both codes are off-lattice → member gets 0 score (both
        # V24 and V28), so it's "scored" but with zero risk.
        self.assertEqual(res.members_scored, 1)
        self.assertEqual(res.aggregate_v24_score, 0.0)


class CodingIntensityTests(unittest.TestCase):

    def test_aetna_cvs_pattern_fires_critical(self):
        """High add-only retrospective share × above-benchmark
        capture ratio → CRITICAL."""
        f = analyze_coding_intensity(
            target_name="AetnaCVSReplay",
            target_hcc_capture_rate=0.85,
            specialty_benchmark_capture_rate=0.60,
            add_only_retrospective_pct=0.92,
            total_ma_revenue_usd=500_000_000,
        )
        self.assertEqual(f.severity, "CRITICAL")
        self.assertGreater(f.fca_exposure_estimate_usd, 0)

    def test_normal_practice_is_low_or_medium(self):
        f = analyze_coding_intensity(
            target_name="Normal",
            target_hcc_capture_rate=0.62,
            specialty_benchmark_capture_rate=0.60,
            add_only_retrospective_pct=0.5,
        )
        self.assertIn(f.severity, ("LOW", "MEDIUM"))
        self.assertEqual(f.fca_exposure_estimate_usd, 0.0)


class MedicaidUnwindTests(unittest.TestCase):

    def test_ochin_q4_2023_trend_replays(self):
        """OCHIN Q4 2023 showed -7% Medicaid volume. Passing that
        trend should yield ~7% revenue-at-risk."""
        r = estimate_medicaid_unwind_impact(
            target_state="OR",
            target_medicaid_revenue_annual_usd=10_000_000,
            target_historical_medicaid_trend_pct=-0.07,
        )
        self.assertAlmostEqual(r.volume_at_risk_pct, 0.07, delta=0.02)
        self.assertAlmostEqual(r.revenue_at_risk_usd, 700_000, delta=100_000)
        self.assertEqual(r.severity, "MEDIUM")

    def test_small_remaining_unwind_is_low(self):
        r = estimate_medicaid_unwind_impact(
            target_state="FL",
            target_medicaid_revenue_annual_usd=5_000_000,
            state_unwind_completion_pct=0.99,
        )
        self.assertEqual(r.severity, "LOW")


class CommercialConcentrationTests(unittest.TestCase):

    def test_hhi_matches_hand_computed(self):
        """Three equal payers → shares 1/3 each → HHI = 3 × (33.33)^2
        ≈ 3333. Close to the MEDIUM threshold."""
        r = compute_commercial_concentration({
            "A": 1_000_000, "B": 1_000_000, "C": 1_000_000,
        })
        self.assertAlmostEqual(r.hhi, 3333.33, delta=1)
        self.assertEqual(r.band, "MEDIUM")

    def test_single_payer_dominance_is_high(self):
        r = compute_commercial_concentration({
            "Top": 9_000_000, "Other": 1_000_000,
        })
        self.assertGreater(r.hhi, 3500)
        self.assertEqual(r.band, "HIGH")
        self.assertAlmostEqual(
            r.market_power_squeeze_scenario_usd, 450_000, delta=1,
        )

    def test_diversified_mix_is_low(self):
        r = compute_commercial_concentration(
            {f"P{i}": 1_000_000 for i in range(15)},
        )
        self.assertEqual(r.band, "LOW")


class RiskContractTests(unittest.TestCase):

    def test_savings_case(self):
        p = project_risk_contract(
            contract_type="MSSP",
            attributed_beneficiaries=5000,
            benchmark_pmpm_usd=1100,
            actual_pmpm_usd=1050,
            shared_savings_rate=0.5,
        )
        self.assertGreater(p.projected_earnings_usd, 0)
        self.assertEqual(p.band, "LOW")

    def test_loss_case_caps_with_stop_loss(self):
        p = project_risk_contract(
            contract_type="ACO_REACH",
            attributed_beneficiaries=10000,
            benchmark_pmpm_usd=1000,
            actual_pmpm_usd=1100,
            shared_savings_rate=0.5,
            shared_loss_rate=0.5,
            stop_loss_cap_usd=2_000_000,
        )
        self.assertEqual(p.projected_earnings_usd, -2_000_000)
        self.assertEqual(p.band, "HIGH")


class PayerBehaviorTests(unittest.TestCase):

    def test_high_prior_auth_denial_flags_high(self):
        f = detect_payer_behavior_signals([{
            "payer": "Aggressive PayerCo",
            "prior_auth_denial_rate": 0.42,
        }])[0]
        self.assertIn(f.severity, ("HIGH", "CRITICAL"))

    def test_downcoding_plus_high_denial_is_critical(self):
        f = detect_payer_behavior_signals([{
            "payer": "Aggressive PayerCo",
            "downcoding_rate": 0.20,
            "prior_auth_denial_rate": 0.40,
        }])[0]
        self.assertEqual(f.severity, "CRITICAL")

    def test_clean_payer_is_low(self):
        f = detect_payer_behavior_signals([{
            "payer": "Benign PayerCo",
            "downcoding_rate": 0.03,
            "prior_auth_denial_rate": 0.08,
            "appeal_overturn_rate": 0.30,
        }])[0]
        self.assertEqual(f.severity, "LOW")


if __name__ == "__main__":
    unittest.main()
