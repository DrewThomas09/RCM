"""Tests for CMS HRRP ingestion + downstream integration."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


class TestParser(unittest.TestCase):
    def test_parses_sample(self):
        from rcm_mc.data.cms_hrrp import (
            parse_hrrp_csv, DEFAULT_HRRP_SAMPLE_PATH,
        )
        records = parse_hrrp_csv(DEFAULT_HRRP_SAMPLE_PATH)
        self.assertGreaterEqual(len(records), 20)

    def test_factor_to_percent_conversion(self):
        """0.97 (factor form) → 3.0% (percent form)."""
        from rcm_mc.data.cms_hrrp import _normalize_payment_adjustment
        self.assertEqual(_normalize_payment_adjustment("0.97"), 3.0)
        self.assertEqual(_normalize_payment_adjustment("1.00"), 0.0)
        self.assertEqual(_normalize_payment_adjustment("0.99"),
                         round((1 - 0.99) * 100, 3))

    def test_already_percent_passes_through(self):
        from rcm_mc.data.cms_hrrp import _normalize_payment_adjustment
        # Already a percent — leave alone
        self.assertEqual(_normalize_payment_adjustment("2.5"), 2.5)
        self.assertEqual(_normalize_payment_adjustment("0.5"), 0.5)

    def test_invalid_value_returns_none(self):
        from rcm_mc.data.cms_hrrp import _normalize_payment_adjustment
        self.assertIsNone(_normalize_payment_adjustment("Not Available"))
        self.assertIsNone(_normalize_payment_adjustment(""))
        self.assertIsNone(_normalize_payment_adjustment("99"))  # bogus

    def test_lifepoint_silsbee_high_penalty(self):
        """Sample seeds 450022 with 0.9700 (3% penalty) — verify
        the highest-penalty row is detectable for the cluster
        insight."""
        from rcm_mc.data.cms_hrrp import (
            parse_hrrp_csv, DEFAULT_HRRP_SAMPLE_PATH,
        )
        records = parse_hrrp_csv(DEFAULT_HRRP_SAMPLE_PATH)
        ls = [r for r in records if r.ccn == "450022"]
        self.assertEqual(len(ls), 1)
        self.assertEqual(ls[0].payment_adjustment_pct, 3.0)


class TestStoreRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refresh_roundtrip(self):
        from rcm_mc.data.cms_hrrp import (
            refresh_hrrp_source, get_penalty_by_ccn,
        )
        n = refresh_hrrp_source(self.store)
        self.assertGreaterEqual(n, 20)

        h = get_penalty_by_ccn(self.store, "450022")
        self.assertIsNotNone(h)
        self.assertEqual(h["payment_adjustment_pct"], 3.0)
        self.assertEqual(h["state"], "TX")

    def test_list_high_penalty(self):
        from rcm_mc.data.cms_hrrp import (
            refresh_hrrp_source, list_high_penalty,
        )
        refresh_hrrp_source(self.store)
        high = list_high_penalty(self.store, min_pct=2.0)
        self.assertGreaterEqual(len(high), 2)
        for row in high:
            self.assertGreaterEqual(row["payment_adjustment_pct"], 2.0)


class TestKnownSources(unittest.TestCase):
    def test_in_known_sources(self):
        from rcm_mc.data.data_refresh import KNOWN_SOURCES
        self.assertIn("cms_hrrp", KNOWN_SOURCES)

    def test_dispatcher_callable(self):
        from rcm_mc.data.data_refresh import _default_refreshers
        refs = _default_refreshers()
        self.assertIn("cms_hrrp", refs)
        self.assertTrue(callable(refs["cms_hrrp"]))


class TestRiskScanShowsHrrp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        from rcm_mc.data.cms_hrrp import refresh_hrrp_source
        refresh_hrrp_source(self.store)
        # Seed a deal pointing at 450022 (3% penalty in sample)
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                ("450022", "LifePoint Silsbee",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"sector": "hospital"})),
            )
            con.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_gather_includes_hrrp_pct(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _gather_per_deal
        deals = _gather_per_deal(self.db)
        ls = next((d for d in deals if d["deal_id"] == "450022"), None)
        self.assertIsNotNone(ls)
        self.assertEqual(ls["hrrp_pct"], 3.0)

    def test_hrrp_column_in_html(self):
        from rcm_mc.ui.portfolio_risk_scan_page import (
            render_portfolio_risk_scan,
        )
        html = render_portfolio_risk_scan(self.db)
        self.assertIn("HRRP", html)
        # 3.0% penalty rendered as red chip
        self.assertIn("3.0%", html)


class TestHrrpInsight(unittest.TestCase):
    def test_insight_fires_with_2plus_high_penalty(self):
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": f"BAD_{i}", "name": f"Bad {i}",
             "sector": "hospital", "stage": "hold",
             "score": 65, "band": "fair",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0,
             "quality_rating": None,
             "hrrp_pct": 2.5}
            for i in range(2)
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
            self.assertIn("hrrp_penalty_cluster", kinds)
        finally:
            tmp.cleanup()

    def test_insight_does_not_fire_below_threshold(self):
        """1.5% is below the 2% bar — not a cluster signal."""
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": f"D_{i}", "name": f"D{i}",
             "sector": "hospital", "stage": "hold",
             "score": 65, "band": "fair",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0,
             "quality_rating": None,
             "hrrp_pct": 1.5}
            for i in range(3)
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
            self.assertNotIn("hrrp_penalty_cluster", kinds)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
