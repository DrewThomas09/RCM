"""Tests for the dashboard's "Sharpest insight · today" headline card.

The wow moment: partner opens /dashboard and the first thing they
see is a bold, tone-colored sentence telling them the single most
notable thing about their portfolio right now — chain concentration
they hadn't noticed, a covenant trip, stale data, or "all clear."
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deal(store, deal_id: str, name: str) -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name, datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": "hospital"})),
        )
        con.commit()


class TestHeadlineInsight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_deals_no_insight(self):
        """Fresh DB → None (dashboard omits the card)."""
        from rcm_mc.ui.dashboard_page import _compute_sharpest_insight
        self.assertIsNone(_compute_sharpest_insight(self.db))

    def test_chain_concentration_detected(self):
        """Two deals in the same CMS POS chain should surface as an
        insight — even if nothing else is wrong, 'you have 2 deals
        in LifePoint' is the thing a partner didn't know."""
        from rcm_mc.data.cms_pos import refresh_pos_source
        refresh_pos_source(self.store)
        # Seed two LifePoint CCNs from the sample
        _seed_deal(self.store, "100007", "LifePoint Memorial")
        _seed_deal(self.store, "450022", "LifePoint Silsbee")

        from rcm_mc.ui.dashboard_page import _compute_sharpest_insight
        ins = _compute_sharpest_insight(self.db)
        self.assertIsNotNone(ins)
        self.assertEqual(ins["kind"], "chain_concentration")
        self.assertIn("LIFEPOINT_001", ins["headline"])
        self.assertEqual(ins["tone"], "warn")

    def test_all_green_surfaces_reassurance(self):
        """Portfolio with ≥3 deals and no flags → positive insight."""
        for i in range(3):
            _seed_deal(self.store, f"DEAL_{i}", f"Hospital {i}")

        from rcm_mc.ui.dashboard_page import _compute_sharpest_insight
        ins = _compute_sharpest_insight(self.db)
        self.assertIsNotNone(ins)
        self.assertEqual(ins["kind"], "all_green")
        self.assertEqual(ins["tone"], "positive")
        self.assertIn("healthy", ins["headline"].lower())

    def test_insight_renders_on_dashboard(self):
        """Rendered headline must appear in the dashboard HTML
        above "What you can run"."""
        for i in range(3):
            _seed_deal(self.store, f"DEAL_{i}", f"Hospital {i}")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Sharpest insight", html)
        # Ordered: sharpest insight must come BEFORE "What you can run"
        insight_pos = html.find("Sharpest insight")
        run_pos = html.find("What you can run")
        self.assertGreater(insight_pos, 0)
        self.assertGreater(run_pos, 0)
        self.assertLess(insight_pos, run_pos,
                        msg="sharpest insight must come before "
                            "'What you can run'")

    def test_insight_is_clickable_link(self):
        """Headline is a full-width link — clicking drops the user
        straight into the drill-down page for that signal."""
        for i in range(3):
            _seed_deal(self.store, f"DEAL_{i}", f"Hospital {i}")

        from rcm_mc.ui.dashboard_page import _render_headline_insight_section
        html = _render_headline_insight_section(self.db)
        self.assertIn('<a href=', html)
        self.assertIn('/pipeline', html)  # all-green tone → pipeline


class TestPriorityOrdering(unittest.TestCase):
    """When multiple insights fire, the highest-score one wins.
    Covenant-tripped should ALWAYS beat chain concentration."""

    def test_covenant_tripped_wins_over_chain(self):
        """Mock `_gather_per_deal` to return deals that trigger BOTH
        the chain-concentration AND covenant-tripped insights, and
        confirm covenant wins on score."""
        from unittest.mock import patch
        fake_deals = [
            {"deal_id": "DEAL_A", "name": "Tripped LifePoint",
             "chain": "LIFEPOINT_001", "chain_size": 3,
             "score": 50, "band": "fair",
             "covenant_status": "TRIPPED",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "sector": "hospital", "stage": "hold"},
            {"deal_id": "DEAL_B", "name": "Other LifePoint",
             "chain": "LIFEPOINT_001", "chain_size": 3,
             "score": 75, "band": "good",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "sector": "hospital", "stage": "hold"},
        ]
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            # _compute_sharpest_insight imports _gather_per_deal
            # from portfolio_risk_scan_page lazily — patch at the
            # source module so the late-binding pulls the mock.
            with patch(
                "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
                return_value=fake_deals,
            ):
                from rcm_mc.ui.dashboard_page import _compute_sharpest_insight
                ins = _compute_sharpest_insight(db)
            self.assertIsNotNone(ins)
            self.assertEqual(ins["kind"], "covenant_tripped",
                             msg="covenant_tripped should outrank "
                                 "chain_concentration in priority")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
