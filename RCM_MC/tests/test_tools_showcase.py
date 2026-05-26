"""The /tools showcase — a clean, grouped, ranked catalogue (no scores, no
ranking methodology) with the raw index behind ?view=all.

Guards the "show everything in ranked order, don't explain the ranking"
redesign: tools appear ordered best-first, but the score and the methodology
are never surfaced to the user.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.tools_showcase_page import render_tools_showcase
from rcm_mc.ui._surface_rankings import RANKINGS


class ShowcaseTests(unittest.TestCase):
    def test_renders_workspace_sections(self):
        h = render_tools_showcase(355)
        for label in ("Diligence", "Source", "Pipeline", "Portfolio",
                      "Research", "Library"):
            self.assertIn(f">{label}</h2>", h)

    def test_shows_all_tools_in_a_section(self):
        # Every diligence tool in the manifest is listed (not just a top-6).
        h = render_tools_showcase(355)
        for r in RANKINGS.get("diligence", []):
            self.assertIn(r["route"], h)

    def test_ranked_order_best_first(self):
        # Within diligence, rows appear in descending ranking order even though
        # the score is hidden.
        h = render_tools_showcase(355)
        routes = re.findall(r'tx-row" href="([^"]+)"', h)
        dil = [r["route"] for r in
               sorted(RANKINGS.get("diligence", []),
                      key=lambda r: -r.get("total", 0.0))]
        seen = [r for r in routes if r in set(dil)]
        self.assertEqual(seen[:len(dil)], dil)

    def test_no_scores_or_methodology(self):
        h = render_tools_showcase(355)
        self.assertNotRegex(h, r"\d\.\d/10")          # no "9.6/10" badges
        self.assertNotIn("scored by usefulness", h)
        self.assertNotIn("rank_surfaces", h)
        self.assertNotIn("usefulness×1.5", h)
        self.assertNotIn("THE #1 SURFACE", h.upper())

    def test_offers_full_index(self):
        self.assertIn("/tools?view=all", render_tools_showcase(355))

    def test_honesty_dots_kept(self):
        # The data-honesty legend stays — that's labelling, not ranking.
        h = render_tools_showcase(355)
        self.assertIn("Live data", h)
        self.assertIn("Illustrative", h)


if __name__ == "__main__":
    unittest.main()
