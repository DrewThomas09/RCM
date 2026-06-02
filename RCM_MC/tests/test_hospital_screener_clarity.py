"""Hospital Screener clarity pass.

You flagged that "Turnaround Targets" returned giant hospitals and the page
wasn't clear about what it screens for. The render layer now:
  - shows presets as labelled cards stating their SIZE range (so intent —
    buy-in-range vs large-cap diligence — is explicit);
  - exposes explicit min/max RANGE filters (+ min-margin, max-revenue) and a
    sort control;
  - shows the active criteria as "IN RANGE →" chips;
  - adds an NPR/Bed column and MUTES implausible (junk-opex) margins instead
    of letting them read as real.
(The size-bounding of the presets themselves lives in server.py.)
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.deal_comparison import render_screen_page


class PresetClarityTests(unittest.TestCase):
    def test_presets_are_cards_with_size_ranges(self) -> None:
        html = render_screen_page(total_scanned=6123)
        self.assertIn("hs-preset", html)
        self.assertIn("Turnaround — acquirable", html)
        self.assertIn("50–400 beds", html)          # explicit acquirable range
        self.assertIn("Large platforms", html)       # the large-cap screen
        # the old vague label is gone
        self.assertNotIn("Turnaround Targets", html)

    def test_active_preset_highlighted(self) -> None:
        html = render_screen_page(
            filters={"min_beds": "50", "max_beds": "400", "max_margin": "3",
                     "sort": "margin"},
            predefined="turnaround", total_scanned=6123)
        self.assertIn("hs-preset-active", html)


class FilterAndChipTests(unittest.TestCase):
    def test_range_filters_and_sort_present(self) -> None:
        html = render_screen_page(total_scanned=6123)
        for field in ("min_margin", "max_revenue", "min_revenue", "max_beds"):
            self.assertIn(f'name="{field}"', html)
        self.assertIn('name="sort"', html)
        self.assertIn("most distressed first", html)

    def test_active_criteria_chips(self) -> None:
        html = render_screen_page(
            filters={"min_beds": "50", "max_beds": "400", "max_margin": "3",
                     "sort": "margin"},
            predefined="turnaround", total_scanned=6123)
        self.assertIn("hs-chip", html)
        self.assertIn("IN RANGE", html)
        self.assertIn("Beds 50–400", html)
        self.assertIn("Sorted: Margin (most distressed first)", html)


class ResultsTests(unittest.TestCase):
    def _results(self):
        return [
            {"ccn": "010001", "name": "Mid Regional MC", "state": "TX",
             "beds": 220, "net_patient_revenue": 180e6,
             "operating_margin": -0.03, "rev_per_bed": 818181},
            {"ccn": "010002", "name": "Aggregate System", "state": "TX",
             "beds": 900, "net_patient_revenue": 7864.7e6,
             "operating_margin": 0.879, "rev_per_bed": 8738555},
        ]

    def test_npr_per_bed_column(self) -> None:
        html = render_screen_page(results=self._results(),
                                  filters={"sort": "revenue"}, total_scanned=6123)
        self.assertIn("NPR/Bed", html)
        self.assertIn("$818K", html)

    def test_implausible_margin_muted_plausible_not(self) -> None:
        html = render_screen_page(results=self._results(),
                                  filters={"sort": "revenue"}, total_scanned=6123)
        # the 87.9% junk-opex margin is muted + flagged
        self.assertIn("hs-dq", html)
        self.assertIn("87.9%", html)
        # the normal -3.0% margin is shown plainly (no dq flag on its cell)
        self.assertIn("-3.0%", html)


if __name__ == "__main__":
    unittest.main()
