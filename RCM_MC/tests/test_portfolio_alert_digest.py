"""Per-deal alert digest on the portfolio deal table (PAGE_INVENTORY fix).

Each row carries its live unacked-alert posture (worst severity + count,
linked to /alerts); deals with no alerts show an em-dash; an evaluator
failure renders no chips, never a 500.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class PortfolioAlertDigestTests(unittest.TestCase):
    def _store_with_overdue_deadline(self, tmp):
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        store.upsert_deal("d1", name="Alpha",
                          profile={"denial_rate": 12.0, "days_in_ar": 50})
        store.upsert_deal("d2", name="Beta",
                          profile={"denial_rate": 9.0, "days_in_ar": 45})
        # A real evaluator trigger: an overdue deadline fires an alert
        # for d1 (no synthetic Alert objects — exercise the real path).
        from rcm_mc.deals.deal_deadlines import add_deadline
        add_deadline(store, deal_id="d1", label="QoE final",
                     due_date="2020-01-01")
        return store

    def test_rows_carry_alert_posture(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_overdue_deadline(tmp)
            from rcm_mc.alerts.alerts import evaluate_active
            fired = [a for a in evaluate_active(store) if a.deal_id == "d1"]
            self.assertTrue(fired, "expected an overdue-deadline alert")
            from rcm_mc.ui.portfolio_overview import render_portfolio_overview
            deals = store.list_deals()
            h = render_portfolio_overview(deals, store)
            self.assertIn("<th>Alerts</th>", h)
            self.assertIn("unacked alert(s)", h)
            self.assertIn('href="/alerts"', h)
            # The clean deal shows an em-dash, not a fabricated zero-chip.
            self.assertIn("—", h)

    def test_no_store_renders_dashes_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_overdue_deadline(tmp)
            deals = store.list_deals()
            from rcm_mc.ui.portfolio_overview import render_portfolio_overview
            h = render_portfolio_overview(deals)        # store=None path
            self.assertIn("<th>Alerts</th>", h)
            self.assertNotIn("unacked alert(s)", h)


if __name__ == "__main__":
    unittest.main()
