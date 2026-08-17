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
                      "links": [{"href": "/diligence/hcris-xray",
                                 "label": "HCRIS X-Ray", "blurb": "j"}]}],
            explainer_head="h", explainer_body="b", explainer_source="s",
            intro_headline="hi", intro_body="bod")
        self.assertIn("Group A", h)
        self.assertIn("HCRIS X-Ray", h)
        self.assertIn("sc-dot", h)        # honesty dot rendered
        self.assertIn("Live data", h)     # legend present

    def test_tier_reflects_surface_status(self):
        # The dot is derived from surface_status, so it can't drift from truth.
        self.assertEqual(_tier("/diligence/hcris-xray"), "green")
        self.assertEqual(_tier("/diligence/management"), "yellow")  # illustrative

    def test_meta_shows_computed_honesty_coverage(self):
        # The catalog header summarises the section's per-tier coverage —
        # counted from surface_status, not hand-set.
        #
        # This used to pin a literal "1 live / 1 illustrative" by feeding
        # the fixture one green route and one yellow one. Three successive
        # picks for the yellow slot (/diligence/management, then
        # /diligence/compare, then /predictive-screener) were each hidden
        # by the next sweep, and as of the 2026-08-17 sweeps NO visible
        # surface classifies yellow any more — which is the point of the
        # sweeps, not a gap in the test. So the expectation is derived:
        # whatever tiers the surviving links carry must be counted and
        # named in the meta line.
        from collections import Counter
        routes = ["/diligence/hcris-xray", "/diligence/xray",
                  "/verticals"]
        h = render_grouped_catalog(
            section="diligence", title="T", eyebrow="X",
            pillars=[{"title": "G", "eyebrow": "E", "body": "b", "links": [
                {"href": r, "label": r, "blurb": "j"} for r in routes]}],
            explainer_head="h", explainer_body="b", explainer_source="s",
            intro_headline="hi", intro_body="bod")
        # 2026-05-28 style-sweep · the meta-line renders mono uppercase
        # per Tier-2 §2.2, so compare case-insensitively.
        label = {"green": "live", "navy": "computed",
                 "data_required": "needs data", "yellow": "illustrative",
                 "red": "placeholder"}
        counts = Counter(_tier(r) for r in routes)
        self.assertTrue(counts, "fixture produced no tiers")
        for tier, n in counts.items():
            self.assertIn(f"{n} {label[tier]}", h.lower(),
                          f"meta line omits the {tier} count")


class DiligenceLandingTests(unittest.TestCase):
    def test_uses_shared_renderer_with_dots(self):
        # Pillar titles track the 2026-08-16 reframe: /diligence is the
        # CMS filing-read section now, so "Profile & Health" / "Audit &
        # Stress" gave way to "The X-Rays" / "Regulatory & Outcomes". The
        # honesty dots + legend are the durable contract.
        h = render_diligence_index()
        self.assertIn("The X-Rays", h)              # pillar
        self.assertIn("Regulatory &amp; Outcomes", h)
        self.assertIn("sc-dot", h)                  # honesty dots
        self.assertIn("Illustrative", h)            # legend

    def test_management_is_not_offered_at_all(self):
        # The named honesty bug was that management READ AS LIVE on
        # /diligence when its figures are illustrative. The ruling since
        # went further: illustrative-figure surfaces are registry-hidden,
        # so it isn't listed here at all. The legend keeps its illustrative
        # swatch regardless of what the page currently lists, so a reader
        # can still tell a computed row from a live one the moment an
        # illustrative surface earns its way back onto the catalog.
        h = render_diligence_index()
        self.assertNotIn('href="/diligence/management"', h)
        self.assertIn("#c9a227", h)   # an illustrative (yellow) dot is present

    def test_catalog_covers_every_served_diligence_route(self):
        # "Add all the diligence layers" — every /diligence/* route the server
        # serves must appear in the catalog, so nothing is orphaned.
        import re
        import pathlib
        from rcm_mc.ui.diligence_index_page import _PILLARS
        in_catalog = {l["href"].split("?")[0]
                      for p in _PILLARS for l in p["links"]}
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        served = set(re.findall(r'"(/diligence/[a-z0-9\-]+)"', src))
        missing = served - in_catalog
        self.assertEqual(missing, set(), f"diligence routes not in catalog: {missing}")


if __name__ == "__main__":
    unittest.main()
