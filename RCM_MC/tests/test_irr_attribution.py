"""Tests for the IRR-Attribution Packet."""
from __future__ import annotations

import unittest


def _baseline_cashflows():
    """A clean 5-year hold:
       Entry: $300M EV at 10× EBITDA ($30M), 50% leverage, 18% margin
       Exit:  $600M EV at 12× EBITDA ($50M), 40% leverage, 22% margin
       Hold: 5 years, no dividend recap, no FX, no sub-line.
    """
    from rcm_mc.irr_attribution import DealCashflows
    return DealCashflows(
        deal_name="Cleanco",
        entry_year=2021, exit_year=2026,
        ev_at_entry_mm=300.0,
        ev_at_exit_mm=600.0,
        ebitda_at_entry_mm=30.0,
        ebitda_at_exit_mm=50.0,
        revenue_at_entry_mm=167.0,    # 30/0.18
        revenue_at_exit_mm=227.0,     # 50/0.22
        net_debt_at_entry_mm=150.0,
        net_debt_at_exit_mm=120.0,
        addon_revenue_contribution_mm=15.0,
        cashflows=[
            (0.0, -150.0),    # entry equity check
            (5.0, 480.0),     # exit equity (600 - 120)
        ],
    )


class TestIRRMath(unittest.TestCase):
    def test_irr_basic(self):
        from rcm_mc.irr_attribution import compute_irr, compute_moic
        cf = [(0.0, -100.0), (5.0, 200.0)]
        irr = compute_irr(cf)
        # Doubling over 5 years → IRR ≈ 14.87%
        self.assertAlmostEqual(irr, 0.1487, places=2)
        moic = compute_moic(cf)
        self.assertAlmostEqual(moic, 2.0, places=2)

    def test_irr_no_outflows_returns_zero(self):
        from rcm_mc.irr_attribution import compute_irr
        # Degenerate: only inflows
        irr = compute_irr([(0.0, 100.0), (1.0, 200.0)])
        self.assertEqual(irr, 0.0)

    def test_irr_with_recap(self):
        """A recap mid-hold should raise IRR vs. lump-sum exit."""
        from rcm_mc.irr_attribution import compute_irr
        no_recap = compute_irr([(0.0, -100.0), (5.0, 200.0)])
        with_recap = compute_irr([
            (0.0, -100.0), (2.0, 50.0), (5.0, 175.0),
        ])
        self.assertGreater(with_recap, no_recap)


class TestDecomposition(unittest.TestCase):
    def test_value_created_components_signed_correctly(self):
        from rcm_mc.irr_attribution import decompose_value_creation
        result = decompose_value_creation(_baseline_cashflows())

        c = result.components
        # All major positive components
        self.assertGreater(c.revenue_growth_organic_mm, 0)
        self.assertGreater(c.revenue_growth_ma_mm, 0)
        self.assertGreater(c.margin_expansion_mm, 0)
        self.assertGreater(c.multiple_expansion_mm, 0)
        self.assertGreater(c.leverage_mm, 0)  # debt paid down

        # Total value created is the sum of EV change + leverage
        # paydown + recap + FX + sub-line
        # = 300 (EV change) + 30 (leverage) = 330
        self.assertAlmostEqual(
            c.total_value_created_mm, 330.0, delta=0.5)

    def test_organic_vs_ma_split(self):
        from rcm_mc.irr_attribution import (
            DealCashflows, decompose_value_creation,
        )
        # All M&A: every dollar of revenue growth is from add-ons
        cf = _baseline_cashflows()
        # Total revenue grew from 167 to 227 = $60M.
        cf.addon_revenue_contribution_mm = 60.0
        result = decompose_value_creation(cf)
        # Organic should be ~0
        self.assertAlmostEqual(
            result.components.revenue_growth_organic_mm,
            0.0, delta=0.5)
        # M&A should be all the revenue contribution
        self.assertGreater(
            result.components.revenue_growth_ma_mm, 0)

    def test_ev_change_decomposes_to_components_plus_cross(self):
        """The four EBITDA-driven components plus cross_terms must
        sum to the total EV change."""
        from rcm_mc.irr_attribution import decompose_value_creation
        cf = _baseline_cashflows()
        result = decompose_value_creation(cf)
        c = result.components
        ebitda_driven = (
            c.revenue_growth_organic_mm
            + c.revenue_growth_ma_mm
            + c.margin_expansion_mm
            + c.multiple_expansion_mm
            + c.cross_terms_mm
        )
        ev_change = cf.ev_at_exit_mm - cf.ev_at_entry_mm
        self.assertAlmostEqual(ebitda_driven, ev_change, delta=0.5)

    def test_dividend_recap_captured(self):
        from rcm_mc.irr_attribution import (
            DealCashflows, decompose_value_creation,
        )
        cf = _baseline_cashflows()
        cf.cashflows = [
            (0.0, -150.0),
            (3.0, 60.0),       # mid-hold recap
            (5.0, 420.0),      # final exit
        ]
        result = decompose_value_creation(cf)
        self.assertAlmostEqual(
            result.components.dividend_recap_mm, 60.0, places=1)


class TestILPAFormat(unittest.TestCase):
    def test_format_returns_required_fields(self):
        from rcm_mc.irr_attribution import (
            decompose_value_creation, format_ilpa_2_0,
        )
        result = decompose_value_creation(_baseline_cashflows())
        ilpa = format_ilpa_2_0(result)
        self.assertEqual(ilpa["ilpa_template_version"], "2.0")
        self.assertIn("value_creation_attribution", ilpa)
        attr = ilpa["value_creation_attribution"]
        for k in ("revenue_growth_organic", "revenue_growth_inorganic",
                  "margin_expansion", "multiple_expansion",
                  "debt_paydown_leverage", "dividend_recap",
                  "subscription_line_credit",
                  "cross_terms_residual",
                  "total_value_created"):
            self.assertIn(k, attr)


class TestLPNarrative(unittest.TestCase):
    def test_renders_required_sections(self):
        from rcm_mc.irr_attribution import (
            decompose_value_creation, render_lp_narrative,
        )
        result = decompose_value_creation(_baseline_cashflows())
        md = render_lp_narrative(result)
        self.assertIn("Cleanco", md)
        self.assertIn("Performance Attribution", md)
        self.assertIn("Value Creation Attribution", md)
        # Header row of the table
        self.assertIn("| Component | $M | Share |", md)


if __name__ == "__main__":
    unittest.main()
