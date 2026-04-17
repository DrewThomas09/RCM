"""Tests for the Scenarios workbench tab (Prompt 20).

Invariants locked here:

1. Tab label "Scenarios" appears in the rendered nav.
2. With 2 scenarios in the packet, two cards render.
3. Pairwise win-probability matrix renders with the expected cells.
4. Recommended scenario carries the accent-border CSS class.
5. Mini-histogram SVG elements render per scenario card.
6. Empty state (no scenarios) shows the instructional message.
7. Overlay histogram has one ``<path>`` per scenario (or none when
   every scenario lacks ``histogram_data``).
8. Add-scenario form panel is rendered and starts hidden.
9. Form inputs are pre-populated from the current bridge's targets.
10. ``packet.scenario_comparison`` round-trips through JSON.
11. Packet without the field deserializes (backward compat).
12. The JS posts to ``simulate/compare`` on submit.
13. Fallback mini-histogram kicks in when ``histogram_data`` is absent
    but percentile data is present.
14. Rationale text is escaped + rendered below the matrix.
15. CSS for the recommended-border is emitted in the page.
"""
from __future__ import annotations

import json
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    EBITDABridgeResult,
    MetricImpact,
)
from rcm_mc.ui.analysis_workbench import render_workbench


def _base_packet(comparison=None) -> DealAnalysisPacket:
    return DealAnalysisPacket(
        deal_id="demo",
        deal_name="Demo Hospital",
        ebitda_bridge=EBITDABridgeResult(
            current_ebitda=60_000_000,
            target_ebitda=72_000_000,
            per_metric_impacts=[
                MetricImpact(
                    metric_key="denial_rate",
                    current_value=12.0, target_value=7.0,
                    ebitda_impact=8_000_000,
                ),
                MetricImpact(
                    metric_key="days_in_ar",
                    current_value=55.0, target_value=45.0,
                    ebitda_impact=4_000_000,
                ),
            ],
        ),
        scenario_comparison=comparison,
    )


def _two_scenarios() -> dict:
    return {
        "per_scenario": {
            "base": {
                "ebitda_impact": {
                    "p10": 5_000_000, "p25": 7_500_000, "p50": 10_000_000,
                    "p75": 12_500_000, "p90": 15_000_000,
                },
                "moic": {"p10": 1.8, "p50": 2.2, "p90": 2.6},
                "variance_contribution": {
                    "denial_rate": 0.5, "days_in_ar": 0.3,
                    "net_collection_rate": 0.2,
                },
                "histogram_data": [
                    {"bin_edge_low": 5e6, "bin_edge_high": 8e6, "count": 10},
                    {"bin_edge_low": 8e6, "bin_edge_high": 11e6, "count": 25},
                    {"bin_edge_low": 11e6, "bin_edge_high": 14e6, "count": 15},
                ],
            },
            "upside": {
                "ebitda_impact": {
                    "p10": 8_000_000, "p25": 11_000_000, "p50": 14_000_000,
                    "p75": 17_000_000, "p90": 20_000_000,
                },
                "moic": {"p10": 2.0, "p50": 2.5, "p90": 3.0},
                "variance_contribution": {
                    "denial_rate": 0.6, "clean_claim_rate": 0.25,
                    "days_in_ar": 0.15,
                },
                "histogram_data": [
                    {"bin_edge_low": 8e6, "bin_edge_high": 12e6, "count": 12},
                    {"bin_edge_low": 12e6, "bin_edge_high": 16e6, "count": 28},
                    {"bin_edge_low": 16e6, "bin_edge_high": 20e6, "count": 10},
                ],
            },
        },
        "pairwise_overlap": {
            "base__vs__upside": 0.25,
            "upside__vs__base": 0.75,
        },
        "recommended_scenario": "upside",
        "rationale": "Upside beats base on risk-adjusted score.",
    }


# ── Tab nav ────────────────────────────────────────────────────────

class TestTabNav(unittest.TestCase):

    def test_scenarios_label_in_nav(self):
        html = render_workbench(_base_packet())
        self.assertIn('data-tab="scenarios"', html)
        self.assertIn(">Scenarios<", html)

    def test_scenarios_panel_element_present(self):
        html = render_workbench(_base_packet())
        self.assertIn('data-panel="scenarios"', html)


# ── Empty state ────────────────────────────────────────────────────

class TestEmptyState(unittest.TestCase):

    def test_empty_state_message(self):
        html = render_workbench(_base_packet())
        self.assertIn("No scenarios compared yet", html)

    def test_empty_state_has_add_button(self):
        html = render_workbench(_base_packet())
        self.assertIn("data-scenario-trigger", html)

    def test_empty_packet_still_renders(self):
        p = DealAnalysisPacket(deal_id="d1")
        html = render_workbench(p)
        self.assertIn("Scenario comparison", html)


# ── Cards ──────────────────────────────────────────────────────────

