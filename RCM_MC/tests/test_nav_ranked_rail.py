"""Nav bars lead with their top-6 ranked surfaces + a 'More →' to the ranked
/best/<section> index (Phase 2B of the front-facing revamp)."""
from __future__ import annotations

import unittest


class RankedRailTests(unittest.TestCase):
    def test_caps_at_six_and_flags_more(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        # research has 11 curated entries → capped to 6 + has_more.
        top, more = _ranked_subnav_items("research")
        self.assertEqual(len(top), 6)
        self.assertTrue(more)

    def test_orders_by_ranking_score(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        from rcm_mc.ui._surface_rankings import RANKINGS
        top, _ = _ranked_subnav_items("source")
        score = {r["route"]: r["total"] for r in RANKINGS.get("source", [])}
        totals = [score.get(s["href"], 0.0) for s in top]
        self.assertEqual(totals, sorted(totals, reverse=True))
        # Target Screener (highest) leads the Source rail.
        self.assertEqual(top[0]["href"], "/target-screener")

    def test_every_core_section_dropdown_has_more_link(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        for sec in ("source", "pipeline", "diligence", "portfolio",
                    "research", "library"):
            h = chartis_shell("<p>x</p>", "T", active_nav="/" + sec)
            self.assertIn(f"/best/{sec}", h, sec)

    def test_short_section_not_padded(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        # portfolio has 4 curated entries → all shown, no fabrication.
        top, _ = _ranked_subnav_items("portfolio")
        self.assertEqual(len(top), 4)


if __name__ == "__main__":
    unittest.main()
