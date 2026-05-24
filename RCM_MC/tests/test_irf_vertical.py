"""IRF vertical — loader + screener + profile + market intel + route.

Data is the vendored CMS Inpatient Rehabilitation Facility Compare snapshot
(real, official, ~1.2k facilities) — no synthetic data, no runtime network.
The universe is small, so per-state samples can be tiny. Readmission and
Medicare-spending measures are lower-is-better and stay out of the profile's
"higher=better" percentile table.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.irf import (
    irf_provider_by_ccn,
    irf_providers_for_state,
    load_irf_providers,
    load_irf_quality,
    load_irf_summary_by_state,
)
from rcm_mc.server import build_server
from rcm_mc.ui.irf_page import render_irf, render_irf_profile


def _a_ccn():
    for ccn, p in load_irf_providers().items():
        if p.state and p.county:
            return ccn
    return next(iter(load_irf_providers()))


class IrfLoaderTests(unittest.TestCase):
    def test_load_and_align(self):
        P, Q = load_irf_providers(), load_irf_quality()
        self.assertGreater(len(P), 800)
        self.assertEqual(set(P) - set(Q), set())
        ccn = _a_ccn()
        self.assertEqual(P[ccn], irf_provider_by_ccn(ccn))
        self.assertIn("Inpatient Rehabilitation Facility Compare", P[ccn].source)

    def test_state_summary_and_filter(self):
        S = load_irf_summary_by_state()
        self.assertGreater(len(S), 30)
        st = load_irf_providers()[_a_ccn()].state
        rows = irf_providers_for_state(st)
        self.assertTrue(rows and all(p.state == st for p in rows))
        self.assertIn("avg_dtc", S[st])


class IrfScreenerTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.state = load_irf_providers()[self.ccn].state

    def test_national_and_caveats(self):
        html = render_irf()
        self.assertIn("ck-page-title", html)
        self.assertIn("INPATIENT REHAB", html)
        self.assertIn("not a final investment recommendation", html.lower())
        self.assertIn("lower-is-better", html.lower())

    def test_state_market_intel_and_links(self):
        html = render_irf({"state": [self.state]})
        self.assertIn("market summary", html)
        self.assertIn("County competition", html)
        self.assertIn(f'/inpatient-rehab/{self.ccn}"', html)

    def test_no_external_calls(self):
        low = render_irf().lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "data.cms.gov",
                    "tile.openstreetmap", "unpkg"):
            self.assertNotIn(bad, low)


class IrfProfileTests(unittest.TestCase):
    def setUp(self):
        self.ccn = _a_ccn()
        self.html = render_irf_profile(self.ccn)
        self.p = load_irf_providers()[self.ccn]

    def test_profile_core(self):
        self.assertIsNotNone(self.html)
        self.assertIn("INPATIENT REHAB FACILITY", self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Discharge to community", self.html)
        self.assertIn(f"Peers in {self.p.state}", self.html)

    def test_lower_is_better_rates_not_in_percentile_table(self):
        # Readmission + MSPB are lower-is-better → must NOT be framed in the
        # "higher = better" percentile metric table.
        self.assertNotIn("Potentially-preventable readmission", self.html)
        self.assertNotIn("Medicare spending per beneficiary", self.html)

    def test_unknown_ccn(self):
        self.assertIsNone(render_irf_profile("000000"))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class IrfRouteTests(unittest.TestCase):
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
        self.assertEqual(self._get("/inpatient-rehab")[0], 200)
        self.assertEqual(self._get(f"/inpatient-rehab/{self.ccn}")[0], 200)
        s, b = self._get("/inpatient-rehab/000000")
        self.assertEqual(s, 404)
        self.assertIn("Not Found", b)

    def test_curated_guide_context(self):
        from rcm_mc.assistant.context.get_page_context import get_page_context
        res = get_page_context("/inpatient-rehab")
        self.assertTrue(res.found)
        self.assertGreaterEqual(len(res.context.common_questions), 8)


if __name__ == "__main__":
    unittest.main()
