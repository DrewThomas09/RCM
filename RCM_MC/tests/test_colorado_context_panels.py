"""Cost Structure + Payer Stress carry real Colorado CONTEXTUAL panels.

Market-level CIVHC data framing (PPPY by region; APM penetration + RBP), shown
as context — never as facility opex or this provider's payer mix. Missing
renders "—", with state-specific caveats.
"""
import unittest

from rcm_mc.ui.data_public.cost_structure_page import render_cost_structure
from rcm_mc.ui.data_public.payer_stress_page import render_payer_stress
from rcm_mc.ui.data_public import _colorado_context as cc


class TestColoradoContextPanels(unittest.TestCase):
    def test_cost_structure_has_colorado_cost_context(self):
        html = render_cost_structure({})
        self.assertIn("Colorado cost context · CONTEXTUAL", html)
        self.assertIn("Per-Person-Per-Year", html)
        self.assertIn("not</b> this facility", html)     # not opex
        self.assertIn("ck-sp", html)                       # source header

    def test_payer_stress_has_payer_pressure_context(self):
        html = render_payer_stress({})
        self.assertIn("Colorado payer-pressure context · CONTEXTUAL", html)
        self.assertIn("x Medicare", html)                  # RBP median
        self.assertIn("not</b> this provider", html)

    def test_panels_use_real_loader_values(self):
        # cost panel reflects payer_cost_by_geography; pressure reflects RBP median
        panel = cc.colorado_cost_context_panel(year="2021", claim_type="Inpatient")
        self.assertIn("DOI Region", panel)
        pressure = cc.colorado_payer_pressure_panel()
        self.assertIn("Medicare", pressure)

    def test_panels_degrade_to_empty_safely(self):
        # A claim type with no rows yields an empty string, not a crash.
        self.assertEqual(cc.colorado_cost_context_panel(
            year="9999", claim_type="Nonexistent"), "")


if __name__ == "__main__":
    unittest.main()
