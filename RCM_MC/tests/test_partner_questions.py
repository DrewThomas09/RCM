"""tests for the partner-question subtitle registry.

PROMPTS.md Phase 3 / Prompt 44: canonical question subtitles for
analytical pages. The registry pins the wording so a future rename
sweep can re-derive subtitles centrally rather than per page.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import _PAGE_QUESTIONS, partner_question


class RegistryShape(unittest.TestCase):

    def test_every_value_is_a_question(self) -> None:
        for route, q in _PAGE_QUESTIONS.items():
            with self.subTest(route=route):
                self.assertTrue(q.endswith("?"),
                                f"{route!r} subtitle should end with ?")

    def test_every_route_starts_with_slash(self) -> None:
        for route in _PAGE_QUESTIONS:
            with self.subTest(route=route):
                self.assertTrue(route.startswith("/"))


class CanonicalQuestionsPresent(unittest.TestCase):

    def test_bear_case_question(self) -> None:
        self.assertEqual(
            partner_question("/diligence/bear-case"),
            "What could break this thesis?",
        )

    def test_deal_mc_question(self) -> None:
        self.assertEqual(
            partner_question("/diligence/deal-mc"),
            "What's the distribution of outcomes?",
        )

    def test_exit_timing_question(self) -> None:
        self.assertEqual(
            partner_question("/diligence/exit-timing"),
            "When and to whom should we exit?",
        )

    def test_counterfactual_question(self) -> None:
        self.assertEqual(
            partner_question("/diligence/counterfactual"),
            "What would change our mind?",
        )

    def test_bankruptcy_question(self) -> None:
        self.assertEqual(
            partner_question("/screening/bankruptcy-survivor"),
            "Does this match a known failure pattern?",
        )


class UnregisteredRouteReturnsNone(unittest.TestCase):

    def test_unknown_route_returns_none(self) -> None:
        self.assertIsNone(partner_question("/some/other/route"))


if __name__ == "__main__":
    unittest.main()
