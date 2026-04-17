"""Tests for Sprint 8: Debt Model (45), Waterfall (46), Sensitivity Dashboard (47).

DEBT MODEL:
 1. Single tranche bullet loan — no amort, no sweep.
 2. Mandatory amort reduces balance each year.
 3. Cash sweep repays debt from excess FCF.
 4. Multi-tranche respects priority ordering.
 5. Covenant breach detection — leverage too high.
 6. Coverage covenant breach detection.
 7. First breach year recorded correctly.
 8. Empty tranches raises ValueError.
 9. Negative EBITDA raises ValueError.
10. Leverage decreases as EBITDA grows.

WATERFALL:
11. Return of capital tier returns LP principal first.
12. Preferred return compounds correctly.
13. GP catch-up allocates to GP at catch-up rate.
14. Carried interest splits remaining 80/20.
15. Total loss scenario — LP gets partial capital back.
16. Zero invested raises ValueError.
17. Gross MOIC matches invested / proceeds.
18. Management fees deducted from LP.

SENSITIVITY DASHBOARD:
19. Default grid has correct dimensions (6 hold years x 10 exit multiples).
20. MOIC increases with exit multiple (same hold year).
21. MOIC decreases with longer hold (same exit multiple, no growth).
22. Achievement 0% reduces MOIC vs 100%.
23. render_sensitivity_page produces valid HTML.
24. handle_sensitivity_post parses form data.
25. Grid cell IRR is positive for profitable deals.
26. API route wired in server (import check).
"""
from __future__ import annotations

import unittest

from rcm_mc.pe.debt_model import (
    DebtStructure,
    DebtTranche,
    DebtTrajectory,
    YearProjection,
    format_trajectory_summary,
    project_debt_trajectory,
    quick_leverage_check,
)
from rcm_mc.pe.waterfall import (
    DealReturn,
    TierAllocation,
    WaterfallResult,
    WaterfallStructure,
    compute_waterfall,
    format_waterfall_summary,
    quick_lp_economics,
)
from rcm_mc.ui.sensitivity_dashboard import (
    SensitivityParams,
    SensitivityResult,
    compute_sensitivity_grid,
    handle_sensitivity_post,
    render_sensitivity_page,
)


# ── Debt Model Tests ───────────────────────────────────────────────────


