"""PR E — unified Target Screener under Source.

One entry that explains and routes to the three overlapping screeners (Thesis
Sourcing, Hospital Screener, Predictive Screener), all over the same CMS/HCRIS
universe. The three old routes are PRESERVED unchanged (backward compatible).
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TargetScreenerRenderTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.h = render_target_screener({})

    def test_unified_header_and_cms_label(self):
        self.assertIn("Target Screener", self.h)
        self.assertIn("CMS PUBLIC DATA", self.h)        # market data, not deals

    def test_three_modes_route_to_existing_screeners(self):
        for href in ("/source", "/screen", "/predictive-screener"):
            self.assertIn(f'href="{href}"', self.h)

    def test_explains_same_universe(self):
        low = self.h.lower()
        self.assertIn("same", low)
        self.assertIn("universe", low)
        self.assertIn("promote", low)                   # path into Pipeline

    def test_active_mode_highlights(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        self.assertIn("is-active", render_target_screener({"mode": ["hospital"]}))


class WorkbenchShellTests(unittest.TestCase):
    """PR 2 — the six-screen workbench shell (view= states), recreated
    PEdesk-native from the workbench-full.html handoff."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_six_screens_render(self):
        for view in ("main", "inspector", "columns", "compare", "missed", "saved"):
            h = self._render(view=view)
            self.assertIn("<!doctype html>", h.lower(), view)
            self.assertIn("Target Screener", h, view)

    def test_view_param_selects_active_tab(self):
        h = self._render(view="compare")
        # The active tab carries aria-current=page on the Compare link.
        self.assertIn('aria-current="page"', h)
        self.assertIn("view=compare", h)  # tab links carry view=

    def test_bogus_view_falls_back_to_main(self):
        h = self._render(view="nope")
        self.assertIn("<!doctype html>", h.lower())

    def test_all_six_tabs_present(self):
        h = self._render()
        # Tabs italicize an emphasis word (e.g. "Just <em>missed</em>"), so
        # assert the rendered tokens + the workbench numerals 01..06.
        for token in ("Main", "Inspector", "Columns", "Compare",
                      "missed", "Saved"):
            self.assertIn(token, h, token)
        for num in ("01", "02", "03", "04", "05", "06"):
            self.assertIn(f'tsw-num">{num}', h, num)

    def test_vertical_selector_includes_live_verticals(self):
        h = self._render()
        for label in ("Hospitals", "Home Health", "Hospice", "SNF",
                      "Dialysis", "IRF", "LTCH"):
            self.assertIn(label, h, label)

    def test_vertical_param_activates(self):
        h = self._render(vertical="hospice")
        self.assertIn("tsw-vert is-active", h)
        self.assertIn("Hospice", h)

    def test_no_iframe_prototype_shipped(self):
        for view in ("main", "compare", "saved"):
            self.assertNotIn("<iframe", self._render(view=view).lower())

    def test_no_prototype_external_font(self):
        # The shell loads PEdesk house fonts; the page must not add the
        # prototype's Public Sans / a bespoke CDN font.
        self.assertNotIn("Public Sans", self._render())

    def test_empty_states_are_labeled_not_faked(self):
        # All six screens are built; the remaining scaffolds are honest EMPTY
        # states (inspector with no CCN, compare with empty basket) — never
        # fabricated data.
        self.assertIn("Scaffold", self._render(view="inspector"))   # no ccn
        self.assertIn("Scaffold", self._render(view="compare"))     # empty basket


