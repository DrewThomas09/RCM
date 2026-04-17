"""Tests for SeekingChartis browser-rendered financial models.

 1. /models/dcf/<deal_id> renders DCF page.
 2. /models/lbo/<deal_id> renders LBO page.
 3. /models/financials/<deal_id> renders 3-statement page.
 4. All model pages have SeekingChartis branding.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestModelPages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        store = PortfolioStore(cls.tf.name)
        store.upsert_deal("test_deal", name="Test Hospital",
                          profile={"denial_rate": 14, "days_in_ar": 50,
                                   "net_revenue": 300e6, "ebitda_margin": 0.12,
                                   "bed_count": 250})
        cls.server, cls.port = _start(cls.tf.name)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        os.unlink(cls.tf.name)

    def test_dcf_page(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/dcf/test_deal",
        ) as r:
            body = r.read().decode()
        self.assertIn("DCF", body)
        self.assertIn("Enterprise Value", body)
        self.assertIn("SeekingChartis", body)
        self.assertIn("cad-topbar", body)

    def test_lbo_page(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/lbo/test_deal",
        ) as r:
            body = r.read().decode()
        self.assertIn("LBO", body)
        self.assertIn("IRR", body)
        self.assertIn("MOIC", body)
        self.assertIn("SeekingChartis", body)

    def test_financials_page(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/financials/test_deal",
        ) as r:
            body = r.read().decode()
        self.assertIn("Financials", body)
        self.assertIn("SeekingChartis", body)
        self.assertIn("cad-topbar", body)

    def test_dcf_has_projections(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/dcf/test_deal",
        ) as r:
            body = r.read().decode()
        self.assertIn("Cash Flow Projections", body)
        self.assertIn("Year", body)

    def test_model_cross_links(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/dcf/test_deal",
        ) as r:
            body = r.read().decode()
        self.assertIn("/models/lbo/test_deal", body)
        self.assertIn("/models/financials/test_deal", body)
        self.assertIn("/analysis/test_deal", body)


if __name__ == "__main__":
    unittest.main()
