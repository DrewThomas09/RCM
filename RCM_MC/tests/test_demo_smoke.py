"""Demo end-to-end smoke: every surface a partner touches must work.

The demo is the product's showcase, so it has to stay fully populated and
error-free across the whole partner walk-through — not just the handful of
pages a feature test happens to cover. This seeds the curated KKR portfolio
into a real HTTP server and asserts that every demo-critical surface returns
200, never renders a Python traceback, and (for the data-bearing pages)
actually contains KKR portfolio content.

If a future change empties a surface or 500s it under demo data, this test
fails loudly — that's the "all demo pages work, fully done" guarantee.
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


# Surfaces grouped by expectation. (path, must_contain_KKR_content?)
# Deal-specific paths use cotiviti (healthy) and envision (distressed).
_SURFACES = [
    # Landing + portfolio roll-ups — must show KKR deals.
    ("/app", True),
    ("/home", True),
    ("/portfolio", True),
    ("/portfolio/map", False),          # geographic — shades states, not names
    ("/portfolio/heatmap", True),
    ("/portfolio/monitor", True),
    ("/cohorts", False),                # cohort aggregates
    ("/alerts", True),
    ("/watchlist", False),
    ("/deals", False),                  # Deal Pipeline (sourcing stage); demo
                                        # deals are held, so correctly not here
    ("/deadlines", False),              # labels, not deal names, in the rail
    # Demo control surface + downloads.
    ("/demo", True),
    ("/demo/download/kkr-deals.json", True),
    ("/demo/download/kkr-deals.csv", True),
    # Owner / personal dashboards.
    ("/my/SB", False),
    ("/owner/JD", False),
    # Deal-specific deep links (cotiviti = green, envision = distressed).
    ("/deal/cotiviti", True),
    ("/deal/envision", True),
    ("/analysis/cotiviti", False),
    ("/hold/cotiviti", False),
    ("/ebitda-bridge/cotiviti", False),
    ("/value-tracker/cotiviti", False),
    ("/models/returns/cotiviti", False),
    ("/models/bridge/cotiviti", False),
]

_KKR_MARKERS = ("Cotiviti", "Envision", "BrightSpring", "Heartland", "KKR",
                "Gland", "PetVet", "Geode")


class TestDemoSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.demo.kkr_demo import seed_kkr_demo
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(db)
        store.init_db()
        seed_kkr_demo(store, run_dir=os.path.join(cls.tmp.name, "runs"))
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

    def test_all_demo_surfaces_render(self):
        failures = []
        for path, needs_kkr in _SURFACES:
            code, body = self._fetch(path)
            if code != 200:
                failures.append(f"{path}: HTTP {code}")
                continue
            if "Traceback (most recent call last)" in body:
                failures.append(f"{path}: server traceback in body")
                continue
            if needs_kkr and not any(m in body for m in _KKR_MARKERS):
                failures.append(f"{path}: no KKR content")
        self.assertEqual(failures, [], "demo surfaces with problems:\n  "
                         + "\n  ".join(failures))


if __name__ == "__main__":
    unittest.main()
