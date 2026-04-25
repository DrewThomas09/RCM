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


def _three_deal_fund():
    """Three realized deals across two vintage years."""
    from rcm_mc.irr_attribution import DealCashflows
    return [
        DealCashflows(
            deal_name="DealA",
            entry_year=2018, exit_year=2023,
            ev_at_entry_mm=200.0, ev_at_exit_mm=400.0,
            ebitda_at_entry_mm=20.0, ebitda_at_exit_mm=40.0,
            revenue_at_entry_mm=110.0, revenue_at_exit_mm=180.0,
            net_debt_at_entry_mm=100.0, net_debt_at_exit_mm=80.0,
            addon_revenue_contribution_mm=20.0,
            cashflows=[(0.0, -100.0), (5.0, 320.0)],
        ),
        DealCashflows(
            deal_name="DealB",
            entry_year=2018, exit_year=2024,
            ev_at_entry_mm=400.0, ev_at_exit_mm=750.0,
            ebitda_at_entry_mm=40.0, ebitda_at_exit_mm=70.0,
            revenue_at_entry_mm=220.0, revenue_at_exit_mm=320.0,
            net_debt_at_entry_mm=200.0, net_debt_at_exit_mm=160.0,
            addon_revenue_contribution_mm=25.0,
            cashflows=[(0.0, -200.0), (6.0, 590.0)],
        ),
        DealCashflows(
            deal_name="DealC",
            entry_year=2020, exit_year=2025,
            ev_at_entry_mm=300.0, ev_at_exit_mm=540.0,
            ebitda_at_entry_mm=30.0, ebitda_at_exit_mm=45.0,
            revenue_at_entry_mm=170.0, revenue_at_exit_mm=205.0,
            net_debt_at_entry_mm=150.0, net_debt_at_exit_mm=130.0,
            addon_revenue_contribution_mm=10.0,
            cashflows=[(0.0, -150.0), (5.0, 410.0)],
        ),
    ]


class TestFundAggregation(unittest.TestCase):
    def test_fund_total_sums_per_deal(self):
        from rcm_mc.irr_attribution import (
            aggregate_fund_attribution,
        )
        fund = aggregate_fund_attribution(
            "TestFund I", _three_deal_fund())
        self.assertEqual(fund.n_deals, 3)
        # Fund total = sum of per-deal totals
        deal_sum = sum(
            r.total_value_created_mm for r in fund.deal_rows)
        self.assertAlmostEqual(
            fund.total_value_created_mm, deal_sum, places=1)

    def test_deal_lookthrough_sorted_descending(self):
        from rcm_mc.irr_attribution import (
            aggregate_fund_attribution,
        )
        fund = aggregate_fund_attribution(
            "TestFund I", _three_deal_fund())
        # Deal rows ordered by total_value_created descending
        totals = [r.total_value_created_mm
                  for r in fund.deal_rows]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_vintage_rollup_buckets_by_year(self):
        from rcm_mc.irr_attribution import (
            aggregate_fund_attribution,
        )
        fund = aggregate_fund_attribution(
            "TestFund I", _three_deal_fund())
        # Two vintages: 2018 (2 deals), 2020 (1 deal)
        self.assertIn(2018, fund.vintage_rollup)
        self.assertIn(2020, fund.vintage_rollup)
        # 2018 vintage total should exceed 2020 (2 deals vs 1)
        v18 = fund.vintage_rollup[2018].total_value_created_mm
        v20 = fund.vintage_rollup[2020].total_value_created_mm
        self.assertGreater(v18, v20)

    def test_format_fund_ilpa_schema(self):
        from rcm_mc.irr_attribution import (
            aggregate_fund_attribution, format_fund_ilpa,
        )
        fund = aggregate_fund_attribution(
            "TestFund I", _three_deal_fund())
        out = format_fund_ilpa(fund)
        self.assertEqual(out["fund_name"], "TestFund I")
        self.assertEqual(out["n_realized_deals"], 3)
        self.assertEqual(out["ilpa_template_version"], "2.0")
        # Required ILPA attribution keys
        attr = out["value_creation_attribution"]
        for k in ("revenue_growth_organic",
                  "revenue_growth_inorganic",
                  "margin_expansion", "multiple_expansion",
                  "debt_paydown_leverage", "fx_translation",
                  "dividend_recap", "subscription_line_credit",
                  "cross_terms_residual"):
            self.assertIn(k, attr)
        # Lookthrough has all 3 deals
        self.assertEqual(len(out["deal_lookthrough"]), 3)
        # Vintage rollup has both years
        self.assertIn("2018", out["vintage_rollup"])
        self.assertIn("2020", out["vintage_rollup"])


if __name__ == "__main__":
    unittest.main()
