"""Lock-in tests for the cycle's interpretability pattern.

Every hero / KPI number in the diligence workflow should carry three
things: the value, a peer benchmark, and a plain-English "What this
shows" callout. These tests assert that the pattern is present on
each of the four surfaces where the interpretability pass landed:

    1. Benchmarks page          — peer-median arrow lines per KPI card
    2. Denial Prediction page   — "What this shows" hero callout + HFMA peer median
    3. Risk Workbench panels    — "What this shows" explainer footers + peer lines on numeric rows
    4. Deal MC page             — "What this shows" hero callout band-keyed off P50

If any of these drift, a partner's first-time reading becomes harder,
so we catch regressions here.
"""
from __future__ import annotations

import unittest


class BenchmarksInterpretabilityTests(unittest.TestCase):
    """The Phase-2 benchmarks page must show peer-median deltas."""

    def _render_live(self):
        from rcm_mc.diligence._pages import render_benchmarks_page
        return render_benchmarks_page(dataset="hospital_02_denial_heavy")

    def test_hero_has_what_this_shows_callout(self):
        h = self._render_live()
        self.assertIn("What this shows", h)

    def test_hero_names_hfma_peer_median(self):
        h = self._render_live()
        self.assertIn("HFMA", h)
        self.assertIn("peer median", h)

    def test_kpi_cards_have_vs_peer_median_line(self):
        """Every KPI card should carry a "▲ ±X vs peer median Y" line."""
        h = self._render_live()
        self.assertIn("vs peer median", h)
        # At least one favorable or unfavorable arrow is rendered.
        self.assertTrue("▲" in h or "▼" in h or "●" in h)

    def test_kpi_card_units_explicit(self):
        """Units (pp for percent, d for days) should appear on the
        delta lines — first-time readers need unit context."""
        h = self._render_live()
        self.assertTrue(" pp" in h or " d" in h or "x" in h)


class DenialPredictionInterpretabilityTests(unittest.TestCase):

    def test_live_render_includes_peer_benchmark_and_callout(self):
        from rcm_mc.ui.denial_prediction_page import (
            render_denial_prediction_page,
        )
        h = render_denial_prediction_page(
            dataset="hospital_02_denial_heavy",
        )
        self.assertIn("What this shows", h)
        self.assertIn("HFMA peer median", h)
        self.assertIn("&gt;0.7 = usable", h)


class RiskWorkbenchInterpretabilityTests(unittest.TestCase):

    def _render_steward(self):
        from rcm_mc.ui.risk_workbench_page import (
            render_risk_workbench, demo_steward_input,
        )
        return render_risk_workbench(demo_steward_input())

    def test_page_has_how_to_read_legend(self):
        h = self._render_steward()
        self.assertIn("How to read these panels", h)
        self.assertIn("GREEN", h)
        self.assertIn("RED", h)

    def test_panels_carry_what_this_shows(self):
        h = self._render_steward()
        self.assertIn("What this shows", h)

    def test_bankruptcy_scan_has_verdict_explanation(self):
        """BankrSurvivor panel should carry a verdict-keyed explanation
        that's specific to the band (not generic)."""
        h = self._render_steward()
        # One of the four verdict explainers must appear (Steward
        # demo is expected to land in CRITICAL or RED).
        band_markers = [
            "walkaway unless the critical patterns are mitigable",
            "Bridge reserves must cover the RED patterns",
            "100-day plan; not a walkaway",
            "Pre-NDA screen",
        ]
        self.assertTrue(
            any(m in h for m in band_markers),
            msg="bankruptcy panel missing verdict explainer",
        )

    def test_real_estate_panel_peer_median_on_rows(self):
        """After the IMPROVE AND REPEAT pass, EBITDAR coverage + rent %
        revenue rows should carry peer-median sublines."""
        h = self._render_steward()
        self.assertIn("peer median ≥1.5x", h)
        self.assertIn("peer median ~3%", h)

    def test_cyber_panel_peer_bands_on_score_row(self):
        h = self._render_steward()
        # The CyberScore row should reference "healthy ≥75" peer band.
        self.assertIn("healthy", h)


