"""Payer Rate Trends leads with a REAL Colorado payer cost trend (CIVHC).

PPPY by payer x year (2017-21) with % change — live; all-payer market cost
trajectory, not contracted rates, Colorado-specific. The corpus regime model
stays below.
"""
import unittest

from rcm_mc.data import payer_data as pdt
from rcm_mc.ui.data_public.payer_rate_trends_page import render_payer_rate_trends


class TestPayerCostTrend(unittest.TestCase):
    def test_trend_loader(self):
        t = pdt.payer_cost_trend()
        self.assertGreater(len(t), 3)
        self.assertIn("pct_change", t.columns)
        self.assertIn("payer_type", t.columns)
        # Commercial rose materially 2017->2021 (real data)
        comm = t[t["payer_type"] == "Commercial"]
        self.assertGreater(float(comm["pct_change"].iloc[0]), 0)

    def test_page_live_section(self):
        h = render_payer_rate_trends()
        self.assertIn("Colorado payer cost trend (PPPY) · LIVE (CIVHC)", h)
        self.assertIn("not</b> contracted reimbursement", h)   # caveat
        self.assertIn("ck-sp", h)

    def test_values_from_loader(self):
        t = pdt.payer_cost_trend()
        comm_pc = float(t[t["payer_type"] == "Commercial"]["pct_change"].iloc[0])
        self.assertIn(f"{comm_pc:+.1f}%", render_payer_rate_trends())


if __name__ == "__main__":
    unittest.main()
