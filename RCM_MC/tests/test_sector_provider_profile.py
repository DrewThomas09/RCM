"""Single-provider deep-dive profiles for Home Health + Hospice.

Drill-down target from the sector screeners: /home-health/<ccn> and
/hospice/<ccn>. CCNs are taken from the live loaders so the tests survive a
data re-vendor. Asserts the profile renders identity + headline KPI + a
quality table + same-state peers (each linking to its own profile) + the
provenance / not-a-recommendation framing, that an unknown CCN is a 404, and
that the screener rows now link into the profiles. No external calls.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.home_health import load_home_health_providers
from rcm_mc.data.hospice import load_hospice_providers
from rcm_mc.server import build_server
from rcm_mc.ui.home_health_page import (
    render_home_health,
    render_home_health_profile,
)
from rcm_mc.ui.hospice_page import render_hospice, render_hospice_profile


def _a_ccn(providers) -> str:
    # A provider with a state set, so the peer/benchmark logic is exercised.
    for ccn, p in providers.items():
        if getattr(p, "state", ""):
            return ccn
    return next(iter(providers))


class HomeHealthProfileTests(unittest.TestCase):
    def setUp(self):
        self.providers = load_home_health_providers()
        self.ccn = _a_ccn(self.providers)
        self.html = render_home_health_profile(self.ccn)

    def test_renders_identity_and_header(self):
        self.assertIsNotNone(self.html)
        self.assertIn("ck-page-title", self.html)
        self.assertIn("HOME HEALTH AGENCY", self.html)
        # Real provider name + CCN in the header.
        self.assertIn(self.providers[self.ccn].provider_name.split("&")[0][:8], self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Provider identity", self.html)

    def test_quality_table_with_state_benchmark(self):
        self.assertIn("Publicly reported quality", self.html)
        self.assertIn("Quality star rating", self.html)
        self.assertIn("Discharge to community", self.html)
        # The per-metric "vs state avg" column header.
        self.assertIn("avg", self.html.lower())

    def test_same_state_peers_link_to_profiles(self):
        self.assertIn("Peers in", self.html)
        # At least one peer row links to another /home-health/<ccn> profile.
        import re
        links = re.findall(r'href="/home-health/(\d+)"', self.html)
        self.assertTrue([c for c in links if c != self.ccn])

    def test_provenance_and_framing(self):
        flat = " ".join(self.html.split())
        self.assertIn("6jpm-sxkc", flat)                       # source dataset
        self.assertIn("not a final investment recommendation", flat.lower())

    def test_back_link_to_screener(self):
        self.assertIn('href="/home-health"', self.html)

    def test_unknown_ccn_returns_none(self):
        self.assertIsNone(render_home_health_profile("000000"))
        self.assertIsNone(render_home_health_profile(""))

    def test_no_external_calls(self):
        # Same convention as the screener test: no map tiles / JS CDNs. The
        # shell's Google-Fonts preconnect (fonts.googleapis.com) is the
        # app-wide standard, so we match "maps.googleapis", not bare
        # "googleapis".
        low = self.html.lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "unpkg"):
            self.assertNotIn(bad, low)

    def test_screener_rows_link_into_profiles(self):
        # State view rows are now drill-down links.
        state = self.providers[self.ccn].state
        sh = render_home_health({"state": [state]})
        self.assertIn(f'/home-health/{self.ccn}"', sh)


class HospiceProfileTests(unittest.TestCase):
    def setUp(self):
        self.providers = load_hospice_providers()
        self.ccn = _a_ccn(self.providers)
        self.html = render_hospice_profile(self.ccn)

    def test_renders_identity_and_header(self):
        self.assertIsNotNone(self.html)
        self.assertIn("ck-page-title", self.html)
        self.assertIn("HOSPICE PROVIDER", self.html)
        self.assertIn(f"CCN {self.ccn}", self.html)
        self.assertIn("Provider identity", self.html)

    def test_quality_table_and_headline(self):
        self.assertIn("Publicly reported quality", self.html)
        self.assertIn("Hospice Care Index", self.html)
        self.assertIn("Composite process measure", self.html)

    def test_peers_and_provenance(self):
        self.assertIn("Peers in", self.html)
        flat = " ".join(self.html.split())
        self.assertIn("yc9t-dgbk", flat)
        self.assertIn("not a final investment recommendation", flat.lower())

    def test_back_link_and_unknown_ccn(self):
        self.assertIn('href="/hospice"', self.html)
        self.assertIsNone(render_hospice_profile("zzzzzz"))

    def test_screener_rows_link_into_profiles(self):
        state = self.providers[self.ccn].state
        sh = render_hospice({"state": [state]})
        self.assertIn(f'/hospice/{self.ccn}"', sh)


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class SectorProfileRouteTests(unittest.TestCase):
    """End-to-end through the HTTP layer: valid CCN 200, unknown CCN 404."""

    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start()
        cls.hh_ccn = _a_ccn(load_home_health_providers())
        cls.ho_ccn = _a_ccn(load_hospice_providers())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        import os
        os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse(); body = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, body

    def test_valid_profiles_200(self):
        self.assertEqual(self._get(f"/home-health/{self.hh_ccn}")[0], 200)
        self.assertEqual(self._get(f"/hospice/{self.ho_ccn}")[0], 200)

    def test_unknown_ccn_404(self):
        s_hh, b_hh = self._get("/home-health/000000")
        self.assertEqual(s_hh, 404)
        self.assertIn("Not Found", b_hh)
        s_ho, _ = self._get("/hospice/zzzzzz")
        self.assertEqual(s_ho, 404)

    def test_screener_still_200(self):
        self.assertEqual(self._get("/home-health")[0], 200)
        self.assertEqual(self._get("/hospice")[0], 200)


if __name__ == "__main__":
    unittest.main()
