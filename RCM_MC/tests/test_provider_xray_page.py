"""CMS Provider X-Ray page + route (/diligence/xray).

Thin editorial-dossier view over the resolver + benchmarked report. Pins:
the search landing, the resolver table for ambiguous queries, the full report
(identity / signals / benchmark table / market context / questions /
limitations), honest not-found, the Diligence nav + palette entry, the curated
Guide context, route 200s, and no external prototype scripts/CDNs.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data.snf import load_snf_providers
from rcm_mc.server import build_server
from rcm_mc.ui.provider_xray_page import render_provider_xray


def _tx_snf() -> str:
    for c, p in load_snf_providers().items():
        if p.state == "TX":
            return c
    return next(iter(load_snf_providers()))


class RenderTests(unittest.TestCase):
    def test_landing_has_search_form(self):
        h = render_provider_xray({})
        self.assertIn("ck-xr-form", h)
        self.assertIn("Run X-Ray", h)
        self.assertIn("CCN, provider ID, or name", h)

    def test_report_has_all_sections(self):
        h = render_provider_xray({"ccn": _tx_snf(), "vertical": "nursing-homes"})
        self.assertIn("ck-xr-identity", h)        # identity header
        self.assertIn("ck-xr-signals", h)         # signal strip
        self.assertIn("Peer benchmarks", h)       # benchmark table
        self.assertIn("Market context", h)        # market panel
        self.assertIn("Suggested diligence questions", h)
        self.assertIn("Evidence", h)              # limitations panel
        self.assertIn("not an investment recommendation", h.lower())
        self.assertIn("not market share", h.lower())

    def test_multi_peer_benchmark_columns(self):
        h = render_provider_xray({"ccn": _tx_snf(), "vertical": "nursing-homes"})
        for col in ("National<br>%ile", "State<br>%ile", "Locality<br>%ile",
                    "Ownership<br>%ile"):
            self.assertIn(col, h)
        self.assertIn("z<br>(state)", h)

    def test_risk_indicators_section_not_a_forecast(self):
        h = render_provider_xray({"ccn": _tx_snf(), "vertical": "nursing-homes"})
        self.assertIn("Risk indicators", h)
        self.assertIn("leading signals, not forecasts", h)
        self.assertIn("NOT trained predictive models", h)

    def test_shares_hcris_xray_kit_grammar(self):
        # Part 3: CMS X-Ray uses the shared xray_kit (navy ribbons + .xr scope
        # + kit tokens) so it matches HCRIS X-Ray, not a generic sector table.
        h = render_provider_xray({"ccn": _tx_snf(), "vertical": "nursing-homes"})
        self.assertIn('<div class="xr">', h)
        self.assertIn("xr-ribbon", h)
        self.assertIn("--xr-navy:#0d2336", h)   # kit tokens resolve in .xr scope

    def test_not_found_is_honest(self):
        h = render_provider_xray({"q": "ZZZZZZ"})
        self.assertIn("No match", h)
        self.assertIn("leading zeroes matter", h)

    def test_hospital_points_to_native_profile(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        hccn = str(_get_latest_per_ccn().iloc[0]["ccn"])
        h = render_provider_xray({"ccn": hccn, "vertical": "hospital"})
        self.assertIn("ck-xr-identity", h)
        self.assertIn(f"/hospital/{hccn}", h)     # native profile link

    def test_no_external_scripts(self):
        h = render_provider_xray({"ccn": _tx_snf(), "vertical": "nursing-homes"})
        low = h.lower()
        for bad in ("unpkg", "react", "babel", "mapbox", "leaflet"):
            self.assertNotIn(bad, low)


class NavAndGuideTests(unittest.TestCase):
    def test_diligence_subnav_has_cms_xray(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        hrefs = [i["href"] for i in _SUB_NAV["diligence"]]
        self.assertIn("/diligence/xray", hrefs)

    def test_palette_has_cms_xray(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = [m["route"] for m in _DEFAULT_PALETTE_MODULES]
        self.assertIn("/diligence/xray", routes)

    def test_guide_context_curated(self):
        from rcm_mc.assistant.context.get_page_context import get_page_context
        res = get_page_context("/diligence/xray")
        self.assertTrue(res.found)
        self.assertGreaterEqual(len(res.context.common_questions), 8)


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False); cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.ccn = _tx_snf()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        import os; os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path); r = c.getresponse(); b = r.read().decode("utf-8", "replace"); c.close()
        return r.status, b

    def test_routes(self):
        self.assertEqual(self._get("/diligence/xray")[0], 200)
        s, b = self._get(f"/diligence/xray?ccn={self.ccn}&vertical=nursing-homes")
        self.assertEqual(s, 200)
        self.assertIn("Peer benchmarks", b)
        self.assertEqual(self._get("/diligence/xray?q=ZZZZZZ")[0], 200)


if __name__ == "__main__":
    unittest.main()
