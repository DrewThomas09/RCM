"""Tests for the ExitReadinessPacket."""
from __future__ import annotations

import unittest


def _baseline_target():
    from rcm_mc.exit_readiness import ExitTarget
    return ExitTarget(
        target_name="Test Hospital Co.",
        sector="hospital",
        ttm_revenue_mm=350.0,
        ttm_ebitda_mm=63.0,    # 18% margin
        growth_rate=0.10,
        ebitda_margin=0.18,
        net_debt_mm=180.0,
        public_comp_multiple=12.5,
        private_comp_multiple=11.0,
        growth_durability_score=0.7,
        cash_pay_share=0.10,
        physician_concentration=0.35,
        payer_concentration=0.40,
    )


class TestArchetypeValuators(unittest.TestCase):
    def test_strategic_pays_premium(self):
        from rcm_mc.exit_readiness import simulate_strategic_exit
        t = _baseline_target()
        result = simulate_strategic_exit(t)
        # Diversified payer mix + cash-pay → should add 1.0+ turn
        self.assertGreater(result.implied_multiple,
                           t.private_comp_multiple)

    def test_secondary_pe_lbo_solves_for_entry(self):
        from rcm_mc.exit_readiness import simulate_secondary_pe
        t = _baseline_target()
        result = simulate_secondary_pe(t)
        self.assertGreater(result.enterprise_value_mm, 0)
        # Implied multiple should be in the 9-13× range typically
        self.assertGreater(result.implied_multiple, 8.0)
        self.assertLess(result.implied_multiple, 14.0)

    def test_sponsor_to_sponsor_premium_over_sec(self):
        from rcm_mc.exit_readiness import (
            simulate_secondary_pe, simulate_sponsor_to_sponsor,
        )
        t = _baseline_target()
        sec = simulate_secondary_pe(t)
        sts = simulate_sponsor_to_sponsor(t)
        self.assertGreater(sts.implied_multiple, sec.implied_multiple)

    def test_take_private_uses_public_comp(self):
        from rcm_mc.exit_readiness import simulate_take_private
        t = _baseline_target()
        result = simulate_take_private(t)
        # 12.5× × 1.25 control premium ≈ 15.6×
        self.assertAlmostEqual(result.implied_multiple, 15.625, places=1)

    def test_take_private_not_viable_when_low_comp(self):
        from rcm_mc.exit_readiness import simulate_take_private
        t = _baseline_target()
        t.public_comp_multiple = 7.0
        result = simulate_take_private(t)
        self.assertEqual(result.valuation_method, "not_viable")

    def test_ipo_floor_revenue(self):
        """A sub-$200M asset shouldn't IPO."""
        from rcm_mc.exit_readiness import simulate_ipo
        t = _baseline_target()
        t.ttm_revenue_mm = 80.0
        result = simulate_ipo(t)
        self.assertEqual(result.valuation_method, "not_viable")

    def test_dividend_recap_distribution(self):
        from rcm_mc.exit_readiness import simulate_dividend_recap
        t = _baseline_target()
        result = simulate_dividend_recap(t)
        # 5.5× × $63M = $346.5M total debt; existing $180M
        # → distribution = $166.5M
        self.assertAlmostEqual(
            result.equity_value_mm, 5.5 * 63.0 - 180.0, places=1)


class TestEquityStory(unittest.TestCase):
    def test_strategic_fit_high_for_diversified(self):
        from rcm_mc.exit_readiness import (
            score_equity_story, ExitArchetype,
        )
        t = _baseline_target()
        # Push cash-pay + growth above the threshold so all three
        # strategic themes match — pure equity-story alignment test.
        t.cash_pay_share = 0.20
        t.growth_rate = 0.15
        t.payer_concentration = 0.35
        score = score_equity_story(t, ExitArchetype.STRATEGIC)
        # All three themes should match
        self.assertEqual(score.fit_score, 1.0)
        self.assertEqual(set(score.matched_themes), {
            "diversified_payer_mix",
            "cross_sell_optionality",
            "growth_above_market",
        })


class TestReadinessGaps(unittest.TestCase):
    def test_high_payer_concentration_flagged(self):
        from rcm_mc.exit_readiness import (
            identify_readiness_gaps, ExitArchetype,
        )
        t = _baseline_target()
        t.payer_concentration = 0.65   # high
        gaps = identify_readiness_gaps(t)
        archetypes = [g.archetype for g in gaps]
        self.assertIn(ExitArchetype.STRATEGIC, archetypes)

    def test_small_target_flagged_for_ipo(self):
        from rcm_mc.exit_readiness import (
            identify_readiness_gaps, ExitArchetype,
        )
        t = _baseline_target()
        t.ttm_revenue_mm = 80.0
        gaps = identify_readiness_gaps(t)
        ipo_gap = [g for g in gaps if g.archetype == ExitArchetype.IPO]
        self.assertEqual(len(ipo_gap), 1)


