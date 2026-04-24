"""Real-estate / lease-economics regression tests (Prompt H).

- Steward 2016 replay: all 5 factors trip → CRITICAL
- Prospect 2019 replay: 4 factors trip → HIGH
- Lease PV matches analytical baseline (constant rent, no
  escalator, flat discount → closed-form annuity PV)
- Rent benchmarks return correct bands per specialty
- Sale-leaseback blocker: MA (IN_EFFECT), CT (PHASED),
  PA (PENDING), unknown state (NONE)
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.real_estate import (
    FACTOR_COVERAGE, FACTOR_ESCALATOR, FACTOR_GEOGRAPHY,
    FACTOR_LEASE_DURATION, FACTOR_REIT_LANDLORD,
    LeaseLine, LeaseSchedule, StewardRiskTier,
    classify_rent_share, compute_capex_wall,
    compute_lease_waterfall, compute_steward_score,
    get_rent_benchmark, rent_is_suicidal,
    sale_leaseback_feasibility,
)


def _steward_2016_schedule() -> LeaseSchedule:
    """Replay of Steward's 2016 MPT master-lease parameters."""
    return LeaseSchedule(
        lines=[
            LeaseLine(
                property_id="St-Elizabeth",
                property_type="HOSPITAL",
                base_rent_annual_usd=18_000_000,
                escalator_pct=0.035,       # >3%
                term_years=20,             # >15
                landlord="Medical Properties Trust",
                property_revenue_annual_usd=130_000_000,
            ),
            LeaseLine(
                property_id="Good-Samaritan",
                property_type="HOSPITAL",
                base_rent_annual_usd=14_000_000,
                escalator_pct=0.032,
                term_years=20,
                landlord="MPT",
                property_revenue_annual_usd=100_000_000,
            ),
        ],
        discount_rate=0.08,
    )


def _prospect_2019_schedule() -> LeaseSchedule:
    """4-factor replay — same profile as Steward EXCEPT geography
    (urban/academic, not rural). Tests the 4-factor → HIGH tier."""
    return LeaseSchedule(
        lines=[
            LeaseLine(
                property_id="Prospect-1",
                property_type="HOSPITAL",
                base_rent_annual_usd=22_000_000,
                escalator_pct=0.035,
                term_years=18,
                landlord="Medical Properties Trust",
                property_revenue_annual_usd=160_000_000,
            ),
        ],
        discount_rate=0.075,
    )


class StewardScoreReplayTests(unittest.TestCase):

    def test_steward_2016_critical(self):
        s = _steward_2016_schedule()
        result = compute_steward_score(
            s,
            portfolio_ebitdar_annual_usd=32_000_000 * 1.2,  # 1.2x coverage
            geography="RURAL",
        )
        self.assertEqual(result.tier, StewardRiskTier.CRITICAL)
        self.assertEqual(result.factor_count, 5)
        for factor in (FACTOR_LEASE_DURATION, FACTOR_ESCALATOR,
                       FACTOR_COVERAGE, FACTOR_GEOGRAPHY,
                       FACTOR_REIT_LANDLORD):
            self.assertIn(factor, result.factors_hit)
        self.assertIn("Steward", (result.matching_case_study or ""))

    def test_prospect_2019_high_not_critical(self):
        s = _prospect_2019_schedule()
        result = compute_steward_score(
            s,
            portfolio_ebitdar_annual_usd=22_000_000 * 1.1,  # coverage <1.4x
            geography="URBAN_ACADEMIC",                     # not rural
        )
        self.assertEqual(result.tier, StewardRiskTier.HIGH)
        self.assertEqual(result.factor_count, 4)
        self.assertNotIn(FACTOR_GEOGRAPHY, result.factors_hit)
        self.assertIn("Prospect", (result.matching_case_study or ""))

    def test_clean_hospital_lease_is_low(self):
        """Short, low-escalator, high-coverage, urban, non-REIT."""
        s = LeaseSchedule(lines=[
            LeaseLine(
                property_id="Clean",
                property_type="HOSPITAL",
                base_rent_annual_usd=5_000_000,
                escalator_pct=0.02,
                term_years=10,
                landlord="Private LLC",
            ),
        ])
        result = compute_steward_score(
            s,
            portfolio_ebitdar_annual_usd=15_000_000,   # 3x coverage
            geography="URBAN_ACADEMIC",
        )
        self.assertEqual(result.tier, StewardRiskTier.LOW)
        self.assertEqual(result.factor_count, 0)


