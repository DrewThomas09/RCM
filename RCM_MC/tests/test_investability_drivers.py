"""Investability composite drivers — which axis drags the score.

A pure function of the three sub-scores + the published AXIS_WEIGHTS,
so the decomposition can never disagree with the composite it
explains. Points-contributed must sum to the composite; the binding
axis is the one losing the most points.
"""
from __future__ import annotations

import unittest

from rcm_mc.pe_intelligence.investability_scorer import (
    AXIS_WEIGHTS, InvestabilityResult, analyze_score_drivers,
)


def _result(opp, val, stab):
    composite = (AXIS_WEIGHTS["opportunity"] * opp
                 + AXIS_WEIGHTS["value"] * val
                 + AXIS_WEIGHTS["stability"] * stab)
    return InvestabilityResult(
        score=int(round(composite * 100)), grade="C",
        opportunity_score=opp, value_score=val, stability_score=stab)


class ScoreDriversTests(unittest.TestCase):
    def test_contributions_sum_to_composite(self):
        r = _result(0.8, 0.4, 0.7)
        d = analyze_score_drivers(r)
        total_contrib = sum(x.points_contributed for x in d.drivers)
        self.assertAlmostEqual(total_contrib, r.score, delta=1.0)

    def test_binding_axis_loses_most(self):
        r = _result(0.8, 0.4, 0.7)   # value weakest & heaviest weight
        d = analyze_score_drivers(r)
        self.assertEqual(d.binding_axis, "value")
        self.assertEqual(d.drivers[0].axis, "value")   # sorted lost-first

    def test_points_lost_formula(self):
        r = _result(0.5, 0.5, 0.5)
        d = analyze_score_drivers(r)
        for x in d.drivers:
            self.assertAlmostEqual(
                x.points_lost, x.weight * (1 - x.score) * 100, places=1)
            self.assertAlmostEqual(
                x.points_contributed, x.weight * x.score * 100, places=1)

    def test_uplift_is_weighted_gap_to_best(self):
        r = _result(0.9, 0.4, 0.6)   # best=opp 0.9, binding=value 0.4
        d = analyze_score_drivers(r)
        # value weight 0.40, gap 0.9-0.4=0.5 → 0.40*0.5*100 = 20
        self.assertEqual(d.uplift_if_binding_fixed, 20)

    def test_near_max_score_has_no_material_drag(self):
        r = _result(0.97, 0.96, 0.98)
        d = analyze_score_drivers(r)
        self.assertLess(d.total_points_lost, 5)
        self.assertIn("near-maxed", d.note)

    def test_to_dict_round_trips(self):
        d = analyze_score_drivers(_result(0.8, 0.4, 0.7))
        dd = d.to_dict()
        self.assertEqual(dd["binding_axis"], "value")
        self.assertEqual(len(dd["drivers"]), 3)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(AXIS_WEIGHTS.values()), 1.0, places=6)

    def test_renders_in_block(self):
        from rcm_mc.ui.chartis.investability_page import _score_drivers_block
        h = _score_drivers_block(62, "C", 0.8, 0.4, 0.7)
        self.assertIn("DECOMPOSITION", h)
        self.assertIn("binding", h)


if __name__ == "__main__":
    unittest.main()
