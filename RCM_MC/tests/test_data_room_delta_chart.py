"""Wave-15 visual: data-room signed surprise chart.

The data room's stated purpose is showing "exactly where the seller
data confirms or contradicts our models", but the contradiction lived
only in a table delta column and a >15% surprise list. Pins the
signed-bar SVG: direction-aware tones, magnitude sort, clamp marker,
ML-only metrics contributing nothing, and the empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.brand import PALETTE
from rcm_mc.ui.data_room_page import _calibration_delta_svg


def _cal(label, pred, delta, direction):
    return SimpleNamespace(
        label=label, ml_predicted=pred,
        delta_from_prediction=delta, direction=direction,
    )


class CalibrationDeltaChartTests(unittest.TestCase):
    def test_direction_aware_tones(self):
        svg = _calibration_delta_svg([
            # Denial rate (lower is better) came in lower → favorable.
            _cal("Denial rate", 0.12, -0.02, "lower"),
            # Margin (higher is better) came in lower → unfavorable.
            _cal("Operating margin", 0.08, -0.02, "higher"),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("Signed Surprise", svg)
        self.assertIn(PALETTE["positive"], svg)
        self.assertIn(PALETTE["negative"], svg)

    def test_sorted_by_magnitude(self):
        svg = _calibration_delta_svg([
            _cal("Small miss", 1.0, 0.05, "higher"),
            _cal("Big miss", 1.0, -0.40, "higher"),
        ])
        self.assertLess(svg.index("Big miss"), svg.index("Small miss"))

    def test_clamp_marker_beyond_50pct(self):
        svg = _calibration_delta_svg([
            _cal("Wild metric", 1.0, 0.80, "higher"),
        ])
        self.assertIn("+80.0%›", svg)

    def test_ml_only_metrics_contribute_nothing(self):
        ml_only = SimpleNamespace(
            label="Untouched", ml_predicted=0.1,
            delta_from_prediction=None, direction="lower",
        )
        self.assertEqual(_calibration_delta_svg([ml_only]), "")

    def test_empty_renders_nothing(self):
        self.assertEqual(_calibration_delta_svg([]), "")


if __name__ == "__main__":
    unittest.main()
