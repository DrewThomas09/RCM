"""tests for ``rcm_mc.ui._ui_kit.recommendation_block``.

PROMPTS.md Phase 2 / Prompt 16. Tests cover each confidence level,
optional dollars, varying reasoning lengths, and HTML escape on
caller-supplied text.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import recommendation_block


def _block(**overrides) -> str:
    args = dict(
        verdict="Proceed at reduced price",
        action="Anchor IC at $54M, not $67M.",
        confidence="medium",
        reasoning=["Variance in payer mix", "Steward-pattern flag"],
    )
    args.update(overrides)
    return recommendation_block(**args)


class ConfidenceLevels(unittest.TestCase):

    def test_high_low_medium_apply_class(self) -> None:
        for level in ("high", "medium", "low", "info"):
            with self.subTest(level=level):
                html = _block(confidence=level)
                self.assertIn(f"confidence-{level}", html)

    def test_invalid_confidence_falls_back_to_info(self) -> None:
        html = _block(confidence="purple")
        self.assertIn("confidence-info", html)
        self.assertNotIn("confidence-purple", html)


class DollarsOptional(unittest.TestCase):

    def test_dollars_renders_when_present(self) -> None:
        html = _block(dollars="$13M EBITDA at risk")
        self.assertIn('class="rec-dollars"', html)
        self.assertIn("$13M EBITDA at risk", html)

    def test_dollars_omitted_when_absent(self) -> None:
        html = _block()
        self.assertNotIn("rec-dollars", html)


class ReasoningLengths(unittest.TestCase):

    def test_one_bullet(self) -> None:
        html = _block(reasoning=["only one"])
        self.assertEqual(html.count("<li>"), 1)

    def test_three_bullets(self) -> None:
        html = _block(reasoning=["a", "b", "c"])
        self.assertEqual(html.count("<li>"), 3)

    def test_five_bullets(self) -> None:
        html = _block(reasoning=["a", "b", "c", "d", "e"])
        self.assertEqual(html.count("<li>"), 5)


class HtmlEscaping(unittest.TestCase):

    def test_verdict_escaped(self) -> None:
        html = _block(verdict="<script>x</script>")
        self.assertIn("&lt;script&gt;", html)

    def test_reasoning_escaped(self) -> None:
        html = _block(reasoning=["<b>bold</b>"])
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", html)


class KeywordOnlyAPI(unittest.TestCase):

    def test_positional_call_rejected(self) -> None:
        with self.assertRaises(TypeError):
            recommendation_block("v", "a", "high", [])  # type: ignore


if __name__ == "__main__":
    unittest.main()
