"""PEdesk Guide context-packet layer — read-only assembly + grading.

Exercises build_guide_context_packet across exact, query-string,
dynamic, and unknown routes; the human-readable summary; and the
read-only policy contract. No AI, RAG, chat, or autonomous behavior is
involved — this is structured-context infrastructure only.
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.guide_context_packet import (
    build_guide_context_packet,
    summarize_context_packet,
)
from rcm_mc.assistant.context.guide_prompt_policy import (
    DEFAULT_UNCERTAINTY_MESSAGE,
    GUIDE_PROMPT_POLICY,
)


class ExactRouteTests(unittest.TestCase):
    def test_hcris_xray_packet(self):
        p = build_guide_context_packet("/diligence/hcris-xray")
        self.assertTrue(p.found_page_context)
        self.assertNotEqual(p.context_quality, "missing")
        self.assertTrue(p.suggested_questions)
        self.assertIn("identity", p.read_only_policy)
        self.assertIn("disallowed_behavior", p.read_only_policy)
        # hcris-xray is linked in Task 2 → at least one metric or source.
        self.assertTrue(
            p.metric_contexts or p.data_source_contexts,
            "expected linked metric/data-source contexts for hcris-xray",
        )

    def test_hcris_xray_is_strong(self):
        p = build_guide_context_packet("/diligence/hcris-xray")
        self.assertEqual(p.context_quality, "strong")


class QueryStringRouteTests(unittest.TestCase):
    def test_query_string_normalizes(self):
        p = build_guide_context_packet(
            "/diligence/risk-workbench?demo=steward"
        )
        self.assertEqual(p.normalized_route, "/diligence/risk-workbench")
        self.assertTrue(p.found_page_context)


class DynamicRouteTests(unittest.TestCase):
    def test_deal_route_generic_dashboard(self):
        p = build_guide_context_packet("/deal/390049")
        self.assertTrue(p.found_page_context)
        self.assertEqual(p.normalized_route, "/deal/390049")
        self.assertIsNotNone(p.page_context)
        self.assertEqual(p.page_context.title, "Deal Dashboard")

    def test_analysis_route_generic_workbench(self):
        p = build_guide_context_packet("/analysis/390049")
        self.assertTrue(p.found_page_context)
        self.assertEqual(p.normalized_route, "/analysis/390049")
        self.assertIsNotNone(p.page_context)
        self.assertEqual(p.page_context.title, "Analysis Workbench")


class UnknownRouteTests(unittest.TestCase):
    def test_unknown_route_missing(self):
        p = build_guide_context_packet("/unknown-route")
        self.assertFalse(p.found_page_context)
        self.assertEqual(p.context_quality, "missing")
        self.assertTrue(p.fallback_message)
        self.assertNotIn("Traceback", p.fallback_message)
        # Policy + default questions still present on a miss.
        self.assertIn("identity", p.read_only_policy)
        self.assertTrue(p.suggested_questions)


class SummaryTests(unittest.TestCase):
    def test_summary_non_empty(self):
        p = build_guide_context_packet("/diligence/hcris-xray")
        s = summarize_context_packet(p)
        self.assertIsInstance(s, str)
        self.assertTrue(s.strip())
        self.assertIn("PEdesk Guide context packet", s)

    def test_summary_handles_missing(self):
        p = build_guide_context_packet("/unknown-route")
        s = summarize_context_packet(p)
        self.assertTrue(s.strip())


class PolicyTests(unittest.TestCase):
    def test_disallowed_behavior_present(self):
        p = build_guide_context_packet("/diligence/hcris-xray")
        disallowed = p.read_only_policy["disallowed_behavior"]
        for forbidden in (
            "modify data",
            "run models",
            "make final investment recommendations",
        ):
            self.assertIn(forbidden, disallowed)

    def test_policy_identity_and_uncertainty(self):
        self.assertIn("read-only", GUIDE_PROMPT_POLICY.identity)
        self.assertIn("source documentation", DEFAULT_UNCERTAINTY_MESSAGE)


if __name__ == "__main__":
    unittest.main()
