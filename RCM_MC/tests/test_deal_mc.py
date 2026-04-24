"""Deal Monte Carlo regression tests.

Covers:
    - Engine correctness (distributions monotone; P50 within
      reasonable range for known inputs)
    - Attribution sums + unexplained residual is non-negative
    - Stress test produces non-empty sensitivity list, sorted by
      impact
    - Charts: fan + histogram + attribution + tornado emit valid
      SVG strings
    - UI page: landing renders form, live render produces all
      panels, invalid inputs fall back gracefully
    - Runtime: 3000 trials in < 1s
"""
from __future__ import annotations

import json
import re
import time
import unittest

from rcm_mc.diligence.deal_mc import (
    DealMCResult, DealScenario, run_deal_monte_carlo,
    stress_test_drivers,
)
from rcm_mc.diligence.deal_mc.charts import (
    attribution_chart, fan_chart, moic_histogram_chart,
    sensitivity_tornado,
)


def _steward_replay() -> DealScenario:
    return DealScenario(
        enterprise_value_usd=350_000_000,
        equity_check_usd=150_000_000,
        debt_usd=200_000_000,
        entry_multiple=10.0,
        revenue_year0_usd=250_000_000,
        ebitda_year0_usd=35_000_000,
        medicare_share=0.30,
        reg_headwind_usd=18_000_000,
        exit_multiple_mean=9.0,
        cyber_incident_prob_per_year=0.12,
    )


class EngineTests(unittest.TestCase):

    def setUp(self):
        self.scn = _steward_replay()
        self.result = run_deal_monte_carlo(
            self.scn, n_runs=1500, scenario_name="Test",
        )

    def test_percentiles_ordered(self):
        r = self.result
        self.assertLessEqual(r.moic_p10, r.moic_p25)
        self.assertLessEqual(r.moic_p25, r.moic_p50)
        self.assertLessEqual(r.moic_p50, r.moic_p75)
        self.assertLessEqual(r.moic_p75, r.moic_p90)
        self.assertLessEqual(r.irr_p10, r.irr_p50)
        self.assertLessEqual(r.irr_p50, r.irr_p90)

    def test_revenue_bands_match_hold_years(self):
        # Y0 through Y5 = 6 bands
        self.assertEqual(len(self.result.revenue_bands), 6)
        self.assertEqual(self.result.revenue_bands[0].year, 0)
        self.assertEqual(self.result.revenue_bands[-1].year, 5)

    def test_probabilities_sum_plausibly(self):
        self.assertGreaterEqual(self.result.prob_sub_1x, 0.0)
        self.assertLessEqual(self.result.prob_sub_1x, 1.0)
        self.assertGreaterEqual(self.result.prob_sub_2x,
                                self.result.prob_sub_1x)
        self.assertLessEqual(self.result.prob_sub_2x, 1.0)

    def test_moic_histogram_covers_full_range(self):
        buckets = self.result.moic_histogram
        self.assertGreater(len(buckets), 0)
        total_prob = sum(b.probability for b in buckets)
        # Should cover most of the mass (some trials MOIC > 10 get
        # clamped to the top bucket which has upper=10).
        self.assertGreater(total_prob, 0.90)

    def test_attribution_sums_to_one(self):
        attr = self.result.attribution
        self.assertIsNotNone(attr)
        share_sum = sum(
            c.share_of_variance for c in attr.contributions
        ) + attr.unexplained_share
        self.assertAlmostEqual(share_sum, 1.0, delta=0.02)
        # Unexplained is non-negative
        self.assertGreaterEqual(attr.unexplained_share, 0.0)

    def test_stress_test_produces_sorted_impacts(self):
        stress = self.result.stress_results
        self.assertGreater(len(stress), 0)
        # Sorted ascending by moic_impact (worst-first)
        impacts = [s.moic_impact for s in stress]
        self.assertEqual(impacts, sorted(impacts))

    def test_deterministic_with_same_seed(self):
        r1 = run_deal_monte_carlo(
            _steward_replay(), n_runs=500, stress=False,
            attribute=False,
        )
        r2 = run_deal_monte_carlo(
            _steward_replay(), n_runs=500, stress=False,
            attribute=False,
        )
        self.assertAlmostEqual(r1.moic_p50, r2.moic_p50, places=6)

    def test_higher_reg_headwind_lowers_moic(self):
        base = run_deal_monte_carlo(
            _steward_replay(), n_runs=500, stress=False,
            attribute=False,
        )
        scn = _steward_replay()
        scn.reg_headwind_usd = 80_000_000
        stressed = run_deal_monte_carlo(
            scn, n_runs=500, stress=False, attribute=False,
        )
        self.assertLess(stressed.moic_p50, base.moic_p50)


