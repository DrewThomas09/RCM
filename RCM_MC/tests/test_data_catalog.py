"""Tests for the data catalog inventory + UI page + HTTP route."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class TestCatalogInventory(unittest.TestCase):
    def test_empty_store_is_empty(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.catalog import (
            inventory_data_sources,
            compute_data_estate_summary,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            entries = inventory_data_sources(store)
            # Tables for ingest sources don't exist yet; the
            # only definitions that match are those created by
            # init_db itself. Catalog should not crash on empty.
            self.assertIsInstance(entries, list)
            summary = compute_data_estate_summary(entries)
            self.assertEqual(summary["n_sources"],
                             len(entries))
        finally:
            tmp.cleanup()

    def test_catalog_picks_up_loaded_sources(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.catalog import inventory_data_sources
        from rcm_mc.data.census_demographics import (
            MarketDemographics, load_acs_demographics,
        )
        from rcm_mc.data.cdc_places import (
            CountyHealthStatistics, load_cdc_places,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()

            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa="33100", year=2023,
                    state="FL", population=6_200_000,
                    population_growth_5yr=0.04),
                MarketDemographics(
                    cbsa="12060", year=2023,
                    state="GA", population=6_300_000),
            ])
            load_cdc_places(store, [
                CountyHealthStatistics(
                    county_fips="13089", year=2023,
                    state="GA", diabetes_pct=12.5),
            ])

            entries = inventory_data_sources(store)
            ids = {e.source_id for e in entries}
            self.assertIn("census_demographics", ids)
            self.assertIn("cdc_places", ids)

            census = next(e for e in entries
                          if e.source_id
                          == "census_demographics")
            self.assertEqual(census.record_count, 2)
            self.assertIsNotNone(census.last_refreshed_at)
            # Just-loaded → freshness should be 0 days
            self.assertEqual(census.freshness_days, 0)
            self.assertIsNotNone(census.quality_score)
            self.assertIn("CBSA",
                          census.coverage_summary)
        finally:
            tmp.cleanup()

    def test_summary_aggregates(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.catalog import (
            inventory_data_sources,
            compute_data_estate_summary,
        )
        from rcm_mc.data.census_demographics import (
            MarketDemographics, load_acs_demographics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa=str(i).zfill(5), year=2023,
                    state="GA", population=100_000)
                for i in range(50)
            ])
            entries = inventory_data_sources(store)
            summary = compute_data_estate_summary(entries)
            self.assertGreaterEqual(summary["n_sources"], 1)
            self.assertGreaterEqual(
                summary["total_records"], 50)
            # Just-loaded → all sources should be fresh
            self.assertEqual(
                summary["fresh_sources"],
                summary["n_sources"])
            self.assertEqual(summary["stale_sources"], 0)
        finally:
            tmp.cleanup()


class TestQualityScoring(unittest.TestCase):
    def test_zero_records(self):
        from rcm_mc.data.catalog import _compute_quality_score
        self.assertIsNone(_compute_quality_score(0, 0, 5))

    def test_high_quality(self):
        """Lots of rows + many unique keys + recent → 0.7+."""
        from rcm_mc.data.catalog import _compute_quality_score
        score = _compute_quality_score(
            100_000, 5_000, freshness_days=5)
        self.assertGreaterEqual(score, 0.7)

    def test_stale_decays(self):
        from rcm_mc.data.catalog import _compute_quality_score
        fresh = _compute_quality_score(10_000, 1_000,
                                       freshness_days=10)
        stale = _compute_quality_score(10_000, 1_000,
                                       freshness_days=400)
        self.assertGreater(fresh, stale)

    def test_unknown_freshness_loses_freshness_component(self):
        from rcm_mc.data.catalog import _compute_quality_score
        score_known = _compute_quality_score(
            10_000, 1_000, freshness_days=10)
        score_unknown = _compute_quality_score(
            10_000, 1_000, freshness_days=None)
        # Gap should equal the freshness component (~0.3)
        self.assertAlmostEqual(
            score_known - score_unknown, 0.3, places=2)


class TestCatalogPageRender(unittest.TestCase):
    def test_empty_state(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.data_catalog_page import (
            render_data_catalog_page,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            html = render_data_catalog_page(store)
            self.assertIn("Data Catalog", html)
            # Empty-state text
            self.assertTrue(
                "No data sources loaded yet" in html
                or "Sources" in html)
        finally:
            tmp.cleanup()

    def test_with_sources(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.data_catalog_page import (
            render_data_catalog_page,
        )
        from rcm_mc.data.census_demographics import (
            MarketDemographics, load_acs_demographics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa="33100", year=2023, state="FL",
                    population=6_200_000),
            ])
            html = render_data_catalog_page(store)
            self.assertIn("Census ACS", html)
            self.assertIn("Quality", html)
            # KPI strip present
            self.assertIn("Sources", html)
            self.assertIn("Total records", html)
            # Quality badge text
            self.assertTrue(
                "high" in html or "medium" in html
                or "low" in html)
        finally:
            tmp.cleanup()


class TestCatalogHTTPRoute(unittest.TestCase):
    """End-to-end via real HTTP server (not mocked)."""

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET,
                           socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_route_renders(self):
        from rcm_mc.server import build_server
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.census_demographics import (
            MarketDemographics, load_acs_demographics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_acs_demographics(store, [
                MarketDemographics(
                    cbsa="33100", year=2023, state="FL",
                    population=6_200_000),
            ])
            port = self._free_port()
            srv, _handler = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                url = f"http://127.0.0.1:{port}/data/catalog"
                with urllib.request.urlopen(
                        url, timeout=5) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode()
                    self.assertIn("Data Catalog", body)
                    self.assertIn("Census ACS", body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
