"""The /deal-pipeline page leads with the computed pipeline value.

The page used to open with an 8-up KPI strip and several charts/tables,
leaving the headline (prob-weighted close + end-to-end conversion)
buried as KPIs #4-5 and in the bottom thesis. This pins that a
ck_value_anchor band now surfaces it at the top.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.deal_pipeline_page import render_deal_pipeline


class DealPipelineLeadAnchorTests(unittest.TestCase):
    def _html(self) -> str:
        return render_deal_pipeline({})

    def test_lead_value_anchor_present(self):
        html = self._html()
        self.assertIn("ck-value-anchor", html)
        self.assertIn("PIPELINE VALUE", html)
        self.assertIn("prob-weighted close", html)

    def test_anchor_leads_before_sourcing_funnel_and_bottom_thesis(self):
        html = self._html()
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Sourcing Funnel"),
        )
        self.assertLess(
            html.index("ck-value-anchor"),
            html.index("Pipeline Thesis"),
        )


if __name__ == "__main__":
    unittest.main()
