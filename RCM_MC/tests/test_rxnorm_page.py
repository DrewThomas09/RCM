"""Tests for the /rxnorm Drug Reference page: render functions, the JSON API,
and the live route wiring (GET page, GET api, POST seed) end-to-end.

Follows the repo convention: multi-step flows run against a real HTTP server on
a free port in open (auth=None) mode, so CSRF is skipped and forms POST as a
partner would.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.rxnorm import run as rxrun
from rcm_mc.ui.data_public.rxnorm_page import build_rxnorm, render_rxnorm_page


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _seed_store(db_path: str) -> PortfolioStore:
    store = PortfolioStore(db_path)
    rxrun(store, state_dir=tempfile.mkdtemp())
    return store


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_state_offers_seed_action(self):
        html = render_rxnorm_page(PortfolioStore(self.db), {})
        self.assertIn("No RxNorm data loaded", html)
        self.assertIn('action="/rxnorm/seed"', html)
        self.assertIn("<html", html.lower())

    def test_populated_page_renders_kpis_and_tools(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {})
        self.assertIn("NDC resolver", html)
        self.assertIn("Drug-class explorer", html)
        self.assertIn("Retired / remapped audit", html)
        self.assertIn("class coverage", html.lower())

    def test_ndc_lookup_renders_resolution(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {"ndc": "0409-1896-20"})
        self.assertIn("00409189620", html)   # canonical key shown
        self.assertIn("morphine", html.lower())

    def test_rxcui_detail_renders_competitive_set(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {"rxcui": "83367"})
        self.assertIn("Competitive set", html)
        self.assertIn("Drug classes", html)

    def test_class_explorer_filters(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {"class_id": "C10AA"})
        self.assertIn("C10AA", html)

    def test_escapes_user_input(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {"q": "<script>x</script>"})
        self.assertNotIn("<script>x</script>", html)

    def test_ndc_decomposition_shown(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {"ndc": "0409-1896-20"})
        self.assertIn("5-4-2 segments", html)
        self.assertIn("labeler", html)

    def test_dataset_browser_sort_and_paginate(self):
        store = _seed_store(self.db)
        html = render_rxnorm_page(store, {
            "dataset": "rxnorm_ndc_crosswalk", "sort": "ndc_11",
            "desc": "1", "ds_page": "0"})
        self.assertIn("Dataset browser", html)
        self.assertIn("/v1/query/rxnorm_ndc_crosswalk", html)
        # second page renders without error even if beyond range
        html2 = render_rxnorm_page(store, {"dataset": "rxnorm_concepts",
                                           "ds_page": "1"})
        self.assertIn("<html", html2.lower())

    def test_build_json_shape(self):
        store = _seed_store(self.db)
        out = build_rxnorm(store, {"ndc": "0409-1896-20", "rxcui": "83367"})
        self.assertIn("summary", out)
        self.assertIn("datasets", out)
        self.assertEqual(out["ndc_lookup"]["match"]["current_rxcui"], "7052")
        self.assertTrue(out["top_classes"])


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _get(self, path: str):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=10) as resp:
            return resp.status, resp.read().decode()

    def test_page_route_200(self):
        status, body = self._get("/rxnorm")
        self.assertEqual(status, 200)
        self.assertIn("Drug reference", body)

    def test_api_route_returns_summary(self):
        status, body = self._get("/api/rxnorm")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("summary", data)
        self.assertIn("datasets", data)

    def _post_seed(self):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/rxnorm/seed", data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            self.assertEqual(resp.status, 200)

    def test_csv_export_after_seed(self):
        self._post_seed()
        status, body = self._get("/rxnorm/export.csv?table=crosswalk")
        self.assertEqual(status, 200)
        self.assertIn("ndc_11", body.splitlines()[0])
        # unknown table → 404
        try:
            self._get("/rxnorm/export.csv?table=bogus")
            self.fail("expected HTTP 404")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)

    def test_seed_post_populates_then_resolves(self):
        # POST the seed action (urllib follows the 303 to /rxnorm).
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/rxnorm/seed", data=b"",
            method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            self.assertEqual(resp.status, 200)
        # Now the API reports a populated crosswalk and an NDC resolves.
        status, body = self._get("/api/rxnorm?ndc=0409-1896-20")
        data = json.loads(body)
        self.assertGreater(data["summary"]["counts"]["dim_rxnorm_concept"], 0)
        self.assertEqual(
            data["ndc_lookup"]["match"]["current_rxcui"], "7052")


if __name__ == "__main__":
    unittest.main()
