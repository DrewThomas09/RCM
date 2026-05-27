"""Guide context-sufficiency regression guard.

The 2026-05-26 sprint mapped placeholder page-contexts 144 -> 1 and expanded
the metric registry so the Guide can answer hard, quantitative questions WITH
the right context (formula + provenance), not just prose. These tests pin that
outcome offline (no Ollama needed): they assert the assembled context packet
actually surfaces the metric/formula a hard question needs, so the coverage
can't silently regress. They test context ASSEMBLY, not model output.
"""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.guide_context_packet import (
    build_guide_context_packet,
)
from rcm_mc.assistant.context.metric_registry import METRIC_REGISTRY
from rcm_mc.assistant.context.page_context_registry import (
    PAGE_CONTEXT_REGISTRY,
    _is_placeholder,
)

_NEEDS = "Needs source documentation."


class CoverageStaysHigh(unittest.TestCase):
    def test_placeholders_stay_essentially_zero(self):
        # The sprint took placeholders to 1 (only /ebitda-bridge, an unwired
        # alias). Guard against silent regression of the whole migration.
        ph = [r for r, c in PAGE_CONTEXT_REGISTRY.items() if _is_placeholder(c)]
        self.assertLessEqual(len(ph), 3, f"placeholders crept back up: {ph}")

    def test_related_routes_have_no_dead_cross_links(self):
        # Every related_routes entry the Guide offers as "open this next" must
        # resolve to a real mapped context — a dead cross-link sends a partner
        # to a route the Guide knows nothing about. The post-build
        # _RELATED_ROUTE_FIXES pass in manual_page_contexts.py repoints the
        # known-wrong links and drops unresolved ones; pin that it holds.
        known = set(PAGE_CONTEXT_REGISTRY.keys())
        broken = {
            r: [rr for rr in (c.related_routes or []) if rr not in known]
            for r, c in PAGE_CONTEXT_REGISTRY.items()
        }
        broken = {r: v for r, v in broken.items() if v}
        self.assertEqual(broken, {}, f"dead Guide cross-links: {broken}")

    def test_tools_index_is_mapped(self):
        # /tools is a real served route (the full searchable tool index) — it
        # must carry a real context, not 404 in the Guide.
        self.assertIn("/tools", PAGE_CONTEXT_REGISTRY)

    def test_core_analytic_routes_grade_strong(self):
        # These are the pages partners hit with hard quantitative questions;
        # each must resolve linked metric/source context (STRONG), not prose
        # alone.
        for route in ("/quant-lab", "/portfolio/regression", "/benchmarks",
                      "/cost-structure", "/debt-service", "/lp-dashboard",
                      "/concentration-risk", "/sector-intel",
                      "/diligence/xray"):
            pkt = build_guide_context_packet(route)
            self.assertEqual(pkt.context_quality, "strong",
                             f"{route} is not STRONG: {pkt.context_quality}")


class HardQuestionContextIsPresent(unittest.TestCase):
    """For a hard question on a route, the packet must carry the metric the
    answer depends on — i.e. the Guide can actually answer it from context."""

    CASES = [
        ("/debt-service", "dscr"),
        ("/lp-dashboard", "tvpi"),
        ("/lp-dashboard", "dpi"),
        ("/concentration-risk", "hhi"),
        ("/benchmarks", "denial_rate"),
        ("/cost-structure", "operating_margin"),
        ("/quant-lab", "operating_margin"),
        ("/nursing-homes", "cms_star_rating"),
        ("/treasury", "days_cash_on_hand"),
        ("/debt-service", "fixed_charge_coverage"),
        ("/working-capital", "cash_conversion_cycle"),
        ("/unit-economics", "gross_margin"),
    ]

    def test_packet_surfaces_the_needed_metric(self):
        for route, metric_id in self.CASES:
            pkt = build_guide_context_packet(route)
            ids = {m.metric_id for m in pkt.metric_contexts}
            self.assertIn(metric_id, ids,
                          f"{route} packet missing metric {metric_id} "
                          f"(has: {sorted(ids)})")


