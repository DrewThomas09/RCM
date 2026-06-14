"""Nav bars lead with the hand-curated flagship pins (_NAV_FLAGSHIPS), then
ranked backfill, + a 'More →' to the ranked /best/<section> index. The front
face is a product decision: the highest-functionality workbenches lead, and
utility renderers (_NAV_DEMOTED) never front-face."""
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

    def test_short_section_backfilled_with_real_navigable_routes_only(self):
        # A short section is backfilled from the curated rail toward a fuller
        # bar, but ONLY with routes that are BOTH real-tier (green/navy/
        # data_required — never illustrative/synthetic) AND navigable bare-GET
        # pages (no form-POST/redirect targets). Pipeline honestly has 3 such
        # pages (a 4th would require a dead link or an illustrative page — both
        # worse than a 3-leaf bar); portfolio has 6. So: populated (>=3),
        # capped (<=6), all real, none in the non-navigable set.
        from rcm_mc.ui._chartis_kit import (
            _ranked_subnav_items, _NAV_NONNAVIGABLE,
        )
        from rcm_mc.diligence.surface_status import classify_surface
        for sec in ("pipeline", "portfolio"):
            top, _ = _ranked_subnav_items(sec)
            self.assertGreaterEqual(len(top), 3, f"{sec} bar too sparse: {top}")
            self.assertLessEqual(len(top), 6, sec)
            for s in top:
                tier = classify_surface(s["href"]).get("tier")
                self.assertIn(tier, ("green", "navy", "data_required"),
                              f"{sec}: padded with non-real {s['href']} ({tier})")
                self.assertNotIn(s["href"], _NAV_NONNAVIGABLE,
                                 f"{sec}: non-navigable leaf {s['href']}")

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

    def test_pinned_hcris_xray_in_diligence_dropdown(self):
        # /diligence/hcris-xray is a flagship product decision (_NAV_FLAGSHIPS):
        # the renderer is thin (engine lives in diligence/hcris_xray/) so the
        # LOC-proxied ranking buries it below the 6-leaf cut, but partners
        # reach for it by name from the Diligence dropdown. Flagship pins lead
        # the bar in workflow order (not score order); the bar stays capped at 6.
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        top, _ = _ranked_subnav_items("diligence")
        hrefs = [s["href"] for s in top]
        self.assertIn("/diligence/hcris-xray", hrefs)
        self.assertEqual(len(top), 6)

    def test_pinned_hcris_xray_renders_in_shell_megamenu(self):
        # The pin must survive all the way into the rendered topbar markup
        # (the mega-menu leaf), not just the helper's return value.
        from rcm_mc.ui._chartis_kit import chartis_shell
        h = chartis_shell("<p>x</p>", "T", active_nav="/diligence")
        self.assertIn('href="/diligence/hcris-xray" class="ck-mega-item"', h)

    def test_bars_never_empty(self):
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items, _SUB_NAV
        for sec in _SUB_NAV:
            top, _ = _ranked_subnav_items(sec)
            self.assertGreaterEqual(len(top), 1, sec)

    def test_diligence_bar_leads_with_flagship_workbenches(self):
        # The front face is the analyst playbook in workflow order — identity
        # → ingest → baseline → X-Ray drill-downs → IC deliverable — not the
        # LOC-score order (which front-faced the niche TX Infusion Market and
        # buried HCRIS X-Ray at #19).
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        top, _ = _ranked_subnav_items("diligence")
        self.assertEqual([s["href"] for s in top], [
            "/diligence/deal", "/diligence/ingest", "/diligence/benchmarks",
            "/diligence/xray", "/diligence/hcris-xray", "/diligence/ic-packet",
        ])

    def test_flagship_pins_lead_every_pinned_section(self):
        # Pins that pass the tier gate render first, in pinned order.
        from rcm_mc.ui._chartis_kit import (
            _NAV_FLAGSHIPS, _ranked_subnav_items,
        )
        from rcm_mc.diligence.surface_status import classify_surface
        for sec, pins in _NAV_FLAGSHIPS.items():
            real = [p for p in pins if classify_surface(p).get("tier")
                    in ("green", "navy", "data_required")][:6]
            top, _ = _ranked_subnav_items(sec)
            self.assertEqual([s["href"] for s in top[:len(real)]], real, sec)

    def test_utility_renderers_never_front_face(self):
        # Chart/export utilities (Excel Mapping et al.) are real pages but
        # tools, not analyses — they live in /best/<section>, never the bar.
        from rcm_mc.ui._chartis_kit import (
            _NAV_DEMOTED, _SUB_NAV, _ranked_subnav_items,
        )
        for sec in _SUB_NAV:
            top, _ = _ranked_subnav_items(sec)
            for s in top:
                self.assertNotIn(s["href"], _NAV_DEMOTED, sec)
        research = [s["href"] for s in _ranked_subnav_items("research")[0]]
        self.assertNotIn("/excel-mapping", research)


if __name__ == "__main__":
    unittest.main()
