"""Tests for SeekingChartis v2 features: methodology, denial, market, dashboard.

 1. /methodology renders.
 2. /models/denial/<deal> renders denial analysis.
 3. /models/market/<deal> renders market analysis.
 4. /deal/<deal> shows dashboard for new deals.
 5. All model pages cross-link correctly.
"""
from __future__ import annotations

import os as _os
import pytest as _pytest

# v2-shell-only tests. The editorial reskin was reverted at commit
# d8bfac4; these assertions check for v2-only HTML markers (ck-topbar,
# shell-v2 branding) that no longer exist on the legacy shell. Skipped
# unless CHARTIS_UI_V2=1 — flip the env var when v2 ships again to
# automatically re-enable.
pytestmark = _pytest.mark.skipif(
    not _os.environ.get('CHARTIS_UI_V2'),
    reason='v2 editorial shell reverted at d8bfac4; tests assert v2-only markers'
)

import json
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


class TestMethodology(unittest.TestCase):

    def test_methodology_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/methodology",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Methodology", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("HCRIS", body)
                self.assertIn("SeekingChartis Score", body)
                self.assertIn("Regression", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealModels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        store = PortfolioStore(cls.tf.name)
        store.upsert_deal("d1", name="Test Hospital",
                          profile={"denial_rate": 14, "days_in_ar": 50,
                                   "net_revenue": 300e6, "bed_count": 250,
                                   "state": "AL"})
        cls.server, cls.port = _start(cls.tf.name)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        os.unlink(cls.tf.name)

    def test_denial_page(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/denial/d1",
        ) as r:
            body = r.read().decode()
        self.assertIn("Denial", body)
        self.assertIn("SeekingChartis", body)
        self.assertIn("ck-topbar", body)

    def test_market_page(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/market/d1",
        ) as r:
            body = r.read().decode()
        self.assertIn("Market Analysis", body)
        self.assertIn("HHI", body)
        self.assertIn("Moat", body)

    def test_deal_dashboard_for_new_deal(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/deal/d1",
        ) as r:
            body = r.read().decode()
        self.assertIn("Test Hospital", body)
        self.assertIn("DCF", body)
        self.assertIn("LBO", body)
        self.assertIn("Market", body)

    def test_model_cross_links(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/models/dcf/d1",
        ) as r:
            body = r.read().decode()
        self.assertIn("/models/lbo/d1", body)
        self.assertIn("/models/financials/d1", body)

    def test_analysis_landing_has_model_links(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/analysis",
        ) as r:
            body = r.read().decode()
        self.assertIn("models/dcf/d1", body)
        self.assertIn("models/denial/d1", body)
        self.assertIn("models/market/d1", body)


if __name__ == "__main__":
    unittest.main()
