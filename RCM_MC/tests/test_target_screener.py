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

    def test_unbuilt_screens_are_labeled_scaffolds_not_fake(self):
        # Honest: not-yet-wired screens declare themselves, never fake data.
        for view in ("inspector", "columns", "compare", "missed", "saved"):
            self.assertIn("Scaffold", self._render(view=view), view)


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
