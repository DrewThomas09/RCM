"""Test for the shared "explain this number" tooltip helper
(campaign target 4C, loop 118).

Phase 4C of the v3 transformation campaign requires that
every numeric on a page that has provenance gets a tooltip
showing the provenance graph explanation. This loop ships
the foundational helper at rcm_mc/ui/_provenance_tooltip.py
that future page-level loops will adopt.

Asserts:
  - With graph=None: returns plain escaped value (no
    tooltip wrapper, no info icon).
  - With graph but metric_key=None / unknown / unresolved:
    same plain-text fallthrough — no broken tooltips ship.
  - With a real ProvenanceGraph + valid metric_key:
    returns the prov-tt wrapper containing the value, an
    info icon, and a hidden card with the prose explanation
    + node type + upstream source list.
  - inject_css=False omits the <style> block (so callers
    rendering many tooltips can pass it once).
  - The label and value arguments are HTML-escaped (no
    injection from data-driven labels).
"""
from __future__ import annotations

import unittest

from rcm_mc.provenance.graph import (
    NodeType,
    ProvenanceGraph,
    ProvenanceNode,
)
from rcm_mc.ui._provenance_tooltip import provenance_tooltip


def _build_fixture_graph() -> ProvenanceGraph:
    """Tiny graph: an HCRIS revenue source feeding a
    CALCULATED operating-margin node. Resolver expects the
    metric node id to be one of the known prefixed forms
    (`bridge:`, `observed:`, etc.) — using `bridge:` here
    because the node is CALCULATED."""
    g = ProvenanceGraph()
    g.add_node(ProvenanceNode(
        id="hcris:rev", label="Net Patient Revenue",
        node_type=NodeType.SOURCE, value=1.0e8, unit="USD",
        source="HCRIS"))
    g.add_node(ProvenanceNode(
        id="bridge:operating_margin",
        label="Operating Margin", node_type=NodeType.CALCULATED,
        value=0.124, unit="pct"))
    g.add_edge("hcris:rev", "bridge:operating_margin")
    return g


class ProvenanceTooltipFallthroughTests(unittest.TestCase):
    """Cases where no tooltip should appear → plain escaped
    value is returned. These guarantee the helper is safe to
    drop into any page render path even without provenance."""

    def test_no_graph_returns_plain_value(self) -> None:
        out = provenance_tooltip("Operating Margin", "12.4%")
        self.assertEqual(out, "12.4%")

    def test_no_metric_key_returns_plain_value(self) -> None:
        # graph supplied, metric_key not — still plain text
        g = _build_fixture_graph()
        out = provenance_tooltip(
            "Operating Margin", "12.4%",
            graph=g, metric_key=None,
        )
        self.assertEqual(out, "12.4%")

    def test_unknown_metric_returns_plain_value(self) -> None:
        g = _build_fixture_graph()
        out = provenance_tooltip(
            "Bogus", "—", graph=g, metric_key="no_such_metric",
        )
        self.assertEqual(out, "—")

    def test_value_is_html_escaped(self) -> None:
        """A pre-formatted value containing HTML special chars
        must be escaped — partner data sometimes contains <
        and > (e.g. '<5%' for 'less than 5%')."""
        out = provenance_tooltip("X", "<5%")
        self.assertNotIn("<5%", out)
        self.assertIn("&lt;5%", out)


class ProvenanceTooltipRenderTests(unittest.TestCase):
    """Cases where the helper should render the full hover
    card with prose, node type, and upstream sources."""

    def test_known_metric_renders_full_card(self) -> None:
        g = _build_fixture_graph()
        out = provenance_tooltip(
            "Operating Margin", "12.4%",
            graph=g, metric_key="operating_margin",
        )
        # Wrapper + value + info icon all present
        self.assertIn('class="prov-tt"', out)
        self.assertIn("12.4%", out)
        self.assertIn('class="prov-tt-icon"', out)
        # Card content
        self.assertIn('class="prov-tt-card"', out)
        self.assertIn("Operating Margin", out)
        # Upstream source label appears in card
        self.assertIn("Net Patient Revenue", out)
        # Node type appears (CALCULATED)
        self.assertIn("CALCULATED", out)

    def test_label_is_html_escaped_in_card(self) -> None:
        g = _build_fixture_graph()
        out = provenance_tooltip(
            "<script>alert('xss')</script>", "12.4%",
            graph=g, metric_key="operating_margin",
        )
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_inject_css_false_omits_style_block(self) -> None:
        g = _build_fixture_graph()
        full = provenance_tooltip(
            "Operating Margin", "12.4%",
            graph=g, metric_key="operating_margin",
            inject_css=True,
        )
        without = provenance_tooltip(
            "Operating Margin", "12.4%",
            graph=g, metric_key="operating_margin",
            inject_css=False,
        )
        # First call ships the style block; second call shouldn't.
        self.assertIn("<style>", full)
        self.assertNotIn("<style>", without)
        # But both should still produce a valid tooltip wrapper.
        self.assertIn('class="prov-tt"', without)

    def test_aria_label_includes_metric(self) -> None:
        """Accessibility: the info icon should announce what
        it's a tooltip *for* via aria-label."""
        g = _build_fixture_graph()
        out = provenance_tooltip(
            "Operating Margin", "12.4%",
            graph=g, metric_key="operating_margin",
        )
        self.assertIn(
            'aria-label="Show provenance for Operating Margin"',
            out,
        )


if __name__ == "__main__":
    unittest.main()
