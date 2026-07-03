"""Tests for the life-sciences valuation engine (finance/life_sciences.py).

Covers the full stack the module ships:
  * Clinical LoA framework — ordering across therapeutic areas.
  * Core rNPV — risk vs success case, phase sensitivity.
  * Epidemiology peak-sales funnel arithmetic.
  * Licensing deal split reconciliation.
  * Monte Carlo — mean reconciles to analytic rNPV; empirical PTS ≈ LoA.
  * Sensitivity tornado ordering + break-even solvers.
  * Real-options abandonment premium (≥ 0, kills the bad branch).
  * Competition-adjusted peak sales (monotone, conserves class TAM).
  * Adjacent subsectors (CDMO, diagnostics), pipeline, runway.
  * Side-by-side comparison structure + markdown rendering.
"""
from __future__ import annotations

import unittest

from rcm_mc.finance.life_sciences import (
    AssetRNPVConfig, DevelopmentPhase, TherapeuticArea,
    value_asset_rnpv, build_rnpv, cumulative_loa,
    EpidemiologyFunnel, peak_sales_from_epidemiology,
    LicensingDeal, RoyaltyTier, value_licensing_deal,
    StochasticInputs, monte_carlo_rnpv,
    sensitivity_tornado, sensitivity_grid,
    breakeven_peak_sales, breakeven_loa, expected_value_blend,
    CommercialScenario, real_options_value,
    competition_adjusted_peak_sales,
    cdmo_capacity_model, diagnostics_unit_economics,
    value_pipeline, runway_analysis,
    compare_assets, compare_assets_deep, compare_scenarios,
)


def _onc_p2(peak=1200.0) -> AssetRNPVConfig:
    return AssetRNPVConfig(
        name="Onc P2", area=TherapeuticArea.ONCOLOGY,
        current_phase=DevelopmentPhase.PHASE_2, peak_sales_musd=peak,
    )


class TestLoAFramework(unittest.TestCase):

    def test_loa_between_zero_and_one(self):
        loa = cumulative_loa(DevelopmentPhase.PHASE_1, TherapeuticArea.ALL)
        self.assertGreater(loa, 0.0)
        self.assertLess(loa, 1.0)

    def test_approved_asset_is_certain(self):
        self.assertEqual(
            cumulative_loa(DevelopmentPhase.APPROVED, TherapeuticArea.ONCOLOGY),
            1.0)

    def test_later_phase_has_higher_loa(self):
        # A Phase-3 asset is closer to approval than a Phase-1 asset.
        p1 = cumulative_loa(DevelopmentPhase.PHASE_1, TherapeuticArea.ONCOLOGY)
        p3 = cumulative_loa(DevelopmentPhase.PHASE_3, TherapeuticArea.ONCOLOGY)
        self.assertGreater(p3, p1)

    def test_hematology_beats_oncology(self):
        # Hematology is the highest-success area, oncology among the lowest.
        heme = cumulative_loa(DevelopmentPhase.PHASE_1, TherapeuticArea.HEMATOLOGY)
        onc = cumulative_loa(DevelopmentPhase.PHASE_1, TherapeuticArea.ONCOLOGY)
        self.assertGreater(heme, onc)

    def test_all_area_loa_near_published_benchmark(self):
        # BIO 2021 headline cumulative LoA from Phase 1 ≈ 7.9%.
        loa = cumulative_loa(DevelopmentPhase.PHASE_1, TherapeuticArea.ALL)
        self.assertAlmostEqual(loa, 0.079, delta=0.02)

    def test_prob_override_changes_loa(self):
        base = cumulative_loa(DevelopmentPhase.PHASE_2, TherapeuticArea.ONCOLOGY)
        bumped = cumulative_loa(DevelopmentPhase.PHASE_2, TherapeuticArea.ONCOLOGY,
                                overrides={"p2_to_p3": 0.9})
        self.assertGreater(bumped, base)


class TestCoreRNPV(unittest.TestCase):

    def test_rnpv_below_success_case(self):
        # A risky pre-approval asset's rNPV must sit far below its
        # approval-case NPV — that gap IS the clinical risk.
        r = value_asset_rnpv(_onc_p2())
        self.assertLess(r.rnpv_musd, r.npv_success_musd)

    def test_bigger_peak_lifts_rnpv(self):
        small = value_asset_rnpv(_onc_p2(500)).rnpv_musd
        big = value_asset_rnpv(_onc_p2(2500)).rnpv_musd
        self.assertGreater(big, small)

    def test_projection_years_present(self):
        r = value_asset_rnpv(_onc_p2())
        self.assertTrue(r.projections)
        # every year round-trips to a dict cleanly
        for y in r.projections:
            self.assertIn("pv", y.to_dict())

    def test_build_rnpv_accepts_string_enums(self):
        r = build_rnpv(area="CNS", current_phase="PHASE_3", peak_sales_musd=900)
        self.assertEqual(r.config.area, TherapeuticArea.CNS)
        self.assertEqual(r.config.current_phase, DevelopmentPhase.PHASE_3)

    def test_to_dict_round_trips(self):
        d = value_asset_rnpv(_onc_p2()).to_dict()
        for key in ("loa", "rnpv_musd", "npv_success_musd", "projections"):
            self.assertIn(key, d)


