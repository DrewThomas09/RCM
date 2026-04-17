"""Tests for PE deal-math layer (Brick 41+)."""
from __future__ import annotations

import unittest

from rcm_mc.pe.pe_math import (
    BridgeResult,
    CovenantCheck,
    ReturnsResult,
    bridge_to_records,
    compute_returns,
    covenant_check,
    format_bridge,
    format_covenant,
    format_hold_grid,
    format_returns,
    hold_period_grid,
    irr,
    value_creation_bridge,
)


class TestValueCreationBridge(unittest.TestCase):
    """Bridge reconciliation is the core invariant — PE ICs reject bridges
    that don't add up. Every test ultimately confirms this."""

    def test_bridge_reconciles_exactly(self):
        """entry_ev + sum(components) == exit_ev (no rounding drift)."""
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=8e6,
            entry_multiple=9.0, exit_multiple=10.0,
            hold_years=5.0, organic_growth_pct=0.03,
        )
        reconstructed = (
            b.entry_ev
            + b.organic_ebitda_contribution
            + b.rcm_uplift_contribution
            + b.multiple_expansion_contribution
        )
        self.assertAlmostEqual(reconstructed, b.exit_ev, places=2)

    def test_total_value_equals_exit_minus_entry(self):
        b = value_creation_bridge(
            entry_ebitda=100e6, uplift=15e6,
            entry_multiple=8.5, exit_multiple=8.5,
            hold_years=3.0,
        )
        self.assertAlmostEqual(b.total_value_created, b.exit_ev - b.entry_ev, places=2)

    def test_zero_organic_growth_zeros_organic_contribution(self):
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=10e6,
            entry_multiple=9.0, exit_multiple=9.0,
            hold_years=5.0, organic_growth_pct=0.0,
        )
        self.assertAlmostEqual(b.organic_ebitda_contribution, 0.0, places=2)
        self.assertAlmostEqual(b.exit_ebitda, b.entry_ebitda + 10e6, places=2)

    def test_no_multiple_expansion_zeros_multiple_component(self):
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=10e6,
            entry_multiple=9.0, exit_multiple=9.0,  # flat
            hold_years=5.0,
        )
        self.assertAlmostEqual(b.multiple_expansion_contribution, 0.0, places=2)

    def test_organic_growth_compounds_correctly(self):
        # 3%/yr × 5 years = 1.03^5 - 1 ≈ 15.93%
        b = value_creation_bridge(
            entry_ebitda=100e6, uplift=0.0,
            entry_multiple=10.0, exit_multiple=10.0,
            hold_years=5.0, organic_growth_pct=0.03,
        )
        expected_growth = 100e6 * (1.03 ** 5) - 100e6
        organic_ebitda_growth = b.organic_ebitda_contribution / b.entry_multiple
        self.assertAlmostEqual(organic_ebitda_growth, expected_growth, places=1)

    def test_rcm_uplift_multiplies_by_entry_multiple(self):
        # $10M uplift × 9x entry = $90M contribution
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=10e6,
            entry_multiple=9.0, exit_multiple=9.0,
            hold_years=5.0,
        )
        self.assertAlmostEqual(b.rcm_uplift_contribution, 90e6, places=2)

    def test_multiple_expansion_uses_exit_ebitda(self):
        # 1x multiple expansion on $60M exit EBITDA = $60M
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=10e6,
            entry_multiple=9.0, exit_multiple=10.0,
            hold_years=5.0, organic_growth_pct=0.0,
        )
        self.assertAlmostEqual(b.multiple_expansion_contribution, 60e6, places=2)

    def test_negative_uplift_is_allowed_value_destruction(self):
        """PE IC committees stress-test downside — negative uplift must model cleanly."""
        b = value_creation_bridge(
            entry_ebitda=50e6, uplift=-5e6,  # RCM degradation
            entry_multiple=9.0, exit_multiple=9.0,
            hold_years=5.0,
        )
        self.assertLess(b.rcm_uplift_contribution, 0)
        self.assertLess(b.exit_ebitda, b.entry_ebitda)

    # ── Input validation ──

    def test_zero_entry_ebitda_raises(self):
        with self.assertRaises(ValueError):
            value_creation_bridge(0.0, 10e6, 9.0, 9.0, 5.0)

    def test_negative_entry_multiple_raises(self):
        with self.assertRaises(ValueError):
            value_creation_bridge(50e6, 10e6, -1.0, 9.0, 5.0)

    def test_zero_hold_years_raises(self):
        with self.assertRaises(ValueError):
            value_creation_bridge(50e6, 10e6, 9.0, 9.0, 0.0)


