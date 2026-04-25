"""Tests for CMS Hospital General Information ingestion + integration."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


class TestParser(unittest.TestCase):
    def test_parses_sample_csv(self):
        from rcm_mc.data.cms_hospital_general import (
            parse_general_csv, DEFAULT_GENERAL_SAMPLE_PATH,
        )
        records = parse_general_csv(DEFAULT_GENERAL_SAMPLE_PATH)
        self.assertGreaterEqual(len(records), 20)

    def test_5_star_hospitals_present(self):
        """Sample includes Hopkins / Mayo / Cleveland Clinic / NWMH /
        Houston Methodist / MSK as 5-star — regression guard."""
        from rcm_mc.data.cms_hospital_general import (
            parse_general_csv, DEFAULT_GENERAL_SAMPLE_PATH,
        )
        records = parse_general_csv(DEFAULT_GENERAL_SAMPLE_PATH)
        five_star = [r for r in records if r.overall_rating == 5]
        self.assertGreaterEqual(len(five_star), 5)

    def test_low_rated_present(self):
        """Sample includes 1- and 2-star hospitals so the
        low_quality_cluster insight has something to detect."""
        from rcm_mc.data.cms_hospital_general import (
            parse_general_csv, DEFAULT_GENERAL_SAMPLE_PATH,
        )
        records = parse_general_csv(DEFAULT_GENERAL_SAMPLE_PATH)
        low = [r for r in records
               if r.overall_rating is not None and r.overall_rating <= 2]
        self.assertGreaterEqual(len(low), 3)

    def test_emergency_services_parsed_as_int(self):
        from rcm_mc.data.cms_hospital_general import (
            parse_general_csv, DEFAULT_GENERAL_SAMPLE_PATH,
        )
        records = parse_general_csv(DEFAULT_GENERAL_SAMPLE_PATH)
        for r in records:
            self.assertIn(r.emergency_services, (0, 1))


class TestStoreRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refresh_roundtrip(self):
        from rcm_mc.data.cms_hospital_general import (
            refresh_general_source, get_quality_by_ccn,
        )
        n = refresh_general_source(self.store)
        self.assertGreaterEqual(n, 20)

        # 240005 = Mayo Clinic Rochester, seeded as 5-star
        q = get_quality_by_ccn(self.store, "240005")
        self.assertIsNotNone(q)
        self.assertEqual(q["overall_rating"], 5)
        self.assertEqual(q["state"], "MN")

    def test_list_low_rated(self):
        from rcm_mc.data.cms_hospital_general import (
            refresh_general_source, list_low_rated,
        )
        refresh_general_source(self.store)
        low = list_low_rated(self.store, max_stars=2)
        self.assertGreaterEqual(len(low), 3)
        for row in low:
            self.assertLessEqual(row["overall_rating"], 2)


class TestKnownSources(unittest.TestCase):
    def test_general_in_known_sources(self):
        from rcm_mc.data.data_refresh import KNOWN_SOURCES
        self.assertIn("cms_general", KNOWN_SOURCES)

    def test_dispatcher_callable(self):
        from rcm_mc.data.data_refresh import _default_refreshers
        refs = _default_refreshers()
        self.assertIn("cms_general", refs)
        self.assertTrue(callable(refs["cms_general"]))


class TestRiskScanShowsQuality(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        from rcm_mc.data.cms_hospital_general import refresh_general_source
        refresh_general_source(self.store)
        # Seed a deal pointing at a 5-star and a 1-star CCN
        with self.store.connect() as con:
            for cid, name in [("240005", "Mayo Clinic"),
                              ("450022", "LifePoint Silsbee")]:
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, "
                    "profile_json) VALUES (?, ?, ?, ?)",
                    (cid, name,
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({"sector": "hospital"})),
                )
            con.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_gather_includes_quality_rating(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _gather_per_deal
        deals = _gather_per_deal(self.db)
        mayo = next((d for d in deals if d["deal_id"] == "240005"), None)
        bad = next((d for d in deals if d["deal_id"] == "450022"), None)
        self.assertIsNotNone(mayo)
        self.assertIsNotNone(bad)
        self.assertEqual(mayo["quality_rating"], 5)
        self.assertEqual(bad["quality_rating"], 1)

    def test_quality_column_in_html(self):
        from rcm_mc.ui.portfolio_risk_scan_page import (
            render_portfolio_risk_scan,
        )
        html = render_portfolio_risk_scan(self.db)
        self.assertIn("Quality", html)
        # 5★ chip rendered with green palette
        self.assertIn("5★", html)
        # 1★ chip with red palette
        self.assertIn("1★", html)


class TestLowQualityInsight(unittest.TestCase):
    def test_insight_fires_with_2plus_low_rated(self):
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": "BAD_1", "name": "Bad 1", "sector": "hospital",
             "stage": "hold", "score": 65, "band": "fair",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0, "quality_rating": 1},
            {"deal_id": "BAD_2", "name": "Bad 2", "sector": "hospital",
             "stage": "hold", "score": 70, "band": "fair",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0, "quality_rating": 2},
        ]
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import _all_insights
                out = _all_insights(db)
            kinds = {i["kind"] for i in out}
            self.assertIn("low_quality_cluster", kinds)
        finally:
            tmp.cleanup()

    def test_insight_does_not_fire_with_one(self):
        """A single low-rated deal isn't a cluster — single_worst_deal
        handles that case via health score."""
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": "BAD", "name": "Bad", "sector": "hospital",
             "stage": "hold", "score": 75, "band": "good",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0, "quality_rating": 2},
        ]
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import _all_insights
                out = _all_insights(db)
            kinds = {i["kind"] for i in out}
            self.assertNotIn("low_quality_cluster", kinds)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
