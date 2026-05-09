"""tests for the voice + button-label audit (P92 + P93)."""
from __future__ import annotations

import unittest

from rcm_mc.ui.voice_audit import audit_button_label, audit_string


class StringAuditFlagsSaasSpeak(unittest.TestCase):

    def test_click_here_flagged(self) -> None:
        issues = audit_string("Click here to load")
        self.assertTrue(issues)
        self.assertEqual(issues[0]["rule"], "saas-phrase")

    def test_loading_ellipsis_flagged(self) -> None:
        issues = audit_string("Loading… please wait")
        self.assertTrue(issues)

    def test_internal_vocab_flagged(self) -> None:
        for s in (
            "Pick a fixture above",
            "Supply a CCD fixture",
            "Phase 3 modules",
            "Train Fraction (0-1)",
            "Simulation Paths",
            "13-step orchestrator",
        ):
            with self.subTest(s=s):
                issues = audit_string(s)
                self.assertTrue(issues, f"expected issue for {s!r}")

    def test_partner_voice_clean(self) -> None:
        # Strong copy from the actual codebase / PROMPTS examples.
        for s in (
            "Pick a deal to analyze.",
            "Alerts on your deals surface here.",
            "When does your thesis hit a covenant cliff?",
            "Diligence is complete enough.",
        ):
            with self.subTest(s=s):
                self.assertEqual(audit_string(s), [])


class ButtonLabelAuditVerbNoun(unittest.TestCase):

    def test_verb_noun_clean(self) -> None:
        for s in (
            "Run Monte Carlo",
            "Render memo",
            "Assemble IC packet",
            "Generate bear case",
            "Find comparables",
            "Audit bridge",
            "Open analysis workbench →",
        ):
            with self.subTest(s=s):
                self.assertEqual(audit_button_label(s), [])

    def test_one_word_verb_flagged(self) -> None:
        for s in ("RUN", "GENERATE", "Compute", "Submit"):
            with self.subTest(s=s):
                issues = audit_button_label(s)
                self.assertTrue(issues)
                self.assertEqual(issues[0]["rule"], "one-word-verb")

    def test_empty_label_flagged(self) -> None:
        self.assertTrue(audit_button_label(""))

    def test_decoration_only_flagged(self) -> None:
        # Just an emoji or arrow; no verb.
        self.assertTrue(audit_button_label("→"))

    def test_non_verb_prefix_flagged(self) -> None:
        # "Now displaying" — descriptive, not actionable.
        issues = audit_button_label("Now displaying results")
        self.assertTrue(issues)
        self.assertEqual(issues[0]["rule"], "non-verb-prefix")


if __name__ == "__main__":
    unittest.main()
