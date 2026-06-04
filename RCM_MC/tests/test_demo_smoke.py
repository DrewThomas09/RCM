"""Demo end-to-end smoke: every surface a partner touches must work.

The demo is the product's showcase, so it has to stay fully populated and
error-free across the whole partner walk-through — not just the handful of
pages a feature test happens to cover. This seeds the curated KKR portfolio
into a real HTTP server and asserts that every demo-critical surface returns
200, never renders a Python traceback, and (for the data-bearing pages)
actually contains KKR portfolio content.

It checks two layers: a curated set of portfolio/landing/demo surfaces, and
*every* deal in the portfolio across the core deal-detail routes — so a
regression that breaks a single deal, or any one surface, fails loudly. This
is the "all demo pages work, fully done" guarantee for the whole demo arc.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# Curated surfaces. (path, must_contain_KKR_content?)
_SURFACES = [
    ("/app", True), ("/home", True), ("/portfolio", True),
    ("/portfolio/map", False), ("/portfolio/heatmap", True),
    ("/portfolio/monitor", True), ("/portfolio/regression", False),
    ("/portfolio/risk-scan", False), ("/portfolio/monte-carlo", False),
    ("/cohorts", False), ("/alerts", True), ("/watchlist", False),
    ("/deals", False), ("/deadlines", False), ("/covenant-monitor", False),
    ("/hold-analysis", False), ("/runs", False), ("/lp-update", False),
    ("/compare", False),
    ("/demo", True), ("/demo/download/kkr-deals.json", True),
    ("/demo/download/kkr-deals.csv", True),
    ("/my/SB", False), ("/owner/JD", False),
]

# Every deal is exercised across these core deal-detail routes.
_DEAL_ROUTES = ["/deal/{}", "/analysis/{}", "/hold/{}", "/ebitda-bridge/{}",
                "/models/returns/{}", "/models/bridge/{}"]

_KKR_MARKERS = ("Cotiviti", "Envision", "BrightSpring", "Heartland", "KKR",
                "Gland", "PetVet", "Geode")


class TestDemoSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.demo.kkr_demo import seed_kkr_demo, KKR_DEMO_DEALS
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(db)
        store.init_db()
        seed_kkr_demo(store, run_dir=os.path.join(cls.tmp.name, "runs"))
        cls.deal_ids = [s["id"] for s in KKR_DEMO_DEALS]
        from rcm_mc.server import build_server
        cls.port = _free_port()
        cls.srv, _ = build_server(port=cls.port, db_path=db, host="127.0.0.1")
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        time.sleep(0.3)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _fetch(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=40) as r:
                return r.getcode(), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def test_curated_surfaces_render(self):
        failures = []
        for path, needs_kkr in _SURFACES:
            code, body = self._fetch(path)
            if code != 200:
                failures.append(f"{path}: HTTP {code}")
            elif "Traceback (most recent call last)" in body:
                failures.append(f"{path}: traceback")
            elif needs_kkr and not any(m in body for m in _KKR_MARKERS):
                failures.append(f"{path}: no KKR content")
        self.assertEqual(failures, [], "surfaces with problems:\n  "
                         + "\n  ".join(failures))

    def test_every_deal_renders(self):
        failures = []
        for did in self.deal_ids:
            for tmpl in _DEAL_ROUTES:
                path = tmpl.format(did)
                code, body = self._fetch(path)
                if code != 200:
                    failures.append(f"{path}: HTTP {code}")
                elif "Traceback (most recent call last)" in body:
                    failures.append(f"{path}: traceback")
        self.assertEqual(failures, [], "deal surfaces with problems:\n  "
                         + "\n  ".join(failures))


if __name__ == "__main__":
    unittest.main()
