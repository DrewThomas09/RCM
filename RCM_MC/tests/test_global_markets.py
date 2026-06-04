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


if __name__ == "__main__":
    unittest.main()
