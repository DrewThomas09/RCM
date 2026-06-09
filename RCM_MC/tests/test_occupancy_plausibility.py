"""Regression: occupancy >100% is a filing artifact, not a real KPI.

bed_days_available (beds × days) is the hard ceiling on inpatient days, so
occupancy = patient_days ÷ bed_days_available can't exceed ~100% over a year.
29 HCRIS hospitals compute >100% (up to 239%) because their bed-days are
understated. Those must be flagged, not shown as "239% occupancy", and must
not fire a "high occupancy" investment catalyst. See
_chartis_kit.occupancy_is_plausible.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import OCCUPANCY_PLAUSIBLE_HI, occupancy_is_plausible


class OccupancyPlausibilityTests(unittest.TestCase):
    def test_normal_values_ok(self):
        for v in (0.0, 0.5, 0.85, 1.0, OCCUPANCY_PLAUSIBLE_HI):
            self.assertTrue(occupancy_is_plausible(v), v)

    def test_impossible_high_flagged(self):
        for v in (1.06, 1.30, 2.39):
            self.assertFalse(occupancy_is_plausible(v), v)

    def test_unknown_not_flagged(self):
        self.assertTrue(occupancy_is_plausible(None))
        self.assertTrue(occupancy_is_plausible(float("nan")))
        self.assertTrue(occupancy_is_plausible("x"))


class XrayOccupancyDisplayTests(unittest.TestCase):
    def _find_ccn(self, predicate):
        import pandas as pd
        from rcm_mc.data.hcris import _get_latest_per_ccn
        df = _get_latest_per_ccn()
        occ = (pd.to_numeric(df["total_patient_days"], errors="coerce")
               / pd.to_numeric(df["bed_days_available"], errors="coerce"))
        df = df.assign(_occ=occ)
        hit = df[df["_occ"].apply(lambda v: v == v and predicate(v))]
        return str(hit.iloc[0]["ccn"]) if len(hit) else None

    def test_artifact_occupancy_is_flagged_not_shown(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        ccn = self._find_ccn(lambda v: v > 1.05)
        self.assertIsNotNone(ccn, "expected a >105% occupancy hospital in HCRIS")
        h = render_hcris_xray_page({"ccn": [ccn]})
        self.assertIn("bed-days filing artifact", h)

    def test_plausible_occupancy_shown_normally(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        ccn = self._find_ccn(lambda v: 0.5 < v < 0.95)
        self.assertIsNotNone(ccn)
        h = render_hcris_xray_page({"ccn": [ccn]})
        self.assertIn("% occupancy", h)
        self.assertNotIn("bed-days filing artifact", h)


class ThesisCardOccupancyGuardTests(unittest.TestCase):
    def test_real_card_does_not_claim_high_occupancy_on_artifact(self):
        # Drive the real thesis card with a >100%-occupancy HCRIS hospital;
        # the "high occupancy" catalyst must not appear (the guard rejects the
        # artifact). Render is heavy (ML models) so this is a single sanity
        # pass against live data, not an exhaustive sweep.
        import pandas as pd
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.thesis_card import render_thesis_card
        df = _get_latest_per_ccn().copy()
        occ = (pd.to_numeric(df["total_patient_days"], errors="coerce")
               / pd.to_numeric(df["bed_days_available"], errors="coerce"))
        if "occupancy_rate" not in df.columns:
            df["occupancy_rate"] = occ
        hit = df[occ > 1.05]
        if hit.empty:
            self.skipTest("no >105% occupancy hospital in this dataset")
        ccn = str(hit.iloc[0]["ccn"])
        html = render_thesis_card(ccn, df)
        self.assertNotIn("High occupancy supports revenue stability", html)


if __name__ == "__main__":
    unittest.main()
