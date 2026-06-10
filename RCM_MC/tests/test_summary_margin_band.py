"""Regression: displayed summary margins exclude out-of-band artifacts.

The predictive screener's "Avg Margin" KPI and the ML-insights avg margin
aggregated raw operating_margin (clipped to [-50%, +100%]), so junk-opex
filing artifacts dragged the headline (predictive: -6.49% raw vs -3.82% on
real margins). Both now filter to the agreed -40%…+30% band via
margin_is_plausible_series, consistent with the X-Ray / command center /
market data.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.ui._chartis_kit import margin_is_plausible_series
from rcm_mc.ui.regression_page import _add_computed_features


class PredictiveSummaryMarginTests(unittest.TestCase):
    def test_avg_margin_kpi_uses_plausible_band(self):
        from rcm_mc.ui.predictive_screener import render_predictive_screener
        df = _add_computed_features(_get_latest_per_ccn())
        m = df["operating_margin"]
        expected = m[margin_is_plausible_series(m)].dropna().mean()
        html = render_predictive_screener(_get_latest_per_ccn(), "")
        # The KPI renders the plausible-band mean (e.g. "-3.8%"), not the raw
        # artifact-skewed value.
        self.assertIn(f"{expected:.1%}", html)
        raw = m.dropna().mean()
        # Sanity: the two differ enough that the test is meaningful.
        self.assertGreater(abs(raw - expected), 0.01)
        self.assertNotIn(f"{raw:.1%}", html.split("Avg Margin")[-1][:200])


if __name__ == "__main__":
    unittest.main()
