"""Test for the 4A metric→glossary link wrapping in
ui/ebitda_bridge_page.py (campaign target 4A, loop 106).

Phase 4A of the v3 transformation campaign requires that every
page mentioning a metric link to ``/metric-glossary#<key>``.
This loop wraps the 6 lever labels in the EBITDA bridge page
(denial_rate, days_in_ar, net_collection_rate, clean_claim_rate,
cost_to_collect, cmi → case_mix_index) in anchor links to the
canonical glossary destination shipped in loop 104.

Asserts:
  - The new _lever_label_link helper produces a real anchor for
    every key in _LEVER_CONFIG, with correct destination
    (cmi → /metric-glossary#case_mix_index, others 1:1).
  - Unknown metric keys fall through to plain escaped text
    (no dead links shipped).
  - Each of the 4 render sites in render_ebitda_bridge has been
    converted from `_html.escape(lev["name"])` to
    `_lever_label_link(lev["name"], lev.get("metric", ""))` —
    i.e. all 6 lever metrics appear as glossary anchors in the
    rendered HTML.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.ui.ebitda_bridge_page import (
    _LEVER_CONFIG,
    _LEVER_METRIC_TO_GLOSSARY,
    _lever_label_link,
)
from rcm_mc.ui.metric_glossary import get_metric_definition


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "rcm_mc" / "ui" / "ebitda_bridge_page.py"
)


class EbitdaBridgeGlossaryLinksTests(unittest.TestCase):
    def test_every_lever_metric_resolves_to_glossary_entry(self) -> None:
        """Every metric_key referenced in _LEVER_CONFIG must
        either appear directly in the glossary or be mapped
        via _LEVER_METRIC_TO_GLOSSARY to a glossary key."""
        for cfg in _LEVER_CONFIG:
            metric = cfg["metric"]
            with self.subTest(metric=metric):
                resolved = _LEVER_METRIC_TO_GLOSSARY.get(
                    metric, metric)
                self.assertIsNotNone(
                    get_metric_definition(resolved),
                    f"lever metric {metric!r} (resolved={resolved!r}) "
                    f"is not in the metric glossary — link will be a 404",
                )

    def test_helper_wraps_known_metric_in_anchor(self) -> None:
        html = _lever_label_link("Denial Rate", "denial_rate")
        self.assertIn('href="/metric-glossary#denial_rate"', html)
        self.assertIn("Denial Rate", html)

    def test_helper_resolves_cmi_alias(self) -> None:
        """The bridge uses the short key `cmi`; the glossary
        key is `case_mix_index`. The mapping in
        _LEVER_METRIC_TO_GLOSSARY must resolve correctly."""
        html = _lever_label_link("CDI / Case Mix Index", "cmi")
        self.assertIn('href="/metric-glossary#case_mix_index"', html)
        self.assertNotIn("#cmi", html)

    def test_helper_falls_through_on_unknown_key(self) -> None:
        """Unknown metric keys produce plain escaped text, not
        a dead anchor — better to render the label without a
        link than ship a broken /metric-glossary#<unknown>."""
        html = _lever_label_link("Mystery Lever", "no_such_metric")
        self.assertNotIn("<a", html)
        self.assertNotIn("href", html)
        self.assertIn("Mystery Lever", html)

    def test_render_sites_use_lever_label_link(self) -> None:
        """The 4 render sites in render_ebitda_bridge that used
        to interpolate `_html.escape(lev["name"])` should now
        call `_lever_label_link(lev["name"], lev.get("metric",
        ""))`. File-grep guard: there should be no remaining
        `_html.escape(lev["name"]` patterns in the module
        (only the helper-routed form)."""
        text = _MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            '_html.escape(lev["name"])', text,
            "ebitda_bridge_page.py still has un-linked "
            '_html.escape(lev["name"]) — Phase 4A regressed',
        )
        self.assertNotIn(
            '_html.escape(lev["name"][:20])', text,
            "ebitda_bridge_page.py still has un-linked "
            'truncated _html.escape(lev["name"][:20])',
        )
        # Positive: the helper is referenced ≥4 times (once per
        # render site).
        ref_count = len(re.findall(r"_lever_label_link\(", text))
        self.assertGreaterEqual(
            ref_count, 4,
            f"_lever_label_link should be called ≥4 times in "
            f"render_ebitda_bridge (one per lever-name render "
            f"site); found {ref_count}",
        )


if __name__ == "__main__":
    unittest.main()
