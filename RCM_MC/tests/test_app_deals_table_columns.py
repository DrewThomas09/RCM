"""The /app deals table no longer renders the dead Drift/Headline columns.

deal_snapshots / latest_per_deal carry no drift_pct or headline field, so
those two columns always rendered blank. They're dropped (per-deal
variance can't be computed within the /app 3-query budget). Pins that
the table is the 6 live columns: Deal · Stage · EV · MOIC · IRR · Covenant.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.chartis._app_deals_table import render_deals_table


class DealsTableColumnsTests(unittest.TestCase):
    def _df(self):
        return pd.DataFrame({
            "deal_id": ["d1"], "name": ["Test Deal"], "stage": ["hold"],
            "entry_ev": [300.0], "moic": [2.1], "irr": [0.2],
            "covenant_status": ["SAFE"],
        })

    def test_no_dead_drift_or_headline_columns(self):
        html = render_deals_table(self._df())
        self.assertNotIn(">Drift<", html)
        self.assertNotIn(">Headline<", html)

    def test_six_live_columns(self):
        html = render_deals_table(self._df())
        for col in ("EV", "MOIC", "IRR", "Covenant", "Stage"):
            self.assertIn(col, html)

    def test_empty_state_colspan_matches(self):
        html = render_deals_table(pd.DataFrame())
        self.assertIn('colspan="6"', html)


if __name__ == "__main__":
    unittest.main()
