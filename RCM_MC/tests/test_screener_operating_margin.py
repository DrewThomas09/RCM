"""Target Screener operating margin: band-gate, not the old -100% clamp.

You flagged that the Hospital Target Screener showed a wall of identical
-100.0% margins and asked for the real margins from the cost report. Root
cause: the old path computed (npr - opex)/npr and CLAMPED to [-1, 1], so every
junk filing (operating expenses far above patient revenue) collapsed to a
uniform -100%, and "most distressed first" buried the real targets under that
artifact.

The fix (`hcris.screener_operating_margin`) GATES instead of clamps: it returns
the real margin only where the filing is trustworthy (net patient revenue
> $1M, positive opex, ratio inside the plausible band), and NaN otherwise so
those rows render as "—" and sort last. These guards pin that behaviour so the
-100% wall can't come back.
"""
from __future__ import annotations

import math
import unittest

import pandas as pd

from rcm_mc.data.hcris import (
    SCREENER_MARGIN_HI,
    SCREENER_MARGIN_LO,
    screener_operating_margin,
)


class ScreenerOperatingMargin(unittest.TestCase):
    def _margins(self, rows):
        df = pd.DataFrame(rows)
        return list(screener_operating_margin(df))

    def test_band_constants_are_a_gate_not_a_unit_clamp(self):
        # The plausible band is tighter than [-1, 1]; that is the whole point.
        self.assertEqual(SCREENER_MARGIN_LO, -0.40)
        self.assertEqual(SCREENER_MARGIN_HI, 0.30)
        self.assertGreater(SCREENER_MARGIN_LO, -1.0)

    def test_trustworthy_filing_returns_real_margin(self):
        # npr $100M, opex $103M -> -3.0% margin, well inside the band.
        (m,) = self._margins([
            {"net_patient_revenue": 100e6, "operating_expenses": 103e6},
        ])
        self.assertAlmostEqual(m, -0.03, places=4)

    def test_healthy_filing_returns_positive_margin(self):
        # npr $100M, opex $80M -> +20% margin.
        (m,) = self._margins([
            {"net_patient_revenue": 100e6, "operating_expenses": 80e6},
        ])
        self.assertAlmostEqual(m, 0.20, places=4)

    def test_junk_filing_is_nan_not_minus_one(self):
        # The exact -100%-wall artifact: opex 5x patient revenue. Old code
        # clamped this to -1.0; the gate must return NaN instead.
        (m,) = self._margins([
            {"net_patient_revenue": 10e6, "operating_expenses": 50e6},
        ])
        self.assertTrue(math.isnan(m), "junk filing must gate to NaN, not -100%")
        self.assertNotEqual(m, -1.0)

    def test_tiny_revenue_is_gated(self):
        # net patient revenue <= $1M is not trustworthy -> NaN.
        (m,) = self._margins([
            {"net_patient_revenue": 0.5e6, "operating_expenses": 0.4e6},
        ])
        self.assertTrue(math.isnan(m))

    def test_nonpositive_opex_is_gated(self):
        (m,) = self._margins([
            {"net_patient_revenue": 100e6, "operating_expenses": 0.0},
        ])
        self.assertTrue(math.isnan(m))

    def test_band_edges(self):
        # -35% sits inside the band (kept); -45% sits outside (gated to NaN).
        kept, gated = self._margins([
            {"net_patient_revenue": 100e6, "operating_expenses": 135e6},  # -0.35
            {"net_patient_revenue": 100e6, "operating_expenses": 145e6},  # -0.45
        ])
        self.assertAlmostEqual(kept, -0.35, places=4)
        self.assertTrue(math.isnan(gated))

    def test_mixed_frame_surfaces_real_varied_margins(self):
        # A realistic mix: the screen should show varied real margins and "—"
        # (NaN) for the untrustworthy rows, never a wall of identical -100%.
        ms = self._margins([
            {"net_patient_revenue": 200e6, "operating_expenses": 206e6},   # -3%
            {"net_patient_revenue": 50e6, "operating_expenses": 250e6},    # junk
            {"net_patient_revenue": 80e6, "operating_expenses": 70e6},     # +12.5%
            {"net_patient_revenue": 120e6, "operating_expenses": 600e6},   # junk
        ])
        real = [x for x in ms if not math.isnan(x)]
        self.assertEqual(len(real), 2)
        # The real margins are varied, not a single repeated artifact value.
        self.assertEqual(len(set(round(x, 4) for x in real)), 2)
        self.assertNotIn(-1.0, real)


if __name__ == "__main__":
    unittest.main()