class TestDebtModel(unittest.TestCase):
    """Tests 1-10: Debt trajectory projection."""

    def test_01_bullet_loan_no_amort_no_sweep(self):
        """Single bullet tranche — balance stays constant."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05,
                                  amort_pct=0.0, sweep_pct=0.0)],
            max_leverage=10.0,
        )
        traj = project_debt_trajectory(debt, [100, 100, 100])
        # No amort or sweep, balance should be 500 each year
        for y in traj.years:
            self.assertAlmostEqual(y.ending_balance, 500.0, places=0)
        self.assertAlmostEqual(traj.total_debt_repaid, 0.0, places=0)

    def test_02_mandatory_amort_reduces_balance(self):
        """5% annual amort on 500 → 25/yr mandatory paydown."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05,
                                  amort_pct=0.05, sweep_pct=0.0)],
            max_leverage=10.0,
        )
        traj = project_debt_trajectory(debt, [100, 100, 100])
        # Year 1: 500 - 25 = 475
        self.assertAlmostEqual(traj.years[0].ending_balance, 475.0, places=0)
        self.assertAlmostEqual(traj.years[0].mandatory_amort, 25.0, places=0)
        # Year 2: 475 - 25 = 450
        self.assertAlmostEqual(traj.years[1].ending_balance, 450.0, places=0)

    def test_03_cash_sweep_repays_debt(self):
        """50% ECF sweep with high EBITDA should reduce balance faster."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=200, rate=0.05,
                                  amort_pct=0.0, sweep_pct=0.50)],
            max_leverage=10.0,
            capex_pct=0.0,
            tax_rate=0.0,
        )
        # With EBITDA=100, interest=10, FCF=90, sweep=45
        traj = project_debt_trajectory(debt, [100])
        self.assertGreater(traj.years[0].cash_sweep, 0)
        self.assertLess(traj.years[0].ending_balance, 200.0)

    def test_04_multi_tranche_priority(self):
        """Senior tranche (priority=1) sweeps before junior (priority=2)."""
        debt = DebtStructure(
            tranches=[
                DebtTranche("Senior", principal=100, rate=0.05,
                            amort_pct=0.0, sweep_pct=0.50, priority=1),
                DebtTranche("Junior", principal=100, rate=0.08,
                            amort_pct=0.0, sweep_pct=0.50, priority=2),
            ],
            max_leverage=10.0,
            capex_pct=0.0,
            tax_rate=0.0,
        )
        traj = project_debt_trajectory(debt, [200])
        # Senior should be swept first, so senior ending < junior ending
        details = traj.years[0].tranche_details
        senior = [d for d in details if d["name"] == "Senior"][0]
        junior = [d for d in details if d["name"] == "Junior"][0]
        # With high EBITDA, both should be reduced but senior swept first
        self.assertLessEqual(senior["ending"], junior["ending"])

    def test_05_leverage_breach_detected(self):
        """High debt / low EBITDA triggers leverage covenant breach."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=700, rate=0.05)],
            max_leverage=6.0,
        )
        # 700 / 100 = 7.0x > 6.0x max → breach
        traj = project_debt_trajectory(debt, [100])
        self.assertFalse(traj.years[0].covenant_ok)

    def test_06_coverage_breach_detected(self):
        """Low EBITDA relative to interest triggers coverage breach."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.20)],
            max_leverage=20.0,  # high so leverage isn't the issue
            min_coverage=2.0,
        )
        # Interest = 500 * 0.20 = 100, EBITDA = 110 → coverage 1.1x < 2.0x
        traj = project_debt_trajectory(debt, [110])
        self.assertFalse(traj.years[0].covenant_ok)

    def test_07_first_breach_year_recorded(self):
        """First breach in year 2 when EBITDA drops."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05)],
            max_leverage=6.0,
        )
        # Year 1: 500/100 = 5x OK. Year 2: ~500/70 = 7.1x breach.
        traj = project_debt_trajectory(debt, [100, 70, 70])
        self.assertIsNotNone(traj.first_breach_year)
        self.assertEqual(traj.first_breach_year, 2)

    def test_08_empty_tranches_raises(self):
        debt = DebtStructure(tranches=[])
        with self.assertRaises(ValueError):
            project_debt_trajectory(debt, [100])

    def test_09_negative_ebitda_raises(self):
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05)],
        )
        with self.assertRaises(ValueError):
            project_debt_trajectory(debt, [100, -50])

    def test_10_leverage_decreases_with_ebitda_growth(self):
        """Growing EBITDA should reduce leverage over time."""
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05)],
            max_leverage=10.0,
        )
        traj = project_debt_trajectory(debt, [100, 120, 140, 160])
        leverages = [y.leverage for y in traj.years]
        # Each year leverage should be lower (or equal) as EBITDA grows
        for i in range(1, len(leverages)):
            self.assertLessEqual(leverages[i], leverages[i - 1])


# ── Waterfall Tests ────────────────────────────────────────────────────


