"""tests for the bear-case recommendation_block + caveats wiring.

PROMPTS.md Phase 3 / Prompts 34 + 35: every analytical page should
end with a modeling-caveats disclosure and a partner-grade
recommendation block. Bear Case is the canary.

These tests exercise the verdict logic directly via the helper —
calling the full page renderer would require the bear-case generator
to run, which is heavy and orthogonal to what we're pinning here.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.bear_case.generator import BearCaseReport
from rcm_mc.ui.bear_case_page import (
    _BEAR_CASE_CAVEATS,
    _recommendation_for_report,
)


def _report(*, crit: int = 0, at_risk_usd: float = 0.0,
            n_evidence: int = 0) -> BearCaseReport:
    """Build a minimal BearCaseReport for verdict-branch testing.

    The dataclass has many fields; only the four we read inside the
    verdict logic actually matter for the assertion path.
    """
    # ``Evidence`` shape varies; we only need a list of the right
    # length so ``len(report.evidence)`` returns the test value. A
    # list of ``None`` would crash other consumers but is fine here.
    return BearCaseReport(
        target_name="Project Test",
        evidence=[None] * n_evidence,  # type: ignore[arg-type]
        critical_count=crit,
        combined_ebitda_at_risk_usd=at_risk_usd,
    )


class VerdictBranches(unittest.TestCase):

    def test_three_or_more_critical_pauses(self) -> None:
        html = _recommendation_for_report(_report(crit=3, at_risk_usd=10e6))
        self.assertIn("Pause for partner review", html)
        self.assertIn("confidence-low", html)

    def test_one_or_two_critical_negotiates(self) -> None:
        html = _recommendation_for_report(_report(crit=1, at_risk_usd=4.5e6))
        self.assertIn("Negotiate at reduced price", html)
        self.assertIn("confidence-medium", html)

    def test_zero_critical_proceeds(self) -> None:
        html = _recommendation_for_report(_report(crit=0))
        self.assertIn("Proceed with focused follow-up", html)
        self.assertIn("confidence-high", html)


class DollarAnchoring(unittest.TestCase):

    def test_dollars_in_output_when_at_risk_set(self) -> None:
        html = _recommendation_for_report(_report(crit=1, at_risk_usd=13e6))
        self.assertIn("rec-dollars", html)
        self.assertIn("$13.0M", html)

    def test_no_dollars_when_zero_at_risk(self) -> None:
        html = _recommendation_for_report(_report(crit=0, at_risk_usd=0))
        self.assertNotIn("rec-dollars", html)


class CaveatsListed(unittest.TestCase):

    def test_caveats_count_matches_spec(self) -> None:
        # Four documented caveats per the bear_case_page module.
        self.assertEqual(len(_BEAR_CASE_CAVEATS), 4)

    def test_caveats_mention_known_weaknesses(self) -> None:
        joined = " ".join(_BEAR_CASE_CAVEATS).lower()
        for needle in (
            "cross-theme correlation",
            "regulatory-calendar timing",
            "ccd",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, joined)


if __name__ == "__main__":
    unittest.main()
