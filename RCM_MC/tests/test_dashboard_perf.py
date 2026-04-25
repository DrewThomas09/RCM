"""Performance regression guards on the dashboard render path.

The dashboard composes ~10 sections — three of them (headline
insight, needs-attention, exposure) all need the same per-deal
risk scan. Without coordination, each section calls
``_gather_per_deal()`` independently, which iterates every deal,
runs ``compute_health()`` (the expensive bit), and queries CMS POS
once per deal. On a 50-deal portfolio: 150 health computes per page
load. The fix: compute it once in render_dashboard and thread it
through every section that needs it.

This test pins the call count via mock so a future refactor that
reverts to per-section calls fails loudly.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


def _seed_deal(store, deal_id: str, name: str) -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name,
             datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": "hospital"})),
        )
        con.commit()


class TestGatherPerDealCalledOnce(unittest.TestCase):
    """One render_dashboard call → exactly one _gather_per_deal call."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        for i in range(3):
            _seed_deal(self.store, f"DEAL_{i}", f"Hospital {i}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_gather_called_once_per_render(self):
        """The render path computes the scan once and threads it
        into every section that needs it. Mock at the source module
        (where the import happens, late-bound) and assert call_count."""
        from unittest.mock import MagicMock
        # The fake scan needs to look like real output enough that
        # the downstream insight + exposure code runs without
        # raising (and skipping due to None).
        fake_deals = [
            {"deal_id": f"DEAL_{i}", "name": f"H{i}",
             "sector": "hospital", "stage": "hold",
             "score": 75, "band": "good",
             "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 5,
             "open_deadlines": 0, "overdue_deadlines": 0,
             "chain": "", "chain_size": 0}
            for i in range(3)
        ]
        with patch(
            "rcm_mc.ui.portfolio_risk_scan_page._gather_per_deal",
            MagicMock(return_value=fake_deals),
        ) as mock_gather:
            from rcm_mc.ui.dashboard_page import render_dashboard
            render_dashboard(self.db)

        self.assertEqual(
            mock_gather.call_count, 1,
            msg=f"_gather_per_deal must be called exactly once per "
                f"dashboard render, got {mock_gather.call_count}. "
                f"This is a real perf bug — each call iterates every "
                f"deal and runs compute_health + POS lookup.",
        )


class TestSectionAcceptsPreComputedDeals(unittest.TestCase):
    """Each section helper that uses the scan must accept a `deals`
    kwarg so render_dashboard can pass the cached result. Without
    this knob, the optimization isn't possible."""

    def test_headline_section_accepts_deals_kwarg(self):
        from rcm_mc.ui.dashboard_page import _render_headline_insight_section
        import inspect
        sig = inspect.signature(_render_headline_insight_section)
        self.assertIn("deals", sig.parameters)

    def test_needs_attention_accepts_deals_kwarg(self):
        from rcm_mc.ui.dashboard_page import _render_needs_attention_section
        import inspect
        sig = inspect.signature(_render_needs_attention_section)
        self.assertIn("deals", sig.parameters)

    def test_exposure_accepts_deals_kwarg(self):
        from rcm_mc.ui.dashboard_page import _render_exposure_section
        import inspect
        sig = inspect.signature(_render_exposure_section)
        self.assertIn("deals", sig.parameters)

    def test_compute_sharpest_insight_accepts_deals_kwarg(self):
        from rcm_mc.ui.dashboard_page import _compute_sharpest_insight
        import inspect
        sig = inspect.signature(_compute_sharpest_insight)
        self.assertIn("deals", sig.parameters)


if __name__ == "__main__":
    unittest.main()
