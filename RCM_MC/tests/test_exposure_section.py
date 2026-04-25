"""Tests for the dashboard's "Portfolio composition" exposure card.

Sector + chain breakdowns rendered as horizontal bars. Answers the
partner question "what's my exposure?" without opening every deal.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deal(store, deal_id: str, name: str, sector: str = "hospital") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name, datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": sector})),
        )
        con.commit()


class TestExposureSection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_zero_or_one_deal_no_section(self):
        """A 0- or 1-deal portfolio has no meaningful breakdown.
        The section must not render."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        # Empty
        html = render_dashboard(self.db)
        self.assertNotIn("Portfolio composition", html)
        # One deal
        _seed_deal(self.store, "ONE_DEAL", "Lonely Hospital")
        html = render_dashboard(self.db)
        self.assertNotIn("Portfolio composition", html)

    def test_sector_breakdown_renders(self):
        for i in range(3):
            _seed_deal(self.store, f"H{i}", f"Hospital {i}",
                       sector="hospital")
        for i in range(2):
            _seed_deal(self.store, f"M{i}", f"Managed Care {i}",
                       sector="managed_care")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Portfolio composition (5 active deals)", html)
        self.assertIn("By sector", html)
        # Both sectors appear with their counts
        self.assertIn("hospital", html)
        self.assertIn("managed_care", html)

    def test_percentages_sum_meaningfully(self):
        """5 deals split 3/2 → 60% + 40%. The numbers in the
        rendered HTML should reflect the actual ratio (rounded
        without crossing 100%)."""
        for i in range(3):
            _seed_deal(self.store, f"H{i}", f"H{i}", sector="hospital")
        for i in range(2):
            _seed_deal(self.store, f"M{i}", f"M{i}", sector="managed_care")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("3 · 60%", html)
        self.assertIn("2 · 40%", html)

    def test_chain_breakdown_appears_when_pos_loaded(self):
        """When CMS POS data is loaded and deal_ids match CCNs in
        chains, the chain breakdown surfaces actual chain names."""
        from rcm_mc.data.cms_pos import refresh_pos_source
        refresh_pos_source(self.store)
        # Seed two LifePoint CCNs from the POS sample
        _seed_deal(self.store, "100007", "LifePoint A")
        _seed_deal(self.store, "450022", "LifePoint B")
        _seed_deal(self.store, "INDEPENDENT", "Solo Hospital")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("By chain", html)
        self.assertIn("LIFEPOINT_001", html)

    def test_chain_breakdown_empty_state(self):
        """When no deal_id maps to a known chain, the chain
        sub-section shows the explanatory empty state instead
        of an empty bar list."""
        # 2 deals, neither matches a CCN in pos_sample.csv
        _seed_deal(self.store, "FAKE_001", "Test A")
        _seed_deal(self.store, "FAKE_002", "Test B")

        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("By chain", html)
        self.assertIn("No chain-affiliated deals", html)


if __name__ == "__main__":
    unittest.main()