class TestScenarioCards(unittest.TestCase):

    def test_two_scenarios_two_cards(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertEqual(html.count('class="scenario-card'), 2)

    def test_each_card_shows_p50_ebitda(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        # Workbench's ``_fmt_money`` emits one decimal for millions —
        # e.g. ``$10.0M`` for base P50 and ``$14.0M`` for upside.
        self.assertIn("$10.0M", html)
        self.assertIn("$14.0M", html)

    def test_each_card_has_mini_histogram_svg(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        # Two <svg> elements for mini-histograms plus one for the
        # overlay — at least 3 svg tags in the scenarios section.
        self.assertGreaterEqual(html.count("<svg"), 3)

    def test_recommended_scenario_accent_border(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn("scenario-card scenario-palette-1 recommended", html)
        self.assertIn("scenario-rec-badge", html)

    def test_top_variance_drivers_rendered(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn("denial_rate", html)
        self.assertIn("days_in_ar", html)
        # Upside-exclusive driver also surfaces.
        self.assertIn("clean_claim_rate", html)


# ── Pairwise matrix ────────────────────────────────────────────────

class TestPairwiseMatrix(unittest.TestCase):

    def test_matrix_cells_render(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn("pairwise-matrix", html)
        self.assertIn("25%", html)
        self.assertIn("75%", html)

    def test_matrix_diagonal_is_self(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn('class="pw-self"', html)

    def test_high_low_classes_applied(self):
        """75% is a clear "base loses → high for upside"; 25% the
        mirror. Expect both high- and low-tinted cells."""
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn('class="pw-high"', html)
        self.assertIn('class="pw-low"', html)

    def test_rationale_text_rendered(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn("Upside beats base", html)


# ── Overlay histogram ──────────────────────────────────────────────

class TestOverlay(unittest.TestCase):

    def test_one_path_per_scenario(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        overlay_section_idx = html.find("Overlay distribution")
        self.assertNotEqual(overlay_section_idx, -1)
        # Path count: one <path> per scenario with histogram_data.
        # Count "M " (moveto commands) — each path starts with it.
        overlay_html = html[overlay_section_idx:]
        path_count = overlay_html.count('<path d="M ')
        self.assertEqual(path_count, 2)

    def test_overlay_empty_when_no_histograms(self):
        """Scenarios without histogram_data should still render the
        tab but skip the overlay — the fallback mini still covers
        the per-card display."""
        cmp_no_hist = {
            "per_scenario": {
                "base": {
                    "ebitda_impact": {"p10": 1e6, "p50": 2e6, "p90": 3e6},
                },
            },
        }
        html = render_workbench(_base_packet(cmp_no_hist))
        # The overlay section renders the "distributions unavailable"
        # fallback when no scenario has histogram_data.
        self.assertIn("distributions unavailable", html)


# ── Add-scenario form ──────────────────────────────────────────────

class TestAddScenarioForm(unittest.TestCase):

    def test_form_present_and_hidden(self):
        html = render_workbench(_base_packet())
        self.assertIn('id="scenario-add-form"', html)
        self.assertIn("scenario-add-form hidden", html)

    def test_form_inputs_prepopulated_from_bridge(self):
        """Form should seed an input per bridge lever with the current
        target value."""
        html = render_workbench(_base_packet())
        self.assertIn('data-scenario-target="denial_rate"', html)
        self.assertIn('value="7.00"', html)
        self.assertIn('data-scenario-target="days_in_ar"', html)
        self.assertIn('value="45.00"', html)

    def test_form_submit_wires_compare_api(self):
        html = render_workbench(_base_packet())
        # JS calls the compare endpoint.
        self.assertIn("/simulate/compare", html)
        self.assertIn("data-scenario-submit", html)
        self.assertIn("data-scenario-cancel", html)


# ── Fallback mini-histogram ────────────────────────────────────────

class TestFallbackMini(unittest.TestCase):

    def test_triangular_fallback_when_no_histogram_data(self):
        cmp = {
            "per_scenario": {
                "only": {
                    "ebitda_impact": {
                        "p10": 1_000_000, "p25": 2_000_000,
                        "p50": 3_000_000, "p75": 4_000_000, "p90": 5_000_000,
                    },
                    "moic": {"p10": 1.2, "p50": 1.5, "p90": 1.8},
                },
            },
            "pairwise_overlap": {},
            "recommended_scenario": "only",
        }
        html = render_workbench(_base_packet(cmp))
        # Card rendered, with a fallback SVG inside it.
        self.assertIn('class="scenario-card', html)
        # Fallback generates <rect> elements in the mini-histogram. We
        # look for the actual ``<div class="scenario-mini">`` wrapper
        # (not the CSS rule that lives earlier in the page) and count
        # rects in the slice that follows.
        card_mini_idx = html.find('<div class="scenario-mini">')
        self.assertNotEqual(card_mini_idx, -1)
        after = html[card_mini_idx: card_mini_idx + 5000]
        self.assertGreater(after.count("<rect"), 5)


# ── Packet field ──────────────────────────────────────────────────

class TestPacketField(unittest.TestCase):

    def test_roundtrip_preserves_comparison(self):
        cmp = _two_scenarios()
        p = _base_packet(cmp)
        p2 = DealAnalysisPacket.from_dict(p.to_dict())
        self.assertIsNotNone(p2.scenario_comparison)
        self.assertEqual(
            p2.scenario_comparison["recommended_scenario"], "upside",
        )

    def test_old_packet_without_field_still_deserializes(self):
        # Simulate a pre-Prompt-20 packet payload.
        d = {"deal_id": "d1"}
        p = DealAnalysisPacket.from_dict(d)
        self.assertIsNone(p.scenario_comparison)

    def test_json_roundtrip(self):
        cmp = _two_scenarios()
        p = _base_packet(cmp)
        restored = DealAnalysisPacket.from_json(p.to_json())
        self.assertEqual(
            restored.scenario_comparison.get("recommended_scenario"),
            "upside",
        )


# ── CSS ────────────────────────────────────────────────────────────

class TestScenarioCSS(unittest.TestCase):

    def test_recommended_border_css_present(self):
        html = render_workbench(_base_packet())
        # Both the rule selector and the accent border are in the page.
        self.assertIn(".scenario-card.recommended", html)
        self.assertIn("2px solid var(--wb-accent)", html)

    def test_palette_classes_present(self):
        html = render_workbench(_base_packet(_two_scenarios()))
        self.assertIn(".scenario-palette-0", html)
        self.assertIn(".scenario-palette-1", html)


if __name__ == "__main__":
    unittest.main()