class TestBridgeToRecords(unittest.TestCase):
    """Bridge rendered as workbook-ready row records."""

    def _sample(self) -> BridgeResult:
        return value_creation_bridge(
            entry_ebitda=50e6, uplift=8e6,
            entry_multiple=9.0, exit_multiple=10.0,
            hold_years=5.0, organic_growth_pct=0.03,
        )

    def test_records_have_five_rows(self):
        rows = bridge_to_records(self._sample())
        self.assertEqual(len(rows), 5)

    def test_rows_are_ordered_entry_organic_uplift_multiple_exit(self):
        rows = bridge_to_records(self._sample())
        self.assertEqual(rows[0]["step"], "Entry EV")
        self.assertEqual(rows[1]["step"], "Organic EBITDA")
        self.assertEqual(rows[2]["step"], "RCM uplift")
        self.assertEqual(rows[3]["step"], "Multiple expansion")
        self.assertEqual(rows[4]["step"], "Exit EV")

    def test_share_of_creation_sums_to_one_for_components(self):
        rows = bridge_to_records(self._sample())
        shares = [r["share_of_creation"] for r in rows if r["share_of_creation"] is not None]
        self.assertAlmostEqual(sum(shares), 1.0, places=4)

    def test_endpoints_have_no_share(self):
        rows = bridge_to_records(self._sample())
        # Entry / Exit EV rows aren't components of "value created"
        self.assertIsNone(rows[0]["share_of_creation"])
        self.assertIsNone(rows[-1]["share_of_creation"])


class TestIRR(unittest.TestCase):
    """IRR solver correctness on closed-form test cases.

    Every IRR assertion below has a closed-form answer that can be
    recomputed by hand — no "looks right" floating-point tolerance creep.
    """

    def test_doubling_in_one_year_is_100_pct(self):
        # -100 at t=0, +200 at t=1 → IRR = 100%
        self.assertAlmostEqual(irr([-100.0, 200.0]), 1.0, places=5)

    def test_doubling_in_five_years(self):
        # -100 at t=0, +200 at t=5 → IRR = 2^(1/5) - 1 ≈ 14.87%
        expected = 2.0 ** (1.0 / 5.0) - 1.0
        self.assertAlmostEqual(irr([-100, 0, 0, 0, 0, 200]), expected, places=5)

    def test_zero_return_irr_is_zero(self):
        # -100 at t=0, +100 at t=1 → IRR = 0
        self.assertAlmostEqual(irr([-100.0, 100.0]), 0.0, places=5)

    def test_negative_return_irr_is_negative(self):
        self.assertLess(irr([-100.0, 50.0]), 0)

    def test_same_sign_cashflows_raise(self):
        # All positive or all negative → no IRR solution
        with self.assertRaises(ValueError):
            irr([100.0, 100.0])
        with self.assertRaises(ValueError):
            irr([-100.0, -50.0])

    def test_needs_two_cashflows(self):
        with self.assertRaises(ValueError):
            irr([])
        with self.assertRaises(ValueError):
            irr([-100.0])


