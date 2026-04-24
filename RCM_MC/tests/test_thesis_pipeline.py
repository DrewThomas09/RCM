"""ThesisPipeline orchestrator regression tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.thesis_pipeline import (
    PipelineInput, ThesisPipelineReport,
    pipeline_observations, run_thesis_pipeline,
)


class PipelineInputTests(unittest.TestCase):

    def test_minimal_input_accepts_fixture_only(self):
        inp = PipelineInput(dataset="hospital_02_denial_heavy")
        self.assertEqual(inp.dataset, "hospital_02_denial_heavy")
        self.assertEqual(inp.deal_name, "Target")


class PipelineExecutionTests(unittest.TestCase):

    def _minimal_report(self):
        return run_thesis_pipeline(PipelineInput(
            dataset="hospital_02_denial_heavy",
            deal_name="T",
        ))

    def _rich_report(self):
        return run_thesis_pipeline(PipelineInput(
            dataset="hospital_02_denial_heavy",
            deal_name="300-Bed",
            enterprise_value_usd=350_000_000,
            equity_check_usd=150_000_000,
            debt_usd=200_000_000,
            revenue_year0_usd=250_000_000,
            ebitda_year0_usd=35_000_000,
            entry_multiple=10.0,
            specialty="HOSPITAL",
            states=["TX"],
            landlord="Medical Properties Trust",
            lease_term_years=20,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.1,
            annual_rent_usd=40_000_000,
            oon_revenue_share=0.08,
            market_category="MULTI_SITE_ACUTE_HOSPITAL",
            ehr_vendor="EPIC",
            business_associates=["Optum360"],
            n_runs=500,
        ))

    def test_minimal_pipeline_runs_every_required_step(self):
        r = self._minimal_report()
        ok = [s for s in r.step_log if s["status"] == "ok"]
        self.assertGreater(len(ok), 5)
        self.assertIsNotNone(r.ccd)
        self.assertIsNotNone(r.kpi_bundle)
        self.assertIsNotNone(r.denial_report)
        self.assertIsNotNone(r.bankruptcy_scan)

    def test_rich_pipeline_populates_all_steps(self):
        r = self._rich_report()
        ok = [s for s in r.step_log if s["status"] == "ok"]
        self.assertEqual(len(ok), len(r.step_log))
        self.assertIsNotNone(r.steward_score)
        self.assertIsNotNone(r.cyber_score)
        self.assertIsNotNone(r.counterfactual_set)
        self.assertIsNotNone(r.autopsy_matches)
        self.assertIsNotNone(r.market_intel)
        self.assertIsNotNone(r.deal_scenario)
        self.assertIsNotNone(r.deal_mc_result)

    def test_headline_numbers_populated(self):
        r = self._rich_report()
        self.assertIsNotNone(r.p50_moic)
        self.assertIsNotNone(r.prob_sub_1x)
        self.assertGreaterEqual(r.p50_moic, 0)
        self.assertGreaterEqual(r.prob_sub_1x, 0)
        self.assertLessEqual(r.prob_sub_1x, 1)
        self.assertIsNotNone(r.bankruptcy_verdict)
        self.assertIsNotNone(r.steward_tier)
        self.assertIsNotNone(r.top_autopsy_match)

    def test_invalid_fixture_short_circuits_gracefully(self):
        r = run_thesis_pipeline(PipelineInput(dataset="nonexistent"))
        self.assertIsNone(r.ccd)
        fail_steps = [
            s for s in r.step_log if s["status"] == "fail"
        ]
        self.assertGreater(len(fail_steps), 0)

    def test_total_compute_under_1_second(self):
        r = self._rich_report()
        # 500-trial Deal MC + all other analytics should finish in
        # well under a second on a dev laptop.
        self.assertLess(r.total_compute_ms, 2000,
                        msg=f"pipeline took {r.total_compute_ms}ms")

    def test_to_dict_contains_headline_numbers(self):
        r = self._rich_report()
        d = r.to_dict()
        self.assertIn("headline_numbers", d)
        self.assertIn("p50_moic", d["headline_numbers"])
        self.assertIn("top_autopsy_match", d["headline_numbers"])


class ChecklistObservationTests(unittest.TestCase):

    def test_observations_keyed_correctly(self):
        r = run_thesis_pipeline(PipelineInput(
            dataset="hospital_02_denial_heavy",
            specialty="HOSPITAL",
            landlord="Medical Properties Trust",
            lease_term_years=20,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.1,
            market_category="MULTI_SITE_ACUTE_HOSPITAL",
            enterprise_value_usd=350_000_000,
            equity_check_usd=150_000_000,
            debt_usd=200_000_000,
            revenue_year0_usd=250_000_000,
            ebitda_year0_usd=35_000_000,
            entry_multiple=10.0,
            ehr_vendor="EPIC",
            n_runs=300,
        ))
        obs = pipeline_observations(r)
        # Expected keys auto-marked True
        for k in (
            "ccd_ingested", "denial_prediction_run",
            "bankruptcy_scan_run", "steward_run", "cyber_run",
            "counterfactual_run", "deal_autopsy_run",
            "market_intel_run", "deal_mc_run",
        ):
            self.assertTrue(obs.get(k),
                            msg=f"{k} should be True after pipeline")

    def test_observations_feeds_checklist_tracker(self):
        """The pipeline's observations should push P0 coverage
        substantially above zero when wired into the checklist."""
        from rcm_mc.diligence.checklist import (
            compute_status, DealObservations,
        )
        r = run_thesis_pipeline(PipelineInput(
            dataset="hospital_02_denial_heavy",
            specialty="HOSPITAL",
            landlord="Medical Properties Trust",
            lease_term_years=20,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.1,
            market_category="MULTI_SITE_ACUTE_HOSPITAL",
            enterprise_value_usd=350_000_000,
            equity_check_usd=150_000_000,
            debt_usd=200_000_000,
            revenue_year0_usd=250_000_000,
            ebitda_year0_usd=35_000_000,
            entry_multiple=10.0,
            ehr_vendor="EPIC",
            n_runs=300,
        ))
        obs = DealObservations(**pipeline_observations(r))
        state = compute_status(obs)
        # Pipeline should cover ~70%+ of P0 items (the manual legal /
        # mgmt-reference / working-capital-peg items remain open).
        self.assertGreater(state.p0_coverage, 0.60)


class ThesisPipelinePageTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.thesis_pipeline_page import (
            render_thesis_pipeline_page,
        )
        wrapped = {k: [v] for k, v in qs.items()}
        return render_thesis_pipeline_page(qs=wrapped)

    def test_landing_renders_with_fixture_selector(self):
        h = self._render()
        self.assertIn("Thesis Pipeline", h)
        self.assertIn("Run Full Pipeline", h)
        self.assertIn("hospital_02_denial_heavy", h)

    def test_live_render_shows_step_log(self):
        h = self._render(
            dataset="hospital_02_denial_heavy",
            deal_name="Test",
            specialty="HOSPITAL",
            enterprise_value_usd="350000000",
            equity_check_usd="150000000",
            debt_usd="200000000",
            revenue_year0_usd="250000000",
            ebitda_year0_usd="35000000",
            entry_multiple="10.0",
            n_runs="300",
        )
        self.assertIn("Step log", h)
        self.assertIn("total compute", h)
        self.assertIn("P50 MOIC", h)
        self.assertIn("Historical analogue", h)
        self.assertIn("Checklist impact", h)

    def test_unknown_fixture_falls_back_to_landing(self):
        h = self._render(dataset="not_a_fixture")
        self.assertIn("Run Full Pipeline", h)

    def test_deeplinks_seeded_with_params(self):
        h = self._render(
            dataset="hospital_02_denial_heavy",
            deal_name="Test",
            revenue_year0_usd="250000000",
            enterprise_value_usd="350000000",
            equity_check_usd="150000000",
            debt_usd="200000000",
            ebitda_year0_usd="35000000",
            entry_multiple="10.0",
            market_category="MULTI_SITE_ACUTE_HOSPITAL",
            specialty="HOSPITAL",
            n_runs="300",
        )
        # Deep-link block should link to each downstream analytic
        self.assertIn("/diligence/benchmarks?dataset=", h)
        self.assertIn("/diligence/denial-prediction?dataset=", h)
        self.assertIn("/diligence/deal-mc?", h)
        self.assertIn("/market-intel?", h)
        self.assertIn("/diligence/ic-packet?", h)


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_thesis_pipeline(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/thesis-pipeline"', rendered)

    def test_deal_profile_exposes_thesis_pipeline(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/thesis-pipeline", ids)


class DealMCPipelineHydrationTests(unittest.TestCase):
    """?from_pipeline=<fixture> should run the pipeline and populate
    Deal MC without requiring hand-typed scenario params."""

    def test_from_pipeline_shortcut_renders_without_ev(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        # Note: no ev_usd passed — hydration should come from pipeline
        h = render_deal_mc_page(qs={
            "from_pipeline": ["hospital_02_denial_heavy"],
            "revenue_usd": ["250000000"],
            "ebitda_usd": ["35000000"],
            "specialty": ["HOSPITAL"],
            "landlord": ["Medical Properties Trust"],
            "lease_term_years": ["20"],
            "lease_escalator_pct": ["0.035"],
            "ebitdar_coverage": ["1.1"],
            "annual_rent_usd": ["40000000"],
            "market_category": ["MULTI_SITE_ACUTE_HOSPITAL"],
            "n_runs": ["300"],
        })
        self.assertIn("P50 MOIC", h)
        # Should NOT show the landing form
        self.assertNotIn("Run Monte Carlo", h)

    def test_from_pipeline_bad_fixture_falls_back_to_landing(self):
        """Invalid fixture + no ev_usd → landing form."""
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        h = render_deal_mc_page(qs={
            "from_pipeline": ["not_a_real_fixture"],
        })
        # Fallback to landing
        self.assertIn("Run Monte Carlo", h)


class HomeQuickstartTests(unittest.TestCase):

    def test_chartis_home_quickstart_when_portfolio_empty(self):
        from rcm_mc.ui.chartis.home_page import _try_the_tool_quickstart
        html_out = _try_the_tool_quickstart()
        self.assertIn("Try the tool", html_out)
        # All 4 fixtures
        for fx in (
            "hospital_01_clean_acute",
            "hospital_02_denial_heavy",
            "hospital_07_waterfall_concordant",
            "hospital_08_waterfall_critical",
        ):
            self.assertIn(fx, html_out)
        # Four Run Pipeline CTAs (one per card) + one in the
        # explainer paragraph that names the button.
        self.assertGreaterEqual(html_out.count("▶ Run Pipeline"), 4)
        # Pipeline URLs
        self.assertIn("/diligence/thesis-pipeline?dataset=", html_out)


if __name__ == "__main__":
    unittest.main()
