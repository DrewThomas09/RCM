"""The portfolio risk scan leads with the risk-posture takeaway.

The page used to open with a 3-up KPI grid; the headline (red-severity
deals needing a decision this week) was buried as KPI #2. This pins
that a ck_value_anchor band now surfaces it at the top, ahead of the
per-deal table. The empty-store branch is unchanged.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.dev.seed import seed_demo_db
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.portfolio_risk_scan_page import render_portfolio_risk_scan


class PortfolioRiskScanLeadAnchorTests(unittest.TestCase):
    def test_anchor_leads_on_seeded_portfolio(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "demo.db")
        seed_demo_db(db, deal_count=7, write_export_files=False, force=True)
        html = render_portfolio_risk_scan(db)
        self.assertIn("ck-value-anchor", html)
        self.assertIn("PORTFOLIO RISK SCAN", html)
        self.assertIn("red-severity", html)
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Per-deal scan"),
        )

    def test_empty_store_branch_still_renders(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "empty.db")
        with PortfolioStore(db).connect():
            pass
        html = render_portfolio_risk_scan(db)
        self.assertIn("No active deals in the portfolio store", html)


if __name__ == "__main__":
    unittest.main()
