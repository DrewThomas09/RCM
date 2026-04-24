"""Labor economics + referral leakage regression tests (Prompt M)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.labor import (
    benchmark_staffing_ratio, detect_synthetic_fte,
    forecast_wage_inflation,
)
from rcm_mc.diligence.referral import (
    analyze_referral_leakage, compute_provider_concentration,
    stress_test_departures,
)


class WageForecastTests(unittest.TestCase):

    def test_ca_rn_higher_than_national(self):
        national = forecast_wage_inflation(
            msa="National", role="RN",
            current_wage_bill_usd=10_000_000,
        )
        ca = forecast_wage_inflation(
            msa="California (CA)", role="RN",
            current_wage_bill_usd=10_000_000,
        )
        self.assertGreater(
            ca.projected_wage_bill_year5_usd,
            national.projected_wage_bill_year5_usd,
        )

    def test_unknown_msa_falls_back_national(self):
        unknown = forecast_wage_inflation(
            msa="Not-a-real-MSA", role="RN",
            current_wage_bill_usd=1_000_000,
        )
        self.assertAlmostEqual(
            unknown.annualized_inflation_pct, 0.045, delta=0.005,
        )


class StaffingBenchmarkTests(unittest.TestCase):

    def test_understaffed_nurses_flags_high(self):
        r = benchmark_staffing_ratio(
            metric="NURSE_PER_OCCUPIED_BED", target_value=0.7,
        )
        self.assertEqual(r.placement, "below_p25")
        self.assertEqual(r.severity, "HIGH")

    def test_unknown_metric_returns_none(self):
        self.assertIsNone(benchmark_staffing_ratio(
            metric="NONSENSE", target_value=1.0,
        ))


class SyntheticFTETests(unittest.TestCase):

    def test_50pct_gap_is_critical(self):
        r = detect_synthetic_fte(
            scheduled_fte=20, billing_npi_count=35,
            fte_941_headcount=22,
        )
        # gap = (35-20)/20 = 0.75 → CRITICAL
        self.assertEqual(r.severity, "CRITICAL")

    def test_small_gap_is_low(self):
        r = detect_synthetic_fte(
            scheduled_fte=20, billing_npi_count=21,
            fte_941_headcount=20,
        )
        self.assertEqual(r.severity, "LOW")


class ReferralLeakageTests(unittest.TestCase):

    def test_heavy_leakage_flags_high(self):
        result = analyze_referral_leakage(
            referrals=[
                {"destination_npi": "IN-1", "count": 20},
                {"destination_npi": "IN-2", "count": 10},
                {"destination_npi": "OUT-1", "count": 50},
            ],
            network_ids=["IN-1", "IN-2"],
            avg_downstream_revenue_per_referral_usd=3000,
        )
        self.assertAlmostEqual(result.leakage_rate, 50 / 80, places=2)
        self.assertEqual(result.severity, "HIGH")
        self.assertAlmostEqual(
            result.leaked_dollars_estimate_usd, 150_000,
        )

    def test_zero_leakage(self):
        result = analyze_referral_leakage(
            referrals=[{"destination_npi": "IN-1", "count": 10}],
            network_ids=["IN-1"],
        )
        self.assertEqual(result.leakage_rate, 0.0)
        self.assertEqual(result.severity, "LOW")


class ProviderConcentrationTests(unittest.TestCase):

    def _roster(self):
        return {
            "P1": 3_000_000, "P2": 1_500_000,
            "P3": 1_000_000, "P4": 500_000,
            "P5": 500_000, "P6": 300_000,
            "P7": 200_000,
        }

    def test_top1_share_is_correct(self):
        r = compute_provider_concentration(self._roster())
        self.assertAlmostEqual(
            r.top1_share, 3_000_000 / 7_000_000, places=3,
        )

    def test_departure_of_top1_is_material(self):
        r = stress_test_departures(
            self._roster(), departing=["P1"],
            follow_on_retention_pct=0.5,
        )
        # 3M × 0.5 / 7M = 21.4% → CRITICAL
        self.assertEqual(r.severity, "CRITICAL")


if __name__ == "__main__":
    unittest.main()
