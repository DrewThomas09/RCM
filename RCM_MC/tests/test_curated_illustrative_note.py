"""Curated tracker pages carry an honest 'illustrative template' marker.

Many data_public tracker pages render realistic-looking numbers built
from hardcoded dataclass lists (the analytic surface ahead of the
data wiring; see docs/PEDESK_UNDERSTANDING/08). ck_illustrative_note()
states that plainly so a partner/LP never mistakes a template for the
portfolio's live, sourced data. This pins the marker on the curated
pages that also lead with a prominent value-anchor (highest-priority
honesty surface) and that it renders ahead of the page's bottom thesis.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_illustrative_note


class IllustrativeNoteHelperTests(unittest.TestCase):
    def test_helper_states_not_live_data(self):
        html = ck_illustrative_note("savings figures")
        self.assertIn("ck-illus-note", html)
        self.assertIn("Illustrative template", html)
        self.assertIn("not this portfolio's live", html)
        self.assertIn("savings figures", html)


class CuratedPagesCarryNoteTests(unittest.TestCase):
    def _pages(self):
        from rcm_mc.ui.data_public.supply_chain_page import render_supply_chain
        from rcm_mc.ui.data_public.drug_pricing_340b_page import (
            render_drug_pricing_340b,
        )
        from rcm_mc.ui.data_public.locum_tracker_page import render_locum_tracker
        from rcm_mc.ui.data_public.insurance_tracker_page import render_insurance
        from rcm_mc.ui.data_public.capital_pacing_page import render_capital_pacing
        from rcm_mc.ui.data_public.quality_scorecard_page import (
            render_quality_scorecard,
        )
        return [
            ("supply_chain", render_supply_chain, "Supply Chain Thesis"),
            ("drug_pricing_340b", render_drug_pricing_340b, "340B Thesis"),
            ("locum_tracker", render_locum_tracker, "Workforce Thesis"),
            ("insurance_tracker", render_insurance, "Insurance Thesis"),
            ("capital_pacing", render_capital_pacing, "Pacing Thesis"),
            ("quality_scorecard", render_quality_scorecard, "Quality Thesis"),
        ]

    def test_each_carries_note_ahead_of_thesis(self):
        for name, fn, bottom in self._pages():
            html = fn({})
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)
            self.assertLess(
                html.index("ck-illus-note"), html.index(bottom), name,
            )


if __name__ == "__main__":
    unittest.main()
