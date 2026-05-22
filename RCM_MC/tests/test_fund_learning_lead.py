"""The fund-learning page leads with the fund's calibration signal.

The page used to open with a 4-up KPI grid; the headline (realized vs
planned EBITDA uplift across closed deals) was buried as KPIs #2-4.
This pins that a ck_value_anchor band now surfaces it at the top,
ahead of the flywheel section.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.pe.value_tracker import _ensure_tables, freeze_bridge_as_plan
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.fund_learning_page import render_fund_learning


class FundLearningLeadAnchorTests(unittest.TestCase):
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
        return render_fund_learning(db)

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("FUND CALIBRATION", html)
        self.assertIn("planned uplift", html)

    def test_anchor_leads_before_flywheel(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("The Compounding Moat"),
        )

    def test_no_data_branch_still_renders(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "empty.db")
        html = render_fund_learning(db)
        self.assertIn("No value creation plans", html)


if __name__ == "__main__":
    unittest.main()
