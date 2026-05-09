"""tests for the four-engine flagship cards.

PROMPTS.md Phase 4 / Prompt 57: each of Monte Carlo / PE-math /
Health & completeness / AI memos gets a flagship card the marketing
page (and per-deal landing) can drop in.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import _FLAGSHIP_ENGINES, engine_flagship_card


class RegistryShape(unittest.TestCase):

    def test_four_engines_defined(self) -> None:
        self.assertEqual(len(_FLAGSHIP_ENGINES), 4)

    def test_keys_are_canonical(self) -> None:
        keys = [e["key"] for e in _FLAGSHIP_ENGINES]
        self.assertEqual(
            keys,
            ["monte_carlo", "pe_math", "health", "memos"],
        )

    def test_each_engine_has_question_headline(self) -> None:
        for e in _FLAGSHIP_ENGINES:
            with self.subTest(key=e["key"]):
                self.assertTrue(e["headline"].endswith("?"))


class CardRendering(unittest.TestCase):

    def test_renders_label_and_headline(self) -> None:
        html = engine_flagship_card("monte_carlo")
        self.assertIn("Monte Carlo", html)
        # Apostrophe is HTML-escaped; match either form.
        self.assertTrue(
            "What's the distribution" in html
            or "What&#x27;s the distribution" in html
        )

    def test_card_uses_engine_flagship_class(self) -> None:
        html = engine_flagship_card("pe_math")
        self.assertIn('class="engine-flagship"', html)

    def test_unknown_key_returns_empty(self) -> None:
        self.assertEqual(engine_flagship_card("nonsense"), "")


class HrefBehaviour(unittest.TestCase):

    def test_with_deal_id_targets_workbench_tab(self) -> None:
        html = engine_flagship_card("monte_carlo", deal_id="aurora")
        self.assertIn(
            'href="/analysis/aurora?tab=monte-carlo"',
            html,
        )

    def test_memos_falls_back_to_qoe_preview(self) -> None:
        # Memos has no workbench tab; falls back to the QoE preview.
        html = engine_flagship_card("memos")
        self.assertIn("/diligence/qoe-memo", html)

    def test_no_deal_no_memos_falls_back_to_methodology(self) -> None:
        html = engine_flagship_card("monte_carlo")
        self.assertIn("/methodology", html)


if __name__ == "__main__":
    unittest.main()