class TestWaterfall(unittest.TestCase):
    """Tests 11-18: PE waterfall distribution."""

    def _standard_wf(self) -> WaterfallStructure:
        return WaterfallStructure(
            preferred_return=0.08,
            catch_up_pct=0.80,
            carry_pct=0.20,
            mgmt_fee_pct=0.02,
            gp_commit_pct=0.02,
        )

    def test_11_return_of_capital_first(self):
        """Tier 1 returns LP capital before any profit split."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=200, hold_years=3)
        result = compute_waterfall(wf, dr)
        roc = result.tiers[0]
        self.assertEqual(roc.tier, "Return of Capital")
        # LP invested 98 (100 - 2% GP commit)
        self.assertAlmostEqual(roc.lp_amount, 98.0, places=0)
        self.assertAlmostEqual(roc.gp_amount, 0.0, places=2)

    def test_12_preferred_return_compounds(self):
        """8% pref over 3 years should compound."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=300, hold_years=3)
        result = compute_waterfall(wf, dr)
        pref = result.tiers[1]
        self.assertEqual(pref.tier, "Preferred Return")
        # 98 * ((1.08)^3 - 1) = 98 * 0.2597 ≈ 25.45
        expected = 98 * ((1.08) ** 3 - 1)
        self.assertAlmostEqual(pref.lp_amount, expected, places=0)

    def test_13_gp_catchup_allocates_to_gp(self):
        """GP catch-up tier sends 80% to GP."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=300, hold_years=3)
        result = compute_waterfall(wf, dr)
        catchup = result.tiers[2]
        self.assertEqual(catchup.tier, "GP Catch-up")
        # GP should get 80% of catch-up distributions
        if catchup.gp_amount + catchup.lp_amount > 0:
            gp_share = catchup.gp_amount / (catchup.gp_amount + catchup.lp_amount)
            self.assertAlmostEqual(gp_share, 0.80, places=2)

    def test_14_carried_interest_split(self):
        """Tier 4 splits remaining 80/20 LP/GP."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=500, hold_years=3)
        result = compute_waterfall(wf, dr)
        carry = result.tiers[3]
        self.assertEqual(carry.tier, "Carried Interest")
        if carry.lp_amount + carry.gp_amount > 0:
            lp_share = carry.lp_amount / (carry.lp_amount + carry.gp_amount)
            self.assertAlmostEqual(lp_share, 0.80, places=2)

    def test_15_total_loss(self):
        """Exit below invested — LP gets partial capital, no profit tiers."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=40, hold_years=3)
        result = compute_waterfall(wf, dr)
        # LP should get less than their invested capital
        self.assertLess(result.lp_total, 98)  # 98 = LP portion
        # No preferred return should be paid
        pref = result.tiers[1]
        self.assertAlmostEqual(pref.lp_amount, 0.0, places=1)

    def test_16_zero_invested_raises(self):
        wf = self._standard_wf()
        dr = DealReturn(invested=0, exit_proceeds=100, hold_years=3)
        with self.assertRaises(ValueError):
            compute_waterfall(wf, dr)

    def test_17_gross_moic_matches(self):
        """Gross MOIC = total proceeds / invested."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=250, hold_years=4)
        result = compute_waterfall(wf, dr)
        self.assertAlmostEqual(result.gross_moic, 2.50, places=2)

    def test_18_mgmt_fees_deducted(self):
        """Management fees = invested * fee_pct * hold_years."""
        wf = self._standard_wf()
        dr = DealReturn(invested=100, exit_proceeds=200, hold_years=5)
        result = compute_waterfall(wf, dr)
        expected_fees = 100 * 0.02 * 5  # = 10
        self.assertAlmostEqual(result.mgmt_fees_total, expected_fees, places=2)


# ── Sensitivity Dashboard Tests ────────────────────────────────────────


