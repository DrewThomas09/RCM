"""Operating-margin data-quality guard on the hospital profile.

A hospital operating margin = (NPR - opex) / NPR. Some HCRIS records
are parent/CCN rollups or have partial expense lines, so opex is far
too low and the computed margin balloons to an impossible value (the
canonical bug: a $7.86B-NPR record showing 87.9%, which implies opex
is only ~12% of revenue). The fix MUTES such margins and badges them
"data quality: review" instead of presenting them as confident KPIs —
while keeping the real number visible (faithful to the filing).

Guards:
  - margin_is_plausible() band: -40%…+30%, None/NaN → True (unknown).
  - A plausible margin renders clean (no mute span, no caveat).
  - An implausible margin is wrapped in the mute span, carries the
    "Data quality: review" caveat, and STILL shows the value.
"""
from __future__ import annotations

import types
import unittest

from rcm_mc.ui._chartis_kit import (
    MARGIN_PLAUSIBLE_HI,
    MARGIN_PLAUSIBLE_LO,
    margin_is_plausible,
)
from rcm_mc.ui.hospital_profile import render_hospital_profile


def _render(npr: float, opex: float) -> str:
    score = types.SimpleNamespace(grade="B", score=72)
    hospital = {
        "ccn": "010001", "name": "Test Regional Medical Center",
        "city": "Austin", "state": "TX", "beds": 220,
        "net_patient_revenue": npr, "operating_expenses": opex,
        "net_income": npr - opex,
        "medicare_day_pct": 0.45, "medicaid_day_pct": 0.20,
    }
    return render_hospital_profile(hospital, score)


class MarginPlausibilityHelperTests(unittest.TestCase):
    def test_band_bounds(self) -> None:
        self.assertEqual((MARGIN_PLAUSIBLE_LO, MARGIN_PLAUSIBLE_HI), (-0.40, 0.30))

    def test_realistic_margins_are_plausible(self) -> None:
        for m in (0.0, 0.04, 0.12, -0.15, 0.30, -0.40):
            self.assertTrue(margin_is_plausible(m), m)

    def test_artifact_margins_are_flagged(self) -> None:
        for m in (0.879, 0.31, -0.41, -0.6, 1.0):
            self.assertFalse(margin_is_plausible(m), m)

    def test_unknown_is_not_flagged(self) -> None:
        # None / non-numeric / NaN → treat as unknown, never raise.
        self.assertTrue(margin_is_plausible(None))
        self.assertTrue(margin_is_plausible(float("nan")))
        self.assertTrue(margin_is_plausible("oops"))  # type: ignore[arg-type]


class HospitalProfileMarginGuardTests(unittest.TestCase):
    def test_plausible_margin_renders_clean(self) -> None:
        # ~4% margin (opex 96% of NPR) — a normal hospital.
        html = _render(100_000_000, 96_000_000)
        self.assertIn("4.0%", html)
        self.assertNotIn('<span class="hp-dq-muted" title=', html)
        self.assertNotIn("Data quality: review", html)

    def test_implausible_margin_is_muted_and_flagged(self) -> None:
        # 87.9% margin (opex ~12% of NPR) — the junk-opex artifact.
        html = _render(7_864_700_000, 950_000_000)
        # value still visible (faithful to the filing) …
        self.assertIn("87.9%", html)
        # … but muted and badged for review.
        self.assertIn('<span class="hp-dq-muted" title=', html)
        self.assertIn("Data quality: review", html)


if __name__ == "__main__":
    unittest.main()