class TestEpidemiology(unittest.TestCase):

    def test_funnel_arithmetic(self):
        f = EpidemiologyFunnel(
            addressable_population=1_000_000,
            diagnosis_rate=0.5, treatment_rate=0.5,
            eligible_fraction=0.5, peak_market_share=0.2,
            annual_net_price_usd=10_000, adherence_persistence=1.0,
        )
        # 1e6 * .5 * .5 * .5 * .2 = 25,000 patients * $10k = $250M
        self.assertAlmostEqual(peak_sales_from_epidemiology(f), 250.0, delta=1.0)

    def test_geographic_expansion_scales(self):
        base = EpidemiologyFunnel(addressable_population=500_000)
        ex_us = EpidemiologyFunnel(addressable_population=500_000, geographies=1.8)
        self.assertGreater(ex_us.peak_sales_musd(), base.peak_sales_musd())


class TestLicensingDeal(unittest.TestCase):

    def test_deal_split_reconciles_to_standalone(self):
        cfg = _onc_p2(1500)
        standalone = value_asset_rnpv(cfg).rnpv_musd
        deal = LicensingDeal(
            upfront_musd=40, approval_milestone_musd=80,
            royalty_tiers=[RoyaltyTier(300, 0.10), RoyaltyTier(float("inf"), 0.15)],
        )
        res = value_licensing_deal(_onc_p2(1500), deal)
        self.assertIsNotNone(res.licensor_rnpv_musd)
        self.assertIsNotNone(res.licensee_rnpv_musd)
        self.assertAlmostEqual(
            res.licensor_rnpv_musd + res.licensee_rnpv_musd,
            standalone, delta=1.0)

    def test_royalty_tiers_are_progressive(self):
        deal = LicensingDeal(royalty_tiers=[RoyaltyTier(100, 0.05),
                                            RoyaltyTier(float("inf"), 0.20)])
        # first $100M at 5% = $5M; next $100M at 20% = $20M → $25M on $200M
        self.assertAlmostEqual(deal.royalty_on(200), 25.0, delta=0.01)


class TestMonteCarlo(unittest.TestCase):

    def test_mc_mean_reconciles_to_analytic(self):
        cfg = _onc_p2()
        mc = monte_carlo_rnpv(cfg, n_trials=20_000, seed=7)
        # The point rNPV is the expected value of the MC distribution.
        self.assertAlmostEqual(mc.mean_musd, mc.analytic_rnpv_musd,
                               delta=max(15.0, abs(mc.analytic_rnpv_musd) * 0.5))

    def test_empirical_pts_matches_loa(self):
        cfg = _onc_p2()
        mc = monte_carlo_rnpv(cfg, StochasticInputs(pos_abs_sd=0.0),
                              n_trials=20_000, seed=11)
        loa = value_asset_rnpv(cfg).loa
        self.assertAlmostEqual(mc.prob_technical_success, loa, delta=0.02)

    def test_distribution_is_skewed_downside(self):
        # With a <10% success rate, the median outcome is a sunk-cost loss.
        mc = monte_carlo_rnpv(_onc_p2(), n_trials=10_000, seed=3)
        self.assertLess(mc.p50_musd, 0.0)
        self.assertGreater(mc.ev_if_success_musd, 0.0)
        self.assertLess(mc.ev_if_failure_musd, 0.0)


class TestSensitivityAndSolvers(unittest.TestCase):

    def test_tornado_sorted_by_swing(self):
        t = sensitivity_tornado(_onc_p2())
        swings = [b.swing for b in t.bars]
        self.assertEqual(swings, sorted(swings, reverse=True))

    def test_breakeven_peak_sales_zeros_rnpv(self):
        cfg = _onc_p2()
        be = breakeven_peak_sales(cfg)
        self.assertIsNotNone(be)
        rnpv_at_be = value_asset_rnpv(
            AssetRNPVConfig(name="be", area=cfg.area,
                            current_phase=cfg.current_phase,
                            peak_sales_musd=be)).rnpv_musd
        self.assertAlmostEqual(rnpv_at_be, 0.0, delta=1.0)

    def test_breakeven_loa_below_benchmark_when_positive(self):
        cfg = _onc_p2()
        actual = value_asset_rnpv(cfg).loa
        be_loa = breakeven_loa(cfg)
        self.assertIsNotNone(be_loa)
        # rNPV is positive at base, so it survives a lower implied LoA.
        self.assertLess(be_loa, actual)

    def test_sensitivity_grid_shape(self):
        g = sensitivity_grid(_onc_p2(), "peak_sales_musd", [600, 1200],
                             "discount_rate", [0.10, 0.15])
        self.assertEqual(len(g.grid), 2)
        self.assertEqual(len(g.grid[0]), 2)
        # higher discount rate lowers value
        self.assertGreater(g.grid[0][0], g.grid[1][0])

    def test_expected_value_blend_between_extremes(self):
        ev = expected_value_blend(_onc_p2(), {
            "Bear": (0.3, {"peak_sales_musd": 400}),
            "Base": (0.5, {}),
            "Bull": (0.2, {"peak_sales_musd": 2800}),
        })
        rnpvs = [s["rnpv_musd"] for s in ev.scenarios]
        self.assertGreaterEqual(ev.expected_rnpv_musd, min(rnpvs))
        self.assertLessEqual(ev.expected_rnpv_musd, max(rnpvs))


