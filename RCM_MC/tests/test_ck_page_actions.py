"""Pins for ck_page_actions — the shared page-action helper.

ck_page_actions wraps the existing Copy share link + Back-to-top
helpers into a single one-liner pages can opt into. The idempotent
JS install guards on each underlying helper mean dropping this
twice on one page never double-binds — pin that contract.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_page_actions


class CkPageActionsTests(unittest.TestCase):

    def test_default_renders_share_and_back_to_top(self):
        out = ck_page_actions()
        self.assertIn("Copy share link", out)
        self.assertIn("Back to top", out)

    def test_install_guards_present(self):
        # Each underlying helper carries an idempotent install guard
        # so dropping the wrapper on a page that already has either
        # helper installed never double-binds.
        out = ck_page_actions()
        self.assertIn("__rcmCopyShareLinkInstalled", out)
        self.assertIn("__rcmBackToTopInstalled", out)

    def test_extras_pass_through_into_actions_row(self):
        out = ck_page_actions(extras_html='<a class="foo">X</a>')
        self.assertIn('<a class="foo">X</a>', out)

    def test_share_can_be_disabled(self):
        out = ck_page_actions(share=False)
        self.assertNotIn("Copy share link", out)
        # Back-to-top still present.
        self.assertIn("Back to top", out)

    def test_back_to_top_can_be_disabled(self):
        out = ck_page_actions(back_to_top=False)
        self.assertNotIn("Back to top", out)
        # Share link still present.
        self.assertIn("Copy share link", out)

    def test_both_can_be_disabled(self):
        # Setting both False still emits the wrapper + CSS, but no
        # buttons or back-to-top floating element.
        out = ck_page_actions(share=False, back_to_top=False)
        self.assertNotIn("Copy share link", out)
        self.assertNotIn("Back to top", out)
        # Wrapper class still present.
        self.assertIn('class="ck-page-actions"', out)

    def test_actions_row_uses_flex_layout(self):
        out = ck_page_actions()
        # The row layout supports right-edge sub-blocks (e.g. wave-16
        # share button) — flex+wrap+gap matches the rhythm used
        # elsewhere on the page-control surfaces.
        self.assertIn(".ck-page-actions{display:flex", out)

    # ── 2026-05-28 Wave E — Print this view button ───────────────
    # Added Print button to the action row so partners can save the
    # current view as PDF or send to printer for IC memos. One edit
    # propagates to every page that already has ck_page_actions
    # (which is every page after waves A-D).

    def test_print_button_present_by_default(self):
        out = ck_page_actions()
        self.assertIn("Print this view", out)
        self.assertIn("data-rcm-print-view", out)

    def test_print_button_install_guard_present(self):
        out = ck_page_actions()
        self.assertIn("__rcmPrintViewInstalled", out)

    def test_print_button_can_be_disabled(self):
        out = ck_page_actions(print_btn=False)
        self.assertNotIn("Print this view", out)
        # Other buttons still present.
        self.assertIn("Copy share link", out)
        self.assertIn("Back to top", out)

    def test_print_button_hides_actions_row_in_print_media(self):
        # @media print rule hides the action row + back-to-top so
        # the printed page doesn't show the buttons themselves.
        out = ck_page_actions()
        self.assertIn(
            "@media print{.ck-page-actions,.ck-back-to-top",
            out,
        )

    # ── Wave F — keyboard shortcuts hint button ──────────────────
    # Pre-wave-F partners discovered the .ck-shortcuts overlay only
    # by accidentally pressing '?'. The new pill makes the affordance
    # visible alongside share + print, wired via the shell's existing
    # data-ck-shortcuts-open click hook.

    def test_shortcuts_button_present_by_default(self):
        out = ck_page_actions()
        self.assertIn("? Shortcuts", out)
        self.assertIn("data-ck-shortcuts-open", out)

    def test_shortcuts_button_can_be_disabled(self):
        out = ck_page_actions(shortcuts=False)
        self.assertNotIn("? Shortcuts", out)
        # Other buttons still present.
        self.assertIn("Copy share link", out)
        self.assertIn("Print this view", out)

    # ── Wave G — ⌘K Palette quick-jump button ──────────────────
    # Discoverability for the Cmd-K command palette which ships in
    # every chartis_shell render. Most partners never discovered it
    # because the affordance was only the keyboard shortcut.

    def test_palette_button_present_by_default(self):
        out = ck_page_actions()
        self.assertIn("⌘K Quick jump", out)
        self.assertIn("data-rcm-palette-open", out)

    def test_palette_button_install_guard_present(self):
        out = ck_page_actions()
        self.assertIn("__rcmPaletteOpenInstalled", out)

    def test_palette_button_can_be_disabled(self):
        out = ck_page_actions(palette=False)
        self.assertNotIn("⌘K Quick jump", out)
        self.assertIn("Copy share link", out)

    # ── Wave H — Metric glossary link ──────────────────────────
    # Pages reference dozens of metrics each but partners had no
    # consistent way to look them up. The pill points to the
    # canonical /metric-glossary where every metric has a
    # definition, rationale, formula, and source documents.

    def test_glossary_link_present_by_default(self):
        out = ck_page_actions()
        self.assertIn("📖 Glossary", out)
        self.assertIn('href="/metric-glossary"', out)

    def test_glossary_link_can_be_disabled(self):
        out = ck_page_actions(glossary=False)
        self.assertNotIn("📖 Glossary", out)
        self.assertIn("Copy share link", out)


if __name__ == "__main__":
    unittest.main()
