"""International phase — the global healthcare-markets map (/markets/global).

Locks in the first international surface: the vendored world geo paths load,
the choropleth renderer emits valid SVG, the curated health-market dataset is
well-formed and joins to the map by ISO2, and the route renders a real map +
ranked table + provenance with no traceback.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWorldGeoPaths(unittest.TestCase):
    def test_paths_loaded(self):
        from rcm_mc.ui._world_geo_paths import (
            WORLD_COUNTRY_PATHS, WORLD_GEO_VIEWBOX,
        )
        self.assertEqual(len(WORLD_GEO_VIEWBOX), 4)
        self.assertGreater(len(WORLD_COUNTRY_PATHS), 150)
        for iso2 in ("US", "DE", "GB", "FR", "JP"):
            self.assertIn(iso2, WORLD_COUNTRY_PATHS)
            rec = WORLD_COUNTRY_PATHS[iso2]
            self.assertTrue(rec["d"].startswith("M"))
            self.assertTrue(rec["name"])
        # Antarctica dropped.
        self.assertNotIn("AQ", WORLD_COUNTRY_PATHS)


class TestWorldMapRenderer(unittest.TestCase):
    def test_renders_svg_with_shading(self):
        from rcm_mc.ui.world_geo_map import render_world_map
        h = render_world_map({"US": 16.6, "DE": 12.7}, metric_label="of GDP",
                             accent={"US"}, value_format=lambda v: f"{v:.1f}%")
        self.assertIn("<svg", h)
        self.assertIn('data-iso="US"', h)
        self.assertIn("16.6%", h)        # tooltip value
        self.assertIn("wgeo-legend", h)

    def test_empty_values_no_crash(self):
        from rcm_mc.ui.world_geo_map import render_world_map
        h = render_world_map({}, empty_message="No data yet.")
        self.assertIn("<svg", h)
        self.assertIn("No data yet.", h)


class TestHealthMarketsData(unittest.TestCase):
    def test_dataset_joins_to_map(self):
        from rcm_mc.data_public.global_health_markets import (
            HEALTH_MARKETS, health_exp_values, pe_active_markets, ranked_markets,
        )
        from rcm_mc.ui._world_geo_paths import WORLD_COUNTRY_PATHS
        self.assertGreaterEqual(len(HEALTH_MARKETS), 25)
        # Every market's ISO2 resolves on the world map.
        for iso2 in HEALTH_MARKETS:
            self.assertIn(iso2, WORLD_COUNTRY_PATHS, f"{iso2} not on map")
        # Values are plausible health-spend shares.
        for v in health_exp_values().values():
            self.assertTrue(0 < v < 25)
        # Ranked descending; US on top.
        rows = ranked_markets()
        self.assertEqual(rows[0]["iso2"], "US")
        self.assertGreaterEqual(rows[0]["health_pct_gdp"], rows[-1]["health_pct_gdp"])
        self.assertTrue(pe_active_markets())

    def test_summary_stats(self):
        from rcm_mc.data_public.global_health_markets import (
            HEALTH_MARKETS, summary_stats,
        )
        s = summary_stats()
        self.assertEqual(s["n_markets"], len(HEALTH_MARKETS))
        self.assertGreater(s["n_pe_active"], 0)
        self.assertLessEqual(s["n_pe_active"], s["n_markets"])
        self.assertTrue(0 < s["mean_all"] < 25)
        self.assertTrue(s["by_region"])
        # region breakdown sums back to the market count
        self.assertEqual(sum(b["count"] for b in s["by_region"]), s["n_markets"])


class TestPortfolioFootprint(unittest.TestCase):
    """INT-4: international deals — country-tagged deals surface on the global
    market views (the demo's Gland Pharma in India)."""

    def setUp(self):
        import os
        import tempfile
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.demo.kkr_demo import seed_kkr_demo
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "p.db"))
        self.store.init_db()
        seed_kkr_demo(self.store, run_dir=os.path.join(self.tmp.name, "r"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_portfolio_markets_groups_by_country(self):
        from rcm_mc.data_public.global_health_markets import portfolio_markets
        fp = portfolio_markets(self.store)
        self.assertIn("US", fp)
        self.assertIn("IN", fp)   # Gland Pharma
        self.assertTrue(any(d["deal_id"] == "gland_pharma" for d in fp["IN"]))
        # Empty/None store → empty footprint (no crash, no None).
        self.assertEqual(portfolio_markets(None), {})

    def test_global_page_shows_footprint(self):
        from rcm_mc.ui.data_public.global_markets_page import render_global_markets
        h = render_global_markets(self.store)
        self.assertIn("Your portfolio footprint", h)
        self.assertIn("/markets/country/IN", h)

    def test_country_page_shows_your_deals(self):
        from rcm_mc.ui.data_public.global_markets_page import render_country_profile
        h = render_country_profile("IN", self.store)
        self.assertIn("Your deals in India", h)
        self.assertIn("Gland", h)


class TestGlobalMarketsRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        PortfolioStore(os.path.join(cls.tmp.name, "p.db")).init_db()
        cls.port = _free_port()
        cls.srv, _ = build_server(port=cls.port,
                                  db_path=os.path.join(cls.tmp.name, "p.db"),
                                  host="127.0.0.1")
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        time.sleep(0.3)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def test_route_renders(self):
        with urllib.request.urlopen(self.base + "/markets/global", timeout=30) as r:
            code = r.getcode()
            b = r.read().decode("utf-8", "replace")
        self.assertEqual(code, 200)
        self.assertNotIn("Traceback (most recent call last)", b)
        self.assertIn("<svg", b)
        self.assertIn("Global healthcare markets", b)
        self.assertIn("United States", b)
        self.assertIn("OECD", b)        # provenance shown
        # INT-2: the comparison graph + region breakdown render too.
        self.assertIn("Health expenditure as % of GDP", b)
        self.assertIn("Mean spend by region", b)
        self.assertGreaterEqual(b.count("<svg"), 2)   # map + chart
        # INT-3: the map links each profiled country to its deep-dive page.
        self.assertIn("/markets/country/DE", b)

    def test_country_profile_route(self):
        with urllib.request.urlopen(self.base + "/markets/country/DE",
                                    timeout=30) as r:
            code = r.getcode()
            b = r.read().decode("utf-8", "replace")
        self.assertEqual(code, 200)
        self.assertNotIn("Traceback (most recent call last)", b)
        self.assertIn("Germany", b)
        self.assertIn("Global rank", b)
        self.assertIn("Europe markets", b)   # regional peer chart

    def test_unknown_country_graceful(self):
        with urllib.request.urlopen(self.base + "/markets/country/ZZ",
                                    timeout=30) as r:
            code = r.getcode()
            b = r.read().decode("utf-8", "replace")
        self.assertEqual(code, 200)
        self.assertIn("Market not tracked", b)
        self.assertNotIn("Traceback (most recent call last)", b)


class TestCountryDetailData(unittest.TestCase):
    def test_country_detail(self):
        from rcm_mc.data_public.global_health_markets import country_detail
        d = country_detail("de")   # case-insensitive
        self.assertIsNotNone(d)
        self.assertEqual(d["iso2"], "DE")
        self.assertEqual(d["name"], "Germany")
        self.assertTrue(1 <= d["rank"] <= d["n_total"])
        self.assertTrue(any(p["iso2"] == "DE" for p in d["region_peers"]))
        self.assertIsNone(country_detail("ZZ"))


if __name__ == "__main__":
    unittest.main()