class LeasePVTests(unittest.TestCase):

    def test_flat_rent_pv_matches_annuity_formula(self):
        """Constant rent with zero escalator over N years at rate r
        should equal the ordinary annuity PV."""
        rent = 1_000_000.0
        years = 5
        rate = 0.08
        s = LeaseSchedule(
            lines=[LeaseLine(
                property_id="A", property_type="HOSPITAL",
                base_rent_annual_usd=rent,
                escalator_pct=0.0, term_years=years,
            )],
            discount_rate=rate,
        )
        wf = compute_lease_waterfall(s, hold_years=years)
        expected = sum(rent / ((1 + rate) ** y) for y in range(1, years + 1))
        self.assertAlmostEqual(
            wf.total_rent_pv_usd, expected, places=2,
        )
        self.assertAlmostEqual(
            wf.total_rent_nominal_usd, rent * years, places=2,
        )

    def test_term_shorter_than_hold_caps_rent(self):
        """Rent drops to zero after term_years even if hold > term."""
        s = LeaseSchedule(
            lines=[LeaseLine(
                property_id="A", property_type="HOSPITAL",
                base_rent_annual_usd=1_000_000,
                escalator_pct=0.0, term_years=3,
            )],
            discount_rate=0.0,
        )
        wf = compute_lease_waterfall(s, hold_years=10)
        self.assertAlmostEqual(
            wf.total_rent_nominal_usd, 3_000_000, places=2,
        )

    def test_rent_share_per_property(self):
        s = LeaseSchedule(lines=[LeaseLine(
            property_id="A", property_type="HOSPITAL",
            base_rent_annual_usd=500_000,
            escalator_pct=0.0, term_years=10,
            property_revenue_annual_usd=5_000_000,
        )])
        wf = compute_lease_waterfall(s, hold_years=10)
        self.assertAlmostEqual(
            wf.per_property[0].rent_pct_of_revenue, 0.10, places=4,
        )

    def test_ebitdar_coverage(self):
        s = LeaseSchedule(lines=[LeaseLine(
            property_id="A", property_type="HOSPITAL",
            base_rent_annual_usd=1_000_000,
            escalator_pct=0.0, term_years=10,
        )])
        wf = compute_lease_waterfall(
            s, hold_years=10,
            portfolio_ebitdar_annual_usd=2_500_000,
        )
        self.assertAlmostEqual(wf.ebitdar_coverage, 2.5, places=4)


class RentBenchmarkSpecialtyTests(unittest.TestCase):

    def test_hospital_band_returns_typical_range(self):
        bench = get_rent_benchmark("HOSPITAL")
        self.assertIsNotNone(bench)
        bands = bench["rent_pct_revenue"]
        self.assertAlmostEqual(bands["p50"], 0.04, delta=0.01)

    def test_classifies_steward_rent_share_as_above_p75(self):
        """Steward's ~15% rent-to-revenue is firmly above the
        hospital p75 benchmark."""
        self.assertEqual(
            classify_rent_share("HOSPITAL", 0.15), "above_p75",
        )

    def test_classifies_normal_hospital_rent_in_range(self):
        self.assertEqual(
            classify_rent_share("HOSPITAL", 0.035),
            "p25_to_p50",
        )

    def test_unknown_specialty_returns_unknown(self):
        self.assertEqual(
            classify_rent_share("WIDGET_FACTORY", 0.20),
            "unknown",
        )

    def test_rent_is_suicidal_flag_for_steward(self):
        # Steward's ~15% on hospitals is 3x the p75 (5%)
        self.assertTrue(rent_is_suicidal("HOSPITAL", 0.15))

    def test_rent_is_suicidal_false_for_normal_asc(self):
        # Normal ASC rent 5% is below 2x p75 (14%)
        self.assertFalse(rent_is_suicidal("ASC", 0.05))


class SaleLeasebackBlockerStateMatrixTests(unittest.TestCase):

    def test_ma_in_effect_not_feasible(self):
        results = sale_leaseback_feasibility(["MA"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "IN_EFFECT")
        self.assertFalse(results[0].feasible)

    def test_ct_phased_still_feasible_in_window(self):
        results = sale_leaseback_feasibility(["CT"])
        self.assertEqual(results[0].status, "PHASED")
        # CT is phased — feasibility depends on timing, default True
        self.assertTrue(results[0].feasible)

    def test_pa_pending_is_feasible_with_watch_caveat(self):
        results = sale_leaseback_feasibility(["PA"])
        self.assertEqual(results[0].status, "PENDING")
        self.assertTrue(results[0].feasible)

    def test_unknown_state_returns_none_status(self):
        results = sale_leaseback_feasibility(["TX"])
        self.assertEqual(results[0].status, "NONE")
        self.assertTrue(results[0].feasible)

    def test_full_matrix_shape(self):
        codes = ["MA", "CT", "PA", "RI", "TX"]
        results = sale_leaseback_feasibility(codes)
        self.assertEqual(len(results), len(codes))
        returned_codes = [r.state_code for r in results]
        self.assertEqual(returned_codes, codes)


class CapexWallTests(unittest.TestCase):

    def test_overaged_assets_produce_backlog(self):
        """Assets depreciated to near-zero with no replacement over
        the useful-life window → HIGH severity + nonzero backlog
        when overage is present."""
        result = compute_capex_wall(
            gross_fixed_assets_usd=200_000_000,
            accumulated_depreciation_usd=180_000_000,
            annual_depreciation_usd=4_000_000,  # → age 45y
            useful_life_years=35,
            hold_years=5,
        )
        self.assertGreater(result.avg_fixed_asset_age_years, 35)
        self.assertGreater(result.deferred_capex_backlog_usd, 0)
        self.assertEqual(result.severity, "HIGH")
        self.assertEqual(len(result.annual_recovery_profile_usd), 5)

    def test_young_assets_are_low_severity(self):
        result = compute_capex_wall(
            gross_fixed_assets_usd=100_000_000,
            accumulated_depreciation_usd=10_000_000,
            annual_depreciation_usd=5_000_000,
            useful_life_years=30,
        )
        self.assertEqual(result.severity, "LOW")
        self.assertEqual(result.deferred_capex_backlog_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
