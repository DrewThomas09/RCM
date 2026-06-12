"""Visuals hub — the graphics-toolkit landing page.

Tests pin the card grid (one per tool, with a live thumbnail + link)
and the route/nav/guide wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.visuals_hub_page import render_visuals_hub_page


class VisualsHubTests(unittest.TestCase):
    def test_renders_a_card_per_tool_with_links(self):
        h = render_visuals_hub_page()
        for tool, href in (("Chart Builder", "/chart-builder"),
                           ("Pie Chart", "/pie-chart"),
                           ("Excel Mapping", "/excel-mapping"),
                           ("Exhibit Composer", "/exhibit")):
            self.assertIn(tool, h, tool)
            self.assertIn(f'href="{href}"', h, href)

    def test_thumbnails_render_real_svgs(self):
        h = render_visuals_hub_page()
        # At least one thumbnail SVG per tool card (4) + page chrome.
        self.assertGreaterEqual(h.count("<svg"), 4)
        self.assertNotIn("None", h.split("<body")[-1]
                         if "<body" in h else h)

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/visuals", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/visuals"), "research")
        self.assertIsNotNone(
            build_guide_context_packet("/visuals").page_context)


if __name__ == "__main__":
    unittest.main()
