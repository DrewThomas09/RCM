"""Every section has a /diligence-style grouped catalog landing.

Guards that Source / Pipeline / Library / Research / Portfolio each render the
shared grouped catalog (pillars + one-liners + honesty dots) at /best/<section>,
that the nav lands there, and that the old standalone ranked list is retired.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.section_landings import render_section_landing, _SECTIONS


class SectionLandingTests(unittest.TestCase):
    def test_every_curated_section_renders_as_a_catalog(self):
        # Was "all five" including portfolio; the Portfolio tab and its
        # curated pillars were dropped in the 2026-08-17 bloat sweep.
        # Driven off _SECTIONS so the next structural change updates it.
        for sec in _SECTIONS:
            h = render_section_landing(sec)
            self.assertIsNotNone(h, sec)
            self.assertIn("sc-pillar-title", h, sec)   # grouped pillars
            self.assertIn("sc-dot", h, sec)            # honesty dots
            self.assertIn("Live data", h, sec)         # legend

    def test_curated_real_routes(self):
        # Pillars reference real, sensible routes (spot-check the
        # flagships). Asserted against the curated pillar data rather
        # than the rendered HTML — the shell's nav rails mention most of
        # these routes on every page, so an `assertIn` over the markup
        # passes even when the pillar is gone. The portfolio and
        # /rcm-benchmarks spot-checks went with the bloat sweep: the
        # section no longer exists and the benchmark bands are hidden.
        def hrefs(section):
            return {link["href"]
                    for pillar in _SECTIONS[section]["pillars"]
                    for link in pillar["links"]}

        self.assertIn("/target-screener", hrefs("source"))
        self.assertIn("/geo-intel", hrefs("source"))
        self.assertIn("/pipeline", hrefs("pipeline"))
        self.assertIn("/cms-sources", hrefs("library"))
        self.assertIn("/nursing-homes", hrefs("research"))

    def test_no_ranking_score_leaks(self):
        for sec in _SECTIONS:
            h = render_section_landing(sec)
            self.assertNotRegex(h, r"\d\.\d/10")
            self.assertNotIn("scored by usefulness", h)

    def test_unknown_section_without_rows_is_none(self):
        self.assertIsNone(render_section_landing("not-a-section"))

    def test_nav_points_sections_to_catalogs(self):
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV
        href = {n["key"]: n["href"] for n in _CORPUS_NAV}
        self.assertEqual(href["source"], "/best/source")
        self.assertEqual(href["library"], "/best/library")
        self.assertEqual(href["diligence"], "/diligence")  # keeps its own
        # The Portfolio tab was dropped in the bloat sweep.
        self.assertNotIn("portfolio", href)


if __name__ == "__main__":
    unittest.main()
