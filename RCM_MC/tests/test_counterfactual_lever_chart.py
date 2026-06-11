"""Wave-21 visual: counterfactual lever impact chart.

The counterfactual advisor rendered each lever as a card — comparing
savings size against feasibility across levers meant reading every
card. Pins the bar chart: feasibility tones, impact sort, qualitative
levers counted not drawn, and the empty states.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.counterfactual.advisor import (
    Counterfactual,
    CounterfactualSet,
)
from rcm_mc.ui.counterfactual_page import (
    _feasibility_color,
    _lever_impact_svg,
)


def _cf(module, usd, feasibility):
    return Counterfactual(
        module=module, original_band="CRITICAL", target_band="AMBER",
        lever="lever", change_description="change",
        estimated_dollar_impact_usd=usd, feasibility=feasibility,
    )


class LeverImpactChartTests(unittest.TestCase):
    def test_renders_bars_with_feasibility_tones(self):
        svg = _lever_impact_svg(CounterfactualSet(items=[
            _cf("CPOM", 2_400_000, "HIGH"),
            _cf("NSA", 600_000, "LOW"),
        ]))
        self.assertIn("<svg", svg)
        self.assertIn("cf-lever-impact", svg)
        self.assertIn(_feasibility_color("HIGH"), svg)
        self.assertIn(_feasibility_color("LOW"), svg)
        self.assertIn("$2.4M · HIGH", svg)
        self.assertIn("$600K · LOW", svg)

    def test_sorted_largest_first(self):
        svg = _lever_impact_svg(CounterfactualSet(items=[
            _cf("Small", 100_000, "HIGH"),
            _cf("Large", 5_000_000, "MEDIUM"),
        ]))
        self.assertLess(svg.index("Large"), svg.index("Small"))

    def test_qualitative_levers_counted_not_drawn(self):
        svg = _lever_impact_svg(CounterfactualSet(items=[
            _cf("Quantified", 1_000_000, "HIGH"),
            _cf("Qualitative", 0, "MEDIUM"),
        ]))
        self.assertIn("1 QUALITATIVE LEVER NOT CHARTED", svg)
        self.assertNotIn("Qualitative</text>", svg)

    def test_no_quantified_levers_renders_nothing(self):
        self.assertEqual(
            _lever_impact_svg(CounterfactualSet(items=[
                _cf("OnlyQual", 0, "HIGH"),
            ])),
            "",
        )
        self.assertEqual(_lever_impact_svg(CounterfactualSet(items=[])), "")


if __name__ == "__main__":
    unittest.main()
