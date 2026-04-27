"""Test for the 4C provenance-tooltip adoption on
ui/portfolio_overview.py (campaign target 4C, loop 160).

Loop 110 + 116 wrapped 7 KPI labels and column headers in
metric_label_link (/metric-glossary anchors). This loop
wraps the 4 KPI VALUE cells (Total Net Revenue, Avg Denial
Rate, Avg Days in AR, Avg Net Collection) in
provenance_tooltip — partners hovering see AGGREGATED
node-type cards (sum / mean across the deal cohort), not
SOURCE/PREDICTED used on per-deal pages.

The graph is built manually (not via build_provenance_
graph, which is per-deal HCRIS-shaped) — each KPI becomes
one ProvenanceNode at observed:<metric> with NodeType
.AGGREGATED.

Asserts:
  - render_portfolio_overview produces 4 prov-tt wrappers.
  - Every wrapper has a paired card.
  - The CSS injects exactly once per render (4 calls; first
    inject_css=True, the other 3 inject_css=False).
  - AGGREGATED node-type label appears (the partner-language
    signal that this is a portfolio-mean, not a per-deal
    SOURCE).
"""
from __future__ import annotations

import re
import unittest

import pandas as pd

from rcm_mc.ui.portfolio_overview import render_portfolio_overview


def _build_deals_fixture() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "deal_id": "D1", "name": "Test Deal A", "stage": "IOI",
            "denial_rate": 0.10, "days_in_ar": 50,
            "net_revenue": 1.5e8,
            "net_collection_rate": 0.93, "health_score": 70,
        },
        {
            "deal_id": "D2", "name": "Test Deal B", "stage": "LOI",
            "denial_rate": 0.12, "days_in_ar": 55,
            "net_revenue": 2.0e8,
            "net_collection_rate": 0.91, "health_score": 65,
        },
    ])


class PortfolioOverviewProvenanceTooltipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.deals = _build_deals_fixture()

    def test_render_includes_four_prov_tt_wrappers(self) -> None:
        out = render_portfolio_overview(self.deals)
        n = len(re.findall(r'class="prov-tt"', out))
        self.assertEqual(
            n, 4,
            f"expected 4 prov-tt wrappers (NPR, Denial, AR, "
            f"Net Collection); found {n}",
        )

    def test_every_wrapper_has_card(self) -> None:
        out = render_portfolio_overview(self.deals)
        n_w = len(re.findall(r'class="prov-tt"', out))
        n_c = len(re.findall(r'class="prov-tt-card"', out))
        self.assertEqual(n_w, n_c)

    def test_tooltip_css_injects_only_once(self) -> None:
        out = render_portfolio_overview(self.deals)
        n = out.count(".prov-tt {")
        self.assertEqual(
            n, 1,
            f"expected exactly 1 prov-tt CSS block; found {n}",
        )

    def test_aggregated_node_type_appears(self) -> None:
        """Portfolio KPIs are AGGREGATED (cohort sum/mean),
        not SOURCE/PREDICTED used on per-deal pages — the
        partner-language signal in the rendered card."""
        out = render_portfolio_overview(self.deals)
        self.assertIn("AGGREGATED", out)


if __name__ == "__main__":
    unittest.main()
