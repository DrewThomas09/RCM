"""tests for ``workbench_tab_layout`` (P80-83 composer).

The actual analysis_workbench.py is 930+ lines of bespoke HTML.
This composer pins the canonical layout shape so future tab
migrations land on the same primitives — kpi_strip at the top,
run-live link in the header, content in the middle,
recommendation_block at the bottom.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import workbench_tab_layout


class CompositionShape(unittest.TestCase):

    def test_full_layout(self) -> None:
        html = workbench_tab_layout(
            "monte-carlo",
            kpis=[
                {"label": "P50 IRR", "value": "22.3%"},
                {"label": "MOIC P50", "value": "2.80x"},
            ],
            content_sections=["<div>histogram</div>", "<div>tornado</div>"],
            recommendation='<aside class="recommendation-block">…</aside>',
            deal_id="aurora",
        )
        # Outer wrapper carries the tab name.
        self.assertIn('data-tab="monte-carlo"', html)
        # KPI strip at the top.
        self.assertIn("kpi-strip", html)
        # Run-live link in the header pointing at the matching module.
        self.assertIn(
            'href="/diligence/deal-mc?deal_id=aurora"',
            html,
        )
        # Content sections concatenated in order.
        self.assertLess(
            html.find("histogram"),
            html.find("tornado"),
        )
        # Recommendation at the bottom.
        self.assertIn("recommendation-block", html)


class GracefulMissingPieces(unittest.TestCase):

    def test_overview_no_run_live_link(self) -> None:
        # Overview's tab key has no live module; layout must omit
        # the link without breaking.
        html = workbench_tab_layout(
            "overview",
            kpis=[{"label": "Headline", "value": "—"}],
            deal_id="aurora",
        )
        self.assertNotIn("run-live-link", html)

    def test_no_kpis_no_header(self) -> None:
        html = workbench_tab_layout(
            "monte-carlo",
            content_sections=["<div>chart</div>"],
            deal_id="aurora",
        )
        self.assertNotIn("workbench-tab-header", html)

    def test_no_recommendation_no_block(self) -> None:
        html = workbench_tab_layout(
            "monte-carlo",
            kpis=[{"label": "x", "value": "1"}],
            deal_id="aurora",
        )
        self.assertNotIn("recommendation-block", html)

    def test_no_deal_id_drops_run_live(self) -> None:
        html = workbench_tab_layout(
            "monte-carlo",
            kpis=[{"label": "x", "value": "1"}],
        )
        self.assertNotIn("run-live-link", html)


if __name__ == "__main__":
    unittest.main()
