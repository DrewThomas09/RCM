"""tests for ``model_verdict`` + ``model_verdict_header`` (P68)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import model_verdict, model_verdict_header


def _panels(severities: list[str]) -> list[dict]:
    return [{"severity": s} for s in severities]


class VerdictBranches(unittest.TestCase):

    def test_critical_triggers_partner_review(self) -> None:
        v = model_verdict(_panels(["CRITICAL", "GREEN", "GREEN"]))
        self.assertEqual(v["verdict"], "NEEDS PARTNER REVIEW")
        self.assertEqual(v["tone"], "critical")

    def test_red_without_critical_triggers_structural(self) -> None:
        v = model_verdict(_panels(["RED", "YELLOW", "GREEN"]))
        self.assertIn("STRUCTURAL CONCERN", v["verdict"])
        self.assertEqual(v["tone"], "negative")

    def test_yellow_only_diligence_acceptable(self) -> None:
        v = model_verdict(_panels(["YELLOW", "GREEN", "GREEN"]))
        self.assertEqual(v["verdict"], "DILIGENCE ACCEPTABLE")
        self.assertEqual(v["tone"], "warning")

    def test_all_green_diligence_clean(self) -> None:
        v = model_verdict(_panels(["GREEN", "GREEN", "GREEN"]))
        self.assertEqual(v["verdict"], "DILIGENCE CLEAN")
        self.assertEqual(v["tone"], "positive")


class CountSummary(unittest.TestCase):

    def test_summary_lists_each_severity(self) -> None:
        v = model_verdict(_panels(
            ["CRITICAL", "YELLOW", "YELLOW", "GREEN", "GREEN", "GREEN"]
        ))
        self.assertIn("1 CRITICAL panel", v["summary"])
        self.assertIn("2 YELLOW panels", v["summary"])
        self.assertIn("3 GREEN panels", v["summary"])

    def test_counts_dict_present(self) -> None:
        v = model_verdict(_panels(
            ["CRITICAL", "GREEN", "GREEN", "GREEN"]
        ))
        self.assertEqual(v["counts"]["CRITICAL"], 1)
        self.assertEqual(v["counts"]["GREEN"], 3)


class GracefulInput(unittest.TestCase):

    def test_empty_panels(self) -> None:
        v = model_verdict([])
        self.assertEqual(v["verdict"], "AWAITING DILIGENCE")
        self.assertEqual(v["tone"], "neutral")

    def test_unknown_severity_falls_through(self) -> None:
        # Unknown severity strings count as nothing — verdict awaits.
        v = model_verdict([{"severity": "purple"}])
        self.assertEqual(v["verdict"], "AWAITING DILIGENCE")

    def test_case_insensitive(self) -> None:
        v = model_verdict([{"severity": "critical"}])
        self.assertEqual(v["verdict"], "NEEDS PARTNER REVIEW")


class HeaderRendering(unittest.TestCase):

    def test_emits_banner(self) -> None:
        html = model_verdict_header(_panels(["CRITICAL", "GREEN"]))
        self.assertIn("model-verdict", html)
        self.assertIn("tone-critical", html)
        self.assertIn("NEEDS PARTNER REVIEW", html)


if __name__ == "__main__":
    unittest.main()