class NewMetricsAreUsable(unittest.TestCase):
    def test_added_metrics_have_real_formulas(self):
        # Standard metrics added this sprint must carry a real (non-placeholder)
        # formula so the Guide can explain "how is X computed".
        for mid in ("hhi", "concentration_ratio", "dscr", "tvpi", "dpi",
                    "rvpi", "days_cash_on_hand", "length_of_stay",
                    "cost_to_charge_ratio", "current_ratio", "gross_margin",
                    "capex_intensity", "fixed_charge_coverage",
                    "interest_coverage", "cash_conversion_cycle", "net_debt"):
            m = METRIC_REGISTRY.get(mid)
            self.assertIsNotNone(m, f"metric {mid} missing from registry")
            self.assertNotEqual(m.formula, _NEEDS,
                                f"{mid} has no real formula")
            self.assertTrue(m.definition and m.caveats,
                            f"{mid} lacks definition/caveats")

    def test_cms_star_rating_is_honest_about_being_external(self):
        # CMS stars are CMS's own composite — must NOT claim an invented
        # formula; formula_confidence must be NOT_APPLICABLE.
        m = METRIC_REGISTRY["cms_star_rating"]
        self.assertEqual(m.formula_confidence.name, "NOT_APPLICABLE")


class BackendConceptDocsArePresent(unittest.TestCase):
    """The Guide must be able to explain the backend ENGINES, not just pages /
    metrics. These concept cards (docs/rag_sources/) are what RAG retrieves for
    "how does the simulation / bridge / quant stack / prediction work" — pin
    that they're in the corpus. Offline: enumerates the RAG sources, no Ollama."""

    def _doc_blob(self):
        from rcm_mc.assistant.rag.document_sources import iter_guide_documents
        docs = [d for d in iter_guide_documents() if d.source_type == "doc"]
        return " ".join((d.title + " " + (d.file_path or "")).lower()
                        for d in docs)

    def test_core_engines_have_a_concept_doc(self):
        blob = self._doc_blob()
        for concept in ("monte_carlo", "value_creation_bridge", "quant_stack",
                        "analysis_packet", "ridge_conformal", "scenario_engine",
                        "provenance_and_data_quality"):
            self.assertIn(concept, blob,
                          f"Guide corpus missing a backend concept doc: {concept}")

    def test_acronym_glossary_is_present(self):
        # A partner asking "what does TVPI / DSCR / RAF / 340B mean" should get
        # an expansion — the healthcare-PE acronym glossary card must be in the
        # corpus so RAG can retrieve it.
        blob = self._doc_blob()
        self.assertIn("pe_healthcare_glossary", blob,
                      "Guide corpus missing the acronym glossary card")

    def test_nuanced_pe_and_process_concept_docs(self):
        # The Guide should also be able to explain nuanced PE concepts and the
        # backend workflows, like an analyst assistant — pin those cards too.
        blob = self._doc_blob()
        for concept in ("pe_fund_economics", "pe_deal_structuring",
                        "pe_value_creation_and_exit", "pe_healthcare_concepts",
                        "process_alerts_lifecycle", "process_deal_lifecycle",
                        "process_exports", "process_portfolio_ops",
                        "process_data_ingestion"):
            self.assertIn(concept, blob,
                          f"Guide corpus missing a concept doc: {concept}")

    def test_survival_doc_states_not_kaplan_meier(self):
        # Honesty guard: the survival concept card must NOT claim KM/Cox.
        from rcm_mc.assistant.rag.document_sources import iter_guide_documents
        qs = next((d for d in iter_guide_documents()
                   if d.source_type == "doc" and "quant_stack" in (d.file_path or "")),
                  None)
        self.assertIsNotNone(qs, "quant_stack concept doc missing")
        self.assertIn("NOT Kaplan-Meier", qs.text)


if __name__ == "__main__":
    unittest.main()
