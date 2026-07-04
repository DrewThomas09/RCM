"""Tests for the Risk-Adjusted Benchmarking UI surface."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing

from rcm_mc.ui.risk_adjusted_benchmark_page import (
    render_risk_adjusted_benchmark_page,
)

_ROUTE = "/diligence/risk-adjusted-benchmark"


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RenderTests(unittest.TestCase):

    def test_landing_renders_form_and_example(self):
        h = render_risk_adjusted_benchmark_page()
        self.assertIn("Risk-Adjusted Benchmarking", h)
        self.assertIn("Run benchmark", h)        # the form button
        self.assertIn("Worked example", h)
        self.assertIn("[RA1]", h)

    def test_result_path_computes_oe(self):
        qs = {
            "metric": ["cost_pmpm"], "target": ["130"], "raf": ["1.30"],
            "peers": ["100, 110, 90, 105"], "peer_rafs": ["1.0,1.0,1.0,1.0"],
            "lower": ["1"],
        }
        h = render_risk_adjusted_benchmark_page(qs)
        self.assertIn("O/E Ratio", h)
        self.assertIn("IN_LINE", h)              # sicker panel → in line

    def test_true_outlier_flagged(self):
        qs = {
            "metric": ["cost_pmpm"], "target": ["140"], "raf": ["1.0"],
            "peers": ["100,100,100,100"], "lower": ["1"],
        }
        h = render_risk_adjusted_benchmark_page(qs)
        self.assertIn("OUTLIER", h)

    def test_bad_input_does_not_crash(self):
        # Garbage input must fall back gracefully (no exception, still a page).
        for qs in (
            {"target": ["abc"], "peers": ["100,110"]},
            {"target": ["100"], "peers": ["not,numbers,xyz"]},
            {"target": ["100"], "raf": ["0"], "peers": ["100"]},
            {"target": ["100"], "peers": ["100,110"], "peer_rafs": ["1.0"]},
        ):
            h = render_risk_adjusted_benchmark_page(qs)
            self.assertIn("Risk-Adjusted Benchmarking", h)

    def test_empty_is_landing(self):
        self.assertIn("Worked example", render_risk_adjusted_benchmark_page({}))


class RegistrationTests(unittest.TestCase):

    def test_in_sub_nav(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = {e["href"] for e in _SUB_NAV["diligence"]}
        self.assertIn(_ROUTE, hrefs)

    def test_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn(_ROUTE, routes)


class RouteTests(unittest.TestCase):

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

    def _get(self, path: str) -> int:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=15,
            ) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_landing_200(self):
        self.assertEqual(self._get(_ROUTE), 200)

    def test_result_200(self):
        q = urllib.parse.urlencode({
            "metric": "cost_pmpm", "target": "130", "raf": "1.30",
            "peers": "100,110,90,105", "lower": "1",
        })
        self.assertEqual(self._get(f"{_ROUTE}?{q}"), 200)


if __name__ == "__main__":
    unittest.main()
