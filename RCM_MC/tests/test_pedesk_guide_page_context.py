"""PEdesk Guide page-context foundation — coverage + lookup behavior.

Pins the acceptance criteria: every discovered route has a valid
context, query/hash/slash normalize, palette aliases resolve, dynamic
per-deal/analysis/portal routes return generic contexts, and unknown
routes return a clean fallback. (Read-only context layer — no AI
sidebar / Ollama / RAG / chat / actions are involved.)
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.discovered_tool_routes import (
    DISCOVERED_TOOL_ROUTES,
)
from rcm_mc.assistant.context.get_page_context import (
    get_page_context,
    normalize_route,
)
from rcm_mc.assistant.context.page_context_registry import (
    PAGE_CONTEXT_REGISTRY,
)
from rcm_mc.assistant.context.validate_page_context_coverage import (
    build_report,
)


class CoverageTests(unittest.TestCase):
    def test_validator_passes_cleanly(self):
        r = build_report()
        self.assertEqual(r.missing, [], "discovered routes missing context")
        self.assertEqual(r.duplicate_routes, [])
        self.assertEqual(r.invalid_categories, [])
        self.assertEqual(r.invalid_source_confidence, [])
        self.assertEqual(r.invalid_data_confidence, [])
        self.assertEqual(r.missing_titles, [])
        self.assertEqual(r.missing_normalized, [])
        self.assertEqual(r.hard_failures, [])

    def test_every_discovered_route_in_registry(self):
        for d in DISCOVERED_TOOL_ROUTES:
            self.assertIn(d.route, PAGE_CONTEXT_REGISTRY, d.route)

    def test_discovered_is_substantial(self):
        # PEdesk has many tools; guard against an empty manifest.
        self.assertGreaterEqual(len(DISCOVERED_TOOL_ROUTES), 60)


class NormalizationTests(unittest.TestCase):
    def test_query_string_stripped(self):
        self.assertEqual(
            normalize_route("/diligence/risk-workbench?demo=steward"),
            "/diligence/risk-workbench",
        )

    def test_hash_and_trailing_slash(self):
        self.assertEqual(normalize_route("/alerts#x"), "/alerts")
        self.assertEqual(normalize_route("/app/"), "/app")


class LookupTests(unittest.TestCase):
    def test_query_route_resolves_to_base(self):
        r = get_page_context("/diligence/risk-workbench?demo=steward")
        self.assertTrue(r.found)
        self.assertEqual(r.normalized_route, "/diligence/risk-workbench")
        self.assertEqual(r.context.title, "Risk Workbench")

    def test_dynamic_deal_routes(self):
        cases = {
            "/deal/390049": "Deal Dashboard",
            "/deal/390049/partner-review": "Partner Review",
            "/deal/390049/ic-packet": "Deal IC Packet",
            "/deal/390049/red-flags": "Deal Red Flags",
            "/analysis/390049": "Analysis Workbench",
            "/portal/eng-77": "Engagement Portal",
        }
        for route, title in cases.items():
            r = get_page_context(route)
            self.assertTrue(r.found, route)
            self.assertEqual(r.context.title, title, route)

    def test_unknown_route_clean_fallback(self):
        r = get_page_context("/totally-unknown-xyz")
        self.assertFalse(r.found)
        self.assertIsNone(r.context)
        self.assertIn("No PEdesk Guide context", r.fallback_message)

    def test_lookup_result_shape_on_match(self):
        r = get_page_context("/app")
        self.assertTrue(r.found)
        self.assertIsNone(r.fallback_message)
        self.assertEqual(r.context.category.value, "home_operations")


if __name__ == "__main__":
    unittest.main()
