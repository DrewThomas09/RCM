"""Every section has a /diligence-style grouped catalog landing.

Guards that Source / Pipeline / Library / Research / Portfolio each render the
shared grouped catalog (pillars + one-liners + honesty dots) at /best/<section>,
that the nav lands there, and that the old standalone ranked list is retired.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.section_landings import render_section_landing, _SECTIONS


class SectionLandingTests(unittest.TestCase):
    def test_all_five_sections_render_as_catalogs(self):
        for sec in ("source", "pipeline", "library", "research", "portfolio"):
            h = render_section_landing(sec)
            self.assertIsNotNone(h, sec)
            self.assertIn("sc-pillar-title", h, sec)   # grouped pillars
            self.assertIn("sc-dot", h, sec)            # honesty dots
            self.assertIn("Live data", h, sec)         # legend

    def test_curated_real_routes(self):
        # Pillars reference real, sensible routes (spot-check the flagships).
        self.assertIn("/target-screener", render_section_landing("source"))
        self.assertIn("/portfolio/regression", render_section_landing("portfolio"))
        self.assertIn("/rcm-benchmarks", render_section_landing("library"))

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
        self.assertEqual(href["portfolio"], "/best/portfolio")
        self.assertEqual(href["diligence"], "/diligence")  # keeps its own


if __name__ == "__main__":
    unittest.main()
