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
    """Bare HTML without the kit fails every rule. Pin that the
    scorer catches the floor case."""

    def test_empty_html_scores_zero(self) -> None:
        report = compliance_check("<html><body><p>nope</p></body></html>")
        self.assertEqual(report["pass"], 0)
        self.assertEqual(report["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
