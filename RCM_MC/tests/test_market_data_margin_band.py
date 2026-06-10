"""Regression: state-median margin uses the agreed plausible band.

market_data computed each state's median operating margin over a loose
[-100%, +100%] window, so junk-opex filing artifacts skewed the state stat
(e.g. TX +0.97% with artifacts vs +2.65% without). It now uses the same
-40%…+30% band as the X-Ray / command center.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui._chartis_kit import MARGIN_PLAUSIBLE_HI, MARGIN_PLAUSIBLE_LO
from rcm_mc.ui.market_data_page import _compute_state_stats


class StateMedianBandTests(unittest.TestCase):
    def test_artifact_margins_excluded_from_state_median(self):
        # Three real ~5% margins and one +90% junk-opex artifact in one state.
        rows = []
        for npr, opex in [(2e8, 1.9e8), (3e8, 2.85e8), (4e8, 3.8e8),
                          (1e8, 1e7)]:   # last → +90% margin (artifact)
            rows.append({"state": "ZZ", "net_patient_revenue": npr,
                         "operating_expenses": opex, "beds": 100,
                         "total_patient_days": 20000, "bed_days_available": 36600})
        stats = _compute_state_stats(pd.DataFrame(rows))
        zz = next(s for s in stats if s["state"] == "ZZ")
        # The +90% artifact is outside the band → excluded → median ≈ 5%.
        self.assertLessEqual(zz["avg_margin"], MARGIN_PLAUSIBLE_HI)
        self.assertGreaterEqual(zz["avg_margin"], MARGIN_PLAUSIBLE_LO)
        self.assertAlmostEqual(zz["avg_margin"], 0.05, places=2)


if __name__ == "__main__":
    unittest.main()
