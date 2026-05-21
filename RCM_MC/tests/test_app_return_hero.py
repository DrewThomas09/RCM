"""Pin for the /app return hero (PR 7 hero metric).

Weighted MOIC leads the Command Center at headline weight with Weighted
IRR secondary and a plain provenance note. When no deal has a recorded
entry EV the hero shows "—" and says why — never a fabricated number
(defensibility). The eyebrow follows the workspace mode (Fund vs
Engagement) like the rest of the two-view copy.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.chartis._app_kpi_strip import _return_hero
from rcm_mc.ui._workspace_mode import CONSULTING, PARTNER, set_workspace_mode


def _df():
    return pd.DataFrame({
        "moic": [2.1, 1.8, None],
        "irr": [0.20, 0.18, None],
        "entry_ev": [300.0, 200.0, 150.0],
    })


class ReturnHeroTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(set_workspace_mode, PARTNER)

    def test_leads_with_weighted_moic_and_irr(self):
        html = _return_hero(
            {"weighted_moic": 1.94, "weighted_irr": 0.219, "deal_count": 5}, _df())
        self.assertIn("weighted MOIC", html)
        self.assertIn("1.94", html)
        self.assertIn("Weighted IRR", html)
        self.assertIn("21.9", html)

    def test_provenance_counts_sized_and_excluded(self):
        # _df has 2 sized rows (entry_ev + moic + irr) and 1 missing.
        html = _return_hero(
            {"weighted_moic": 1.94, "weighted_irr": 0.219, "deal_count": 3}, _df())
        self.assertIn("2 sized deals", html)
        self.assertIn("1 excluded for missing EV", html)

    def test_honest_suppression_when_no_sized_deal(self):
        html = _return_hero(
            {"weighted_moic": None, "weighted_irr": None, "deal_count": 0},
            pd.DataFrame())
        self.assertIn("—", html)
        self.assertIn("Awaiting the first deal", html)
        # No fabricated IRR line when MOIC is unavailable.
        self.assertNotIn("Weighted IRR", html)

    def test_eyebrow_follows_workspace_mode(self):
        roll = {"weighted_moic": 1.94, "weighted_irr": 0.219, "deal_count": 5}
        set_workspace_mode(PARTNER)
        self.assertIn("Fund-level return", _return_hero(roll, _df()))
        set_workspace_mode(CONSULTING)
        self.assertIn("Engagement-level return", _return_hero(roll, _df()))


if __name__ == "__main__":
    unittest.main()
