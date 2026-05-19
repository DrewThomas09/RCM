"""Pin for the EBITDA-Δ tornado chart on /deal/<id>/stress.

Replaces the bland multi-section scenario tables with a glanceable
horizontal-bar view sorted by EBITDA delta — partners see "where
the deal hurts" without scanning per-section tables.
"""
from __future__ import annotations

import unittest


class TornadoTests(unittest.TestCase):
    def test_renders_one_bar_per_scenario(self):
        from rcm_mc.ui.chartis.stress_page import (
            _ebitda_delta_tornado,
        )
        svg = _ebitda_delta_tornado([
            {"name": "rate_shock", "ebitda_delta_pct": -0.12,
             "passes": False, "covenant_breach": True},
            {"name": "vol_drop", "ebitda_delta_pct": -0.08,
             "passes": False, "covenant_breach": False},
            {"name": "baseline", "ebitda_delta_pct": 0.0,
             "passes": True, "covenant_breach": False},
            {"name": "upside", "ebitda_delta_pct": 0.05,
             "passes": True, "covenant_breach": False},
        ])
        self.assertTrue(svg.startswith("<svg"))
        # One bar per scenario
        self.assertEqual(svg.count("<rect"), 4)
        # Value labels
        self.assertIn("-12.0%", svg)
        self.assertIn("+5.0%", svg)
        # Axis label
        self.assertIn("EBITDA Δ", svg)

    def test_negative_breach_uses_brick_red(self):
        from rcm_mc.ui.chartis.stress_page import (
            _ebitda_delta_tornado,
        )
        # Breach + negative delta → covenant-breach color
        svg = _ebitda_delta_tornado([
            {"name": "breach", "ebitda_delta_pct": -0.15,
             "passes": False, "covenant_breach": True},
        ])
        self.assertIn("#b5321e", svg)

    def test_positive_uses_green(self):
        from rcm_mc.ui.chartis.stress_page import (
            _ebitda_delta_tornado,
        )
        svg = _ebitda_delta_tornado([
            {"name": "upside", "ebitda_delta_pct": 0.10,
             "passes": True, "covenant_breach": False},
        ])
        self.assertIn("#0a8a5f", svg)

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.stress_page import (
            _ebitda_delta_tornado,
        )
        self.assertEqual(_ebitda_delta_tornado([]), "")

    def test_skips_scenarios_with_no_delta(self):
        from rcm_mc.ui.chartis.stress_page import (
            _ebitda_delta_tornado,
        )
        # Mix of scenarios with and without delta — only those with
        # a numeric delta plot.
        svg = _ebitda_delta_tornado([
            {"name": "has_delta", "ebitda_delta_pct": -0.05,
             "passes": False, "covenant_breach": False},
            {"name": "no_delta", "ebitda_delta_pct": None,
             "passes": True, "covenant_breach": False},
            {"name": "str_delta_oops",
             "ebitda_delta_pct": "broken",
             "passes": True, "covenant_breach": False},
        ])
        self.assertEqual(svg.count("<rect"), 1)


if __name__ == "__main__":
    unittest.main()
