"""Tests for the read-only PEdesk Guide prompt builder + answer cleaner."""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context import build_guide_context_packet
from rcm_mc.assistant.guide_prompt_builder import (
    build_guide_system_prompt,
    build_guide_user_prompt,
    clean_guide_answer,
    packet_to_prompt_context,
)


class PromptBuilderTests(unittest.TestCase):
    def setUp(self):
        self.packet = build_guide_context_packet("/diligence/hcris-xray")

    def test_user_prompt_includes_page_and_sources_and_limits(self):
        prompt = build_guide_user_prompt(
            "Where does this data come from?", self.packet
        )
        self.assertIn("HCRIS X-Ray", prompt)
        self.assertIn("cms_hcris", prompt)  # data-source context present
        self.assertIn("limitations", prompt.lower())
        self.assertIn("Where does this data come from?", prompt)

    def test_system_prompt_has_readonly_policy_and_rules(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        # explicit disallowed behaviors
        self.assertIn("final investment recommendations", sysp)
        self.assertIn("modify data", sysp)
        self.assertIn("do not invent formula", sysp)
        # read-only identity present
        self.assertIn("read-only", sysp)
        # no chain-of-thought
        self.assertIn("<think>", sysp)  # mentioned as forbidden

    def test_system_prompt_invites_analysis_but_keeps_guardrails(self):
        # The Guide should act like an analyst (interpret/connect into analysis
        # + suggest a next step), WITHOUT crossing into buy/sell calls or
        # losing the read-only / no-fabrication contract.
        sysp = build_guide_system_prompt(self.packet).lower()
        self.assertIn("analyze", sysp)
        self.assertIn("driver or risk", sysp)
        self.assertIn("next step", sysp)
        self.assertIn("diligence analyst", sysp)
        # guardrails intact
        self.assertIn("not a buy/sell/hold call", sysp)
        self.assertIn("final investment recommendations", sysp)
        self.assertIn("ground every claim in the provided context", sysp)

    def test_analyst_lens_does_not_trip_the_recommendation_guard(self):
        # The new style language itself must not read as an investment
        # recommendation to the eval gate.
        from rcm_mc.assistant.eval.guide_eval import has_investment_recommendation
        sysp = build_guide_system_prompt(self.packet)
        self.assertFalse(has_investment_recommendation(sysp)[0])

    def test_packet_to_prompt_context_respects_max_chars(self):
        small = packet_to_prompt_context(self.packet, max_chars=400)
        self.assertLessEqual(len(small), 400)
        # limitations / missing notes are never dropped entirely
        self.assertIn("Some context was omitted for length.", small)

    def test_clean_strips_think_blocks(self):
        self.assertEqual(
            clean_guide_answer("<think>secret reasoning</think>Real answer."),
            "Real answer.",
        )
        # dangling unterminated think tail also removed
        self.assertEqual(
            clean_guide_answer("Answer here.\n<think>leaked tail"),
            "Answer here.",
        )
        # multiline think block
        out = clean_guide_answer("<think>\nstep 1\nstep 2\n</think>\nFinal.")
        self.assertNotIn("step 1", out)
        self.assertEqual(out, "Final.")

    def test_clean_trims_repetitive_preamble_but_keeps_caveats(self):
        out = clean_guide_answer(
            "Based on the provided context, HCRIS data may lag operations."
        )
        self.assertNotIn("Based on the provided context", out)
        self.assertIn("HCRIS data may lag operations.", out)

    def test_system_prompt_has_answer_style_guidance(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        # A dedicated readability section with a direct-answer-first rule,
        # a length ceiling, the plain labels, and a no-filler instruction.
        self.assertIn("answer style", sysp)
        self.assertIn("1-2 sentence", sysp)
        self.assertIn("150 words", sysp)
        self.assertIn("filler", sysp)
        for label in ("what it means", "where it comes from",
                      "why it matters", "caveat"):
            self.assertIn(label, sysp)
        # Readability guidance must not weaken the read-only contract.
        self.assertIn("final investment recommendations", sysp)

    def test_system_prompt_has_retrieved_context_rule(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        self.assertIn("retrieved", sysp)
        self.assertIn("primary", sysp)
        self.assertIn("not this deal's data", sysp)

    def test_user_prompt_with_rag_context_keeps_packet_primary(self):
        rag_block = ("=== Additional local Guide context (retrieved) ===\n"
                     "[1] Metric Registry — Denial Rate [metric · denial_rate]: "
                     "Share of claims denied.")
        prompt = build_guide_user_prompt(
            "What does denial rate mean?", self.packet, rag_block)
        # page packet still present + retrieved block appended after it
        self.assertIn("HCRIS X-Ray", prompt)
        self.assertIn("Additional local Guide context", prompt)
        self.assertLess(prompt.index("HCRIS X-Ray"),
                        prompt.index("Additional local Guide context"))
        self.assertIn("page context is primary", prompt)

    def test_user_prompt_without_rag_is_unchanged(self):
        # Backward compatible: omitting rag_context reproduces the v1 prompt.
        a = build_guide_user_prompt("Q?", self.packet)
        b = build_guide_user_prompt("Q?", self.packet, "")
        self.assertEqual(a, b)
        self.assertNotIn("Additional local Guide context", a)

    def test_unknown_route_prompt_is_conservative(self):
        pkt = build_guide_context_packet("/unknown-route")
        prompt = build_guide_user_prompt("What does this page do?", pkt)
        self.assertIn("missing", prompt.lower())  # context_quality / notes
        # builder must not crash on a missing page_context
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
