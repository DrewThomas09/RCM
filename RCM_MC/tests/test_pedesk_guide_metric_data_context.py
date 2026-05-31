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

    def test_new_glossary_metrics_in_registry(self):
        """PR #1276 added first_pass_resolution_rate and payer_diversity
        as full _m() entries in METRIC_REGISTRY — these are real RCM
        metrics from /metric-glossary that didn't have clean alias
        targets in the existing registry. Verify both are now
        resolvable by id and via their canonical alias spellings."""
        for q in ("first_pass_resolution_rate", "fpr",
                  "first-pass resolution"):
            r = get_metric_context(q)
            self.assertTrue(r.found, f"{q!r} should resolve")
            self.assertEqual(r.metric_id, "first_pass_resolution_rate")
        for q in ("payer_diversity", "payer diversity",
                  "inverse hhi payer"):
            r = get_metric_context(q)
            self.assertTrue(r.found, f"{q!r} should resolve")
            self.assertEqual(r.metric_id, "payer_diversity")

    def test_six_remaining_glossary_metrics_in_registry(self):
        """PR #1284 added the final 6 hospital/financial glossary
        metrics as full _m() entries: debt_to_revenue, fte_per_aob,
        revenue_per_bed, expense_per_bed, total_patient_days,
        net_to_gross_ratio. Verify each resolves by id and by its
        canonical label spelling."""
        for mid in (
            "debt_to_revenue", "fte_per_aob", "revenue_per_bed",
            "expense_per_bed", "total_patient_days",
            "net_to_gross_ratio",
        ):
            r = get_metric_context(mid)
            self.assertTrue(r.found, f"{mid!r} should resolve")
            self.assertEqual(r.metric_id, mid)
        label_cases = [
            ("Debt to Revenue", "debt_to_revenue"),
            ("FTE per AOB", "fte_per_aob"),
            ("Revenue per Bed", "revenue_per_bed"),
            ("Expense per Bed", "expense_per_bed"),
            ("Total Patient Days", "total_patient_days"),
            ("Net-to-Gross Ratio", "net_to_gross_ratio"),
        ]
        for label, expected in label_cases:
            r = get_metric_context(label)
            self.assertTrue(r.found, f"{label!r} should resolve")
            self.assertEqual(r.metric_id, expected)

    def test_glossary_aliases_resolve(self):
        """The /metric-glossary page (rcm_mc/ui/metric_glossary.py) has
        13 entries not in METRIC_REGISTRY. PR #1275 adds aliases for
        the 4 that map cleanly to existing registry concepts so the
        Guide recognizes them when a partner uses the glossary spelling.
        Verify each glossary alias resolves to the expected metric."""
        cases = [
            ("labor pct of npsr", "labor_cost_ratio"),
            ("labor_pct_of_npsr", "labor_cost_ratio"),
            ("medicare day pct", "medicare_exposure"),
            ("medicare_day_pct", "medicare_exposure"),
            ("medicaid day pct", "medicaid_exposure"),
            ("medicaid_day_pct", "medicaid_exposure"),
            ("commercial pct", "commercial_payer_exposure"),
            ("commercial_pct", "commercial_payer_exposure"),
        ]
        for alias, expected in cases:
            r = get_metric_context(alias)
            self.assertTrue(
                r.found,
                f"Glossary alias {alias!r} should resolve to "
                f"{expected!r} but lookup failed.",
            )
            self.assertEqual(
                r.metric_id, expected,
                f"Glossary alias {alias!r} resolved to "
                f"{r.metric_id!r}, expected {expected!r}.",
            )


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
