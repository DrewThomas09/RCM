"""PEdesk Guide metric + data-source registries — lookups + quality.

Read-only context layer only (no AI sidebar / Ollama / RAG / chat /
actions / DB memory). Pins the Task-2 acceptance criteria.
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.get_data_source_context import (
    get_data_source_context,
)
from rcm_mc.assistant.context.get_metric_context import get_metric_context
from rcm_mc.assistant.context.data_source_registry import DATA_SOURCE_REGISTRY
from rcm_mc.assistant.context.metric_registry import METRIC_REGISTRY
from rcm_mc.assistant.context.page_context_registry import PAGE_CONTEXT_REGISTRY
from rcm_mc.assistant.context.validate_guide_context_quality import build_report


class MetricLookupTests(unittest.TestCase):
    def test_denial_rate_by_label(self):
        r = get_metric_context("denial rate")
        self.assertTrue(r.found)
        self.assertEqual(r.metric_id, "denial_rate")

    def test_wrvu_case_insensitive_alias(self):
        r = get_metric_context("wRVU")
        self.assertTrue(r.found)
        self.assertEqual(r.metric_id, "wrvu")

    def test_unknown_metric_fallback(self):
        r = get_metric_context("not a metric")
        self.assertFalse(r.found)
        self.assertIsNone(r.context)
        self.assertIn("No PEdesk Guide metric", r.fallback_message)

    def test_registry_substantial(self):
        self.assertGreaterEqual(len(METRIC_REGISTRY), 50)


class DataSourceLookupTests(unittest.TestCase):
    def test_cms_hcris_by_label(self):
        r = get_data_source_context("CMS HCRIS")
        self.assertTrue(r.found)
        self.assertEqual(r.source_id, "cms_hcris")

    def test_837_alias(self):
        r = get_data_source_context("837")
        self.assertTrue(r.found)
        self.assertEqual(r.source_id, "edi_837")

    def test_unknown_source_fallback(self):
        r = get_data_source_context("unknown")
        self.assertFalse(r.found)
        self.assertIsNone(r.context)
        self.assertIn("No PEdesk Guide data-source", r.fallback_message)

    def test_registry_substantial(self):
        self.assertGreaterEqual(len(DATA_SOURCE_REGISTRY), 30)


class PageConnectionTests(unittest.TestCase):
    HIGH_PRIORITY = [
        "/diligence/hcris-xray", "/diligence/bridge-audit",
        "/diligence/payer-stress", "/diligence/denial-prediction",
        "/diligence/physician-eu", "/portfolio/monitor", "/data",
        "/methodology",
    ]

    def test_high_priority_pages_reference_only_valid_ids(self):
        for route in self.HIGH_PRIORITY:
            ctx = PAGE_CONTEXT_REGISTRY[route]
            for mid in ctx.metric_ids:
                self.assertIn(mid, METRIC_REGISTRY, f"{route} -> {mid}")
            for sid in ctx.data_source_ids:
                self.assertIn(sid, DATA_SOURCE_REGISTRY, f"{route} -> {sid}")

    def test_high_priority_pages_are_connected(self):
        for route in self.HIGH_PRIORITY:
            ctx = PAGE_CONTEXT_REGISTRY[route]
            self.assertTrue(
                ctx.metric_ids or ctx.data_source_ids,
                f"{route} has no metric/data-source links",
            )


class QualityValidatorTests(unittest.TestCase):
    def test_quality_validator_passes(self):
        r = build_report()
        self.assertEqual(r.invalid_metric_refs, [])
        self.assertEqual(r.invalid_source_refs, [])
        self.assertEqual(r.duplicate_metric_ids, [])
        self.assertEqual(r.duplicate_source_ids, [])
        self.assertEqual(r.broken_aliases, [])
        self.assertEqual(r.hard_failures, [])


if __name__ == "__main__":
    unittest.main()
