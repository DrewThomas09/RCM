"""Shared grouped section-catalog renderer + the Diligence landing that uses it.

Guards the gold-standard pattern the user picked: surfaces grouped into named
pillars with a one-line job each, and an honesty dot (live / computed /
illustrative) on every row so a partner is never misled about a surface's data.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.section_catalog_page import render_grouped_catalog, _tier
from rcm_mc.ui.diligence_index_page import render_diligence_index


class CatalogRendererTests(unittest.TestCase):
    def test_renders_pillars_and_links(self):
        h = render_grouped_catalog(
            section="diligence", title="Test", eyebrow="X",
            pillars=[{"title": "Group A", "eyebrow": "EY", "body": "b",
                      "links": [{"href": "/diligence/payer-stress",
                                 "label": "Payer Stress", "blurb": "j"}]}],
            explainer_head="h", explainer_body="b", explainer_source="s",
            intro_headline="hi", intro_body="bod")
        self.assertIn("Group A", h)
        self.assertIn("Payer Stress", h)
        self.assertIn("sc-dot", h)        # honesty dot rendered
        self.assertIn("Live data", h)     # legend present

    def test_tier_reflects_surface_status(self):
        # The dot is derived from surface_status, so it can't drift from truth.
        self.assertEqual(_tier("/diligence/payer-stress"), "green")
        self.assertEqual(_tier("/diligence/management"), "yellow")  # illustrative


class DiligenceLandingTests(unittest.TestCase):
    def test_uses_shared_renderer_with_dots(self):
        h = render_diligence_index()
        self.assertIn("Profile &amp; Health", h)   # pillar
        self.assertIn("Audit &amp; Stress", h)
        self.assertIn("sc-dot", h)                  # honesty dots
        self.assertIn("Illustrative", h)            # legend

    def test_management_shows_illustrative_not_live(self):
        # The named honesty bug: management must not read as live on /diligence.
        h = render_diligence_index()
        self.assertIn("/diligence/management", h)
        self.assertIn("#c9a227", h)   # an illustrative (yellow) dot is present


if __name__ == "__main__":
    unittest.main()
