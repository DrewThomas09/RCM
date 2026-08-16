"""Hidden surfaces are listed nowhere — and deleted nowhere.

The product is a public-data verification and visualization surface: load a
CMS / Medicare / Medicaid / hospital dataset, see it charted, trace every
figure to its filing. Three classes of page work against that promise and
are ruled Hidden in ``rcm_mc.ui._surface_visibility``:

  * illustrative-figure pages (numbers from a hardcoded dataclass, not a
    filing),
  * single-target / single-market study suites (the Texas infusion scan,
    the IFT/MMT transport study) — real work, but legible only inside one
    engagement,
  * the sponsor-corpus / PE-narrative long tail.

Hidden is a BROWSE ruling, not a routing one. This module guards both
halves: nothing offers a hidden surface, and every hidden surface still
serves. The deal TRACKERS are explicitly not hidden — they track real,
publicly-reported transactions and stay listed.
"""
from __future__ import annotations

import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing

from rcm_mc.ui._surface_visibility import HIDDEN_ROUTES, is_hidden, is_visible


# A sample spanning all three rationales, plus their sub-routes.
HIDDEN_SAMPLE = (
    "/denovo-expansion",              # illustrative
    "/sponsor-track-record",          # illustrative / sponsor corpus
    "/diligence/texas-infusion",      # single-market study
    "/diligence/texas-infusion/workforce",   # …and its sub-routes
    "/diligence/texas-infusion/jcode-benchmark",
    "/ift",                           # single-target study suite
    "/ift-mmt",
    "/in-depth-ift-bls-als1-als2-cct",
    "/pe-intelligence",               # PE narrative
    "/bear-cases",
)

# What the cleanup must NOT touch: the public-data reads, the visualization
# tools, and the deal trackers.
VISIBLE_SAMPLE = (
    "/target-screener", "/diligence/hcris-xray", "/market-data",
    "/cms-data-browser", "/cms-sources", "/data", "/metric-glossary",
    "/methodology", "/regulatory-calendar", "/state-compare",
    "/county-explorer", "/geo-map", "/visuals", "/chart-builder",
    "/nursing-homes", "/home-health", "/hospice", "/dialysis",
    "/deal-library", "/deal-library/sponsors", "/verified-deals",
    "/news", "/pipeline", "/portfolio",
)


class RulingTests(unittest.TestCase):
    def test_hidden_sample_is_hidden(self):
        for route in HIDDEN_SAMPLE:
            self.assertTrue(is_hidden(route), route)
            self.assertFalse(is_visible(route), route)

    def test_keepers_stay_visible(self):
        for route in VISIBLE_SAMPLE:
            self.assertFalse(is_hidden(route), route)
            self.assertTrue(is_visible(route), route)

    def test_prefix_match_respects_route_boundaries(self):
        # "/ift" hides the study suite (/ift, /ift-mmt, /ift/x) without
        # swallowing an unrelated route that merely starts with the letters.
        self.assertTrue(is_hidden("/ift"))
        self.assertTrue(is_hidden("/ift-demand"))
        self.assertFalse(is_hidden("/iftar"))
        self.assertFalse(is_hidden("/shift-report"))

    def test_a_hidden_route_hides_its_sub_paths(self):
        # A per-facility view of an illustrative page is the same page with
        # a parameter — it hides with its parent.
        self.assertTrue(is_hidden("/competitive-intel/123456"))
        self.assertTrue(is_hidden("/diligence/texas-infusion/workforce"))

    def test_no_visible_route_sits_under_a_hidden_one(self):
        # The sub-path rule above is only safe while no keeper is nested
        # under a hidden parent (/deal-library/comps under a hidden
        # /deal-library would be the failure mode). Pinned against the
        # real served-route table, not a sample.
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        served = set(re.findall(r"""path\s*==\s*['"](/[^'"]+)['"]""", src))
        for route in served:
            if is_hidden(route):
                continue
            for parent in HIDDEN_ROUTES:
                self.assertFalse(
                    route.startswith(parent + "/"),
                    f"visible {route} nests under hidden {parent}")

    def test_query_strings_and_trailing_slashes_normalize(self):
        self.assertTrue(is_hidden("/diligence/texas-infusion?metro=DFW"))
        self.assertTrue(is_hidden("/ift/"))
        self.assertFalse(is_hidden("/diligence/hcris-xray?ccn=123456"))

    def test_deal_trackers_are_not_swept_up(self):
        # Named carve-out: the trackers follow publicly-reported deals and
        # are the good version of the corpus idea. Hiding them would be a
        # misread of the cleanup.
        for route in ("/deal-library", "/deal-library/comps",
                      "/deal-library/sponsors", "/verified-deals",
                      "/news", "/market-scan", "/pipeline"):
            self.assertNotIn(route, HIDDEN_ROUTES, route)
            self.assertTrue(is_visible(route), route)


