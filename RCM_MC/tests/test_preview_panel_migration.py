"""tests for the preview_panel canary migration.

PROMPTS.md Phase 3 / Prompt 29: form-only diligence pages waste 70%
of the screen. The Bear Case landing is the canary — adds a right-
rail preview_panel beside the form. Subsequent pages (Ingestion,
Benchmarks, Bridge Audit, Deal MC, etc.) follow in piecewise sweeps.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.bear_case_page import _landing


class BearCaseHasPreview(unittest.TestCase):

    def setUp(self) -> None:
        self.html = _landing()

    def test_preview_panel_renders(self) -> None:
        self.assertIn('class="preview-panel"', self.html)
        self.assertIn('data-preview="true"', self.html)

    def test_preview_caption_explains_output(self) -> None:
        # The caption must hint at what the partner gets — pin a
        # token from our copy.
        self.assertIn("Ranked evidence", self.html)

    def test_form_and_preview_in_same_grid(self) -> None:
        # Two-column grid is the layout shape the spec calls for —
        # form left (3fr), preview right (2fr).
        self.assertIn("grid-template-columns:3fr 2fr", self.html)


class BearCaseHasRecentRuns(unittest.TestCase):
    """P30 canary: form-only pages get a recent-runs continuity rail."""

    def setUp(self) -> None:
        self.html = _landing()

    def test_recent_runs_section_present(self) -> None:
        self.assertIn('class="recent-runs"', self.html)

    def test_empty_state_copy_when_no_history(self) -> None:
        # Bear case runs aren't yet routed through a per-module table.
        # The rail must render the empty-state copy until they are.
        self.assertIn("No bear cases yet", self.html)


class BearCaseFormSectionMigrated(unittest.TestCase):
    """Post-Phase-7 follow-up: P43's form_section actually lands on
    Bear Case rather than the previous flat 13-input grid."""

    def setUp(self) -> None:
        self.html = _landing()

    def test_four_form_sections_present(self) -> None:
        # Identity / Capital / Real estate / Run parameters.
        self.assertEqual(self.html.count("form-section-label"), 4)

    def test_each_section_label_renders(self) -> None:
        for label in (
            "Identity", "Capital", "Real estate", "Run parameters",
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.html)


class BearCaseSubmitMigratedToActionButton(unittest.TestCase):
    """P31 canary: form-submit migrated to action_button. The button
    must render with the kit's btn-primary class and carry the
    expected-duration data attribute that powers the busy state."""

    def setUp(self) -> None:
        self.html = _landing()

    def test_submit_uses_btn_primary_class(self) -> None:
        # Pull the rendered submit button and confirm class.
        self.assertIn(
            'class="btn-primary" type="submit"',
            self.html,
        )

    def test_submit_carries_duration_attribute(self) -> None:
        self.assertIn('data-expected-seconds="2"', self.html)

    def test_no_legacy_bc_form_submit_button(self) -> None:
        # The bespoke bc-form-submit class should no longer be on the
        # actual submit button — the CSS rule lingers as a no-op.
        # We inspect for the literal opening of a button that uses
        # the legacy class.
        self.assertNotIn(
            '<button class="bc-form-submit"',
            self.html,
        )


if __name__ == "__main__":
    unittest.main()
