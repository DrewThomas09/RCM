"""Dialysis vertical — loader + screener + profile + market intel.

Data is the vendored CMS Dialysis Facility Compare 'Listing by Facility'
snapshot (real, official, ~7.5k facilities) — no synthetic data, no runtime
network. Outcome rates are lower-is-better and stay out of the profile's
"higher=better" percentile table.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.dialysis import (
    dialysis_provider_by_ccn,
    dialysis_providers_for_state,
    load_dialysis_providers,
    load_dialysis_quality,
    load_dialysis_summary_by_state,
)
from rcm_mc.server import build_server
from rcm_mc.ui.dialysis_page import render_dialysis, render_dialysis_profile


def _a_ccn():
    for ccn, p in load_dialysis_providers().items():
        if p.state and p.county:
            return ccn
    return next(iter(load_dialysis_providers()))


class DialysisLoaderTests(unittest.TestCase):
    def test_load_and_align(self):
        P, Q = load_dialysis_providers(), load_dialysis_quality()
        self.assertGreater(len(P), 5000)
        self.assertEqual(set(P) - set(Q), set())
        ccn = _a_ccn()
        self.assertEqual(P[ccn], dialysis_provider_by_ccn(ccn))
        self.assertIn("Dialysis Facility Compare", P[ccn].source)

    def test_state_summary_and_filter(self):
        S = load_dialysis_summary_by_state()
        self.assertGreater(len(S), 40)
        st = load_dialysis_providers()[_a_ccn()].state
        rows = dialysis_providers_for_state(st)
        self.assertTrue(rows and all(p.state == st for p in rows))
        self.assertIn("avg_five_star", S[st])


class DialysisScreenerTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.state = load_dialysis_providers()[self.ccn].state

    def test_national_and_caveats(self):
        html = render_dialysis()
        self.assertIn("ck-page-title", html)
        self.assertIn("DIALYSIS", html)
        self.assertIn("not a final investment recommendation", html.lower())
        self.assertIn("lower-is-better", html.lower())

    def test_state_market_intel_and_links(self):
        html = render_dialysis({"state": [self.state]})
        self.assertIn("market summary", html)
        self.assertIn("County competition", html)
        self.assertIn(f'/dialysis/{self.ccn}"', html)

    def test_no_external_calls(self):
        low = render_dialysis().lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "data.cms.gov",
                    "tile.openstreetmap", "unpkg"):
            self.assertNotIn(bad, low)


class DialysisProfileTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.html = render_dialysis_profile(self.ccn)
        self.p = load_dialysis_providers()[self.ccn]

    def test_profile_core(self):
        self.assertIsNotNone(self.html)
        self.assertIn("DIALYSIS FACILITY", self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Overall 5-star rating", self.html)
        self.assertIn(f"Peers in {self.p.state}", self.html)

    def test_lower_is_better_rates_not_in_percentile_table(self):
        # Outcome rates must NOT be in the "higher = better" metric table.
        self.assertNotIn("Mortality rate", self.html)
        self.assertNotIn("Hospitalization rate", self.html)

    def test_unknown_ccn(self):
        self.assertIsNone(render_dialysis_profile("000000"))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class DialysisRouteTests(unittest.TestCase):
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
        self.assertEqual(self._get("/dialysis")[0], 200)
        self.assertEqual(self._get(f"/dialysis/{self.ccn}")[0], 200)
        s, b = self._get("/dialysis/000000")
        self.assertEqual(s, 404)
        self.assertIn("Not Found", b)

    def test_curated_guide_context(self):
        from rcm_mc.assistant.context.get_page_context import get_page_context
        res = get_page_context("/dialysis")
        self.assertTrue(res.found)
        self.assertGreaterEqual(len(res.context.common_questions), 8)


if __name__ == "__main__":
    unittest.main()
