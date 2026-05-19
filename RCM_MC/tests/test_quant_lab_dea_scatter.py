"""Pin for the DEA efficiency-frontier scatter on /quant-lab.

Adds the canonical "input vs output" DEA visualization above the
existing efficiency table. Frontier hospitals render as stars
(top-left envelope); non-frontier render as colored dots by
efficiency band (amber 0.5+, brick 0.3-0.5, plum <0.3).
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _score(**kwargs):
    return SimpleNamespace(
        ccn=kwargs.get("ccn", "X"),
        hospital_name=kwargs.get("hospital_name", "Hosp"),
        state=kwargs.get("state", "MA"),
        efficiency_score=kwargs.get("efficiency_score", 0.5),
        is_frontier=kwargs.get("is_frontier", False),
        input_levels=kwargs.get(
            "input_levels", {"operating_expenses": 50_000_000},
        ),
        output_levels=kwargs.get(
            "output_levels", {"net_patient_revenue": 75_000_000},
        ),
    )


class DeaFrontierScatterTests(unittest.TestCase):
    def test_frontier_renders_as_star(self):
        from rcm_mc.ui.quant_lab_page import _dea_frontier_scatter
        svg = _dea_frontier_scatter([
            _score(efficiency_score=0.98, is_frontier=True),
        ])
        # Star = <polygon>
        self.assertEqual(svg.count("<polygon"), 1)
        # No non-frontier circles when all are frontier
        self.assertEqual(svg.count("<circle"), 0)

    def test_non_frontier_renders_as_dot(self):
        from rcm_mc.ui.quant_lab_page import _dea_frontier_scatter
        svg = _dea_frontier_scatter([
            _score(efficiency_score=0.5, is_frontier=False),
        ])
        self.assertEqual(svg.count("<circle"), 1)
        self.assertEqual(svg.count("<polygon"), 0)

    def test_mixed_frontier_and_non_frontier(self):
        from rcm_mc.ui.quant_lab_page import _dea_frontier_scatter
        svg = _dea_frontier_scatter([
            _score(ccn="A", efficiency_score=0.98, is_frontier=True),
            _score(ccn="B", efficiency_score=0.55, is_frontier=False),
            _score(ccn="C", efficiency_score=0.25, is_frontier=False),
        ])
        self.assertEqual(svg.count("<polygon"), 1)
        self.assertEqual(svg.count("<circle"), 2)
        # Axis labels
        self.assertIn("Operating expenses", svg)
        self.assertIn("Net patient revenue", svg)
        # Frontier legend marker
        self.assertIn("FRONTIER", svg)

    def test_skips_rows_with_missing_input_or_output(self):
        from rcm_mc.ui.quant_lab_page import _dea_frontier_scatter
        # Row with no operating_expenses → skipped
        svg = _dea_frontier_scatter([
            _score(ccn="OK", efficiency_score=0.5, is_frontier=False,
                   input_levels={"operating_expenses": 1e7},
                   output_levels={"net_patient_revenue": 1.5e7}),
            _score(ccn="NO_INP", efficiency_score=0.5, is_frontier=False,
                   input_levels={"other_input": 1e7},
                   output_levels={"net_patient_revenue": 1.5e7}),
            _score(ccn="ZERO", efficiency_score=0.5, is_frontier=False,
                   input_levels={"operating_expenses": 0},
                   output_levels={"net_patient_revenue": 1.5e7}),
        ])
        self.assertEqual(svg.count("<circle"), 1)

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.quant_lab_page import _dea_frontier_scatter
        self.assertEqual(_dea_frontier_scatter([]), "")


if __name__ == "__main__":
    unittest.main()
