"""Hidden surfaces are listed nowhere — and deleted nowhere.

The product is **healthcare-PE deal tracking on top of aggregated CMS
data**, with the X-rays at its centre. Seven classes of page work against
that and are ruled Hidden in ``rcm_mc.ui._surface_visibility``:

  * illustrative-figure pages (numbers from a hardcoded dataclass, not a
    filing),
  * single-target / single-sector study suites — the Texas infusion scan,
    the IFT/MMT transport study, the imaging atlas, the /market sector
    reports: real work, legible only inside one engagement,
  * the sponsor-corpus / PE-narrative long tail,
  * deal EXECUTION — the artifacts of running a transaction (IC packets,
    QoE memos, CDD scoping, covenant stress, LP reporting) as opposed to
    tracking one, plus the seeded slider models (payer stress, cost
    structure) that look like filing reads and are not,
  * named one-offs (/conferences),
  * the bloat: build-your-own chart and regression tools, licensed
    narrative reference, model output dressed as a screen, portfolio ops,
  * duplicate data catalogs — nine surfaces answered "what data do you
    have"; three stay.

Three lines get re-litigated on every sweep, so all three are pinned by
name below:

  * **breadth, not subject** — a whole CMS program's Care Compare
    universe read nationally (/nursing-homes, /hospice, /dialysis, …)
    stays; a bespoke single-sector study does not.
  * **tracking, not execution** — /deal-library, /verified-deals, /news,
    /market-scan, /pipeline follow publicly-reported transactions and
    stay listed.
  * **a filing, not a model** — a page that prints what a cost report
    says is an X-ray; a page that seeds two figures from one and then
    hands you sliders is a deal-economics tool. The three surfaces that
    crossed that line late (/payer-stress, /diligence/payer-stress,
    /cost-structure) have their own case below.

Hidden is a BROWSE ruling, not a routing one. This module guards both
halves: nothing offers a hidden surface, and every hidden surface still
serves.
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
    "/radiology-imaging",             # bespoke single-sector study
    "/market",                        # sector M&A report catalog…
    "/market/infusion",               # …and its per-sector writeups
    "/diligence/ic-packet",           # deal EXECUTION, not tracking
    "/diligence/qoe-memo",
    "/diligence/physician-eu",        # "Provider Economics"
    "/cdd",
    "/engagements",
    "/conferences",                   # named one-off
    "/pipeline/rollup",
    "/lp-update",
)

# What the cleanup must NOT touch: the public-data reads, the visualization
# tools, and the deal trackers.
VISIBLE_SAMPLE = (
    # The X-rays — the centre of gravity, and the thing to be most
    # careful about: every sweep so far has had to be checked against
    # this row.
    "/diligence/hcris-xray", "/diligence/xray",
    # CMS aggregation. Sweep 5 cut nine competing data catalogs down to
    # three with distinct jobs, so this row names those three by hand.
    "/target-screener", "/data", "/cms-sources", "/data-quality",
    "/metric-glossary", "/methodology", "/methodology/calculations",
    "/rate-environment", "/regulatory-calendar",
    "/state-compare", "/county-explorer",
    # Whole-program Care Compare universes — sector-specific, but each is
    # a national read of a CMS program, which is the distinction that
    # separates them from the infusion / IFT / imaging studies.
    "/nursing-homes", "/home-health", "/hospice", "/dialysis",
    "/inpatient-rehab", "/long-term-care-hospital", "/verticals",
    # Scanners
    "/target-screener", "/screen", "/health-system-lookup", "/npi-cleaner",
    # Deal TRACKING — in the SPACE. /portfolio was on this row until the
    # bloat sweep: running your own book is not tracking the market.
    "/deal-library", "/deal-library/sponsors", "/deal-library/comps",
    "/verified-deals", "/news", "/market-scan", "/pipeline",
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

    def test_program_universes_survive_the_sector_sweep(self):
        # The infusion / IFT / imaging studies are hidden as bespoke
        # single-sector work. The line is sector BREADTH, not subject:
        # a whole CMS program's Care Compare universe read nationally is
        # exactly the aggregation this product is for.
        for route in ("/nursing-homes", "/home-health", "/hospice",
                      "/dialysis", "/inpatient-rehab",
                      "/long-term-care-hospital", "/verticals"):
            self.assertTrue(is_visible(route), route)
        for route in ("/radiology-imaging", "/diligence/infusion-markets",
                      "/ift-markets", "/market/infusion"):
            self.assertTrue(is_hidden(route), route)

    def test_the_xrays_are_never_swept_up(self):
        # Named as the thing worth keeping. Each sweep re-checks it.
        for route in ("/diligence/hcris-xray", "/diligence/xray"):
            self.assertNotIn(route, HIDDEN_ROUTES, route)
            self.assertTrue(is_visible(route), route)

    def test_diligence_benchmarks_is_the_rcm_product_under_a_third_url(self):
        # Carved out of the revenue-cycle-benchmark block twice, as "it
        # places a FACILITY against its peer cohort". The renderer says
        # otherwise: eyebrow "RCM DILIGENCE · PHASE 2 OF 4", lede "Five
        # HFMA KPIs against acute-care peer bands … the Phase-2 evidence
        # base for the RCM thesis", source note crediting the same HFMA
        # MAP Key 2021 bands as /benchmarks and /rcm-benchmarks, and a
        # FIXTURE claims file behind a selector rather than a filing. Its
        # three sibling phases were already hidden; a workspace cannot be
        # three-quarters hidden.
        for route in ("/benchmarks", "/rcm-benchmarks",
                      "/diligence/benchmarks", "/diligence/snapshot",
                      "/diligence/root-cause", "/diligence/qoe-memo"):
            self.assertTrue(is_hidden(route), route)

    def test_the_seeded_slider_models_are_not_xrays(self):
        # /diligence/payer-stress, /payer-stress and /cost-structure rode
        # the row above through three sweeps as X-rays. They are not: each
        # takes a CCN, seeds two or three real HCRIS figures, and then
        # hands the reader sliders ("what if commercial rates cut 5%").
        # /cost-structure's own registry entry concedes its COGS / SG&A /
        # labor split "stays illustrative-labeled". An X-ray prints what a
        # filing says; these print what you assume. The real HCRIS opex
        # figures underneath them are on /diligence/hcris-xray.
        for route in ("/diligence/payer-stress", "/payer-stress",
                      "/cost-structure"):
            self.assertTrue(is_hidden(route), route)

    def test_the_data_catalog_is_not_nine_data_catalogs(self):
        # Sweep 5 found nine surfaces all answering "what data do you
        # have". Three stay, with distinct jobs: the canonical inventory,
        # the CMS-specific registry, and the surface that admits what is
        # missing. The rest duplicated those, catalogued data the product
        # does NOT hold (credentialed CMS microdata, free third-party
        # APIs), or inventoried connectors rather than datasets.
        for route in ("/data", "/cms-sources", "/data-quality"):
            self.assertTrue(is_visible(route), f"keeper: {route}")
        for route in ("/data/catalog", "/cms-data-browser",
                      "/data-intelligence", "/tools/open-data",
                      "/data-apis", "/tools/nonpublic-cms",
                      "/connector-estate"):
            self.assertTrue(is_hidden(route), f"duplicate: {route}")

    def test_deployment_plumbing_is_internal_not_hidden(self):
        # Operator surfaces (job queue, run history, audit chain, source
        # health, settings) are wanted from the user and admin menus and
        # are simply never carded in a catalog. Internal, not Hidden —
        # the distinction matters because is_visible() gates both, but
        # only INTERNAL_ROUTES documents "keeps its menu link".
        from rcm_mc.ui._surface_visibility import is_internal
        for route in ("/jobs", "/runs", "/audit", "/admin/audit-chain",
                      "/admin/data-sources", "/ops", "/team",
                      "/guide/context-debug", "/settings",
                      "/settings/ai", "/settings/workspace"):
            self.assertTrue(is_internal(route), route)
            self.assertFalse(is_hidden(route), f"{route}: internal, not hidden")
            self.assertFalse(is_visible(route), route)

    def test_bloat_sweep_hid_the_named_families(self):
        # The bloat ruling, by the names it was given: portfolio ops, the
        # graphics toolkit ("the excel image generator"), the interactive
        # regressions, the state maps, and the thin input-only surfaces.
        for route in ("/portfolio", "/portfolio/monitor", "/cohorts",
                      "/visuals", "/chart-builder", "/pie-chart", "/exhibit",
                      "/charts", "/excel-mapping", "/excel-templates",
                      "/portfolio/regression", "/ml-insights",
                      "/geo-map", "/geo-metrics",
                      "/query", "/screening/dashboard",
                      "/rcm-benchmarks", "/benchmarks", "/labor-market",
                      "/rxnorm", "/markets/global"):
            self.assertTrue(is_hidden(route), route)

    def test_npi_cleaner_is_explicitly_kept(self):
        # Named as a keeper while the rest of the utilities went. It is a
        # provider-identity tool running a real claims file through the
        # offline NPPES registry.
        for route in ("/npi-cleaner", "/npi-cleaner/history"):
            self.assertTrue(is_visible(route), route)

    def test_tracking_stays_execution_goes(self):
        # The product is deal TRACKING plus CMS aggregation. Tracking a
        # transaction stays; the artifacts of running one do not.
        for route in ("/deal-library", "/verified-deals", "/news",
                      "/market-scan", "/pipeline"):
            self.assertTrue(is_visible(route), f"tracking: {route}")
        for route in ("/diligence/ic-packet", "/diligence/qoe-memo",
                      "/diligence/cdd-scope", "/diligence/expert-calls",
                      "/diligence/deal-mc", "/diligence/counterfactual",
                      "/engagements", "/lp-update"):
            self.assertTrue(is_hidden(route), f"execution: {route}")

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

    def test_keyboard_quick_jump_offers_nothing_hidden(self):
        # The vim-style "g + letter" table in _SHORTCUTS_JS is chrome you
        # cannot see: it ships on every page and navigates on a keypress.
        # It kept `g o → /portfolio` and `g d → /diligence/deal` after
        # both were hidden, which is an offer of the route however
        # invisible. `g m → /my/<owner>` is exempt for the same reason the
        # topbar user menu is — personal entry point, not a catalog entry.
        from rcm_mc.ui._chartis_kit import _SHORTCUTS_JS, _SHORTCUTS_HTML
        table = re.search(r"var GO_TARGETS = \{(.*?)\};", _SHORTCUTS_JS,
                          re.S)
        self.assertIsNotNone(table, "GO_TARGETS table not found")
        targets = re.findall(r"'(/[^']*)'", table.group(1))
        self.assertTrue(targets)
        for route in targets:
            if route.startswith("/my/"):
                continue
            self.assertFalse(is_hidden(route), f"g-jump offers {route}")
        # The help dialog must not advertise a jump the table dropped.
        self.assertNotIn("Portfolio", _SHORTCUTS_HTML)

    def test_the_editorial_shell_chrome_offers_nothing_hidden(self):
        # The primary shell, held to the same standard as the legacy one
        # below. Nothing HIDDEN may appear anywhere in its chrome. The
        # INTERNAL routes it does carry are all inside the topbar user
        # menu (/users, /audit, /settings/workspace) or the personal
        # entry point (/my/<owner>) — the documented exemption, and the
        # test asserts they sit in the user-dropdown markup rather than
        # taking it on trust.
        import re as _re
        from rcm_mc.ui._chartis_kit import chartis_shell
        from rcm_mc.ui._surface_visibility import is_internal
        html = chartis_shell("<p>x</p>", "T")
        # Case-insensitive: /my/<owner> carries an uppercase owner code.
        hrefs = sorted(set(_re.findall(r'href="(/[A-Za-z0-9/.\-]+)', html)))
        self.assertTrue(hrefs, "editorial shell rendered no links at all")
        exempt = [h for h in hrefs
                  if is_internal(h) or h == "/my" or h.startswith("/my/")]
        self.assertEqual([h for h in hrefs
                          if is_hidden(h) and h not in exempt], [])
        for href in exempt:
            in_menu = _re.search(
                r'href="' + _re.escape(href)
                + r'[^"]*"[^>]*class="ck-(?:user-dropdown-item|mode-chip|user-recent[a-z-]*)"',
                html)
            self.assertTrue(in_menu,
                            f"{href} is internal but not in the user menu")

    def test_the_legacy_shell_sidebar_offers_nothing_hidden(self):
        # The dark "Chartis Consulting" shell is a second, complete page
        # chrome a reader can switch to from /settings/workspace, and its
        # primary sidebar went untouched by four hide sweeps — it was
        # offering 36 of its 44 items after those sweeps had ruled them
        # hidden. A shell you can switch to is a place you browse.
        import re as _re
        from rcm_mc.ui._chartis_kit_legacy import chartis_shell as legacy
        html = legacy("<p>x</p>", "T")
        hrefs = _re.findall(r'<a href="([^"]+)" class="ck-nav-item', html)
        self.assertTrue(hrefs, "legacy sidebar rendered no items at all")
        for href in hrefs:
            self.assertTrue(is_visible(href.split("?", 1)[0]),
                            f"legacy sidebar: {href}")

    def test_the_legacy_shell_palette_offers_nothing_hidden(self):
        # Same gap as the sidebar, in the same shell: the legacy Cmd+K
        # palette was offering 33 of its 55 entries after four sweeps had
        # hidden them, including the whole RUN block of deal-execution
        # tools. Asserted over the shell's rendered output, so it covers
        # the palette as a reader actually meets it.
        import re as _re
        from rcm_mc.ui._chartis_kit_legacy import chartis_shell as legacy
        html = legacy("<p>x</p>", "T")
        hrefs = _re.findall(
            r'class="ck-palette-item"[^>]*href="([^"]+)"', html)
        self.assertTrue(hrefs, "legacy palette rendered no items at all")
        for href in hrefs:
            self.assertTrue(is_visible(href.split("?", 1)[0]),
                            f"legacy palette: {href}")

    def test_the_legacy_shell_chrome_offers_nothing_hidden_anywhere(self):
        # The catch-all for this shell: every internal href anywhere in
        # its chrome, not just the two constructs above. Two sweeps found
        # the sidebar and the palette by hand; this finds the third.
        import re as _re
        from rcm_mc.ui._chartis_kit_legacy import chartis_shell as legacy
        html = legacy("<p>x</p>", "T")
        hrefs = sorted(set(_re.findall(r'href="(/[a-z0-9/.\-]+)', html)))
        leaked = [h for h in hrefs if not is_visible(h)]
        self.assertEqual(leaked, [], f"legacy shell chrome: {leaked}")

    def test_the_legacy_shell_drops_emptied_section_headings(self):
        # Filtering the sidebar emptied whole sections. A heading with
        # nothing under it reads as a broken nav, so it goes too.
        import re as _re
        from rcm_mc.ui._chartis_kit_legacy import chartis_shell as legacy
        html = legacy("<p>x</p>", "T")
        # Every rendered separator must be followed by at least one item
        # before the next separator or the end of the nav.
        chunks = _re.split(r'<div class="ck-nav-sep">[^<]*</div>', html)
        for chunk in chunks[1:]:
            self.assertIn("ck-nav-item", chunk.split("</nav>")[0],
                          "a section heading has no items under it")

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
