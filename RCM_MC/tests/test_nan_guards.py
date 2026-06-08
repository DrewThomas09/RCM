"""Regression: numeric formatters must never leak 'nan'/'inf' into the UI.

Hospital/CCN pages run live regressions and ML predictions on HCRIS data
that is frequently incomplete for a given facility (a zero-variance
feature, a missing Medicaid Day %, a competitor with no revenue on file).
The computations then return NaN/inf, and several formatters printed the
literal 'nan' / '+nan' / '$nanM' / 'nan%' straight into partner-facing
tables. These guard the shared formatters at the source.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui.regression_page import _fmt_num
from rcm_mc.ui.market_analysis_page import _finite, _npr, _pct
from rcm_mc.ui.ml_insights_page import _factor_contribution_chart, _na


class FmtNumGuardTests(unittest.TestCase):
    def test_nan_and_inf_render_dash(self):
        self.assertEqual(_fmt_num(float("nan")), "—")
        self.assertEqual(_fmt_num(float("inf")), "—")
        self.assertEqual(_fmt_num(float("-inf")), "—")

    def test_finite_values_unchanged(self):
        self.assertEqual(_fmt_num(2_500_000_000), "$2.50B")
        self.assertEqual(_fmt_num(105_200_000), "$105.2M")
        self.assertEqual(_fmt_num(0.1733), "0.1733")


class MarketHelperGuardTests(unittest.TestCase):
    def test_pct_guards_nan(self):
        self.assertEqual(_pct(float("nan")), "n/a")
        self.assertEqual(_pct(None), "n/a")
        self.assertEqual(_pct(0.821), "82.1%")

    def test_npr_guards_nan(self):
        self.assertEqual(_npr(float("nan")), "n/a")
        self.assertEqual(_npr(49_000_000), "$49M")

    def test_finite(self):
        self.assertTrue(_finite(1.0))
        self.assertFalse(_finite(float("nan")))
        self.assertFalse(_finite(float("inf")))
        self.assertFalse(_finite(None))
        self.assertFalse(_finite("x"))


class MlInsightsNaGuardTests(unittest.TestCase):
    def test_na_guards(self):
        self.assertEqual(_na(float("nan"), ".1%"), "—")
        self.assertEqual(_na(None, "+.4f"), "—")
        self.assertEqual(_na(0.5, ".1%"), "50.0%")
        self.assertEqual(_na(-0.0017, "+.4f"), "-0.0017")

    def test_factor_chart_geometry_survives_nan(self):
        # Regression: a NaN contribution poisoned max_abs and the bar
        # geometry, emitting x="nan"/width="nan" into the SVG. Geometry
        # must stay finite; the label may read "—".
        svg = _factor_contribution_chart([
            {"feature": "Occupancy Rate", "contribution": 0.19,
             "direction": "reduces"},
            {"feature": "Medicaid Day Pct", "contribution": float("nan"),
             "direction": "increases"},
        ])
        self.assertNotIn("nan", svg)
        self.assertNotIn("NaN", svg)


if __name__ == "__main__":
    unittest.main()
