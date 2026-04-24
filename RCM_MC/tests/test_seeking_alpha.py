"""Tests for the Seeking Alpha market-intel surface."""
from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.market_intel import (
    PETransaction, list_transactions, multiple_band_by_specialty,
    sponsor_activity, transactions_for_specialty,
)


class PETransactionLibraryTests(unittest.TestCase):

    def test_library_loads_transactions(self):
        txs = list_transactions()
        self.assertGreater(len(txs), 5)
        # All must have date, target, sponsor
        for t in txs:
            self.assertTrue(t.date)
            self.assertTrue(t.target)
            self.assertTrue(t.sponsor)
            self.assertTrue(t.specialty)

    def test_sort_is_most_recent_first(self):
        txs = list_transactions()
        for a, b in zip(txs, txs[1:]):
            self.assertGreaterEqual(a.date, b.date)

    def test_transactions_for_specialty_filters(self):
        txs = transactions_for_specialty("DERMATOLOGY")
        self.assertGreater(len(txs), 0)
        for t in txs:
            self.assertEqual(t.specialty.upper(), "DERMATOLOGY")

    def test_transactions_for_unknown_specialty_returns_empty(self):
        self.assertEqual(
            transactions_for_specialty("VETERINARY_MEDICINE"), [],
        )

    def test_transactions_for_empty_specialty_returns_empty(self):
        self.assertEqual(transactions_for_specialty(""), [])

    def test_sponsor_activity_counts(self):
        act = sponsor_activity(lookback_months=24)
        self.assertIsInstance(act, dict)
        if act:
            for sponsor, count in act.items():
                self.assertGreater(count, 0)

    def test_multiple_band_by_specialty(self):
        bands = multiple_band_by_specialty()
        self.assertGreater(len(bands), 0)
        for sp, b in bands.items():
            self.assertIn("median", b)
            self.assertIn("min", b)
            self.assertIn("max", b)
            self.assertLessEqual(b["min"], b["median"])
            self.assertLessEqual(b["median"], b["max"])

    def test_to_dict_roundtrip(self):
        txs = list_transactions()
        for t in txs[:3]:
            payload = t.to_dict()
            dumped = json.dumps(payload, default=str)
            reloaded = json.loads(dumped)
            self.assertEqual(reloaded["target"], t.target)


class SeekingAlphaUIRenderTests(unittest.TestCase):

    def test_default_render(self):
        from rcm_mc.ui.seeking_alpha_page import render_seeking_alpha_page
        html = render_seeking_alpha_page({})
        self.assertIn("Seeking Alpha", html)
        self.assertIn("HCA", html)
        self.assertIn("EV / EBITDA", html)
        self.assertIn("PE transactions", html)
        self.assertIn("data-sortable", html)
        self.assertIn("data-export-json", html)

    def test_specialty_filter(self):
        from rcm_mc.ui.seeking_alpha_page import render_seeking_alpha_page
        html = render_seeking_alpha_page({"specialty": ["DIALYSIS"]})
        self.assertIn("Seeking Alpha", html)
        # Dialysis filter limits tx list but page still renders comps

    def test_unknown_specialty_does_not_crash(self):
        from rcm_mc.ui.seeking_alpha_page import render_seeking_alpha_page
        html = render_seeking_alpha_page(
            {"specialty": ["VETERINARY_MEDICINE"]},
        )
        self.assertIn("Seeking Alpha", html)
        # Should still render the public comps + sector heatmap

    def test_sponsor_filter_partial_match(self):
        from rcm_mc.ui.seeking_alpha_page import render_seeking_alpha_page
        html = render_seeking_alpha_page({"sponsor": ["Audax"]})
        self.assertIn("Audax", html)


class HTTPEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import http.server
        import socket
        import threading
        from rcm_mc.server import RCMHandler
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_seeking_alpha_page_responds(self):
        url = (
            f"http://127.0.0.1:{self.port}/market-intel/seeking-alpha"
        )
        r = urlopen(url, timeout=15)
        self.assertEqual(r.status, 200)
        body = r.read().decode("utf-8")
        self.assertIn("Seeking Alpha", body)
        self.assertIn("HCA", body)

    def test_seeking_alpha_with_filters(self):
        qs = urlencode({
            "specialty": "DERMATOLOGY", "sponsor": "Harvest",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/market-intel/seeking-alpha?{qs}"
        )
        r = urlopen(url, timeout=15)
        self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()
