"""The /tools showcase — curated default (top-6 + diligence spotlight) with the
full index demoted to ?view=all.

Guards the "don't overwhelm, lead with the best" redesign: the showcase shows a
bounded set of top-ranked, front-facing surfaces and always offers a path to
the full index; the full index stays reachable and links back.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.tools_showcase_page import render_tools_showcase, _gated_sorted
from rcm_mc.ui._surface_rankings import RANKINGS


class ShowcaseTests(unittest.TestCase):
    def test_renders_bounded_hero(self):
        h = render_tools_showcase(355)
        # exactly the top 6 hero cards (anchor count, not CSS class defs)
        self.assertEqual(h.count('class="tsh-card"'), 6)

    def test_hero_is_top_ranked_front_facing(self):
        h = render_tools_showcase(355)
        # The overall #1 (Target Screener) must lead.
        self.assertIn("/target-screener", h)
        # No illustrative/placeholder tiers leak into the showcase.
        weak = [r for sec in RANKINGS.values() for r in sec
                if r.get("tier") in ("yellow", "red")]
        # Pick a weak route (if any) and assert it's not a hero card link.
        for r in weak[:20]:
            self.assertNotIn(f'class="tsh-card" href="{r["route"]}"', h)

    def test_spotlights_diligence(self):
        h = render_tools_showcase(355)
        self.assertIn("Top diligence layers", h)
        self.assertIn("/best/diligence", h)

    def test_always_offers_full_index(self):
        h = render_tools_showcase(355)
        self.assertIn("/tools?view=all", h)

    def test_gated_sort_descending_front_facing(self):
        rows = _gated_sorted(RANKINGS.get("diligence", []))
        totals = [r["total"] for r in rows]
        self.assertEqual(totals, sorted(totals, reverse=True))
        self.assertTrue(all(r["tier"] in ("green", "navy", "data_required")
                            for r in rows))

    def test_route_dispatches_both_views(self):
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        self.assertIn("render_tools_showcase", src)
        self.assertIn("_route_tools_index_full", src)
        self.assertIn('qs.get("view")', src)


if __name__ == "__main__":
    unittest.main()