class TestComputeReturns(unittest.TestCase):
    """MOIC + IRR on PE-style hold scenarios."""

    def test_moic_is_total_over_entry(self):
        r = compute_returns(entry_equity=100e6, exit_proceeds=300e6, hold_years=5.0)
        self.assertAlmostEqual(r.moic, 3.0, places=5)

    def test_moic_includes_interim_distributions(self):
        # 100M in, 50M interim dividend at year 3, 200M exit at year 5 → MOIC=2.5x
        r = compute_returns(
            entry_equity=100e6, exit_proceeds=200e6, hold_years=5.0,
            interim_cash_flows=[0, 0, 50e6, 0],
        )
        self.assertAlmostEqual(r.moic, 2.5, places=5)

    def test_irr_matches_closed_form_simple_hold(self):
        # 100 in, 250 out in 5 years → IRR = 2.5^(1/5) - 1 ≈ 20.11%
        r = compute_returns(entry_equity=100.0, exit_proceeds=250.0, hold_years=5.0)
        expected = 2.5 ** (1.0 / 5.0) - 1.0
        self.assertAlmostEqual(r.irr, expected, places=4)

    def test_irr_fractional_hold_years(self):
        # 4.5-year hold must not snap to 4 or 5 — exponent is fractional
        r = compute_returns(entry_equity=100.0, exit_proceeds=200.0, hold_years=4.5)
        # Expected: 2^(1/4.5) - 1
        expected = 2.0 ** (1.0 / 4.5) - 1.0
        self.assertAlmostEqual(r.irr, expected, places=4)

    def test_interim_dividend_boosts_irr_above_moic_only_calc(self):
        """Getting cash back early raises IRR even at same MOIC."""
        r_late = compute_returns(entry_equity=100.0, exit_proceeds=300.0, hold_years=5.0)
        r_early = compute_returns(
            entry_equity=100.0, exit_proceeds=200.0, hold_years=5.0,
            interim_cash_flows=[100.0, 0, 0, 0],  # year-1 dividend
        )
        self.assertAlmostEqual(r_late.moic, r_early.moic, places=5)  # both 3.0x
        self.assertGreater(r_early.irr, r_late.irr)

    def test_total_distributions_sums_exit_plus_interim(self):
        r = compute_returns(
            entry_equity=100.0, exit_proceeds=200.0, hold_years=5.0,
            interim_cash_flows=[10.0, 20.0, 30.0, 0],
        )
        self.assertAlmostEqual(r.total_distributions, 260.0, places=5)

    # ── Input validation ──

    def test_zero_entry_equity_raises(self):
        with self.assertRaises(ValueError):
            compute_returns(0.0, 100.0, 5.0)

    def test_zero_hold_years_raises(self):
        with self.assertRaises(ValueError):
            compute_returns(100.0, 200.0, 0.0)


class TestFormatReturns(unittest.TestCase):
    def test_format_includes_moic_and_irr(self):
        r = compute_returns(entry_equity=100e6, exit_proceeds=300e6, hold_years=5.0)
        text = format_returns(r)
        self.assertIn("MOIC", text)
        self.assertIn("IRR", text)
        self.assertIn("3.00x", text)

    def test_format_shows_interim_flows_when_present(self):
        r = compute_returns(
            entry_equity=100e6, exit_proceeds=200e6, hold_years=5.0,
            interim_cash_flows=[25e6, 0, 0, 0],
        )
        text = format_returns(r)
        self.assertIn("Interim flows", text)


