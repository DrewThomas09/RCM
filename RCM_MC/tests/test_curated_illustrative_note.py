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


class CuratedPagesBatch2CarryNoteTests(unittest.TestCase):
    """Batch 2 — the remaining confirmed-curated pages that also lead
    with a value-anchor. (Excludes scenario_mc [live], tax_structure
    [calculator], rollup_economics [corpus per deep-trace] — those are
    NOT illustrative and must not carry the marker.)"""

    def _renderers(self):
        from rcm_mc.ui.data_public.tech_stack_page import render_tech_stack
        from rcm_mc.ui.data_public.workforce_planning_page import (
            render_workforce_planning,
        )
        from rcm_mc.ui.data_public.value_creation_plan_page import (
            render_value_creation_plan,
        )
        from rcm_mc.ui.data_public.unit_economics_page import (
            render_unit_economics,
        )
        from rcm_mc.ui.data_public.working_capital_page import (
            render_working_capital,
        )
        from rcm_mc.ui.data_public.deal_origination_page import (
            render_deal_origination,
        )
        from rcm_mc.ui.data_public.deal_pipeline_page import (
            render_deal_pipeline,
        )
        from rcm_mc.ui.data_public.competitive_intel_page import (
            render_competitive_intel,
        )
        from rcm_mc.ui.data_public.patient_experience_page import (
            render_patient_experience,
        )
        from rcm_mc.ui.data_public.regulatory_risk_page import (
            render_regulatory_risk,
        )
        from rcm_mc.ui.data_public.clinical_outcomes_page import (
            render_clinical_outcomes,
        )
        return [
            render_tech_stack, render_workforce_planning,
            render_value_creation_plan, render_unit_economics,
            render_working_capital, render_deal_origination,
            render_deal_pipeline, render_competitive_intel,
            render_patient_experience, render_regulatory_risk,
            render_clinical_outcomes,
        ]

    def test_each_carries_marker(self):
        for fn in self._renderers():
            html = fn({})
            self.assertIn("ck-illus-note", html, fn.__name__)
            self.assertIn("Illustrative template", html, fn.__name__)

    def test_calculator_pages_label_illustrative_defaults_honestly(self):
        # scenario_mc + tax_structure_analyzer are calculators that compute off
        # the user's inputs but render with ILLUSTRATIVE DEFAULT figures until
        # those inputs are supplied. The honest label is exactly that — an
        # "illustrative defaults; computes off your inputs" note — NOT a blanket
        # "illustrative" mislabel and NOT presenting the defaults as live.
        # (Updated from the original "must not carry any marker" expectation,
        # which predated these pages adopting the honest illustrative-defaults
        # note.)
        from rcm_mc.ui.data_public.scenario_mc_page import render_scenario_mc
        from rcm_mc.ui.data_public.tax_structure_analyzer_page import (
            render_tax_structure_analyzer,
        )
        for html in (render_scenario_mc({}), render_tax_structure_analyzer({})):
            self.assertIn("ck-illus-note", html)
            # the note must clarify the figures are defaults computed off inputs,
            # not a static illustrative dashboard
            self.assertIn("illustrative defaults", html)
            self.assertIn("your inputs", html)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
