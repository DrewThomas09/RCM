"""tests for ``tour_overlay`` (P77)."""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui._ui_kit import tour_overlay


WORKBENCH_TOUR = [
    {"selector": '[data-tab="overview"]',
     "title": "Overview",
     "body": "The headline number for this deal."},
    {"selector": '[data-tab="rcm-profile"]',
     "title": "RCM Profile",
     "body": "How this hospital benchmarks against its peers."},
    {"selector": '[data-tab="ebitda-bridge"]',
     "title": "EBITDA Bridge",
     "body": "Sliders to test value-creation hypotheses."},
    {"selector": '[data-tab="monte-carlo"]',
     "title": "Monte Carlo",
     "body": "Distribution of outcomes under uncertainty."},
    {"selector": '[data-tab="risk"]',
     "title": "Risk & Diligence",
     "body": "Partner-action items."},
]


class StructureAndContent(unittest.TestCase):

    def test_steps_count_matches(self) -> None:
        html = tour_overlay(WORKBENCH_TOUR)
        self.assertEqual(html.count('class="tour-step"'), 5)
        self.assertIn('data-step-count="5"', html)

    def test_each_step_has_target(self) -> None:
        html = tour_overlay(WORKBENCH_TOUR)
        # Quotes inside the selector get escaped to &quot; in
        # attribute context; substring-match each tour-step's
        # unique data-tab fragment.
        for step in WORKBENCH_TOUR:
            tab_name = step["selector"].split('"')[1]  # e.g. "overview"
            with self.subTest(tab_name=tab_name):
                self.assertIn(tab_name, html)

    def test_each_step_hidden_by_default(self) -> None:
        # 5 step <li …  hidden> + 1 outer container <div … hidden …>.
        html = tour_overlay(WORKBENCH_TOUR)
        self.assertEqual(html.count(" hidden"), 6)

    def test_controls_present(self) -> None:
        html = tour_overlay(WORKBENCH_TOUR)
        self.assertIn("tour-skip", html)
        self.assertIn("tour-prev", html)
        self.assertIn("tour-next", html)


class GracefulInput(unittest.TestCase):

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(tour_overlay([]), "")


class TourJSAttachedFromShell(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_tour_js_present(self) -> None:
        self.assertIn("tour-overlay", self.html)
        self.assertIn("data-tour", self.html)
        self.assertIn("active", self.html)


if __name__ == "__main__":
    unittest.main()
