"""Regression: operating-margin verification is centralized and consistent.

A HCRIS operating margin outside the agreed −40%…+30% band is almost always
a filing artifact (incomplete/aggregated opex), not a real result. Three
guarantees are asserted here:

  1. ``margin_flag`` classifies *why* a value is implausible ("high"/"low")
     so a surface can FLAG it rather than silently drop it to "—".
  2. The DataFrame-level gate (``margin_is_plausible_series``) uses the SAME
     band as the per-row display gate — a looser local band previously let
     ±100% artifacts inflate the command-center "distressed" count and skew
     its median margin.
  3. The target screener carries a per-row flag and surfaces a count of
     flagged hospitals (verification transparency), and the command center
     gates its headline stats.
"""
import unittest

import pandas as pd

from rcm_mc.ui._chartis_kit import (
    MARGIN_PLAUSIBLE_HI,
    MARGIN_PLAUSIBLE_LO,
    margin_flag,
    margin_is_plausible,
    margin_is_plausible_series,
)


class MarginFlagTests(unittest.TestCase):
    def test_high_artifact_flagged_high(self):
        self.assertEqual(margin_flag(0.45), "high")
        self.assertEqual(margin_flag(MARGIN_PLAUSIBLE_HI + 0.001), "high")

    def test_low_artifact_flagged_low(self):
        self.assertEqual(margin_flag(-0.60), "low")
        self.assertEqual(margin_flag(MARGIN_PLAUSIBLE_LO - 0.001), "low")

    def test_plausible_not_flagged(self):
        for m in (-0.40, -0.05, 0.0, 0.05, 0.30):
            self.assertIsNone(margin_flag(m), m)

    def test_unknown_not_flagged(self):
        self.assertIsNone(margin_flag(None))
        self.assertIsNone(margin_flag(float("nan")))
        self.assertIsNone(margin_flag("x"))

    def test_flag_agrees_with_is_plausible(self):
        # The boolean gate and the reason-classifier share one band.
        for m in (-0.6, -0.4, -0.1, 0.0, 0.2, 0.3, 0.5):
            self.assertEqual(margin_is_plausible(m), margin_flag(m) is None, m)


class MarginSeriesGateTests(unittest.TestCase):
    def test_series_gate_matches_scalar_band(self):
        s = pd.Series([-0.60, -0.40, -0.05, 0.10, 0.30, 0.55, float("nan")])
        ok = margin_is_plausible_series(s)
        # NaN is "unknown" → kept True (don't flag); artifacts → False.
        self.assertEqual(ok.tolist(), [False, True, True, True, True, False, True])

    def test_series_excludes_artifacts_from_stats(self):
        # A ±100% artifact must not survive the gate into a median/count.
        s = pd.Series([0.02, 0.03, 1.0, -1.0, 0.99])
        clean = s[margin_is_plausible_series(s)].dropna()
        self.assertEqual(sorted(clean.tolist()), [0.02, 0.03])


class CommandCenterStatGateTests(unittest.TestCase):
    def test_distressed_count_excludes_artifacts(self):
        # Two real distressed (<-5%), one artifact at the -100% extreme that
        # must NOT be counted as distressed once the band gate is applied.
        df = pd.DataFrame({"operating_margin": [-0.08, -0.12, -1.00, 0.03]})
        mask = margin_is_plausible_series(df["operating_margin"])
        clean = df.loc[mask.fillna(False), "operating_margin"].dropna()
        self.assertEqual(int((clean < -0.05).sum()), 2)


class TargetScreenerFlagTests(unittest.TestCase):
    def test_hospital_rows_carry_margin_flag(self):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        rows = _vertical_rows("hospitals", limit=None)
        self.assertTrue(rows, "expected a non-empty HCRIS hospital universe")
        # Flagged rows have their value gated to None AND a flag reason set,
        # and every shown value is inside the plausible band.
        for r in rows:
            if r.get("q_flag") is not None:
                self.assertIn(r["q_flag"], ("high", "low"))
                self.assertIsNone(r["q"])
            if r.get("q") is not None:
                self.assertTrue(margin_is_plausible(r["q"]))
        # At least one too-high artifact exists in the live data and is flagged.
        self.assertTrue(any(r.get("q_flag") == "high" for r in rows))

    def test_flag_renders_a_marker_not_bare_dash(self):
        from rcm_mc.ui.target_screener_page import _fmt_q
        high = _fmt_q({"q": None, "q_flag": "high", "q_pct": True})
        self.assertIn("⚑", high)
        self.assertIn("HCRIS filing", high)
        # No flag → plain em-dash, no marker.
        plain = _fmt_q({"q": None, "q_flag": None, "q_pct": True})
        self.assertNotIn("⚑", plain)


if __name__ == "__main__":
    unittest.main()
