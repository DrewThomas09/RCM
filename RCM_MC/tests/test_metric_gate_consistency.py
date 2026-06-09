"""Regression: occupancy / net-to-gross are gated CONSISTENTLY across surfaces.

PR #1644/#1645 gated impossible occupancy (>105%) and net-to-gross (>100%) on
the HCRIS X-Ray. But the IC memo, competitive-intel, and regression pages
recomputed the same metrics with no upper bound, so one hospital could read
"239% occupancy" on those pages and "—" on the X-Ray. These assert the gate
is applied everywhere the value is shown, so a reference to a hospital's
occupancy/net-to-gross is the same number on every page.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ui._chartis_kit import OCCUPANCY_PLAUSIBLE_HI

# A hospital whose patient-days exceed bed-days available (impossible >100%)
# and whose net patient revenue exceeds gross (impossible >100% net-to-gross).
_ARTIFACT = {
    "ccn": "999999", "state": "TX", "name": "ARTIFACT GENERAL",
    "net_patient_revenue": 3e8, "operating_expenses": 2.7e8,
    "gross_patient_revenue": 2e8,            # gross < net → n2g > 1
    "beds": 100, "total_patient_days": 85000,
    "bed_days_available": 36600,             # occ ≈ 232%
    "medicare_day_pct": 0.4, "medicaid_day_pct": 0.15,
}
_CLEAN = {**_ARTIFACT, "ccn": "999998", "name": "CLEAN GENERAL",
          "gross_patient_revenue": 7e8, "total_patient_days": 26000}


class DataframeOccupancyGateTests(unittest.TestCase):
    def test_competitive_intel_gates_occupancy(self):
        from rcm_mc.ui.competitive_intel_page import _add_features
        out = _add_features(pd.DataFrame([_ARTIFACT]))
        self.assertTrue(pd.isna(out["occupancy_rate"].iloc[0]))

    def test_regression_gates_occupancy(self):
        from rcm_mc.ui.regression_page import _add_computed_features
        out = _add_computed_features(pd.DataFrame([_ARTIFACT]))
        self.assertTrue(pd.isna(out["occupancy_rate"].iloc[0]))

    def test_clean_occupancy_survives(self):
        from rcm_mc.ui.competitive_intel_page import _add_features
        out = _add_features(pd.DataFrame([_CLEAN]))
        occ = out["occupancy_rate"].iloc[0]
        self.assertFalse(pd.isna(occ))
        self.assertLessEqual(occ, OCCUPANCY_PLAUSIBLE_HI)


class IcMemoGateTests(unittest.TestCase):
    def test_ic_memo_gates_occupancy_and_n2g(self):
        from rcm_mc.ui.ic_memo_page import _build_memo_data
        df = pd.DataFrame([_ARTIFACT, _CLEAN])
        d = _build_memo_data("999999", df)
        self.assertIsNone(d["occupancy"])   # 232% → None
        self.assertIsNone(d["n2g"])         # net > gross → None

    def test_ic_memo_keeps_clean_values(self):
        from rcm_mc.ui.ic_memo_page import _build_memo_data
        df = pd.DataFrame([_ARTIFACT, _CLEAN])
        d = _build_memo_data("999998", df)
        self.assertIsNotNone(d["occupancy"])
        self.assertIsNotNone(d["n2g"])


class PctFormatterNoneSafeTests(unittest.TestCase):
    def test_pct_renders_dash_for_none_and_nan(self):
        from rcm_mc.ui.ic_memo_page import _pct
        self.assertEqual(_pct(None), "—")
        self.assertEqual(_pct(float("nan")), "—")
        self.assertEqual(_pct(0.42), "42.0%")


if __name__ == "__main__":
    unittest.main()
