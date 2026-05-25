"""PEdesk Market Intelligence loader — licensed SimplyAnalytics-derived data.

Data is the normalized export (state-level % Age 65+, FIPS-keyed). Tests assert
the variable catalog + values load, FIPS leading zeros are preserved, real
national percentiles compute, ranking works, screenshot-only files are NOT
treated as data, missing values stay missing (no fabrication), and the source
is registered. No runtime network.
"""
from __future__ import annotations

import csv
import http.client
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from rcm_mc.data import market_intel as mi


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class MarketIntelDataTests(unittest.TestCase):
    def test_variable_catalog_loads(self):
        vs = mi.load_market_variables()
        self.assertTrue(vs)
        v = mi.load_market_variable("age_65_plus_pct")
        self.assertIsNotNone(v)
        self.assertEqual(v["category"], "AGE")
        self.assertEqual(v["source"], "SimplyAnalytics (licensed)")
        self.assertTrue(v["diligence_use"])

    def test_state_values_and_fips_preserved(self):
        rows = mi.load_market_values("state")
        self.assertGreaterEqual(len(rows), 50)
        # FIPS keeps the leading zero (Alabama = "01", not "1").
        al = next(r for r in rows if r["geo_name"] == "Alabama")
        self.assertEqual(al["fips"], "01")
        self.assertEqual(len(al["fips"]), 2)

    def test_percentiles_real_and_bounded(self):
        rows = mi.rank_markets("age_65_plus_pct", "state")
        self.assertTrue(rows)
        pcts = [float(r["percentile_national"]) for r in rows]
        self.assertTrue(all(0 <= p <= 100 for p in pcts))
        # Highest-senior market ranks at/near the top percentile.
        self.assertGreater(float(rows[0]["percentile_national"]), 90)

    def test_ranking_is_descending_real_values(self):
        rows = mi.rank_markets("age_65_plus_pct", "state", limit=5)
        vals = [float(r["value"]) for r in rows]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_profile_for_fips(self):
        fl = mi.market_profile_for_geo("12")  # Florida
        self.assertEqual(fl["geo_name"], "Florida")
        self.assertIn("age_65_plus_pct", fl["variables"])

    def test_provider_supply_export_required_is_empty_not_fabricated(self):
        # NAICS 621111 provider counts shown in screenshots but NOT yet exported
        # → loader returns [] honestly (never invented).
        self.assertEqual(mi.provider_supply_for_naics("621111"), [])

    def test_no_screenshot_data_committed(self):
        # Only tabular-derived CSVs are committed; no .png/.xlsx under data/.
        d = Path(mi.__file__).resolve().parent.parent.parent / "data" / "market_intel"
        bad = list(d.glob("*.png")) + list(d.glob("*.xlsx"))
        self.assertEqual(bad, [], f"raw files committed: {bad}")

    def test_source_registered(self):
        src = mi.market_intel_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "market_intel")
        self.assertIn("simplyanalytics", str(src[0]).lower())


class MarketGeoRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import os
        os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        b = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, b

    def test_index_renders_with_map_and_source(self):
        s, b = self._get("/market-intel/geo")
        self.assertEqual(s, 200)
        self.assertIn("Market Intelligence", b)
        self.assertIn("usgeo-state", b)               # real choropleth, not screenshot
        self.assertIn("Licensed market data derived", b)
        self.assertIn("Export backlog", b)            # honest about missing exports

    def test_state_profile_renders(self):
        s, b = self._get("/market-intel/geo/12")      # Florida
        self.assertEqual(s, 200)
        self.assertIn("Florida", b)

    def test_unknown_fips_safe(self):
        s, b = self._get("/market-intel/geo/99")
        self.assertEqual(s, 200)
        self.assertIn("not found", b.lower())

    def test_existing_market_intel_route_unaffected(self):
        # The financial /market-intel page must still resolve (not shadowed).
        s, _ = self._get("/market-intel")
        self.assertEqual(s, 200)

    def test_login_unaffected(self):
        s, _ = self._get("/login")
        self.assertIn(s, (200, 302, 303))


if __name__ == "__main__":
    unittest.main()