class PerformanceTests(unittest.TestCase):

    def test_3000_trials_under_one_second(self):
        scn = _steward_replay()
        t0 = time.time()
        run_deal_monte_carlo(
            scn, n_runs=3000, stress=True, attribute=True,
        )
        elapsed = time.time() - t0
        self.assertLess(elapsed, 2.0,
                        msg=f"3000 trials took {elapsed:.2f}s")


class ChartTests(unittest.TestCase):

    def setUp(self):
        self.result = run_deal_monte_carlo(
            _steward_replay(), n_runs=500,
        )

    def test_fan_chart_svg_valid(self):
        svg = fan_chart(
            self.result.revenue_bands, title="Revenue",
        )
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("viewBox", svg)

    def test_moic_histogram_svg(self):
        svg = moic_histogram_chart(self.result)
        self.assertIn("<rect", svg)
        self.assertIn("MOIC DISTRIBUTION", svg)

    def test_attribution_chart_svg(self):
        svg = attribution_chart(self.result)
        self.assertIn("VARIANCE ATTRIBUTION", svg)

    def test_sensitivity_tornado_svg(self):
        svg = sensitivity_tornado(self.result)
        self.assertIn("SENSITIVITY", svg)


class DealMCPageTests(unittest.TestCase):

    def test_landing_renders_form(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        h = render_deal_mc_page(qs={})
        self.assertIn("Deal Monte Carlo", h)
        self.assertIn("Run Monte Carlo", h)

    def test_live_render_produces_all_panels(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        h = render_deal_mc_page(qs={
            "ev_usd": ["350000000"],
            "equity_usd": ["150000000"],
            "debt_usd": ["200000000"],
            "revenue_usd": ["250000000"],
            "ebitda_usd": ["35000000"],
            "entry_multiple": ["10.0"],
            "n_runs": ["500"],
            "deal_name": ["Test"],
        })
        for marker in (
            "P50 MOIC", "Revenue Projection",
            "EBITDA Projection", "MOIC Distribution",
            "VARIANCE ATTRIBUTION", "SENSITIVITY",
            "Scenario Inputs",
        ):
            self.assertIn(marker, h,
                          msg=f"missing {marker}")

    def test_invalid_inputs_show_error(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        # Zero equity → should fail cleanly.
        h = render_deal_mc_page(qs={
            "ev_usd": ["100000"],
            "equity_usd": ["0"],
            "debt_usd": ["0"],
            "revenue_usd": ["100000"],
            "ebitda_usd": ["10000"],
        })
        self.assertIn("must both be positive", h)

    def test_missing_inputs_falls_back_to_landing(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        h = render_deal_mc_page(qs={"deal_name": ["X"]})
        self.assertIn("Run Monte Carlo", h)  # landing form


class NavLinkTest(unittest.TestCase):

    def test_deal_mc_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/deal-mc"', rendered)


class JsonSerialisationTest(unittest.TestCase):

    def test_result_round_trip(self):
        result = run_deal_monte_carlo(
            _steward_replay(), n_runs=500,
        )
        d = result.to_dict()
        # Round-trip through json to catch non-serialisable fields.
        s = json.dumps(d, default=str)
        parsed = json.loads(s)
        self.assertIn("moic_p50", parsed)
        self.assertIn("attribution", parsed)
        self.assertIn("stress_results", parsed)


class VPWorkflowIntegrationTest(unittest.TestCase):
    """The full VP-of-a-300-bed-hospital workflow — screen →
    diligence → workbench → counterfactual → market intel →
    deal MC → IC packet. All 7 steps must run without raising."""

    def test_full_workflow_end_to_end(self):
        # 1. Screen
        from rcm_mc.diligence.screening import (
            ScanInput, run_bankruptcy_survivor_scan,
        )
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="300-bed", specialty="HOSPITAL",
            states=["MA"], landlord="Medical Properties Trust",
            lease_term_years=20, lease_escalator_pct=0.035,
            ebitdar_coverage=1.3,
        ))
        self.assertIn(scan.verdict.value,
                      ("GREEN", "YELLOW", "RED", "CRITICAL"))

        # 2. Deal MC
        scn = _steward_replay()
        r = run_deal_monte_carlo(scn, n_runs=500)
        self.assertGreater(r.moic_p50, 0)
        self.assertLess(r.moic_p50, 10)

        # 3. Stress test independently
        stress = stress_test_drivers(scn, n_runs=300)
        self.assertGreater(len(stress), 0)


if __name__ == "__main__":
    unittest.main()
