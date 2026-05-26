"""Nav bars lead with their top-6 ranked surfaces + a 'More →' to the ranked
/best/<section> index (Phase 2B of the front-facing revamp)."""
from __future__ import annotations

import unittest


class RankedRailTests(unittest.TestCase):
    def test_caps_at_six_and_flags_more(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        # research has 11 curated entries (5 strong, 6 yellow) → the bar shows
        # only the strong ones (gate), ≤6, and flags more (the rest live in
        # the ranked /best index).
        top, more = _ranked_subnav_items("research")
        self.assertLessEqual(len(top), 6)
        self.assertGreaterEqual(len(top), 1)
        self.assertTrue(more)
        # diligence has 6 strong → a full bar of 6.
        dtop, _ = _ranked_subnav_items("diligence")
        self.assertEqual(len(dtop), 6)

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

    def test_front_facing_gate_no_weak_tiers_in_bars(self):
        # "Front facing shows evidence of good things": no illustrative (yellow)
        # or placeholder (red) surface leads a nav bar — they're demoted to the
        # ranked /best index (shown there with an honest tier dot).
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items, _SUB_NAV
        from rcm_mc.diligence.surface_status import classify_surface
        for sec in _SUB_NAV:
            top, _ = _ranked_subnav_items(sec)
            for s in top:
                tier = classify_surface(s["href"]).get("tier")
                self.assertNotIn(tier, ("red", "yellow"),
                                 f"{sec}: weak surface {s['href']} ({tier}) in bar")

    def test_bars_never_empty(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items, _SUB_NAV
        for sec in _SUB_NAV:
            top, _ = _ranked_subnav_items(sec)
            self.assertGreaterEqual(len(top), 1, sec)


if __name__ == "__main__":
    unittest.main()