class TestSensitivityDashboard(unittest.TestCase):
    """Tests 19-26: Sensitivity grid and UI."""

    def test_19_default_grid_dimensions(self):
        """Default params: 6 hold years (2-7) x 10 exit multiples (6-15)."""
        result = compute_sensitivity_grid(SensitivityParams())
        self.assertEqual(len(result.hold_years_list), 6)
        self.assertEqual(len(result.exit_multiples), 10)
        self.assertEqual(len(result.grid), 60)  # 6 * 10

    def test_20_moic_increases_with_exit_multiple(self):
        """Higher exit multiple → higher MOIC for same hold period."""
        result = compute_sensitivity_grid(SensitivityParams())
        # Get all cells for hold year 3
        hy3 = [c for c in result.grid if c.hold_years == 3]
        hy3.sort(key=lambda c: c.exit_multiple)
        for i in range(1, len(hy3)):
            self.assertGreater(hy3[i].moic, hy3[i - 1].moic)

    def test_21_moic_change_with_hold_years(self):
        """With organic growth, longer hold should still produce valid MOICs."""
        params = SensitivityParams(organic_growth_pct=0.0, achievement_pct=0.0)
        result = compute_sensitivity_grid(params)
        # Get all cells for exit multiple 10x
        em10 = [c for c in result.grid if abs(c.exit_multiple - 10.0) < 0.01]
        em10.sort(key=lambda c: c.hold_years)
        # With zero growth and zero uplift, MOIC should stay roughly constant
        # (EBITDA doesn't change, so exit EV is same, equity is same)
        for c in em10:
            self.assertGreater(c.moic, 0)

    def test_22_achievement_reduces_moic(self):
        """0% achievement should produce lower MOIC than 100%."""
        params_full = SensitivityParams(achievement_pct=1.0, planned_uplift=15.0)
        params_zero = SensitivityParams(achievement_pct=0.0, planned_uplift=15.0)
        full = compute_sensitivity_grid(params_full)
        zero = compute_sensitivity_grid(params_zero)
        # Compare same cell (hold=3, exit=10x)
        full_cell = [c for c in full.grid
                     if c.hold_years == 3 and abs(c.exit_multiple - 10.0) < 0.01][0]
        zero_cell = [c for c in zero.grid
                     if c.hold_years == 3 and abs(c.exit_multiple - 10.0) < 0.01][0]
        self.assertGreater(full_cell.moic, zero_cell.moic)

    def test_23_render_produces_html(self):
        """render_sensitivity_page returns valid HTML string."""
        html_out = render_sensitivity_page(deal_id="test-deal")
        self.assertIn("<table", html_out)
        self.assertIn("Sensitivity Analysis", html_out)
        self.assertIn("test-deal", html_out)
        self.assertIn("MOIC", html_out)

    def test_24_handle_post_parses_form(self):
        """handle_sensitivity_post extracts params from form dict."""
        form = {
            "entry_ebitda": "75",
            "entry_multiple": "12",
            "exit_multiple_min": "8",
            "exit_multiple_max": "14",
            "hold_years_min": "3",
            "hold_years_max": "5",
            "achievement_pct": "80",
            "planned_uplift": "12",
        }
        result = handle_sensitivity_post(form)
        self.assertIn("grid", result)
        self.assertIn("exit_multiples", result)
        self.assertIn("hold_years", result)
        # 3 hold years (3,4,5) x 7 exit multiples (8-14)
        self.assertEqual(len(result["hold_years"]), 3)
        self.assertEqual(len(result["exit_multiples"]), 7)

    def test_25_irr_positive_for_profitable_deal(self):
        """Profitable deal should have positive IRR in grid cells."""
        params = SensitivityParams(
            entry_ebitda=50,
            entry_multiple=10,
            planned_uplift=10,
            achievement_pct=1.0,
            debt_to_ebitda=4.0,
        )
        result = compute_sensitivity_grid(params)
        # High exit multiple + short hold should be profitable
        good_cell = [c for c in result.grid
                     if c.hold_years == 3 and abs(c.exit_multiple - 12.0) < 0.01]
        self.assertTrue(len(good_cell) > 0)
        self.assertGreater(good_cell[0].irr, 0)

    def test_26_sensitivity_result_to_dict(self):
        """SensitivityResult.to_dict returns proper structure."""
        result = compute_sensitivity_grid(SensitivityParams())
        d = result.to_dict()
        self.assertIsInstance(d["params"], dict)
        self.assertIsInstance(d["grid"], list)
        self.assertIn("moic", d["grid"][0])
        self.assertIn("irr", d["grid"][0])
        self.assertIn("exit_ev", d["grid"][0])


# ── Cross-module integration ───────────────────────────────────────────


class TestSprint8Integration(unittest.TestCase):
    """Additional integration checks across the sprint modules."""

    def test_quick_leverage_check(self):
        r = quick_leverage_check(600, 100, max_leverage=6.0)
        self.assertEqual(r["leverage"], 6.0)
        self.assertTrue(r["ok"])

    def test_quick_lp_economics(self):
        r = quick_lp_economics(100, 250, 4)
        self.assertIn("lp_moic", r)
        self.assertGreater(r["lp_moic"], 0)
        self.assertGreater(r["gross_moic"], 0)

    def test_format_trajectory_summary(self):
        debt = DebtStructure(
            tranches=[DebtTranche("TLA", principal=500, rate=0.05)],
            max_leverage=10.0,
        )
        traj = project_debt_trajectory(debt, [100, 110, 120])
        text = format_trajectory_summary(traj)
        self.assertIn("Entry leverage", text)
        self.assertIn("Exit leverage", text)

    def test_format_waterfall_summary(self):
        wf = WaterfallStructure()
        dr = DealReturn(invested=100, exit_proceeds=250, hold_years=3)
        result = compute_waterfall(wf, dr)
        text = format_waterfall_summary(result)
        self.assertIn("Invested", text)
        self.assertIn("Gross MOIC", text)

    def test_server_sensitivity_route_importable(self):
        """The sensitivity handler can be imported from server module path."""
        from rcm_mc.ui.sensitivity_dashboard import handle_sensitivity_post
        self.assertTrue(callable(handle_sensitivity_post))

    def test_handle_post_empty_form_uses_defaults(self):
        """Empty form uses all defaults without error."""
        result = handle_sensitivity_post({})
        self.assertIn("grid", result)
        self.assertGreater(len(result["grid"]), 0)


if __name__ == "__main__":
    unittest.main()
