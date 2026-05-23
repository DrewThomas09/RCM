"""The regression page's no-data state should orient the user.

A diligence user landing on an empty page needs to know what the page is
for, why it's empty, and what to do next — not just "No data available."
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.regression_page import render_regression_page


class RegressionEmptyStateTests(unittest.TestCase):
    def test_portfolio_empty_state_is_actionable(self):
        html = render_regression_page(
            data_source="portfolio", deals_df=pd.DataFrame())
        self.assertIn("No data loaded yet.", html)        # clear state
        self.assertIn("driver models", html)              # what the page does
        self.assertIn("Pipeline", html)                   # next step
        self.assertNotIn("No data available.", html)      # old thin copy gone

    def test_hcris_empty_state_points_to_data_load(self):
        html = render_regression_page(
            data_source="hcris", hcris_df=pd.DataFrame())
        self.assertIn("No data loaded yet.", html)
        self.assertIn("rcm-mc data refresh", html)        # concrete next step


if __name__ == "__main__":
    unittest.main()
