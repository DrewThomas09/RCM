"""Tests for Bridge v3 — VBC cohort LTV + capitation engine.

Coverage:
  • CMS-HCC V28 risk scoring + V28 phase-in
  • PCC/TCC capitation revenue with quality withhold
  • Two-sided shared-savings (upside / downside / cap)
  • Multi-year cohort LTV + panel rollup
  • Bayesian shrinkage on cohort PMPM observations
"""
from __future__ import annotations

import unittest


class TestHCCScoring(unittest.TestCase):
    def test_demographic_only_no_hcc(self):
        from rcm_mc.vbc import compute_hcc_score
        # 70-year-old female, no chronic conditions, PY2026
        score = compute_hcc_score(
            age=70, female=True, hcc_distribution={},
            payment_year=2026,
        )
        # Demographic factor for 70-74 female ≈ 0.398 × 1.05 = 0.418
        # Then × 0.941 coding intensity = ~0.393
        self.assertAlmostEqual(score, 0.418 * 0.941, places=2)

    def test_diabetes_uplift_in_v28(self):
        """V28 increased the diabetes-no-comp weight from 0.105 to
        0.166 — a 58% reweight that shows up in scored revenue."""
        from rcm_mc.vbc import compute_hcc_score
        no_dm = compute_hcc_score(
            age=70, female=False, hcc_distribution={},
            payment_year=2026,
        )
        with_dm = compute_hcc_score(
            age=70, female=False,
            hcc_distribution={"HCC_DM_NO_COMP": 1.0},
            payment_year=2026,
        )
        uplift = with_dm - no_dm
        # 0.166 × 0.941 = 0.156 uplift
        self.assertGreater(uplift, 0.14)
        self.assertLess(uplift, 0.17)

    def test_v28_phase_in_blends(self):
        """A condition that is ZERO-weighted in V28 (HCC_VASC) but
        weighted in V24 should fade out as V28 phase-in advances."""
        from rcm_mc.vbc import compute_hcc_score, V28_PHASE_IN
        scores = []
        for year in (2024, 2025, 2026):
            s = compute_hcc_score(
                age=70, female=False,
                hcc_distribution={"HCC_VASC": 1.0},
                payment_year=year,
            )
            scores.append(s)
        # Score should monotonically decrease as V28 phases in
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], scores[2])
        # PY2026 should be 100% V28 → HCC_VASC adds nothing beyond demo
        demo_only = compute_hcc_score(
            age=70, female=False, hcc_distribution={},
            payment_year=2026,
        )
        self.assertAlmostEqual(scores[2], demo_only, places=3)
        # Verify the published phase-in schedule
        self.assertEqual(V28_PHASE_IN[2026], 1.0)
        self.assertAlmostEqual(V28_PHASE_IN[2024], 0.33, places=2)


class TestCapitationRevenue(unittest.TestCase):
    def test_quality_withhold_released_at_full_score(self):
        from rcm_mc.vbc import compute_capitation_revenue, ContractTerms
        c = ContractTerms(
            contract_type="TCC", benchmark_pmpm=1100.0,
            risk_score=1.0, quality_withhold_pct=0.02,
        )
        # Quality 1.0 → all withhold released → net == gross
        result = compute_capitation_revenue(
            cohort_size=1000, contract=c, quality_score=1.0)
        self.assertAlmostEqual(
            result["net_revenue"],
            result["gross_capitation"], places=2)
        self.assertEqual(result["withhold_forfeited"], 0.0)

    def test_quality_score_zero_forfeits_withhold(self):
        from rcm_mc.vbc import compute_capitation_revenue, ContractTerms
        c = ContractTerms(quality_withhold_pct=0.02)
        result = compute_capitation_revenue(
            cohort_size=1000, contract=c, quality_score=0.0)
        # Net should be (1 - 0.02) of gross when withhold is fully forfeit
        self.assertAlmostEqual(
            result["net_revenue"],
            result["gross_capitation"] * 0.98,
            places=2,
        )
        self.assertGreater(result["withhold_forfeited"], 0)

    def test_risk_score_scales_revenue(self):
        from rcm_mc.vbc import compute_capitation_revenue, ContractTerms
        base = compute_capitation_revenue(
            cohort_size=1000,
            contract=ContractTerms(risk_score=1.0),
        )
        elevated = compute_capitation_revenue(
            cohort_size=1000,
            contract=ContractTerms(risk_score=1.4),
        )
        # 40% more risk → 40% more gross capitation
        self.assertAlmostEqual(
            elevated["gross_capitation"] / base["gross_capitation"],
            1.4, places=2,
        )


