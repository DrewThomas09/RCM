"""Pin for the MOIC-by-scenario bar chart on /scenario-modeler.

The scenario comparison spread MOIC across table columns; this lead bar
chart makes the winning case obvious — each scenario a bar (share of the
best MOIC), with the best case and any >=2.0x in the positive tone.
"""
from __future__ import annotations

import unittest


def _r(name, moic):
    return {"scenario": {"name": name}, "moic": moic}


class ScenarioMoicBarsTests(unittest.TestCase):
    _BAR = 'ck-bar-row-fill" style="width:'

    def _bars(self, results):
        from rcm_mc.ui.scenario_modeler_page import _scenario_moic_bars
        return _scenario_moic_bars(results)

    def test_one_bar_per_scenario(self):
        html = self._bars([_r("Base", 2.1), _r("Bull", 3.4), _r("Bear", 1.4)])
        self.assertIn("Scenario Returns", html)
        self.assertEqual(html.count(self._BAR), 3)

    def test_best_is_full_width(self):
        html = self._bars([_r("Base", 2.0), _r("Bull", 4.0)])
        self.assertIn("width:100.0%", html)  # Bull = best

    def test_best_and_above_2x_are_positive(self):
        html = self._bars([_r("Base", 2.1), _r("Bear", 1.4)])
        # Base ≥2.0x → positive; Bear <2.0x and not best → teal.
        self.assertIn("%;background:var(--sc-positive)", html)
        self.assertIn("%;background:var(--sc-teal)", html)

    def test_skips_zero_moic(self):
        html = self._bars([_r("A", 2.0), _r("B", 0), _r("C", 1.5)])
        self.assertEqual(html.count(self._BAR), 2)

    def test_empty_below_two(self):
        self.assertEqual(self._bars([_r("Solo", 2.0)]), "")


if __name__ == "__main__":
    unittest.main()