class ListingSurfaceTests(unittest.TestCase):
    """No listing surface offers a hidden route."""

    _CARD_HREF = re.compile(r'class="(?:sc-link|sb-card|tx-row|dlx-link|'
                            r'cdh-link|ti-card)"[^>]*href="([^"]+)"')

    def _assert_clean(self, html: str, where: str) -> None:
        for route in self._CARD_HREF.findall(html):
            self.assertFalse(is_hidden(route), f"{where}: offers {route}")

    def test_section_landings_offer_nothing_hidden(self):
        from rcm_mc.ui.section_landings import _SECTIONS, render_section_landing
        for section in list(_SECTIONS) + ["uncategorized"]:
            html = render_section_landing(section)
            if html:
                self._assert_clean(html, f"/best/{section}")

    def test_ranked_best_pages_offer_nothing_hidden(self):
        from rcm_mc.ui.section_best_page import render_section_best
        from rcm_mc.ui._surface_rankings import RANKINGS
        for section in RANKINGS:
            self._assert_clean(render_section_best(section), f"/best/{section}")

    def test_diligence_index_offers_nothing_hidden(self):
        from rcm_mc.ui.diligence_index_page import render_diligence_index
        self._assert_clean(render_diligence_index(), "/diligence")

    def test_cdd_hub_offers_nothing_hidden(self):
        from rcm_mc.ui.cdd_hub_page import render_cdd_hub
        self._assert_clean(render_cdd_hub(), "/cdd")

    def test_tools_showcase_offers_nothing_hidden(self):
        from rcm_mc.ui.tools_showcase_page import render_tools_showcase
        self._assert_clean(render_tools_showcase(355), "/tools")

    def test_nav_bars_offer_nothing_hidden(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _ranked_subnav_items
        for section in _SUB_NAV:
            top, _ = _ranked_subnav_items(section)
            for item in top:
                self.assertFalse(is_hidden(item["href"]),
                                 f"{section} nav bar: {item}")

    def test_command_palette_offers_nothing_hidden(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, ck_command_palette,
        )
        html = ck_command_palette(_DEFAULT_PALETTE_MODULES)
        for route in re.findall(r'data-route="([^"]*)"', html):
            if route:            # the entity-jump row ships an empty route
                self.assertFalse(is_hidden(route), f"palette: {route}")

    def test_palette_filters_caller_supplied_modules_too(self):
        # A page passing its own curated palette gets the ruling for free.
        from rcm_mc.ui._chartis_kit import ck_command_palette
        html = ck_command_palette([
            {"id": "a", "title": "TX Infusion", "route": "/diligence/texas-infusion"},
            {"id": "b", "title": "HCRIS X-Ray", "route": "/diligence/hcris-xray"},
        ])
        self.assertNotIn("/diligence/texas-infusion", html)
        self.assertIn("/diligence/hcris-xray", html)

    def test_tools_index_cards_offer_nothing_hidden(self):
        from rcm_mc.server import RCMHandler
        workspaces, _total = RCMHandler._build_tools_index_data()
        for ws in workspaces:
            for tool in ws["tools"]:
                self.assertFalse(is_hidden(tool["path"]),
                                 f"/tools card: {tool['path']}")

    def test_module_index_maps_only_what_it_can_offer(self):
        from rcm_mc.data_public.module_index import compute_module_index
        result = compute_module_index()
        for mod in result.modules:
            self.assertFalse(is_hidden(mod.route), f"/module-index: {mod.route}")
        # The headline count describes the filtered list, not the raw one.
        self.assertEqual(result.total_modules, len(result.modules))


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class StillServesTests(unittest.TestCase):
    """Hidden is not deleted — every hidden route still answers a GET.

    This is the half of the ruling that is easy to lose: a later cleanup
    that actually removes a handler would pass every test above and break
    every deep link a reader has already saved.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _status(self, path: str) -> int:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=20,
            ) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_hidden_routes_still_render(self):
        for route in HIDDEN_SAMPLE:
            self.assertEqual(self._status(route), 200, route)


if __name__ == "__main__":
    unittest.main()
