"""Exit Timing + Buyer-Type Fit regression tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.exit_timing import (
    BUYER_PLAYBOOKS, BuyerFitScore, BuyerType,
    ExitCurvePoint, ExitRecommendation, ExitTimingReport,
    analyze_exit_timing, build_exit_curve, score_all_buyers,
    score_buyer_fit,
)


def _sample_ebitda_trajectory() -> list:
    # Compounded 5%/yr from 35M over 8 years
    eb = [35_000_000]
    for _ in range(8):
        eb.append(eb[-1] * 1.05)
    return eb


class CurveTests(unittest.TestCase):

    def test_curve_generates_points_for_each_hold(self):
        curve = build_exit_curve(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            exit_multiple_by_year=[9.0] * 9,
        )
        # Default candidates are years 2-7
        self.assertEqual(len(curve), 6)
        self.assertEqual(curve[0].year, 2)
        self.assertEqual(curve[-1].year, 7)

    def test_moic_grows_with_hold(self):
        curve = build_exit_curve(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            exit_multiple_by_year=[9.0] * 9,
        )
        moics = [p.moic for p in curve]
        self.assertEqual(moics, sorted(moics))

    def test_debt_paydown_reduces_remaining_debt(self):
        curve = build_exit_curve(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            exit_multiple_by_year=[9.0] * 9,
        )
        debts = [p.remaining_debt_usd for p in curve]
        # Strictly decreasing
        for i in range(1, len(debts)):
            self.assertLess(debts[i], debts[i - 1])

    def test_bad_ebitda_year_skipped(self):
        """Year with zero EBITDA is skipped, not crashed."""
        trajectory = _sample_ebitda_trajectory()
        trajectory[4] = 0.0  # zero out year 4
        curve = build_exit_curve(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=trajectory,
            exit_multiple_by_year=[9.0] * 9,
        )
        years = [p.year for p in curve]
        self.assertNotIn(4, years)


class BuyerFitTests(unittest.TestCase):

    def test_all_buyer_types_scored(self):
        scores = score_all_buyers(ebitda_year_exit_usd=50_000_000)
        self.assertEqual(len(scores), len(BuyerType))

    def test_strategic_fit_high_with_clean_profile(self):
        s = score_buyer_fit(
            BuyerType.STRATEGIC,
            ebitda_year_exit_usd=75_000_000,
            regulatory_verdict="GREEN",
            commercial_payer_share=0.50,
            sector_sentiment="positive",
            management_score=80,
            top_1_payer_share=0.20,
        )
        self.assertGreaterEqual(s.fit_score, 75)

    def test_ipo_requires_scale(self):
        # EBITDA $50M should not fit IPO (needs $100M+)
        s = score_buyer_fit(
            BuyerType.IPO,
            ebitda_year_exit_usd=50_000_000,
            regulatory_verdict="GREEN",
        )
        self.assertLess(s.fit_score, 70)

    def test_strategic_rejects_oversized_targets(self):
        # $300M EBITDA is beyond strategic appetite
        s = score_buyer_fit(
            BuyerType.STRATEGIC,
            ebitda_year_exit_usd=300_000_000,
        )
        self.assertIn(
            "platform-sized",
            " ".join(s.unfavorable_hits).lower(),
        )

    def test_regulatory_red_is_universal_negative(self):
        for bt in (BuyerType.STRATEGIC, BuyerType.PE_SECONDARY,
                   BuyerType.IPO):
            s = score_buyer_fit(
                bt,
                ebitda_year_exit_usd=80_000_000,
                regulatory_verdict="RED",
            )
            self.assertIn(
                "HSR", " ".join(s.unfavorable_hits),
            )


class AnalyzerTests(unittest.TestCase):

    def _analyze(self, **kwargs):
        defaults = dict(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            peer_median_multiple=9.0,
        )
        defaults.update(kwargs)
        return analyze_exit_timing(**defaults)

    def test_report_has_curve_and_buyers(self):
        r = self._analyze()
        self.assertGreater(len(r.curve), 0)
        self.assertGreater(len(r.buyer_fit), 0)

    def test_recommendation_produced(self):
        r = self._analyze(
            regulatory_verdict="GREEN",
            commercial_payer_share=0.45,
            sector_sentiment="positive",
            management_score=75,
            top_1_payer_share=0.22,
        )
        self.assertIsNotNone(r.recommendation)
        self.assertIn(r.recommendation.exit_year, range(2, 8))
        self.assertGreater(r.recommendation.expected_moic, 1.0)

    def test_recommendation_includes_rationale_sentence(self):
        r = self._analyze(
            regulatory_verdict="GREEN",
            sector_sentiment="positive",
        )
        self.assertIsNotNone(r.recommendation)
        self.assertTrue(r.recommendation.rationale)

    def test_empty_ebitda_no_curve(self):
        r = analyze_exit_timing(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=[],
        )
        self.assertEqual(r.curve, [])

    def test_sponsor_hold_not_recommended_when_moic_clears(self):
        """When real exits clear MOIC 1.5x, sponsor-hold should not
        be the top recommendation."""
        r = self._analyze(
            regulatory_verdict="GREEN",
            commercial_payer_share=0.45,
            sector_sentiment="positive",
        )
        self.assertIsNotNone(r.recommendation)
        self.assertNotEqual(
            r.recommendation.buyer_type, BuyerType.SPONSOR_HOLD,
        )

    def test_report_to_dict_round_trip(self):
        import json
        r = self._analyze(regulatory_verdict="GREEN")
        d = r.to_dict()
        json.dumps(d, default=str)
        self.assertIn("curve", d)
        self.assertIn("recommendation", d)


class ExitTimingPageTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.exit_timing_page import render_exit_timing_page
        wrapped = {k: [v] for k, v in qs.items()}
        return render_exit_timing_page(qs=wrapped)

    def test_landing_without_inputs(self):
        h = self._render()
        self.assertIn("Exit Timing", h)
        self.assertIn("Compute exit path", h)

    def test_live_render_produces_curve_and_radar(self):
        h = self._render(
            equity_check_usd="150000000",
            debt_year0_usd="200000000",
            ebitda_year0_usd="35000000",
            ebitda_growth="0.06",
            peer_median_multiple="9.0",
            sector_sentiment="positive",
            regulatory_verdict="GREEN",
        )
        self.assertIn("IRR × MOIC BY EXIT YEAR", h)
        self.assertIn("BUYER-TYPE FIT", h)
        self.assertIn("Recommended exit path", h)

    def test_invalid_inputs_falls_back_to_landing(self):
        h = self._render(equity_check_usd="abc")
        self.assertIn("Compute exit path", h)

    def test_buyer_playbook_cards_all_render(self):
        h = self._render(
            equity_check_usd="150000000",
            debt_year0_usd="200000000",
            ebitda_year0_usd="35000000",
        )
        for label in (
            "Strategic acquirer", "PE secondary",
            "IPO / public-market exit",
            "Extend hold (sponsor retains)",
        ):
            self.assertIn(label, h, msg=f"missing buyer {label}")


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_exit_timing(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        h = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/exit-timing"', h)

    def test_deal_profile_exposes_exit_timing(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/exit-timing", ids)


class ICPacketIntegrationTests(unittest.TestCase):

    def _analyze(self):
        return analyze_exit_timing(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            peer_median_multiple=9.0,
            regulatory_verdict="GREEN",
            sector_sentiment="positive",
        )

    def test_exit_strategy_section_renders(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        r = self._analyze()
        h = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            exit_timing_report=r,
        )
        self.assertIn("Exit Strategy", h)
        self.assertIn("Recommended exit", h)

    def test_exit_strategy_silent_when_no_report(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        h = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            exit_timing_report=None,
        )
        self.assertNotIn("Exit Strategy", h)


class BelowHurdleFallbackTests(unittest.TestCase):
    """When no exit candidate clears MOIC 1.5x, the recommender
    should still produce a recommendation flagged as below-hurdle
    so partners see the real read rather than None."""

    def test_below_hurdle_produces_flagged_recommendation(self):
        # Very high entry + flat EBITDA → MOIC never clears 1.5x
        flat_ebitda = [35_000_000] * 9
        r = analyze_exit_timing(
            equity_check_usd=300_000_000,  # enormous equity
            debt_year0_usd=50_000_000,
            ebitda_median_by_year=flat_ebitda,
            peer_median_multiple=9.0,
        )
        self.assertIsNotNone(r.recommendation)
        self.assertIn(
            "No exit candidate clears", r.recommendation.summary,
        )
        self.assertIn(
            "Best-of-bad options", r.recommendation.rationale,
        )

    def test_strong_scenario_no_flag(self):
        # Normal scenario that clears 1.5x should not carry the flag
        r = analyze_exit_timing(
            equity_check_usd=150_000_000,
            debt_year0_usd=200_000_000,
            ebitda_median_by_year=_sample_ebitda_trajectory(),
            peer_median_multiple=9.0,
            regulatory_verdict="GREEN",
        )
        self.assertIsNotNone(r.recommendation)
        self.assertNotIn(
            "No exit candidate clears", r.recommendation.summary,
        )


class DealMCCrossLinkTests(unittest.TestCase):
    """Deal MC page should surface an Exit Timing deep-link with
    current scenario params pre-seeded."""

    def _render_mc(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        return render_deal_mc_page(qs={
            "ev_usd": ["350000000"],
            "equity_usd": ["150000000"],
            "debt_usd": ["200000000"],
            "revenue_usd": ["250000000"],
            "ebitda_usd": ["35000000"],
            "entry_multiple": ["10.0"],
            "n_runs": ["300"],
            "deal_name": ["Aurora"],
        })

    def test_exit_timing_cta_present(self):
        h = self._render_mc()
        self.assertIn("Open Exit Timing", h)
        self.assertIn("Next step", h)

    def test_exit_timing_url_preserves_scenario_inputs(self):
        h = self._render_mc()
        self.assertIn("/diligence/exit-timing?", h)
        self.assertIn("equity_check_usd=150000000", h)
        self.assertIn("debt_year0_usd=200000000", h)
        self.assertIn("ebitda_year0_usd=35000000", h)


class PipelineIntegrationTests(unittest.TestCase):

    def test_pipeline_runs_exit_timing_step(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
        )
        inp = PipelineInput(
            dataset="hospital_02_denial_heavy",
            deal_name="Test",
            enterprise_value_usd=350_000_000,
            equity_check_usd=150_000_000,
            debt_usd=200_000_000,
            revenue_year0_usd=250_000_000,
            ebitda_year0_usd=35_000_000,
            entry_multiple=10.0,
            market_category="MULTI_SITE_ACUTE_HOSPITAL",
            specialty="HOSPITAL",
            n_runs=300,
        )
        report = run_thesis_pipeline(inp)
        # Exit timing runs after Deal MC, so the scenario + MC must be OK
        self.assertIsNotNone(report.deal_mc_result)
        self.assertIsNotNone(report.exit_timing_report)
        # Headline numbers on the ThesisPipelineReport are propagated
        self.assertIsNotNone(report.exit_recommendation_year)


if __name__ == "__main__":
    unittest.main()