class TestSharedSavings(unittest.TestCase):
    def test_savings_above_msr(self):
        from rcm_mc.vbc import compute_shared_savings, ContractTerms
        c = ContractTerms(
            benchmark_pmpm=1100.0, risk_score=1.0,
            msr_pct=0.02, upside_share=1.0, upside_cap_pct=0.10,
        )
        # Actual PMPM 5% below benchmark → 5% - 2% MSR = 3% savings
        result = compute_shared_savings(
            cohort_size=1000, contract=c, actual_pmpm=1045.0)
        self.assertEqual(result["side"], "savings")
        self.assertGreater(result["net_shared"], 0)

    def test_losses_below_mlr(self):
        from rcm_mc.vbc import compute_shared_savings, ContractTerms
        c = ContractTerms(
            benchmark_pmpm=1100.0, risk_score=1.0,
            mlr_pct=0.02, downside_share=1.0, downside_cap_pct=0.05,
        )
        # Actual PMPM 5% above benchmark → 5% - 2% MLR = 3% loss
        result = compute_shared_savings(
            cohort_size=1000, contract=c, actual_pmpm=1155.0)
        self.assertEqual(result["side"], "losses")
        self.assertLess(result["net_shared"], 0)

    def test_neutral_band_around_benchmark(self):
        """If actual PMPM is within MSR/MLR of benchmark, neither
        upside nor downside fires."""
        from rcm_mc.vbc import compute_shared_savings, ContractTerms
        c = ContractTerms(msr_pct=0.02, mlr_pct=0.02)
        # Actual exactly at benchmark
        r = compute_shared_savings(
            cohort_size=1000, contract=c, actual_pmpm=1100.0)
        self.assertEqual(r["side"], "neutral")
        self.assertEqual(r["net_shared"], 0.0)


class TestCohortLTV(unittest.TestCase):
    def setUp(self):
        from rcm_mc.vbc import Cohort, ContractTerms
        self.cohort = Cohort(
            cohort_id="MA_TX_75plus",
            name="Texas MA 75+ duals",
            size=2000, avg_age=78,
            pct_female=0.58,
            pct_dual_eligible=0.30,
            hcc_distribution={
                "HCC_DM_NO_COMP": 0.32,
                "HCC_CHF": 0.18,
                "HCC_COPD": 0.24,
            },
            annual_pmpm_cost=1080.0,
            quality_score=0.88,
            expected_attrition_rate=0.08,
        )
        self.contract = ContractTerms(
            contract_type="TCC", benchmark_pmpm=1180.0,
            risk_score=1.0, quality_withhold_pct=0.02,
            msr_pct=0.02, mlr_pct=0.02,
            upside_share=1.0, downside_share=1.0,
        )

    def test_ltv_positive_for_well_managed_cohort(self):
        from rcm_mc.vbc import compute_cohort_ltv
        result = compute_cohort_ltv(
            self.cohort, self.contract,
            horizon_years=5, discount_rate=0.10,
            starting_payment_year=2026, operating_cost_pmpm=80.0,
        )
        self.assertEqual(result.starting_lives, 2000)
        self.assertEqual(result.horizon_years, 5)
        self.assertEqual(len(result.cashflow_by_year), 5)
        # Profitable cohort → positive LTV
        self.assertGreater(result.nominal_ltv, 0)
        self.assertGreater(result.discounted_ltv, 0)
        # Discounted < nominal (10% rate, 5 years)
        self.assertLess(result.discounted_ltv, result.nominal_ltv)

    def test_ltv_attrition_decays_lives(self):
        """8% attrition over 5 years → ~67% of starting cohort
        retained at year 5."""
        from rcm_mc.vbc import compute_cohort_ltv
        result = compute_cohort_ltv(
            self.cohort, self.contract,
            horizon_years=5, starting_payment_year=2026,
        )
        first_year_lives = result.cashflow_by_year[0]["lives"]
        last_year_lives = result.cashflow_by_year[-1]["lives"]
        self.assertLess(last_year_lives, first_year_lives)
        # Approximate attrition: 0.92^4 = 0.716
        self.assertAlmostEqual(
            last_year_lives / first_year_lives, 0.716, places=2,
        )

    def test_v28_phase_complete_in_ltv_window(self):
        """Starting in 2026, every year of the LTV horizon should
        be in the V28 steady state (1.0)."""
        from rcm_mc.vbc import compute_cohort_ltv, V28_PHASE_IN
        result = compute_cohort_ltv(
            self.cohort, self.contract,
            horizon_years=5, starting_payment_year=2026,
        )
        from rcm_mc.vbc.hcc import _v28_phase
        for cf in result.cashflow_by_year:
            self.assertEqual(_v28_phase(cf["year"]), 1.0)