class TestPacket(unittest.TestCase):
    def test_full_packet_returns_all_archetypes(self):
        from rcm_mc.exit_readiness import (
            run_exit_readiness_packet, ExitArchetype,
        )
        t = _baseline_target()
        result = run_exit_readiness_packet(t)
        self.assertEqual(result.target_name, "Test Hospital Co.")
        archetypes = {v.archetype for v in result.valuations}
        self.assertEqual(len(archetypes), 7)
        # Recommendation must be a real exit (not div recap)
        self.assertNotEqual(
            result.recommended_archetype, ExitArchetype.DIVIDEND_RECAP)
        self.assertGreater(result.recommended_ev_mm, 0)


class TestRoadmap(unittest.TestCase):
    def test_low_readiness_target_score(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap,
        )
        # Target with several severe gaps
        t = ExitTarget(
            target_name="Gap-Heavy Co",
            sector="hospital",
            ttm_revenue_mm=80.0,         # below IPO floor
            ttm_ebitda_mm=8.0,           # below sponsor S2S floor
            growth_rate=0.05,            # below CV growth
            ebitda_margin=0.10,          # below SecPE margin
            net_debt_mm=50.0,
            public_comp_multiple=8.0,    # below take-private
            private_comp_multiple=10.0,
            growth_durability_score=0.4, # below CV durability
            cash_pay_share=0.30,         # high (s2s gap)
            physician_concentration=0.50,  # high (SecPE gap)
            payer_concentration=0.65,    # high (strategic gap)
        )
        roadmap = build_readiness_roadmap(t)
        # Many gaps → readiness score well below 1.0
        self.assertLess(roadmap.readiness_score, 0.5)
        self.assertGreater(roadmap.total_gaps, 4)
        self.assertGreater(roadmap.high_severity_count, 0)

    def test_clean_target_high_score(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap,
        )
        # Target with no gaps
        t = ExitTarget(
            target_name="Clean Co",
            sector="hospital",
            ttm_revenue_mm=400.0,
            ttm_ebitda_mm=72.0,
            growth_rate=0.12,
            ebitda_margin=0.18,
            net_debt_mm=180.0,
            public_comp_multiple=12.5,
            private_comp_multiple=11.0,
            growth_durability_score=0.75,
            cash_pay_share=0.10,
            physician_concentration=0.30,
            payer_concentration=0.40,
        )
        roadmap = build_readiness_roadmap(t)
        # Few or no gaps → score near 1.0
        self.assertGreaterEqual(roadmap.readiness_score, 0.85)

    def test_roadmap_quarters_sorted(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap,
        )
        t = ExitTarget(
            target_name="Mixed Co", sector="hospital",
            ttm_revenue_mm=80.0, ttm_ebitda_mm=8.0,
            growth_rate=0.05, ebitda_margin=0.10,
            cash_pay_share=0.30, physician_concentration=0.50,
            payer_concentration=0.65, public_comp_multiple=8.0,
            private_comp_multiple=10.0,
            growth_durability_score=0.4,
        )
        roadmap = build_readiness_roadmap(t)
        # Quarter indices are non-decreasing
        indices = [q.quarter_index for q in roadmap.quarters]
        self.assertEqual(indices, sorted(indices))
        # First quarter contains high-severity gaps
        if roadmap.quarters:
            first_q = roadmap.quarters[0]
            if first_q.gaps:
                self.assertEqual(first_q.gaps[0].severity, "high")

    def test_sponsor_to_sponsor_cash_pay_gap(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap, ExitArchetype,
        )
        t = ExitTarget(
            target_name="High Cash-Pay Co",
            sector="physician_group",
            ttm_revenue_mm=300.0, ttm_ebitda_mm=50.0,
            cash_pay_share=0.30,    # triggers s2s gap
        )
        roadmap = build_readiness_roadmap(t)
        s2s_gaps = [
            g
            for q in roadmap.quarters
            for g in q.gaps
            if g.archetype == ExitArchetype.SPONSOR_TO_SPONSOR
        ]
        self.assertGreater(len(s2s_gaps), 0)

    def test_continuation_growth_gap(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap, ExitArchetype,
        )
        t = ExitTarget(
            target_name="Slow-Growth Co",
            sector="hospital",
            ttm_revenue_mm=350.0, ttm_ebitda_mm=63.0,
            growth_rate=0.04,    # triggers CV gap
            growth_durability_score=0.5,  # also triggers CV
        )
        roadmap = build_readiness_roadmap(t)
        cv_gaps = [
            g
            for q in roadmap.quarters
            for g in q.gaps
            if g.archetype == ExitArchetype.CONTINUATION
        ]
        self.assertGreaterEqual(len(cv_gaps), 1)

    def test_render_markdown(self):
        from rcm_mc.exit_readiness import (
            ExitTarget, build_readiness_roadmap,
            render_roadmap_markdown,
        )
        t = ExitTarget(
            target_name="Render Co",
            sector="hospital",
            ttm_revenue_mm=80.0, ttm_ebitda_mm=8.0,
            cash_pay_share=0.30,
        )
        roadmap = build_readiness_roadmap(t)
        md = render_roadmap_markdown(roadmap)
        self.assertIn("## Readiness Roadmap", md)
        self.assertIn("Readiness score", md)


if __name__ == "__main__":
    unittest.main()
