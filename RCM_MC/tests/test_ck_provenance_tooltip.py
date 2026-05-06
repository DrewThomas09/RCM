"""Test ck_provenance_tooltip — cycle 34 kit-level entry point.

Two paths: (1) ``explainer`` mode wraps a value in a hover card
with a plain-text methodology sentence; (2) ``graph`` + ``metric_key``
mode defers to ``rcm_mc/ui/_provenance_tooltip.py::provenance_tooltip``
which pulls from a per-deal provenance graph. With neither, returns
escape-safe value.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_provenance_tooltip


class CkProvenanceTooltipTests(unittest.TestCase):
    def test_no_args_returns_escaped_value(self):
        # No explainer, no graph → fall-through to plain escaped text.
        html = ck_provenance_tooltip("Operating Margin", "12.4%")
        self.assertEqual(html, "12.4%")

    def test_no_args_escapes_special_chars(self):
        html = ck_provenance_tooltip("X", "<script>x</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_explainer_mode_renders_card(self):
        html = ck_provenance_tooltip(
            "Operating Margin", "12.4%",
            explainer="Calculated from net revenue minus operating expenses.",
        )
        # Wrapper class
        self.assertIn('class="ck-prov-tt"', html)
        # Info icon
        self.assertIn('class="ck-prov-tt-icon"', html)
        # Card with label + explainer
        self.assertIn('class="ck-prov-tt-card"', html)
        self.assertIn(">Operating Margin</span>", html)
        self.assertIn("Calculated from net revenue", html)
        # CSS injected on first call
        self.assertIn("<style>", html)

    def test_explainer_mode_can_skip_css_injection(self):
        html = ck_provenance_tooltip(
            "X", "12", explainer="Why 12.", inject_css=False,
        )
        self.assertIn('class="ck-prov-tt"', html)
        self.assertNotIn("<style>", html)

    def test_explainer_html_escape(self):
        html = ck_provenance_tooltip(
            "<L>", "<V>",
            explainer="<script>alert(1)</script>",
        )
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;L&gt;", html)
        self.assertIn("&lt;V&gt;", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_graph_mode_defers_to_provenance_tooltip(self):
        # When graph + metric_key are provided, defer to the
        # underlying helper. With graph=None being falsy, the
        # provenance_tooltip helper returns escape-safe text.
        # We pass a dummy non-None graph so the deferral path runs;
        # the underlying helper falls through gracefully when
        # metric_key isn't recognised.
        class _NullGraph:
            pass
        html = ck_provenance_tooltip(
            "X", "12",
            graph=_NullGraph(), metric_key="bogus",
        )
        # Shouldn't render the cycle-34 explainer card (graph mode)
        self.assertNotIn('class="ck-prov-tt-card"', html)
        # And the underlying helper escapes the value
        self.assertIn("12", html)


if __name__ == "__main__":
    unittest.main()
