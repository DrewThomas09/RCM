"""Tools card-grid index — COMPLETENESS contract + render guards.

The product promise for /tools: the Full A–Z view must contain EVERY route the
app serves, each as a card that links there. No ghost pages. These tests pin
that so a newly-shipped route can never silently fall off the index — and so a
regression in bucketing/dedup is caught immediately. They test the data
assembly (RCMHandler._build_tools_index_data, a classmethod) and the rendered
HTML (rcm_mc.ui.tools_index_page.render_tools_index).
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.server import RCMHandler
from rcm_mc.ui.tools_index_page import render_tools_index, TIER_TO_STATUS


def _data():
    return RCMHandler._build_tools_index_data()


def _routes_in(sections):
    return [t["path"] for sec in sections for t in sec["tools"]]


class CompletenessContract(unittest.TestCase):
    def test_every_discovered_route_is_a_card_in_the_az(self):
        ws, index, _, _ = _data()
        discovered = set(RCMHandler._discover_all_routes())
        az_routes = set(_routes_in(index))
        missing = discovered - az_routes
        self.assertEqual(missing, set(),
                         f"ghost pages missing from the A–Z tools index: "
                         f"{sorted(missing)}")

    def test_every_discovered_route_is_in_a_workspace_card_too(self):
        ws, index, _, _ = _data()
        discovered = set(RCMHandler._discover_all_routes())
        ws_routes = set(_routes_in(ws))
        missing = discovered - ws_routes
        self.assertEqual(missing, set(),
                         f"routes missing from the workspace view: "
                         f"{sorted(missing)}")

    def test_no_duplicate_cards_within_a_view(self):
        ws, index, _, _ = _data()
        for name, secs in (("A–Z", index), ("workspace", ws)):
            routes = _routes_in(secs)
            dupes = {r for r in routes if routes.count(r) > 1}
            self.assertEqual(dupes, set(), f"{name}: duplicate cards {dupes}")

    def test_rendered_az_html_has_a_card_per_route(self):
        # End-to-end: the actual HTML carries one card (href) per discovered
        # route in the A–Z view region — not just the data structure.
        ws, index, tw, ti = _data()
        html = render_tools_index(workspaces=ws, index=index,
                                  total_ws=tw, total_idx=ti)
        idx_pos = html.find('data-view="index"')
        self.assertGreater(idx_pos, 0, "no A–Z view rendered")
        az_html = html[idx_pos:]
        carded = set(re.findall(r'class="ti-card" href="([^"]+)"', az_html))
        discovered = set(RCMHandler._discover_all_routes())
        missing = discovered - carded
        self.assertEqual(missing, set(),
                         f"routes discovered but not rendered as A–Z cards: "
                         f"{sorted(missing)}")

    def test_total_idx_count_matches_route_universe(self):
        ws, index, tw, ti = _data()
        self.assertEqual(ti, len(_routes_in(index)))
        # A–Z covers at least every discovered route (may add a few curated
        # palette-only routes like /my/AT).
        self.assertGreaterEqual(ti, len(RCMHandler._discover_all_routes()))


class NoDuplicates(unittest.TestCase):
    def test_no_duplicate_card_labels_in_either_view(self):
        # Two cards must never read identically — distinct pages get distinct
        # names (de-collision); true redirect aliases are merged away.
        from collections import Counter
        ws, index, _, _ = _data()
        for view_name, secs in (("A–Z", index), ("workspace", ws)):
            names = [t["name"] for sec in secs for t in sec["tools"]]
            dupes = {n for n, c in Counter(x.lower() for x in names).items()
                     if c > 1}
            self.assertEqual(dupes, set(),
                             f"{view_name}: duplicate card labels {dupes}")

    def test_redirect_aliases_are_safe_merged_not_carded(self):
        # Pure "renamed →" redirects shouldn't appear as their own card — the
        # canonical target is the real card. (Hidden at discovery.)
        ws, index, _, _ = _data()
        az = {t["path"] for sec in index for t in sec["tools"]}
        for alias, canonical in (("/portfolio-analytics", "/deal-corpus-analytics"),
                                 ("/deals-library", "/library")):
            self.assertNotIn(alias, az, f"{alias} is a redirect — should merge")
            self.assertIn(canonical, az, f"canonical {canonical} missing")

    def test_no_query_param_variants_as_cards(self):
        # A ?param variant of a base route is not its own card.
        ws, index, _, _ = _data()
        for sec in index:
            for t in sec["tools"]:
                self.assertNotIn("?", t["path"], f"query variant carded: {t['path']}")


class StatusBuckets(unittest.TestCase):
    def test_every_card_has_a_valid_status(self):
        ws, index, _, _ = _data()
        valid = set(TIER_TO_STATUS.values())
        for sec in index:
            for t in sec["tools"]:
                self.assertIn(t["status"], valid,
                              f"{t['path']} has bad status {t['status']}")

    def test_status_reflects_real_surface_tier(self):
        # Honest mapping: a known real-data route reads 'live', a known
        # illustrative seed-corpus route reads 'illustrative' — never inverted.
        from rcm_mc.diligence.surface_status import classify_surface
        ws, index, _, _ = _data()
        by_route = {t["path"]: t["status"]
                    for sec in index for t in sec["tools"]}
        for route, status in by_route.items():
            tier = (classify_surface(route) or {}).get("tier") or "green"
            self.assertEqual(status, TIER_TO_STATUS.get(tier, "live"),
                             f"{route}: status {status} != tier {tier} mapping")


class RenderStructure(unittest.TestCase):
    def setUp(self):
        ws, index, tw, ti = _data()
        self.html = render_tools_index(workspaces=ws, index=index,
                                       total_ws=tw, total_idx=ti)

    def test_has_chrome_masthead_legend_and_both_views(self):
        for marker in ("ti-controls", "data-ti-search", "ti-mast",
                       "ti-legend", "data-status-chip",
                       'data-view="workspace"', 'data-view="index"',
                       "mode-index", "__TI_META__"):
            self.assertIn(marker, self.html, marker)

    def test_legend_has_all_four_status_filters(self):
        for sid in ("live", "computed", "needs", "illustrative"):
            self.assertIn(f'data-status-chip="{sid}"', self.html)

    def test_cards_carry_search_and_route_attrs(self):
        # The client filter needs data-search + data-status; tests need data-route.
        self.assertIn("data-search=", self.html)
        self.assertIn("data-status=", self.html)
        self.assertIn("data-route=", self.html)


if __name__ == "__main__":
    unittest.main()