class TestHoldPeriodGrid(unittest.TestCase):
    """Sensitivity grid: hold-years × exit-multiples → IRR/MOIC."""

    def _sample_rows(self):
        return hold_period_grid(
            entry_ebitda=50e6,
            uplift_by_year={3: 5e6, 5: 8e6, 7: 9e6},
            entry_multiple=9.0,
            exit_multiples=[8.0, 9.0, 10.0],
            hold_years_list=[3, 5, 7],
            entry_equity=180e6,
            debt_at_entry=270e6,
            debt_at_exit_by_year={3: 240e6, 5: 220e6, 7: 200e6},
            organic_growth_pct=0.03,
        )

    def test_grid_has_row_per_scenario(self):
        rows = self._sample_rows()
        self.assertEqual(len(rows), 3 * 3)  # 3 holds × 3 multiples

    def test_each_row_has_required_keys(self):
        required = {
            "hold_years", "exit_multiple", "entry_ev", "exit_ev",
            "entry_equity", "exit_debt", "exit_equity", "underwater",
            "moic", "irr", "total_value_created", "rcm_uplift_share",
        }
        for r in self._sample_rows():
            self.assertTrue(required.issubset(set(r.keys())),
                            msg=f"Missing: {required - set(r.keys())}")

    def test_longer_hold_at_same_multiple_gives_higher_moic_but_lower_irr(self):
        """Canonical PE tradeoff: hold longer → MOIC up, IRR decays."""
        rows = self._sample_rows()
        by_key = {(r["hold_years"], r["exit_multiple"]): r for r in rows}
        r3 = by_key[(3, 9.0)]
        r5 = by_key[(5, 9.0)]
        r7 = by_key[(7, 9.0)]
        # MOIC monotonically non-decreasing with longer hold (debt paid
        # down, more EBITDA compounding)
        self.assertLess(r3["moic"], r5["moic"])
        self.assertLess(r5["moic"], r7["moic"])
        # IRR generally decays; at least the 3y should be > 7y
        self.assertGreater(r3["irr"], r7["irr"])

    def test_higher_exit_multiple_increases_moic(self):
        rows = self._sample_rows()
        by_key = {(r["hold_years"], r["exit_multiple"]): r for r in rows}
        self.assertLess(by_key[(5, 8.0)]["moic"], by_key[(5, 10.0)]["moic"])

    def test_underwater_flag_when_exit_ev_below_debt(self):
        # Force underwater: 3x entry, 2x exit (value destruction), huge debt
        rows = hold_period_grid(
            entry_ebitda=50e6,
            uplift_by_year={5: -20e6},  # severe degradation
            entry_multiple=5.0,
            exit_multiples=[2.0],
            hold_years_list=[5],
            entry_equity=50e6,
            debt_at_entry=200e6,
            debt_at_exit_by_year={5: 200e6},
        )
        self.assertTrue(rows[0]["underwater"])

    def test_missing_uplift_year_raises(self):
        with self.assertRaises(ValueError):
            hold_period_grid(
                entry_ebitda=50e6,
                uplift_by_year={3: 5e6},
                entry_multiple=9.0, exit_multiples=[10.0],
                hold_years_list=[3, 5],  # 5 missing from uplift_by_year
                entry_equity=180e6,
            )

    def test_rcm_uplift_share_is_nonnegative_when_uplift_positive(self):
        """Share >100% is valid (multiple compression offsets organic + RCM);
        the invariant is only that uplift_share >= 0 when uplift > 0."""
        rows = self._sample_rows()
        for r in rows:
            if r["total_value_created"] > 0:
                self.assertGreaterEqual(r["rcm_uplift_share"], 0.0)

    def test_rcm_uplift_share_roughly_one_when_multiple_flat_and_no_organic(self):
        """With no organic growth and no multiple expansion, RCM share = 100%."""
        rows = hold_period_grid(
            entry_ebitda=50e6, uplift_by_year={5: 10e6},
            entry_multiple=9.0, exit_multiples=[9.0],
            hold_years_list=[5], entry_equity=180e6, debt_at_entry=270e6,
            organic_growth_pct=0.0,
        )
        self.assertAlmostEqual(rows[0]["rcm_uplift_share"], 1.0, places=4)


class TestFormatHoldGrid(unittest.TestCase):
    def test_grid_renders_header_and_rows(self):
        rows = hold_period_grid(
            entry_ebitda=50e6,
            uplift_by_year={5: 8e6},
            entry_multiple=9.0,
            exit_multiples=[9.0, 10.0],
            hold_years_list=[5],
            entry_equity=180e6,
            debt_at_entry=270e6,
        )
        out = format_hold_grid(rows)
        self.assertIn("Hold", out)
        self.assertIn("9.0x", out)
        self.assertIn("10.0x", out)
        self.assertIn("5y", out)

    def test_empty_rows_renders_placeholder(self):
        self.assertIn("no scenarios", format_hold_grid([]))


