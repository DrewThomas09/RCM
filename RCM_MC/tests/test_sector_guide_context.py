"""Guide context coverage for the Sector Intelligence pages (Phase 2B completion).

/home-health and /hospice are now first-class: discovered routes, manual
PageContexts, metric + data-source registry entries, and RAG corpus
inclusion — so the Guide can explain them honestly (public benchmark data,
not target financials, not an investment recommendation).
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context import build_guide_context_packet
from rcm_mc.assistant.context.metric_registry import METRIC_REGISTRY
from rcm_mc.assistant.context.data_source_registry import DATA_SOURCE_REGISTRY
from rcm_mc.assistant.context.types import DataConfidence


class SectorGuideContextTests(unittest.TestCase):
    def test_home_health_context_resolves_strong(self):
        p = build_guide_context_packet("/home-health")
        self.assertEqual(p.context_quality, "strong")
        self.assertGreaterEqual(len(p.metric_contexts), 3)
        self.assertGreaterEqual(len(p.data_source_contexts), 1)
        self.assertTrue(p.suggested_questions)
        # public benchmark, not target data
        self.assertEqual(p.page_context.data_confidence,
                         DataConfidence.PUBLIC_BENCHMARK_DATA)
        # honest limitation present
        joined = " ".join(p.page_context.limitations).lower()
        self.assertIn("medicare-certified", joined)

    def test_hospice_context_resolves_strong(self):
        p = build_guide_context_packet("/hospice")
        self.assertEqual(p.context_quality, "strong")
        self.assertGreaterEqual(len(p.metric_contexts), 3)
        self.assertEqual(p.page_context.data_confidence,
                         DataConfidence.PUBLIC_BENCHMARK_DATA)

    def test_registry_entries_exist(self):
        for m in ("home_health_star_rating", "discharge_to_community",
                  "hospice_care_index", "visits_in_last_days"):
            self.assertIn(m, METRIC_REGISTRY)
        for s in ("cms_home_health_provider_data", "cms_hospice_provider_data",
                  "cms_provider_data_catalog"):
            self.assertIn(s, DATA_SOURCE_REGISTRY)

    def test_metrics_are_public_benchmark_not_target(self):
        # The sector quality metrics must not claim observed target data.
        for m in ("home_health_star_rating", "hospice_care_index"):
            mc = METRIC_REGISTRY[m]
            self.assertEqual(mc.data_confidence, DataConfidence.PUBLIC_BENCHMARK_DATA)

    def test_rag_corpus_includes_sectors(self):
        from rcm_mc.assistant.rag.document_sources import iter_guide_documents
        docs = list(iter_guide_documents())
        routes = {getattr(d, "route", "") for d in docs}
        self.assertIn("/home-health", routes)
        self.assertIn("/hospice", routes)
        blob = " ".join(d.text for d in docs)
        self.assertIn("Hospice Care Index", blob)


if __name__ == "__main__":
    unittest.main()
