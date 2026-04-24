"""Management Scorecard regression tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.management_scorecard import (
    ComplevelBand, Executive, ExecutiveScore, ForecastHistory,
    ManagementReport, PriorRole, RedFlag, Role,
    analyze_team, score_executive,
    score_comp_structure, score_forecast_reliability,
    score_prior_role, score_tenure,
)


def _good_ceo() -> Executive:
    return Executive(
        name="Good CEO", role=Role.CEO,
        years_in_role=6, years_at_facility=6,
        total_cash_comp_usd=850_000,
        has_equity_rollover=True,
        has_clawback_provisions=True,
        performance_weighted_bonus=True,
        comp_band=ComplevelBand.P50,
        forecast_history=[
            ForecastHistory("Q1", "EBITDA", 10_000_000, 10_200_000),
            ForecastHistory("Q2", "EBITDA", 10_500_000, 10_400_000),
            ForecastHistory("Q3", "EBITDA", 11_000_000, 11_100_000),
        ],
        prior_roles=[
            PriorRole(employer="HealthCo", role="COO",
                      start_year=2014, end_year=2019,
                      outcome="STRONG_EXIT"),
        ],
    )


def _bad_ceo() -> Executive:
    return Executive(
        name="Bad CEO", role=Role.CEO,
        years_in_role=0.5, years_at_facility=0.5,
        total_cash_comp_usd=1_800_000,
        has_equity_rollover=False,
        comp_band=ComplevelBand.ABOVE_P90,
        forecast_history=[
            ForecastHistory("Q1", "EBITDA", 10_000_000, 7_500_000),
            ForecastHistory("Q2", "EBITDA", 11_000_000, 8_000_000),
        ],
        prior_roles=[
            PriorRole(employer="FailCo", role="CEO",
                      start_year=2018, end_year=2022,
                      outcome="CHAPTER_11"),
        ],
    )


class DimensionScorerTests(unittest.TestCase):

    def test_forecast_reliability_beat_is_100(self):
        hist = [
            ForecastHistory("Q1", "EBITDA", 10, 10.1),
            ForecastHistory("Q2", "EBITDA", 10, 10.2),
        ]
        score, reason, haircut = score_forecast_reliability(hist)
        self.assertEqual(score, 100)
        self.assertEqual(haircut, 0.0)
        self.assertIn("reliable", reason)

    def test_forecast_reliability_heavy_miss(self):
        hist = [
            ForecastHistory("Q1", "EBITDA", 10, 7),    # 30% miss
            ForecastHistory("Q2", "EBITDA", 10, 7.5),  # 25% miss
        ]
        score, reason, haircut = score_forecast_reliability(hist)
        self.assertLess(score, 20)
        self.assertGreaterEqual(haircut, 0.25)

    def test_forecast_reliability_empty_history(self):
        score, reason, haircut = score_forecast_reliability([])
        self.assertEqual(score, 50)
        self.assertIsNone(haircut)

    def test_comp_structure_p50_with_alignment(self):
        e = _good_ceo()
        score, reason = score_comp_structure(e)
        self.assertGreaterEqual(score, 80)

    def test_comp_structure_above_p90_penalized(self):
        e = Executive(
            name="X", role=Role.CEO,
            comp_band=ComplevelBand.ABOVE_P90,
            has_equity_rollover=False,
        )
        score, reason = score_comp_structure(e)
        self.assertLess(score, 40)
        self.assertIn("p90", reason.lower())

    def test_tenure_long_returns_100(self):
        e = Executive(name="X", years_at_facility=8)
        score, reason = score_tenure(e)
        self.assertEqual(score, 100)

    def test_tenure_short_returns_low(self):
        e = Executive(name="X", years_at_facility=0.5)
        score, reason = score_tenure(e)
        self.assertLessEqual(score, 30)

    def test_tenure_unknown_returns_neutral(self):
        e = Executive(name="X")
        score, reason = score_tenure(e)
        self.assertEqual(score, 50)

    def test_prior_role_chapter_11_triggers_critical_flag(self):
        e = Executive(
            name="X",
            prior_roles=[
                PriorRole(employer="FailCo", role="CEO",
                          outcome="CHAPTER_11"),
            ],
        )
        score, reason, flags = score_prior_role(e)
        self.assertLessEqual(score, 30)
        self.assertTrue(any(f.severity == "CRITICAL" for f in flags))

    def test_prior_role_strong_exit_clean(self):
        e = Executive(
            name="X",
            prior_roles=[
                PriorRole(employer="GoodCo", role="CEO",
                          outcome="STRONG_EXIT"),
                PriorRole(employer="AlsoGood", role="COO",
                          outcome="STRONG_EXIT"),
            ],
        )
        score, reason, flags = score_prior_role(e)
        self.assertGreaterEqual(score, 90)
        self.assertEqual(len(flags), 0)


class ExecutiveScorerTests(unittest.TestCase):

    def test_good_ceo_high_overall(self):
        s = score_executive(_good_ceo())
        self.assertGreaterEqual(s.overall, 80)
        self.assertFalse(s.is_red_flag)

    def test_bad_ceo_capped_at_40(self):
        """Red-flag override: any dimension below 30 clips overall
        to 40 — partners see the structural problem."""
        s = score_executive(_bad_ceo())
        self.assertLessEqual(s.overall, 40)
        self.assertTrue(s.is_red_flag)

    def test_confidence_high_with_full_data(self):
        s = score_executive(_good_ceo())
        # Good CEO has 3 periods + 1 prior — MEDIUM confidence
        self.assertIn(s.confidence, ("MEDIUM", "HIGH"))

    def test_confidence_low_with_no_data(self):
        e = Executive(name="Sparse", role=Role.CEO)
        s = score_executive(e)
        self.assertEqual(s.confidence, "LOW")


class TeamAnalyzerTests(unittest.TestCase):

    def test_empty_team_returns_empty_report(self):
        r = analyze_team([])
        self.assertEqual(r.team_size, 0)
        self.assertEqual(r.aggregate_overall, 0)

    def test_clean_team_no_haircut(self):
        r = analyze_team([_good_ceo()])
        if r.bridge_haircut:
            self.assertLess(r.bridge_haircut.recommended_haircut_pct, 0.05)

    def test_bad_ceo_triggers_haircut(self):
        r = analyze_team([_bad_ceo()], guidance_ebitda_usd=10_000_000)
        self.assertIsNotNone(r.bridge_haircut)
        self.assertGreater(r.bridge_haircut.recommended_haircut_pct, 0.10)
        self.assertIsNotNone(r.bridge_haircut.dollar_adjustment_usd)

    def test_critical_flag_rolls_up_to_team(self):
        r = analyze_team([_bad_ceo()])
        self.assertGreater(r.critical_flag_count, 0)
        self.assertTrue(r.has_critical_flags)

    def test_role_weighted_aggregate(self):
        """CEO score should move the aggregate more than CHRO."""
        ceo = _good_ceo()
        ceo.role = Role.CEO
        bad_ceo = _bad_ceo()
        bad_ceo.role = Role.CEO
        # Team with good CEO + bad CHRO
        chro = Executive(name="Bad CHRO", role=Role.CHRO,
                         years_at_facility=0.2,
                         comp_band=ComplevelBand.ABOVE_P90)
        r1 = analyze_team([ceo, chro])
        # Team with bad CEO + good CHRO
        good_chro = Executive(name="Good CHRO", role=Role.CHRO,
                              years_at_facility=6,
                              comp_band=ComplevelBand.P50,
                              has_equity_rollover=True)
        r2 = analyze_team([bad_ceo, good_chro])
        # CEO weighting dominates — good-CEO team should beat bad-CEO team
        self.assertGreater(r1.aggregate_overall, r2.aggregate_overall)

    def test_summary_critical_flags_call_out_partner(self):
        r = analyze_team([_bad_ceo()])
        self.assertIn("CRITICAL", r.summary)


class ManagementScorecardPageTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.management_scorecard_page import (
            render_management_scorecard_page,
        )
        wrapped = {k: [v] for k, v in qs.items()}
        return render_management_scorecard_page(qs=wrapped)

    def test_landing_renders(self):
        h = self._render()
        self.assertIn("Management Scorecard", h)
        self.assertIn("Team aggregate", h)

    def test_demo_roster_surfaces_ceo(self):
        h = self._render()
        self.assertIn("Jane Doe", h)
        self.assertIn("CEO", h)

    def test_critical_flag_visible(self):
        h = self._render()
        # Jane Doe's Steward prior → CRITICAL flag
        self.assertIn("CRITICAL", h)

    def test_haircut_lever_renders_with_guidance(self):
        h = self._render(
            target_name="Test Target",
            guidance_ebitda_usd="10000000",
        )
        self.assertIn("Dollar adjustment", h)

    def test_bookmark_hint_and_json_export(self):
        h = self._render()
        self.assertIn("<kbd", h)
        self.assertIn("data-export-json", h)
        self.assertIn("management_scorecard_report", h)


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_management_link(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        h = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/management"', h)

    def test_deal_profile_exposes_management(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/management", ids)


class ICPacketIntegrationTests(unittest.TestCase):

    def _render_packet(self, **kwargs):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        return render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            **kwargs,
        )

    def test_mgmt_section_renders_with_critical_flags(self):
        report = analyze_team(
            [_bad_ceo()], guidance_ebitda_usd=10_000_000,
        )
        h = self._render_packet(management_report=report)
        self.assertIn("Management Scorecard", h)
        self.assertIn("Recommended guidance haircut", h)
        self.assertIn("Bad CEO", h)

    def test_mgmt_section_silent_when_no_report(self):
        h = self._render_packet(management_report=None)
        self.assertNotIn("Management Scorecard", h)

    def test_mgmt_section_short_when_team_clean(self):
        """Clean team (high aggregate, no flags) should render a
        short all-clear paragraph, not a red-flag call-out."""
        report = analyze_team([_good_ceo()])
        h = self._render_packet(management_report=report)
        self.assertIn("Management Scorecard", h)
        self.assertIn("thesis enabler", h)


if __name__ == "__main__":
    unittest.main()
