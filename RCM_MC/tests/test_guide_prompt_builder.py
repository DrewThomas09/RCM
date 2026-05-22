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

    def test_unknown_route_prompt_is_conservative(self):
        pkt = build_guide_context_packet("/unknown-route")
        prompt = build_guide_user_prompt("What does this page do?", pkt)
        self.assertIn("missing", prompt.lower())  # context_quality / notes
        # builder must not crash on a missing page_context
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