class TestPanelLTV(unittest.TestCase):
    def test_panel_aggregates_cohorts(self):
        from rcm_mc.vbc import (
            Cohort, CohortPanel, ContractTerms,
            project_panel_lifetime_value,
        )
        panel = CohortPanel(
            panel_id="ACO_REACH_2026",
            operator_name="Friendly Health PCs",
            cohorts=[
                Cohort(cohort_id="C1", size=1500, avg_age=70,
                       hcc_distribution={"HCC_DM_NO_COMP": 0.25}),
                Cohort(cohort_id="C2", size=900, avg_age=80,
                       hcc_distribution={"HCC_CHF": 0.20}),
            ],
            benchmark_year=2026,
        )
        contract = ContractTerms(
            contract_type="TCC", benchmark_pmpm=1100.0,
        )
        result = project_panel_lifetime_value(
            panel, contract, horizon_years=3,
        )
        self.assertEqual(result["starting_lives"], 2400)
        self.assertEqual(len(result["per_cohort"]), 2)
        # Sum of per-cohort LTV equals total
        total = sum(c["nominal_ltv"] for c in result["per_cohort"])
        self.assertAlmostEqual(
            total, result["total_nominal_ltv"], places=1,
        )


class TestShrinkage(unittest.TestCase):
    def test_small_cohort_shrunk_more(self):
        from rcm_mc.vbc import bayesian_shrink_cohort
        # Population: 5 cohorts at $1000 PMPM (low variance)
        pop = [1000, 1010, 990, 1020, 980]
        # Small cohort with extreme observation
        small_post, small_w = bayesian_shrink_cohort(
            cohort_observed_pmpm=1500.0,
            cohort_size=50,
            population_pmpms=pop,
        )
        # Large cohort with same observation
        big_post, big_w = bayesian_shrink_cohort(
            cohort_observed_pmpm=1500.0,
            cohort_size=10000,
            population_pmpms=pop,
        )
        # Small cohort gets shrunk more → posterior closer to mean
        self.assertLess(abs(small_post - 1000),
                        abs(big_post - 1000))
        # Trust weight smaller for the small cohort
        self.assertLess(small_w, big_w)

    def test_zero_size_returns_population_mean(self):
        from rcm_mc.vbc import bayesian_shrink_cohort
        post, w = bayesian_shrink_cohort(
            cohort_observed_pmpm=999.0,
            cohort_size=0,
            population_pmpms=[1000, 1100, 900],
        )
        self.assertAlmostEqual(post, 1000.0, places=1)
        self.assertEqual(w, 0.0)


if __name__ == "__main__":
    unittest.main()
