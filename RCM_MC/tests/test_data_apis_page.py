"""Tests for the Public Data APIs catalog page (/data-apis).

Page renders with a real chart and every source; JSON API mirrors the catalog;
the route serves 200 and is reachable from nav/palette/breadcrumb.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import public_api_catalog as cat
from rcm_mc.ui.data_public.data_apis_page import (
    build_data_apis, render_data_apis_page)


class PageRenderTests(unittest.TestCase):
    def test_page_has_title_chart_and_kpis(self):
        h = render_data_apis_page({})
        self.assertIn("Public Data APIs", h)
        self.assertIn("<svg", h)              # the coverage chart
        self.assertIn("Public APIs", h)       # KPI label
        self.assertIn("No key needed", h)

    def test_has_two_professional_charts(self):
        h = render_data_apis_page({})
        # Coverage-by-question + available-vs-planned roadmap.
        self.assertGreaterEqual(h.count("<svg"), 2)
        self.assertIn("available now vs", h.lower())

    def test_every_source_appears(self):
        import html
        h = render_data_apis_page({})
        for s in cat.all_sources():
            self.assertIn(html.escape(s.name), h, f"{s.id} missing from page")

    def test_category_headers_render(self):
        import html
        h = render_data_apis_page({})
        for _cid, label, _members in cat.by_category():
            self.assertIn(html.escape(label), h)

    def test_docs_links_present(self):
        h = render_data_apis_page({})
        # Each source links its docs.
        for s in cat.all_sources():
            self.assertIn(s.docs_url, h)

    def test_explore_launchpad_links_to_in_repo_charts(self):
        h = render_data_apis_page({})
        wired_with_route = [s for s in cat.all_sources() if s.explore_route]
        self.assertTrue(wired_with_route)
        for s in wired_with_route:
            self.assertIn(s.explore_route, h)
            # The route points at a real in-repo explorer: either a
            # Further Analysis dataset chart or the connector-estate
            # browser (estate-backed sources).
            self.assertTrue(
                s.explore_route.startswith("/further-analysis?dataset=")
                or s.explore_route.startswith("/connector-estate?connector="),
                f"{s.id} explore route {s.explore_route!r} not an "
                f"in-repo explorer")

    def test_ready_strip_maps_to_real_explorer_datasets(self):
        from rcm_mc.diligence import further_analysis as fa
        from rcm_mc.ui.data_public.data_apis_page import _READY_BY_QUESTION
        ids = {d.id for d in fa.list_datasets()}
        valid_cats = dict(cat.CATEGORIES)
        for cid, ds_ids in _READY_BY_QUESTION.items():
            self.assertIn(cid, valid_cats, f"{cid} not a diligence category")
            for ds in ds_ids:
                self.assertIn(ds, ids, f"ready strip -> unknown dataset {ds}")
        # The page surfaces the launchpad strip with real explorer links.
        h = render_data_apis_page({})
        self.assertIn("Ready in-repo", h)
        self.assertIn("/further-analysis?dataset=provider_supply", h)

    def test_explore_routes_resolve_to_real_datasets(self):
        from rcm_mc.diligence import further_analysis as fa
        ids = {d.id for d in fa.list_datasets()}
        for s in cat.all_sources():
            if not s.explore_route or "dataset=" not in s.explore_route:
                continue
            ds = s.explore_route.split("dataset=", 1)[1].split("&", 1)[0]
            self.assertIn(ds, ids, f"{s.id} explore route -> unknown {ds}")

    def test_estate_explore_routes_name_real_connectors(self):
        # Estate-backed sources link the connector-estate browser; when
        # the repo-root estate is present the ?connector= value must be a
        # registered connector name (skip cleanly on wheel installs).
        from rcm_mc.data_public import connector_estate as est
        if not est.estate_available():
            self.skipTest("repo-root connector estate not present")
        names = {s["connector"] for s in est.connectors_summary()}
        estate_sources = [s for s in cat.all_sources()
                          if s.explore_route.startswith(
                              "/connector-estate?connector=")]
        self.assertGreaterEqual(len(estate_sources), 13)
        for s in estate_sources:
            conn = s.explore_route.split("connector=", 1)[1].split("&", 1)[0]
            self.assertIn(conn, names, f"{s.id} -> unknown connector {conn}")


class JsonApiTests(unittest.TestCase):
    def test_payload_mirrors_catalog(self):
        p = build_data_apis({})
        self.assertEqual(p["summary"]["total"], len(cat.all_sources()))
        self.assertEqual(len(p["categories"]), len(cat.CATEGORIES))
        flat = [s for c in p["categories"] for s in c["sources"]]
        self.assertEqual(len(flat), len(cat.all_sources()))
        # Each source entry carries the discovery fields.
        for s in flat:
            for k in ("id", "base_url", "access", "status", "is_wired",
                      "answers"):
                self.assertIn(k, s)


class HttpRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        import socket
        import tempfile
        import threading
        import time
        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls._port = s.getsockname()[1]
        s.close()
        srv, _ = build_server(port=cls._port,
                              db_path=os.path.join(cls._tmp.name, "p.db"),
                              host="127.0.0.1")
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _get(self, path):
        import urllib.error
        import urllib.request
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{path}", timeout=10)
        except urllib.error.HTTPError as exc:
            return exc

    def test_page_route_serves_html(self):
        resp = self._get("/data-apis")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Public Data APIs", body)
        self.assertIn("<svg", body)

    def test_json_route_serves_catalog(self):
        import json
        resp = self._get("/api/data-apis")
        self.assertEqual(resp.status, 200)
        payload = json.loads(resp.read().decode())
        self.assertEqual(payload["summary"]["total"], len(cat.all_sources()))


class WiringTests(unittest.TestCase):
    def test_route_in_nav_palette_and_breadcrumb(self):
        from rcm_mc.ui import _chartis_kit as kit
        src = ""
        import inspect
        src = inspect.getsource(kit)
        self.assertIn('"/data-apis"', src)
        # Breadcrumb section map resolves the route to a section.
        self.assertIn('"/data-apis": "research"', src)


if __name__ == "__main__":
    unittest.main()
