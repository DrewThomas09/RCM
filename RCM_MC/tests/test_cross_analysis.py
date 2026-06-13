"""Tests for Cross-Dataset Analysis — the correlation engine + page.

Exercises the join/correlation math (None-safe, real stats), the query
resolver, the JSON payload, the page render (scatter + stat block), and the
HTTP route + nav wiring.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.diligence import cross_analysis as ca
from rcm_mc.ui.cross_analysis_page import render_cross_analysis_page


class EngineTests(unittest.TestCase):
    def test_state_grain_universe_is_joinable(self):
        sgs = ca.state_grain_datasets()
        self.assertGreaterEqual(len(sgs), 10)
        for d in sgs:
            self.assertEqual(d.grain, "state")

    def test_correlate_returns_real_stats(self):
        r = ca.correlate("ma_penetration", "penetration_pct",
                         "hcris_state", "operating_margin")
        self.assertTrue(r["ok"])
        self.assertEqual(r["stats"]["n"], len(r["table"]["rows"]))
        self.assertGreaterEqual(r["stats"]["n"], 40)   # ~51 states joined
        rr = r["stats"]["pearson_r"]
        self.assertIsNotNone(rr)
        self.assertGreaterEqual(rr, -1.0)
        self.assertLessEqual(rr, 1.0)
        # R² is r squared.
        self.assertAlmostEqual(r["stats"]["r2"], rr * rr, places=9)

    def test_pearson_matches_known_value(self):
        # Perfect positive line -> r == 1.
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        self.assertAlmostEqual(ca._pearson(xs, ys), 1.0, places=9)
        # Perfect negative line -> r == -1.
        self.assertAlmostEqual(ca._pearson(xs, ys[::-1]), -1.0, places=9)

    def test_join_drops_states_missing_either_value(self):
        # Build maps where Y is missing a state X has.
        dx = ca.fa.DATASETS["state_demographics"]
        xmap = ca._value_map(dx, "uninsured_rate")
        self.assertTrue(xmap)
        # No NaN/inf leaks into the value map.
        for v in xmap.values():
            self.assertFalse(math.isnan(v) or math.isinf(v))

    def test_constant_series_has_no_correlation(self):
        self.assertIsNone(ca._pearson([1, 1, 1, 1], [1, 2, 3, 4]))

    def test_small_n_returns_none(self):
        self.assertIsNone(ca._pearson([1, 2], [1, 2]))

    def test_nonexistent_dataset_fails_gracefully(self):
        r = ca.correlate("nope", "x", "hcris_state", "operating_margin")
        self.assertFalse(r["ok"])


class ResolveAndJsonTests(unittest.TestCase):
    def test_defaults_resolve_to_a_populated_pair(self):
        spec = ca.resolve_query({})
        self.assertTrue(spec["result"]["ok"])
        self.assertTrue(spec["result"]["table"]["rows"])

    def test_invalid_ids_clamp(self):
        spec = ca.resolve_query({"x": ["bogus"], "y": ["bogus"],
                                 "xm": ["nope"], "ym": ["nope"]})
        ids = {d.id for d in ca.state_grain_datasets()}
        self.assertIn(spec["x_id"], ids)
        self.assertIn(spec["y_id"], ids)

    def test_json_payload_shape(self):
        p = ca.build_cross_analysis({})
        for k in ("selected", "stats", "ok", "joined", "catalog"):
            self.assertIn(k, p)
        self.assertEqual(len(p["catalog"]), len(ca.state_grain_datasets()))
        self.assertTrue(p["joined"])


class PageTests(unittest.TestCase):
    def test_page_renders_scatter_and_stats(self):
        h = render_cross_analysis_page({})
        self.assertIn("Cross-Dataset Analysis", h)
        self.assertIn("<svg", h)
        self.assertIn("Correlation (r)", h)
        self.assertIn("R²", h)

    def test_page_handles_custom_pair(self):
        h = render_cross_analysis_page({
            "x": ["state_demographics"], "xm": ["uninsured_rate"],
            "y": ["oig_exclusions_state"], "ym": ["exclusions"]})
        self.assertIn("<svg", h)

    def test_wired_into_nav_and_breadcrumb(self):
        import inspect
        from rcm_mc.ui import _chartis_kit as kit
        src = inspect.getsource(kit)
        self.assertIn('"/cross-analysis"', src)
        self.assertIn('"/cross-analysis": "research"', src)


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

    def test_page_route_200(self):
        resp = self._get("/cross-analysis?x=hcahps&xm=overall_rating_9_10"
                         "&y=snf_turnover&ym=median_turnover")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Cross-Dataset Analysis", body)
        self.assertIn("<svg", body)

    def test_json_route_200(self):
        import json
        resp = self._get("/api/cross-analysis")
        self.assertEqual(resp.status, 200)
        payload = json.loads(resp.read().decode())
        self.assertIn("stats", payload)


if __name__ == "__main__":
    unittest.main()
