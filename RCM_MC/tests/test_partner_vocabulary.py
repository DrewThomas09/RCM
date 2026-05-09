"""tests for the partner-vocabulary canary migration.

PROMPTS.md Phase 3 / Prompt 45: internal terms ("fixture", "CCD",
"Phase N", "Train Fraction", "Simulation Paths") leak into user-
facing copy. Bear Case is the canary — its form labels and callouts
are migrated to partner vocabulary.

Subsequent pages (Thesis Pipeline, Deal MC, Counterfactual, etc.)
follow piecewise. The acceptance bar from the spec — zero "fixture"
in user-facing strings — applies platform-wide once the sweep is
complete; for now we pin the canary's exit state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.bear_case_page import _landing


class BearCasePartnerVocabulary(unittest.TestCase):

    def setUp(self) -> None:
        self.html = _landing()

    def test_form_label_says_claims_dataset_not_fixture(self) -> None:
        # Field label is the most-visible internal-vocab leak.
        self.assertIn("Claims dataset", self.html)
        self.assertNotIn("Dataset fixture", self.html)

    def test_simulation_label_uses_partner_vocab(self) -> None:
        self.assertIn("Number of simulations", self.html)
        self.assertNotIn("N simulation paths", self.html)


class BearCaseHelpCopyMigrated(unittest.TestCase):
    """Pin the helper-copy migration for the no-CCD callout. Callable
    only via ``_render_bear_case_no_ccd`` which requires the bear-case
    generator path; for the canary we exercise the literal source
    rather than running the renderer end-to-end."""

    def test_ccd_fixture_phrase_replaced(self) -> None:
        import inspect
        from rcm_mc.ui import bear_case_page

        src = inspect.getsource(bear_case_page)
        # The two specific user-facing lines that previously said
        # "CCD fixture" / "Supply a dataset fixture" must read in
        # partner vocabulary now.
        self.assertNotIn("CCD claims fixture", src)
        self.assertNotIn("Supply a dataset fixture", src)


if __name__ == "__main__":
    unittest.main()
