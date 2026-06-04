"""b175 — the regression leverage×residual scatter was squished + unreadable.

Reported: the influence scatter looked "horrible, so squished," with hospital
names piled on top of each other and the x-axis title "Leverage h_ii" overlapping
the tick numbers. Causes: preserveAspectRatio="none" stretched/distorted the
panel; the axis title sat 4px from the tick row; and all 20 flagged points were
labeled at once. Fixed: proportional scaling, a taller panel with the title
clear of the ticks, and only the top-9 (by Cook's D) labeled with greedy
vertical de-collision.
"""
from __future__ import annotations

import re
import unittest


def _result_with_outliers(n=20):
    outs = []
    for i in range(n):
        outs.append({
            "name": f"Hosp {i:02d} Mem",
            "leverage": 0.005 + (i % 5) * 0.001,   # clustered low leverage
            "std_residual": -0.5 + (i % 3) * 0.2,  # clustered residual
            "cooks_d": 0.5 - i * 0.01,
            "influence_class": "high_leverage",
        })
    return {"n": 5000, "outliers": outs}


class TestLeverageScatter(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.regression_page import _rge_leverage_scatter
        self.html = _rge_leverage_scatter(_result_with_outliers())

    def test_proportional_not_distorted(self):
        # The squish came from preserveAspectRatio="none" stretching the panel.
        self.assertIn('preserveAspectRatio="xMidYMid meet"', self.html)
        self.assertNotIn('preserveAspectRatio="none"', self.html)

    def test_labels_capped_to_avoid_pile(self):
        # Only the top-9 hospital labels render (not all 20 piled up). Count the
        # data labels by the "Hosp NN Mem" pattern.
        labels = re.findall(r"Hosp \d+ Mem", self.html)
        self.assertLessEqual(len(labels), 9)
        self.assertGreater(len(labels), 0)

    def test_axis_title_present(self):
        self.assertIn("Leverage h_ii", self.html)


if __name__ == "__main__":
    unittest.main()
