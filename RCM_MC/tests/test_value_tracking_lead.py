"""The value-tracking page leads with the computed realization.

The plan-active page used to open with a 5-up KPI grid; the headline
(realized vs planned uplift + realization %) was only readable by
scanning the grid. This pins that a ck_value_anchor band now surfaces
it at the top, ahead of the frozen-plan section.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.pe.value_tracker import _ensure_tables, freeze_bridge_as_plan
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.value_tracking_page import render_value_tracker


class ValueTrackingLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        d = tempfile.mkdtemp()
        db = os.path.join(d, "p.db")
        with PortfolioStore(db).connect() as con:
            _ensure_tables(con)
            freeze_bridge_as_plan(
                con, "DEAL-1", "010001", "Test Hosp",
                {
                    "total_ebitda_impact": 5_000_000,
                    "levers": [
                        {"name": "Denials", "ebitda_impact": 2_000_000,
                         "ramp_months": 12},
                    ],
                },
            )
            con.commit()
        return render_value_tracker("DEAL-1", db)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("VALUE REALIZATION", html)
        self.assertIn("planned uplift", html)

    def test_anchor_leads_before_frozen_plan(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Frozen Bridge Plan"),
        )

    def test_no_plan_branch_still_renders(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "empty.db")
        html = render_value_tracker("DEAL-NONE", db)
        self.assertIn("No Value Creation Plan", html)


if __name__ == "__main__":
    unittest.main()
