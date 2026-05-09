"""tests for the final consistency sweep (P100).

Runs the compliance scorer against a representative ``chartis_shell``
render and asserts every shipped Phase 1-7 contract is in place.
"""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui.compliance_sweep import RULES, compliance_check


class RuleRegistry(unittest.TestCase):

    def test_rule_count_reasonable(self) -> None:
        self.assertGreaterEqual(len(RULES), 10)

    def test_each_rule_has_label(self) -> None:
        for key, label, predicate in RULES:
            with self.subTest(key=key):
                self.assertTrue(label)
                self.assertTrue(callable(predicate))


class ComplianceScoreOnShell(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")
        cls.report = compliance_check(cls.html)

    def test_full_compliance_on_default_shell(self) -> None:
        # The default shell ships every Phase-1-7 piece — score = 100%.
        self.assertEqual(
            self.report["pass"], self.report["total"],
            f"Failing rules: "
            f"{[r['key'] for r in self.report['results'] if not r['passed']]}",
        )

    def test_score_is_one_for_default_shell(self) -> None:
        self.assertEqual(self.report["score"], 1.0)


class ComplianceScoreOnEmptyHTML(unittest.TestCase):
    """Bare HTML without the kit fails every kit-presence rule. Pin
    that the scorer catches the floor case. Number-format-clean is
    the one exception — bare HTML has no numbers to mis-format, so
    the rule legitimately passes (1/N), not fails."""

    def test_empty_html_fails_kit_presence_rules(self) -> None:
        report = compliance_check("<html><body><p>nope</p></body></html>")
        # Every kit-presence rule fails on bare HTML. The audit-style
        # rules (number-format-clean, voice-clean, primary-buttons-
        # verb-noun) all pass *vacuously* — bare HTML has no numbers,
        # no SaaS-speak, no primary buttons to flag.
        passed_keys = {r["key"] for r in report["results"] if r["passed"]}
        self.assertEqual(
            passed_keys,
            {"number-format-clean", "voice-clean", "primary-buttons-verb-noun"},
            f"unexpected passes on bare HTML: {passed_keys}",
        )
        # Score is N/total where N is the count of vacuous-pass rules.
        # The floor: well below 0.5 — the kit-presence rules dominate.
        self.assertLess(report["score"], 0.3)


if __name__ == "__main__":
    unittest.main()