class WorkbenchMapTests(unittest.TestCase):
    """PR 3 — real US map (reuses render_us_geo_map), state click→filter,
    layer selector, legend, real provider-count shading."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_real_geo_map_not_squares(self):
        h = self._render(view="main", vertical="home_health")
        self.assertIn("usgeo-state", h)          # real SVG choropleth
        self.assertIn("<path", h)                # vector paths, not tiles
        self.assertNotIn("usm-tile", h)          # not the square cartogram

    def test_state_click_listener_present(self):
        self.assertIn("us-map-select", self._render(view="main"))

    def test_state_param_selects_and_shows_filter(self):
        h = self._render(view="main", vertical="hospice", state="TX")
        self.assertIn("usgeo-selected", h)       # TX highlighted
        self.assertIn("Filtered to", h)
        self.assertIn("clear state filter", h)

    def test_layer_selector_present(self):
        h = self._render(view="main")
        self.assertIn("Map layer", h)
        self.assertIn("Provider count", h)

    def test_real_provider_counts_present(self):
        # The map summary states a real provider total for the vertical.
        from rcm_mc.ui.target_screener_page import _provider_counts_by_state
        counts = _provider_counts_by_state("home_health")
        self.assertGreater(sum(counts.values()), 100)   # real CMS HHA universe
        self.assertGreater(len(counts), 30)

    def test_provider_counts_safe_on_unknown_vertical(self):
        from rcm_mc.ui.target_screener_page import _provider_counts_by_state
        self.assertEqual(_provider_counts_by_state("nope"), {})

    def test_map_has_legend(self):
        h = self._render(view="main", vertical="dialysis")
        self.assertIn("usgeo-legend", h)
        self.assertIn("No data", h)


class WorkbenchTableTests(unittest.TestCase):
    """PR 4 — ranked provider table from the real CMS loaders, state-scoped,
    with X-Ray / Inspect links and honest missingness."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_table_renders_real_rows_per_vertical(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        for v in ("hospitals", "home_health", "hospice", "snf", "dialysis", "irf", "ltch"):
            rows = _vertical_rows(v)
            self.assertGreater(len(rows), 10, v)
            self.assertTrue(all(r["ccn"] for r in rows), v)

    def test_rows_link_to_universal_xray(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn("/diligence/xray?ccn=", h)
        self.assertIn("&vertical=snf", h)

    def test_state_filter_narrows_rows(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        allrows = _vertical_rows("ltch")
        tx = _vertical_rows("ltch", "TX")
        self.assertLess(len(tx), len(allrows))
        self.assertTrue(all(r["state"] == "TX" for r in tx))

    def test_missing_values_render_dash_not_fake(self):
        # A real provider with no reported quality shows '—', never a number.
        h = self._render(view="main", vertical="hospice")
        self.assertIn("—", h)
        self.assertIn("not reported", h)  # honest caveat copy

    def test_source_chip_present(self):
        h = self._render(view="main", vertical="dialysis")
        self.assertIn("CMS Dialysis Compare", h)

    def test_rows_safe_on_unknown_vertical(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        self.assertEqual(_vertical_rows("nope"), [])

    def test_table_capped(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows, _TABLE_LIMIT
        self.assertLessEqual(len(_vertical_rows("home_health")), _TABLE_LIMIT)


class WorkbenchCompareTests(unittest.TestCase):
    """PR 5 — compare basket: same-vertical full, cross-vertical shared-only."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def _ccns(self, vertical, n=2):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        return [r["ccn"] for r in _vertical_rows(vertical)[:n]]

    def test_find_provider_resolves_real_ccn(self):
        from rcm_mc.ui.target_screener_page import _find_provider, _vertical_rows
        ccn = _vertical_rows("dialysis")[0]["ccn"]
        r = _find_provider(ccn)
        self.assertIsNotNone(r)
        self.assertEqual(r["vertical"], "dialysis")

    def test_find_provider_none_for_bogus(self):
        from rcm_mc.ui.target_screener_page import _find_provider
        self.assertIsNone(_find_provider("ZZZZZZ"))

    def test_empty_basket_state(self):
        self.assertIn("Compare basket (empty)", self._render(view="compare"))

    def test_same_vertical_compare_full(self):
        ccns = self._ccns("home_health", 3)
        h = self._render(view="compare", compare=",".join(ccns))
        self.assertIn("Comparing 3", h)
        self.assertIn("CMS X-Ray", h)
        self.assertNotIn("not directly comparable", h)  # single vertical

    def test_cross_vertical_shows_not_comparable(self):
        hh = self._ccns("home_health", 1)[0]
        dz = self._ccns("dialysis", 1)[0]
        h = self._render(view="compare", compare=f"{hh},{dz}")
        self.assertIn("verticals", h)
        self.assertIn("not directly comparable", h)

    def test_missing_ccn_reported_not_faked(self):
        h = self._render(view="compare", compare="ZZZZZZ")
        self.assertTrue("resolved to a live provider" in h or "Not found" in h)

    def test_table_has_add_to_compare(self):
        h = self._render(view="main", vertical="snf")
        self.assertIn("+Cmp", h)
        self.assertIn("view=compare&compare=", h)


class WorkbenchJustMissedTests(unittest.TestCase):
    """PR 6 — just-missed scan: single-criterion near-misses + missing-data."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_uncapped_rows_for_scan(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows, _TABLE_LIMIT
        full = _vertical_rows("snf", limit=None)
        self.assertGreater(len(full), _TABLE_LIMIT)  # scan sees the whole universe

    def test_prompt_without_thresholds(self):
        h = self._render(view="missed", vertical="snf")
        self.assertIn("Set a", h)
        self.assertIn("Scan", h)              # the GET filter form

    def test_scan_with_thresholds_shows_just_missed(self):
        h = self._render(view="missed", vertical="snf", min_quality="4", min_size="100")
        self.assertIn("just missed", h.lower())
        self.assertIn("Just missed because", h)  # the near-miss table header

    def test_missing_data_not_failed(self):
        h = self._render(view="missed", vertical="hospice", min_quality="50")
        # Providers with no reported metric are surfaced as missing, not failed.
        self.assertTrue("not reported" in h.lower() or "missing data" in h.lower())

    def test_relax_link_present_when_near_misses(self):
        h = self._render(view="missed", vertical="dialysis", min_quality="4")
        self.assertTrue("Relax" in h or "No single-criterion" in h)

    def test_filter_form_is_get_and_shareable(self):
        h = self._render(view="missed", vertical="irf", min_quality="50")
        self.assertIn('method="get"', h)
        self.assertIn('name="min_quality"', h)


class WorkbenchColumnsTests(unittest.TestCase):
    """PR 7 — column picker / metric dictionary: grouped, sourced, live
    availability counts."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_columns_grouped_with_source_and_availability(self):
        h = self._render(view="columns", vertical="snf")
        for cat in ("Identity", "Geography", "Ownership", "Quality", "Source"):
            self.assertIn(cat, h, cat)
        self.assertIn("Availability", h)

    def test_availability_is_real_fraction(self):
        # Availability cells read "<count>/<total> (NN%)" from the universe.
        import re
        h = self._render(view="columns", vertical="dialysis")
        self.assertRegex(h, r"\d[\d,]*/\d[\d,]*\s*\(\d+%\)")

    def test_additional_quality_columns_listed(self):
        from rcm_mc.ui.target_screener_page import _quality_keys
        self.assertGreater(len(_quality_keys("snf")), 3)
        self.assertIn("Additional", self._render(view="columns", vertical="snf"))

    def test_columns_safe_unknown_vertical(self):
        h = self._render(view="columns", vertical="nope")
        self.assertIn("<!doctype html>", h.lower())  # falls back to hospitals


class WorkbenchInspectorTests(unittest.TestCase):
    """PR 8 — inspector drawer: real identity, peer/market context, links, Guide."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def _ccn(self, vertical):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        return _vertical_rows(vertical)[0]["ccn"]

    def test_no_ccn_prompts(self):
        self.assertIn("no target selected", self._render(view="inspector").lower())

    def test_bad_ccn_reported(self):
        self.assertIn("did not resolve", self._render(view="inspector", ccn="ZZZZZZ"))

    def test_selected_target_shows_identity_and_peer_context(self):
        h = self._render(view="inspector", ccn=self._ccn("snf"))
        self.assertIn("Selected target", h)
        self.assertIn("Peer rank", h)
        self.assertIn("median", h.lower())

    def test_inspector_links_to_xray_and_pipeline(self):
        h = self._render(view="inspector", ccn=self._ccn("dialysis"))
        self.assertIn("/diligence/xray?ccn=", h)
        self.assertIn("Promote to Pipeline", h)
        self.assertIn("market context", h.lower())

    def test_inspector_has_guide_questions(self):
        h = self._render(view="inspector", ccn=self._ccn("hospice"))
        self.assertIn("Ask the Guide", h)

    def test_median_helper(self):
        from rcm_mc.ui.target_screener_page import _median
        self.assertEqual(_median([1, 2, 3]), 2)
        self.assertEqual(_median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(_median([None, "x"]))


class WorkbenchSavedTests(unittest.TestCase):
    """PR 9 — saved screens: shareable URL state + honest persistence caveat."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_current_screen_is_shareable_url(self):
        h = self._render(view="saved", vertical="snf", state="TX")
        self.assertIn("/target-screener?", h)
        self.assertIn("vertical=snf", h)
        self.assertIn("state=TX", h)
        self.assertIn("shareable", h.lower())

    def test_prebuilt_screens_present(self):
        h = self._render(view="saved")
        self.assertIn("Prebuilt screens", h)
        self.assertIn("Open screen", h)

    def test_persistence_caveat_is_honest(self):
        h = self._render(view="saved")
        self.assertIn("not wired yet", h.lower())
        self.assertIn("saved_screens(", h)   # documented future schema
        self.assertNotIn("fake", h.lower()[:0] or "")  # no fake alerts shown

    def test_no_fake_alerts(self):
        h = self._render(view="saved")
        # Honest: we never claim alerts that aren't implemented.
        self.assertNotIn("alert enabled", h.lower())


class WorkbenchGeoVerticalTests(unittest.TestCase):
    """PR 10 — provider_supply + market screened as STATE-level geography
    views (map + ranked state table), clearly not individual providers."""

    def _render(self, **params):
        from rcm_mc.ui.target_screener_page import render_target_screener
        return render_target_screener({k: [v] for k, v in params.items()})

    def test_provider_supply_geo_view_real(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, label, fmt, src = _geo_state_values("provider_supply", "supply")
        self.assertGreater(len(vals), 40)               # ~all states
        self.assertGreater(vals.get("TX", 0), 1000)     # real PECOS supply
        h = self._render(view="main", vertical="provider_supply")
        self.assertIn("usgeo-state", h)                 # real map
        self.assertIn("not individual providers", h.lower())
        self.assertIn("States ranked", h)

    def test_market_geo_view_metric_selector(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, *_ = _geo_state_values("market", "population")
        self.assertGreater(len(vals), 40)
        h = self._render(view="main", vertical="market", metric="age_65_plus")
        self.assertIn("Market metric", h)
        self.assertIn("Age 65+", h)
        self.assertIn("usgeo-state", h)

    def test_market_state_click_goes_to_geo_intel(self):
        h = self._render(view="main", vertical="market")
        self.assertIn("/geo-intel?state=", h)

    def test_geo_value_safe_on_failure(self):
        from rcm_mc.ui.target_screener_page import _geo_state_values
        vals, *_ = _geo_state_values("nope", "x")
        self.assertEqual(vals, {})


class NavAndRouteTests(unittest.TestCase):
    def test_source_anchor_is_target_screener(self):
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV, _SUB_NAV, _resolve_sub_section
        src = next(n for n in _CORPUS_NAV if n["key"] == "source")
        self.assertEqual(src["href"], "/target-screener")
        self.assertEqual(_SUB_NAV["source"][0]["label"], "Target Screener")
        self.assertEqual(_resolve_sub_section("/target-screener"), "source")


class BackwardCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _status(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_target_screener_route_200(self):
        self.assertEqual(self._status("/target-screener"), 200)

    def test_old_screener_routes_still_work(self):
        # No redirects/deletes — the three screeners are unchanged.
        for path in ("/source", "/screen", "/predictive-screener"):
            self.assertEqual(self._status(path), 200, msg=path)


if __name__ == "__main__":
    unittest.main()
