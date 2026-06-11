"""Wave-13 visual: white-space conviction spectrum.

The white-space page rendered opportunity cards per dimension but the
0–1 conviction distribution — where the scores actually cluster
against the 0.25/0.50/0.75 bands the explainer describes — had no
visual. Pins the dot-spectrum SVG: per-dimension rows, threshold
guides, score tones, best-per-row labels, and empty states.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.white_space_page import (
    _score_color,
    _score_spectrum_svg,
)


def _by_dim():
    return {
        "geographic": [
            {"name": "Texas", "score": 0.82, "dimension": "geographic"},
            {"name": "Ohio", "score": 0.41, "dimension": "geographic"},
        ],
        "segment": [
            {"name": "Behavioral bolt-on", "score": 0.55,
             "dimension": "segment"},
        ],
        "channel": [],
    }


class ScoreSpectrumTests(unittest.TestCase):
    def test_renders_rows_guides_and_tones(self):
        svg = _score_spectrum_svg(_by_dim())
        self.assertIn("<svg", svg)
        self.assertIn("ck-ws-spectrum", svg)
        self.assertIn("GEOGRAPHIC", svg)
        self.assertIn("SEGMENT", svg)
        # Channel row has no opportunities — omitted, not faked.
        self.assertNotIn("CHANNEL", svg)
        # Threshold guides at the documented bands.
        for tag in ("0.25", "0.50", "0.75"):
            self.assertIn(f">{tag}</text>", svg)
        self.assertIn(_score_color(0.82), svg)  # strong-fit tone
        self.assertIn(_score_color(0.41), svg)  # low-conviction tone

    def test_best_per_dimension_labeled(self):
        svg = _score_spectrum_svg(_by_dim())
        self.assertIn("Texas", svg)
        self.assertIn("0.82", svg)
        # Runner-up dots are unlabeled.
        self.assertNotIn("Ohio", svg)

    def test_scores_clamped_to_axis(self):
        svg = _score_spectrum_svg({
            "segment": [{"name": "Wild", "score": 1.7}],
        })
        self.assertIn("<svg", svg)
        # Clamped to 1.0 — the dot's cx never exceeds the axis end
        # (label_w 110 + axis_w 540 = 650).
        self.assertIn('cx="650.0"', svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_score_spectrum_svg({}), "")
        self.assertEqual(
            _score_spectrum_svg({"geographic": [], "segment": []}), "")


if __name__ == "__main__":
    unittest.main()
