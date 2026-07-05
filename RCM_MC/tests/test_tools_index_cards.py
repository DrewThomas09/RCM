"""Tools card-grid index — COMPLETENESS contract + render guards.

The product promise for /tools: the single workspace-grouped grid must
contain EVERY route the app serves, each exactly once, as a card that
links there. No ghost pages, no duplicates. These tests pin that so a
newly-shipped route can never silently fall off the index — and so a
regression in bucketing/dedup is caught immediately. They test the data
assembly (RCMHandler._build_tools_index_data, a classmethod) and the
rendered HTML (rcm_mc.ui.tools_index_page.render_tools_index).
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
    def test_every_discovered_route_is_a_card(self):
        ws, _ = _data()
        discovered = set(RCMHandler._discover_all_routes())
        carded = set(_routes_in(ws))
        missing = discovered - carded
        self.assertEqual(missing, set(),
                         f"ghost pages missing from the tools index: "
                         f"{sorted(missing)}")

    def test_no_duplicate_cards(self):
        ws, _ = _data()
        routes = _routes_in(ws)
        dupes = {r for r in routes if routes.count(r) > 1}
        self.assertEqual(dupes, set(), f"duplicate cards {dupes}")

    def test_rendered_html_has_exactly_one_card_per_route(self):
        # End-to-end: the actual HTML carries exactly one card (data-route)
        # per route — the old two-view design rendered every card twice.
        ws, total = _data()
        html = render_tools_index(workspaces=ws, total=total)
        # Scope to actual grid cards — the shell's Cmd-K palette also
        # carries data-route attributes.
        carded = re.findall(r'class="ti-card" href="[^"]*"[^>]*'
                            r'data-route="([^"]+)"', html)
        self.assertEqual(sorted(set(carded)), sorted(carded),
                         "a route renders as more than one card")
        discovered = set(RCMHandler._discover_all_routes())
        missing = discovered - set(carded)
        self.assertEqual(missing, set(),
                         f"routes discovered but not rendered as cards: "
                         f"{sorted(missing)}")

    def test_total_matches_route_universe(self):
        ws, total = _data()
        self.assertEqual(total, len(_routes_in(ws)))
        # The grid covers at least every discovered route (plus a few
        # curated palette-only routes like /my/AT).
        self.assertGreaterEqual(total, len(RCMHandler._discover_all_routes()))


class NoDuplicates(unittest.TestCase):
    def test_no_duplicate_card_labels(self):
        # Two cards must never read identically — distinct pages get distinct
        # names (de-collision); true redirect aliases are merged away.
        from collections import Counter
        ws, _ = _data()
        names = [t["name"] for sec in ws for t in sec["tools"]]
        dupes = {n for n, c in Counter(x.lower() for x in names).items()
                 if c > 1}
        self.assertEqual(dupes, set(), f"duplicate card labels {dupes}")

    def test_redirect_aliases_are_safe_merged_not_carded(self):
        # Pure "renamed →" redirects shouldn't appear as their own card — the
        # canonical target is the real card. (Hidden at discovery.)
        ws, _ = _data()
        az = set(_routes_in(ws))
        for alias, canonical in (("/portfolio-analytics", "/deal-corpus-analytics"),
                                 ("/deals-library", "/library")):
            self.assertNotIn(alias, az, f"{alias} is a redirect — should merge")
            self.assertIn(canonical, az, f"canonical {canonical} missing")

    def test_no_query_param_variants_as_cards(self):
        ws, _ = _data()
        for sec in ws:
            for t in sec["tools"]:
                self.assertNotIn("?", t["path"], f"query variant carded: {t['path']}")


class NoDeadCards(unittest.TestCase):
    def test_known_parametric_and_redirect_routes_are_not_carded(self):
        # Fast guard: routes that 404 on a bare GET (parametric — need a
        # deal/section sub-path) or redirect (renamed) must not be cards.
        ws, _ = _data()
        az = set(_routes_in(ws))
        for dead in ("/models/causal", "/models/lbo", "/best", "/hold",
                     "/data-room", "/diligence/synthesis", "/ic-memo",
                     "/screening", "/outputs", "/deals", "/audit/enter"):
            self.assertNotIn(dead, az, f"dead/parametric route carded: {dead}")

    def test_internal_build_pages_are_not_carded(self):
        # /v3-status and /v5-status (internal migration dashboards) were
        # removed 2026-07-05 — they read as build notes on the tools grid.
        ws, _ = _data()
        az = set(_routes_in(ws))
        for internal in ("/v3-status", "/v5-status"):
            self.assertNotIn(internal, az, f"internal page carded: {internal}")

    def test_feature_scoped_api_endpoints_are_not_carded(self):
        # Any "/api/" path segment is a JSON/POST endpoint, not a page —
        # /npi-cleaner/api/* carded as dead tiles when #1906 landed.
        ws, _ = _data()
        for sec in ws:
            for t in sec["tools"]:
                self.assertNotIn("/api/", t["path"],
                                 f"API endpoint carded: {t['path']}")

    def test_every_card_returns_200(self):
        # The definitive health contract: boot a real server and GET every
        # card. None may 404/redirect/500 — a card that doesn't render is
        # worse than no card. (Empty temp DB; well-built pages show an empty
        # state.)
        import os, socket, tempfile, threading, time
        import urllib.error as _ue
        import urllib.request as _u
        from rcm_mc.server import build_server

        ws, _ = _data()
        routes = _routes_in(ws)

        class _NoRedirect(_u.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = _u.build_opener(_NoRedirect)

        sk = socket.socket(); sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]; sk.close()
        tmp = tempfile.mkdtemp()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); time.sleep(0.3)
        bad = {}
        try:
            for r in routes:
                try:
                    code = opener.open(
                        _u.Request(f"http://127.0.0.1:{port}{r}"), timeout=20
                    ).status
                    if code != 200:
                        bad[r] = code
                except _ue.HTTPError as e:
                    bad[r] = e.code
                except Exception as e:  # noqa: BLE001
                    bad[r] = f"ERR:{type(e).__name__}"
        finally:
            server.shutdown(); server.server_close()
        self.assertEqual(bad, {}, f"cards that do not render 200: {bad}")


class StatusBuckets(unittest.TestCase):
    def test_every_card_has_a_valid_status(self):
        ws, _ = _data()
        valid = set(TIER_TO_STATUS.values())
        for sec in ws:
            for t in sec["tools"]:
                self.assertIn(t["status"], valid,
                              f"{t['path']} has bad status {t['status']}")

    def test_status_reflects_real_surface_tier(self):
        # Honest mapping: a known real-data route reads 'live', a known
        # illustrative seed-corpus route reads 'illustrative' — never inverted.
        from rcm_mc.diligence.surface_status import classify_surface
        ws, _ = _data()
        by_route = {t["path"]: t["status"]
                    for sec in ws for t in sec["tools"]}
        for route, status in by_route.items():
            tier = (classify_surface(route) or {}).get("tier") or "green"
            self.assertEqual(status, TIER_TO_STATUS.get(tier, "live"),
                             f"{route}: status {status} != tier {tier} mapping")


class RenderStructure(unittest.TestCase):
    def setUp(self):
        ws, total = _data()
        self.ws = ws
        self.html = render_tools_index(workspaces=ws, total=total)

    def test_has_chrome_masthead_legend_and_grid(self):
        for marker in ("ti-controls", "data-ti-search", "ti-mast",
                       "ti-legend", "data-status-chip", "data-ti-main",
                       "__TI_META__"):
            self.assertIn(marker, self.html, marker)

    def test_legend_has_all_four_status_filters(self):
        for sid in ("live", "computed", "needs", "illustrative"):
            self.assertIn(f'data-status-chip="{sid}"', self.html)

    def test_cards_carry_search_and_route_attrs(self):
        # The client filter needs data-search + data-status; tests need data-route.
        self.assertIn("data-search=", self.html)
        self.assertIn("data-status=", self.html)
        self.assertIn("data-route=", self.html)

    def test_density_toggle_renders(self):
        self.assertIn('data-density-btn="detailed"', self.html)
        self.assertIn('data-density-btn="compact"', self.html)
        # detailed is the default: main has no compact class
        self.assertNotIn('class="ti-main mode-compact"', self.html)

    def test_jump_rail_links_every_section(self):
        rails = re.findall(r'<nav class="ti-jump"', self.html)
        self.assertEqual(len(rails), 1)
        for sec in self.ws:
            self.assertIn(f'href="#ws-{sec["id"]}"', self.html)


class DeepLinkDensity(unittest.TestCase):
    def test_compact_deep_link_renders_compact(self):
        # /tools?view=compact (legacy ?view=all) lands on the compact
        # density server-side.
        ws, total = _data()
        html = render_tools_index(workspaces=ws, total=total,
                                  initial_view="compact")
        self.assertIn('data-mode="compact"', html)
        self.assertIn('class="ti-main mode-compact"', html)

    def test_legacy_view_all_maps_to_compact(self):
        ws, total = _data()
        html = render_tools_index(workspaces=ws, total=total,
                                  initial_view="all")
        self.assertIn('data-mode="compact"', html)

    def test_bogus_initial_view_falls_back_to_detailed(self):
        ws, total = _data()
        html = render_tools_index(workspaces=ws, total=total,
                                  initial_view="nonsense")
        self.assertIn('data-mode="detailed"', html)


if __name__ == "__main__":
    unittest.main()