class DealMCInterpretabilityTests(unittest.TestCase):

    def _run_dmc(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        return render_deal_mc_page(qs={
            "ev_usd": ["350000000"],
            "equity_usd": ["150000000"],
            "debt_usd": ["200000000"],
            "revenue_usd": ["250000000"],
            "ebitda_usd": ["35000000"],
            "entry_multiple": ["10.0"],
            "n_runs": ["500"],
            "deal_name": ["T"],
        })

    def test_hero_has_what_this_shows_callout(self):
        h = self._run_dmc()
        self.assertIn("What this shows", h)

    def test_hero_interprets_moic_band(self):
        """Some form of band-specific narrative should appear —
        one of the four partner-speak strings keyed off P50 + P(sub-1x)."""
        h = self._run_dmc()
        band_markers = [
            "top quintile of realized outcomes",
            "acceptable but not-top-quintile",
            "Marginal P50 MOIC",
            "walkaway unless material offer-shape",
            "downside probability",
        ]
        self.assertTrue(
            any(m in h for m in band_markers),
            msg="Deal MC hero missing band-keyed interpretation",
        )


class DealAutopsyInterpretabilityTests(unittest.TestCase):

    def test_autopsy_page_has_what_this_shows(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        # Full 9-dim Steward signature — ensures top match clears
        # the 0.80 similarity threshold that triggers the alert banner.
        h = render_deal_autopsy_page(qs={
            "lease_intensity": ["0.90"],
            "ebitdar_stress": ["0.85"],
            "medicare_mix": ["0.55"],
            "payer_concentration": ["0.35"],
            "denial_rate": ["0.14"],
            "dar_stress": ["0.60"],
            "regulatory_exposure": ["0.58"],
            "physician_concentration": ["0.30"],
            "oon_revenue_share": ["0.08"],
        })
        self.assertIn("What this shows", h)
        # Signature alert banner
        self.assertIn("underwriting a deal", h)


class CounterfactualInterpretabilityTests(unittest.TestCase):

    def test_counterfactual_hero_has_what_this_shows(self):
        from rcm_mc.ui.counterfactual_page import (
            render_counterfactual_page,
        )
        h = render_counterfactual_page(
            dataset="hospital_02_denial_heavy",
        )
        self.assertIn("What this shows", h)

    def test_counterfactual_feasibility_explainer_in_render(self):
        """Directly exercise the render function with a synthesized
        CounterfactualSet so the test doesn't depend on fixture
        math producing RED findings."""
        from rcm_mc.diligence.counterfactual import (
            Counterfactual, CounterfactualSet,
        )
        from rcm_mc.ui.counterfactual_page import _render_counterfactuals
        cf_set = CounterfactualSet(items=[
            Counterfactual(
                module="STEWARD", original_band="RED",
                target_band="YELLOW", lever="ESCALATOR_CAP",
                change_description="Cap escalator at 2%",
                estimated_dollar_impact_usd=12_000_000.0,
                feasibility="MEDIUM",
                narrative="narrative body",
                deal_structure_implication="reduce bid by $15M",
            ),
        ])
        html_out = _render_counterfactuals(cf_set)
        self.assertIn("Feasibility MEDIUM", html_out)
        self.assertIn("Requires seller agreement", html_out)


class DealMCChartInterpretabilityTests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.deal_mc_page import render_deal_mc_page
        return render_deal_mc_page(qs={
            "ev_usd": ["350000000"], "equity_usd": ["150000000"],
            "debt_usd": ["200000000"], "revenue_usd": ["250000000"],
            "ebitda_usd": ["35000000"], "entry_multiple": ["10.0"],
            "n_runs": ["500"], "deal_name": ["T"],
        })

    def test_how_to_read_present_on_every_chart(self):
        h = self._render()
        self.assertGreaterEqual(h.count("How to read:"), 4,
                                msg="at least 4 charts should have How-to-read")

    def test_fan_chart_explainer(self):
        h = self._render()
        self.assertIn("X-axis is hold year", h)

    def test_histogram_explainer(self):
        h = self._render()
        self.assertIn("Height of each bar", h)

    def test_attribution_and_tornado_explainers(self):
        h = self._render()
        self.assertIn("Each bar is a stochastic driver", h)
        self.assertIn("MOIC change when one driver is pushed", h)


class RiskWorkbenchPeerContextTests(unittest.TestCase):

    def test_regulatory_panel_has_peer_context(self):
        from rcm_mc.ui.risk_workbench_page import (
            render_risk_workbench, WorkbenchInput,
        )
        h = render_risk_workbench(WorkbenchInput(
            target_name="Test",
            legal_structure="CORPORATE",
            states=["TX"],
            specialty="HOSPITAL",
            hopd_revenue_annual_usd=50_000_000.0,
        ))
        # Regulatory panel's Total $ at risk row should carry peer sub-line
        self.assertTrue(
            "peer norm" in h or "thesis-breaking" in h or "within peer norm" in h,
            msg="regulatory panel missing peer context line",
        )


class ComparePageInterpretabilityTests(unittest.TestCase):

    def test_compare_has_what_this_shows_and_how_to_read(self):
        from rcm_mc.ui.compare_page import render_compare_page
        h = render_compare_page(
            left="hospital_01_clean_acute",
            right="hospital_02_denial_heavy",
        )
        self.assertIn("What this shows", h)
        self.assertIn("How to read", h)

    def test_compare_delta_narrative_present(self):
        from rcm_mc.ui.compare_page import render_compare_page
        h = render_compare_page(
            left="hospital_01_clean_acute",
            right="hospital_02_denial_heavy",
        )
        expected = [
            "more revenue", "more OON exposure",
            "materially similar", "NSA risk",
        ]
        self.assertTrue(
            any(e in h for e in expected),
            msg="compare page delta narrative missing",
        )


class ExitTimingInterpretabilityTests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.exit_timing_page import render_exit_timing_page
        return render_exit_timing_page(qs={
            "equity_check_usd": ["150000000"],
            "debt_year0_usd": ["200000000"],
            "ebitda_year0_usd": ["35000000"],
            "ebitda_growth": ["0.06"],
            "peer_median_multiple": ["9.0"],
            "sector_sentiment": ["positive"],
            "regulatory_verdict": ["GREEN"],
        })

    def test_kpi_tiles_have_provenance(self):
        h = self._render()
        # Each of year / MOIC / IRR / proceeds has provenance tooltip
        self.assertGreaterEqual(h.count("data-provenance"), 4)

    def test_score_band_legend_present(self):
        h = self._render()
        self.assertIn("Score bands:", h)

    def test_curve_how_to_read_with_axis_labels(self):
        h = self._render()
        self.assertIn("X-axis is candidate exit year", h)
        self.assertIn("left axis", h)
        self.assertIn("right axis", h)

    def test_radar_how_to_read(self):
        h = self._render()
        self.assertIn("Outer ring is 100/100 fit", h)
        self.assertIn("wider polygon", h)

    def test_irr_band_context_rendered(self):
        h = self._render()
        # IRR tile carries "vs 15% peer base" context
        self.assertIn("peer base", h)

    def test_moic_band_label_rendered(self):
        h = self._render()
        self.assertTrue(
            "top quintile" in h or "acceptable" in h or "below hurdle" in h,
        )

    def test_curve_implication_narrative(self):
        h = self._render()
        # Peak-IRR narrative sentence names year + delta cost
        self.assertIn("Implication:", h)


class ManagementScorecardInterpretabilityTests(unittest.TestCase):

    def _render(self):
        from rcm_mc.ui.management_scorecard_page import (
            render_management_scorecard_page,
        )
        return render_management_scorecard_page()

    def test_how_to_read_callout_present(self):
        h = self._render()
        self.assertIn("How to read these cards", h)

    def test_score_band_legend_present(self):
        h = self._render()
        self.assertIn("Score bands:", h)

    def test_dimension_tooltip_strings_present(self):
        h = self._render()
        # Forecast reliability tooltip content
        self.assertIn("hit every period", h)

    def test_band_label_on_dim_tile(self):
        h = self._render()
        # At least one of the 4 band labels appears
        self.assertTrue(
            "STRONG" in h or "GOOD" in h
            or "WEAK" in h or "RED FLAG" in h,
        )


if __name__ == "__main__":
    unittest.main()