class TestRealOptions(unittest.TestCase):

    def test_option_premium_nonnegative(self):
        scn = [CommercialScenario("Bear", 0.35, 300),
               CommercialScenario("Base", 0.45, 1200),
               CommercialScenario("Bull", 0.20, 3000)]
        ro = real_options_value(_onc_p2(), scn,
                                reveal_after=DevelopmentPhase.PHASE_2)
        self.assertGreaterEqual(ro.option_premium_musd, -1e-6)

    def test_abandons_value_destructive_branch(self):
        scn = [CommercialScenario("Bear", 0.5, 150),
               CommercialScenario("Bull", 0.5, 3000)]
        ro = real_options_value(_onc_p2(), scn,
                                reveal_after=DevelopmentPhase.PHASE_2)
        self.assertIn("Bear", ro.abandon_scenarios)
        self.assertIn("Bull", ro.continue_scenarios)


class TestCompetition(unittest.TestCase):

    def test_shares_monotone_by_entry_order(self):
        peaks = [competition_adjusted_peak_sales(4000, oe, 4) for oe in (1, 2, 3, 4)]
        self.assertEqual(peaks, sorted(peaks, reverse=True))

    def test_class_tam_conserved(self):
        total = sum(competition_adjusted_peak_sales(4000, oe, 4) for oe in (1, 2, 3, 4))
        self.assertAlmostEqual(total, 4000.0, delta=1.0)

    def test_differentiation_lifts_share(self):
        me_too = competition_adjusted_peak_sales(4000, 3, 4, differentiation=0.7)
        best = competition_adjusted_peak_sales(4000, 3, 4, differentiation=1.5)
        self.assertGreater(best, me_too)


class TestAdjacentSubsectors(unittest.TestCase):

    def test_cdmo_scales_with_utilization(self):
        low = cdmo_capacity_model(6, 40, 0.5)
        high = cdmo_capacity_model(6, 40, 0.9)
        self.assertGreater(high.revenue_musd, low.revenue_musd)
        self.assertGreater(high.ebitda_margin, low.ebitda_margin)  # operating leverage

    def test_diagnostics_consumable_annuity_dominates(self):
        dx = diagnostics_unit_economics(2000, 300, 25000, 4000, 45)
        self.assertGreater(dx.consumable_share, 0.5)

    def test_pipeline_sums_assets_and_nets_cash(self):
        cfgs = [_onc_p2(1000), AssetRNPVConfig(
            name="Heme", area=TherapeuticArea.HEMATOLOGY,
            current_phase=DevelopmentPhase.PHASE_3, peak_sales_musd=800)]
        res = value_pipeline(cfgs, annual_platform_gna_musd=20,
                             net_cash_musd=150)
        self.assertEqual(len(res.assets), 2)
        # equity = gross − G&A PV + cash
        self.assertAlmostEqual(
            res.equity_value_musd,
            res.gross_pipeline_rnpv_musd - res.platform_gna_pv_musd + res.net_cash_musd,
            delta=0.01)

    def test_runway_and_financing_need(self):
        r = runway_analysis(180, 22, target_runway_months=30)
        self.assertAlmostEqual(r.runway_months, 180 / 22 * 3, delta=0.1)
        self.assertGreater(r.financing_need_musd, 0.0)


class TestSideBySide(unittest.TestCase):

    def test_compare_assets_aligned_columns(self):
        cmp = compare_assets([
            _onc_p2(1200),
            AssetRNPVConfig(name="Heme", area=TherapeuticArea.HEMATOLOGY,
                            current_phase=DevelopmentPhase.PHASE_2,
                            peak_sales_musd=1200),
        ])
        self.assertEqual(cmp.columns, ["Onc P2", "Heme"])
        self.assertTrue(all(len(r.display) == 2 for r in cmp.rows))

    def test_compare_scenarios_includes_base(self):
        cmp = compare_scenarios(_onc_p2(), {
            "Bear": {"peak_sales_musd": 500, "p2_to_p3": 0.18},
            "Bull": {"peak_sales_musd": 2500},
        })
        self.assertEqual(cmp.columns[0], "Base")
        self.assertIn("Bear", cmp.columns)
        md = cmp.to_markdown()
        self.assertIn("| Metric |", md)
        self.assertIn("rNPV", md)

    def test_deep_comparison_adds_distribution_rows(self):
        cmp = compare_assets_deep([_onc_p2(1200), _onc_p2(2000)],
                                  n_trials=2000, seed=5)
        labels = [r.label for r in cmp.rows]
        self.assertTrue(any("P50" in l for l in labels))
        self.assertTrue(any("P(reaches market)" in l for l in labels))


if __name__ == "__main__":
    unittest.main()
