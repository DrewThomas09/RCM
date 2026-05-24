"""LTCH vertical — loader + screener + profile + market intel + route.

Data is the vendored CMS Long-Term Care Hospital Compare snapshot (real,
official, ~320 facilities) — no synthetic data, no runtime network. The
universe is tiny, so per-state samples are often single-digit. Readmission
and Medicare-spending measures are lower-is-better and stay out of the
profile's "higher=better" percentile table.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.ltch import (
    load_ltch_providers,
    load_ltch_quality,
    load_ltch_summary_by_state,
    ltch_provider_by_ccn,
    ltch_providers_for_state,
)
from rcm_mc.server import build_server
from rcm_mc.ui.ltch_page import render_ltch, render_ltch_profile


def _a_ccn():
    for ccn, p in load_ltch_providers().items():
        if p.state and p.county:
            return ccn
    return next(iter(load_ltch_providers()))


class LtchLoaderTests(unittest.TestCase):
    def test_load_and_align(self):
        P, Q = load_ltch_providers(), load_ltch_quality()
        self.assertGreater(len(P), 250)
        self.assertEqual(set(P) - set(Q), set())
        ccn = _a_ccn()
        self.assertEqual(P[ccn], ltch_provider_by_ccn(ccn))
        self.assertIn("Long-Term Care Hospital Compare", P[ccn].source)

    def test_state_summary_and_filter(self):
        S = load_ltch_summary_by_state()
        self.assertGreater(len(S), 20)
        st = load_ltch_providers()[_a_ccn()].state
        rows = ltch_providers_for_state(st)
        self.assertTrue(rows and all(p.state == st for p in rows))
        self.assertIn("avg_dtc", S[st])


class LtchScreenerTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.state = load_ltch_providers()[self.ccn].state

    def test_national_and_caveats(self):
        html = render_ltch()
        self.assertIn("ck-page-title", html)
        self.assertIn("LONG-TERM CARE HOSPITAL", html)
        self.assertIn("not a final investment recommendation", html.lower())
        self.assertIn("lower-is-better", html.lower())

    def test_state_market_intel_and_links(self):
        html = render_ltch({"state": [self.state]})
        self.assertIn("market summary", html)
        self.assertIn("County competition", html)
        self.assertIn(f'/long-term-care-hospital/{self.ccn}"', html)

    def test_no_external_calls(self):
        low = render_ltch().lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "data.cms.gov",
                    "tile.openstreetmap", "unpkg"):
            self.assertNotIn(bad, low)


class LtchProfileTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.html = render_ltch_profile(self.ccn)
        self.p = load_ltch_providers()[self.ccn]

    def test_profile_core(self):
        self.assertIsNotNone(self.html)
        self.assertIn("LONG-TERM CARE HOSPITAL", self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Discharge to community", self.html)
        self.assertIn(f"Peers in {self.p.state}", self.html)

    def test_lower_is_better_rates_not_in_percentile_table(self):
        # Readmission + MSPB are lower-is-better → must NOT be framed in the
        # "higher = better" percentile metric table.
        self.assertNotIn("Potentially-preventable readmission", self.html)
        self.assertNotIn("Medicare spending per beneficiary", self.html)

    def test_unknown_ccn(self):
        self.assertIsNone(render_ltch_profile("000000"))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class LtchRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False); cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.ccn = _a_ccn()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        import os; os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path); r = c.getresponse(); b = r.read().decode("utf-8","replace"); c.close()
        return r.status, b

    def test_routes(self):
        self.assertEqual(self._get("/long-term-care-hospital")[0], 200)
        self.assertEqual(self._get(f"/long-term-care-hospital/{self.ccn}")[0], 200)
        s, b = self._get("/long-term-care-hospital/000000")
        self.assertEqual(s, 404)
        self.assertIn("Not Found", b)

    def test_curated_guide_context(self):
        from rcm_mc.assistant.context.get_page_context import get_page_context
        res = get_page_context("/long-term-care-hospital")
        self.assertTrue(res.found)
        self.assertGreaterEqual(len(res.context.common_questions), 8)


if __name__ == "__main__":
    unittest.main()