class TestCovenantCheck(unittest.TestCase):
    """Leverage / covenant headroom — the PE downside-committee staple."""

    def test_actual_leverage_is_debt_over_ebitda(self):
        c = covenant_check(ebitda=50e6, debt=300e6, covenant_max_leverage=7.0)
        self.assertAlmostEqual(c.actual_leverage, 6.0, places=5)

    def test_headroom_positive_when_under_covenant(self):
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5)
        self.assertGreater(c.covenant_headroom_turns, 0)
        self.assertAlmostEqual(c.covenant_headroom_turns, 6.5 - 5.4, places=3)

    def test_headroom_negative_when_tripped(self):
        c = covenant_check(ebitda=35e6, debt=270e6, covenant_max_leverage=6.5)
        self.assertLess(c.covenant_headroom_turns, 0)

    def test_trip_ebitda_equals_debt_over_covenant(self):
        # Trips when EBITDA = debt / covenant
        c = covenant_check(ebitda=50e6, debt=300e6, covenant_max_leverage=6.0)
        self.assertAlmostEqual(c.covenant_trips_at_ebitda, 50e6, places=2)

    def test_ebitda_cushion_pct_matches_formula(self):
        # EBITDA $50M, trips at $41.5M → cushion = (50-41.5)/50 = 17%
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5)
        expected = (50e6 - (270e6 / 6.5)) / 50e6
        self.assertAlmostEqual(c.ebitda_cushion_pct, expected, places=5)

    def test_cushion_negative_when_already_tripped(self):
        c = covenant_check(ebitda=35e6, debt=270e6, covenant_max_leverage=6.5)
        self.assertLess(c.ebitda_cushion_pct, 0)

    def test_interest_coverage_uses_rate_times_debt(self):
        # $50M EBITDA / ($270M × 8%) = 50 / 21.6 = 2.31x
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5,
                           interest_rate=0.08)
        self.assertAlmostEqual(c.interest_coverage, 50e6 / (270e6 * 0.08), places=3)

    def test_interest_coverage_zero_when_rate_is_zero(self):
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5,
                           interest_rate=0.0)
        self.assertEqual(c.interest_coverage, 0.0)

    # ── Input validation ──

    def test_zero_ebitda_raises(self):
        with self.assertRaises(ValueError):
            covenant_check(0.0, 270e6, 6.5)

    def test_negative_debt_raises(self):
        with self.assertRaises(ValueError):
            covenant_check(50e6, -10e6, 6.5)

    def test_zero_covenant_raises(self):
        with self.assertRaises(ValueError):
            covenant_check(50e6, 270e6, 0.0)


class TestFormatCovenant(unittest.TestCase):
    def test_safe_label_when_headroom_ge_1_turn(self):
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5)
        self.assertIn("SAFE", format_covenant(c))

    def test_tight_label_when_headroom_below_1(self):
        c = covenant_check(ebitda=45e6, debt=270e6, covenant_max_leverage=6.5)
        # 6.0x actual, 6.5x covenant → 0.5 turn headroom (tight)
        self.assertIn("TIGHT", format_covenant(c))

    def test_tripped_label_when_negative(self):
        c = covenant_check(ebitda=30e6, debt=270e6, covenant_max_leverage=6.5)
        self.assertIn("TRIPPED", format_covenant(c))

    def test_includes_all_key_fields(self):
        c = covenant_check(ebitda=50e6, debt=270e6, covenant_max_leverage=6.5,
                           interest_rate=0.08)
        text = format_covenant(c)
        self.assertIn("Actual leverage", text)
        self.assertIn("Covenant maximum", text)
        self.assertIn("Headroom", text)
        self.assertIn("EBITDA cushion", text)
        self.assertIn("Interest coverage", text)


class TestFormatBridge(unittest.TestCase):
    def test_terminal_block_contains_all_sections(self):
        b = value_creation_bridge(50e6, 8e6, 9.0, 10.0, 5.0, 0.03)
        text = format_bridge(b)
        self.assertIn("Value Creation Bridge", text)
        self.assertIn("Entry EBITDA", text)
        self.assertIn("Exit EV", text)
        self.assertIn("Organic EBITDA", text)
        self.assertIn("RCM uplift", text)
        self.assertIn("Multiple exp", text)
        self.assertIn("Total value created", text)

    def test_hold_years_in_header(self):
        b = value_creation_bridge(50e6, 8e6, 9.0, 10.0, 7.0)
        self.assertIn("7-year hold", format_bridge(b))
