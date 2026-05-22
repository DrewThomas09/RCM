"""The /app metric catalog shows only the columns it can source.

The deal-level columns (RCM DRAG / COVENANTS / INITIATIVES) and DPI/TVPI
could not be sourced from the data the catalog receives, so they rendered
dead "—". Per the simplify decision, the catalog now shows only the live
fund-level RETURNS metrics (Weighted MOIC / IRR); the deal-level data is
shown in the dedicated blocks on the same page.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis._app_metric_catalog import render_metric_catalog


class MetricCatalogSimplifiedTests(unittest.TestCase):
    def test_shows_live_returns(self):
        html = render_metric_catalog(rollup={"weighted_moic": 1.94, "weighted_irr": 0.219})
        self.assertIn("RETURNS", html)
        self.assertIn("1.94", html)   # Weighted MOIC
        self.assertIn("21.9", html)   # Weighted IRR

    def test_dead_columns_removed(self):
        html = render_metric_catalog(rollup={"weighted_moic": 2.0, "weighted_irr": 0.2})
        for dead in ("RCM DRAG", "COVENANTS", "INITIATIVES", ">DPI<", "TVPI"):
            self.assertNotIn(dead, html)

    def test_missing_rollup_shows_dash_not_fake(self):
        html = render_metric_catalog(rollup=None)
        self.assertIn("RETURNS", html)
        self.assertIn("—", html)

    def test_focused_packet_kwarg_still_accepted(self):
        # Signature compat — app_page still passes focused_packet=...
        html = render_metric_catalog(rollup={"weighted_moic": 2.0}, focused_packet=object())
        self.assertIn("METRIC CATALOG", html)


if __name__ == "__main__":
    unittest.main()
