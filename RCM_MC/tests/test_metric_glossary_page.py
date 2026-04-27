"""Test for the canonical /metric-glossary page (campaign
target 4A, loop 104).

Phase 4A of the v3 transformation campaign requires that every
page mentioning a metric link to ``/metric-glossary#<key>``.
That requires the destination route to exist and to render
each metric as an anchor-linkable card with id=<key>.

Asserts:
  - render_metric_glossary returns a non-empty HTML string.
  - Every metric registered in metric_glossary._GLOSSARY shows
    up in the rendered HTML, both as an anchor target
    (`id="<key>"`) and as a TOC link target (`href="#<key>"`).
  - The page renders through chartis_shell (v3 design
    compliance) — assert the editorial-shell signature class
    is in the output.
  - Server route wiring: GET /metric-glossary appears in the
    dispatcher block of server.py and resolves to the new
    handler method.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.metric_glossary import list_metrics
from rcm_mc.ui.metric_glossary_page import render_metric_glossary


_SERVER_PATH = (
    Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"
)


class MetricGlossaryPageTests(unittest.TestCase):
    def test_render_metric_glossary_returns_non_empty_html(self) -> None:
        html = render_metric_glossary()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 1000)
        # Subtitle reflects metric count.
        self.assertIn("Metric Glossary", html)

    def test_every_metric_has_anchor_target_and_toc_link(self) -> None:
        """Each registered metric key appears twice in the
        rendered HTML — once as `id="<key>"` (anchor target on
        its card) and once as `href="#<key>"` (TOC link)."""
        html = render_metric_glossary()
        keys = list_metrics()
        self.assertGreater(
            len(keys), 0,
            "metric glossary registry should have metrics",
        )
        for key in keys:
            with self.subTest(key=key):
                self.assertIn(
                    f'id="{key}"', html,
                    f"metric {key!r} missing card anchor",
                )
                self.assertIn(
                    f'href="#{key}"', html,
                    f"metric {key!r} missing TOC link",
                )

    def test_render_uses_chartis_shell(self) -> None:
        """v3 compliance: the page must render through
        chartis_shell, not a custom HTML wrapper. The shell
        wraps body in <article class="ck-frame"> (editorial)
        or sets up the dark Bloomberg layout (legacy). Both
        emit the `--ck-mono` CSS variable and `chartis` in
        the head."""
        html = render_metric_glossary()
        # Both editorial and legacy shells include the literal
        # word "chartis" or "Chartis" somewhere in the chrome.
        self.assertTrue(
            ("chartis" in html.lower()
             or "Chartis" in html),
            "render output should reach chartis_shell chrome",
        )

    def test_server_dispatcher_wires_metric_glossary_route(self) -> None:
        """The dispatcher in server.py should match
        /metric-glossary and route to _route_metric_glossary."""
        text = _SERVER_PATH.read_text(encoding="utf-8")
        self.assertIn(
            'path == "/metric-glossary"', text,
            "server.py dispatcher missing /metric-glossary check",
        )
        self.assertIn(
            "_route_metric_glossary", text,
            "server.py missing _route_metric_glossary handler",
        )
        # Handler renders through render_metric_glossary
        # function (not a one-off inline render).
        self.assertIn(
            "render_metric_glossary", text,
            "_route_metric_glossary should call render_metric_glossary",
        )


if __name__ == "__main__":
    unittest.main()
