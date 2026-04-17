"""Tests for the healthcare economic ontology.

Three contracts this file locks in:

1. Every required metric listed in the build spec has an entry in
   ``METRIC_ONTOLOGY`` with a well-formed ``MetricDefinition``.
2. Causal-path explanations for the partner-facing headline metrics
   (``denial_rate``, ``days_in_ar``, ``clean_claim_rate``,
   ``net_collection_rate``) cite the right drivers, pathway, and
   reimbursement regime.
3. The packet builder decorates each :class:`ProfileMetric` with the
   ontology metadata, so the workbench and renderers don't need a
   side lookup.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    MetricSource,
    ObservedMetric,
    ProfileMetric,
)
from rcm_mc.analysis.packet_builder import (
    _attach_ontology,
    build_analysis_packet,
)
from rcm_mc.domain.econ_ontology import (
    METRIC_ONTOLOGY,
    ConfidenceClass,
    Directionality,
    Domain,
    FinancialPathway,
    MechanismEdge,
    MetricDefinition,
    ReimbursementProfile,
    causal_graph,
    classify_metric,
    explain_causal_path,
)
from rcm_mc.portfolio.store import PortfolioStore


# ── Ontology coverage ────────────────────────────────────────────────

REQUIRED_METRICS = {
    "denial_rate",
    "initial_denial_rate",
    "final_denial_rate",
    "clean_claim_rate",
    "first_pass_resolution_rate",
    "days_in_ar",
    "ar_over_90_pct",
    "net_collection_rate",
    "cost_to_collect",
    "discharged_not_final_billed_days",
    "avoidable_denial_pct",
    "coding_denial_rate",
    "auth_denial_rate",
    "eligibility_denial_rate",
    "timely_filing_denial_rate",
    "medical_necessity_denial_rate",
    "gross_revenue",
    "net_revenue",
    "ebitda",
    "ebitda_margin",
    "payer_mix_commercial",
    "payer_mix_medicare",
    "payer_mix_medicaid",
    "payer_mix_self_pay",
    "case_mix_index",
    "bad_debt",
}


class TestOntologyCoverage(unittest.TestCase):
    def test_every_required_metric_has_a_definition(self):
        missing = REQUIRED_METRICS - set(METRIC_ONTOLOGY.keys())
        self.assertFalse(
            missing,
            f"Missing ontology entries for: {sorted(missing)}",
        )

    def test_every_definition_is_well_formed(self):
        for key, defn in METRIC_ONTOLOGY.items():
            self.assertIsInstance(defn, MetricDefinition)
            self.assertIsInstance(defn.domain, Domain)
            self.assertIsInstance(defn.directionality, Directionality)
            self.assertIsInstance(defn.financial_pathway, FinancialPathway)
            self.assertIsInstance(defn.confidence_class, ConfidenceClass)
            self.assertIsInstance(defn.reimbursement_sensitivity,
                                   ReimbursementProfile)
            self.assertEqual(defn.metric_key, key)
            self.assertTrue(defn.display_name)
            self.assertTrue(defn.economic_mechanism)

    def test_classify_metric_returns_the_entry(self):
        defn = classify_metric("denial_rate")
        self.assertEqual(defn.metric_key, "denial_rate")
        self.assertEqual(defn.directionality, Directionality.LOWER_IS_BETTER)

    def test_classify_unknown_raises(self):
        with self.assertRaises(KeyError):
            classify_metric("nonexistent_metric")


# ── Reimbursement sensitivity tags ──────────────────────────────────

class TestReimbursementSensitivity(unittest.TestCase):
    def test_cmi_high_under_drg_and_low_under_capitated(self):
        defn = classify_metric("case_mix_index")
        r = defn.reimbursement_sensitivity
        self.assertGreaterEqual(r.prospective_drg, 0.8)
        self.assertLessEqual(r.capitated, 0.5)

    def test_denial_rate_high_under_ffs(self):
        r = classify_metric("denial_rate").reimbursement_sensitivity
        self.assertGreaterEqual(r.fee_for_service, 0.8)

    def test_days_in_ar_low_under_capitated(self):
        r = classify_metric("days_in_ar").reimbursement_sensitivity
        self.assertLess(r.capitated, r.fee_for_service)

    def test_payer_mix_commercial_drives_revenue(self):
        defn = classify_metric("payer_mix_commercial")
        self.assertEqual(defn.financial_pathway, FinancialPathway.REVENUE)


# ── Causal graph ────────────────────────────────────────────────────

class TestCausalGraph(unittest.TestCase):
    def test_graph_has_nodes_and_edges(self):
        g = causal_graph()
        self.assertGreaterEqual(len(g.nodes), len(REQUIRED_METRICS))
        self.assertGreater(len(g.edges), 0)
        for edge in g.edges:
            self.assertIsInstance(edge, MechanismEdge)
            self.assertIn(edge.parent, g.nodes)
            self.assertIn(edge.child, g.nodes)

    def test_denial_rate_parents_include_front_end_failures(self):
        g = causal_graph()
        parents = {p.metric_key for p in g.parents_of("denial_rate")}
        self.assertIn("eligibility_denial_rate", parents)
        self.assertIn("auth_denial_rate", parents)
        self.assertIn("coding_denial_rate", parents)

    def test_days_in_ar_children_affect_collections(self):
        g = causal_graph()
        children = {c.metric_key for c in g.children_of("days_in_ar")}
        self.assertIn("net_collection_rate", children)
        self.assertIn("ar_over_90_pct", children)

    def test_no_self_loops(self):
        g = causal_graph()
        for edge in g.edges:
            self.assertNotEqual(
                edge.parent, edge.child,
                f"self-loop on {edge.parent}",
            )

    def test_financial_metrics_end_in_ebitda(self):
        """Every direct parent of ebitda_margin should eventually
        trace through net_revenue or ebitda — we want the P&L to
        terminate on the headline number."""
        g = causal_graph()
        margin_parents = {p.metric_key for p in g.parents_of("ebitda_margin")}
        self.assertIn("ebitda", margin_parents)
        self.assertIn("net_revenue", margin_parents)


# ── Causal path explanations ────────────────────────────────────────

class TestCausalPathExplanations(unittest.TestCase):
    def _check_common(self, metric_key: str, must_contain: list):
        text = explain_causal_path(metric_key)
        for fragment in must_contain:
            self.assertIn(
                fragment.lower(), text.lower(),
                f"expected {fragment!r} in explanation of {metric_key!r}:\n{text}",
            )
        return text

    def test_denial_rate_explanation(self):
        self._check_common("denial_rate", [
            "denial", "revenue", "reimbursement",
        ])

    def test_days_in_ar_explanation(self):
        text = self._check_common("days_in_ar", [
            "working capital", "cash",
        ])
        self.assertIn("lower is better", text.lower())

    def test_clean_claim_rate_explanation(self):
        text = self._check_common("clean_claim_rate", [
            "clean claim", "higher is better",
        ])
        # Tags surface for the workbench tooltip.
        self.assertIn("front_end_quality", text)

    def test_net_collection_rate_explanation(self):
        text = self._check_common("net_collection_rate", [
            "net collection rate", "higher is better", "revenue",
        ])
        # Parents must include denial flow / days_in_ar.
        lower = text.lower()
        self.assertTrue("denial" in lower or "days in ar" in lower)

    def test_unknown_metric_returns_safe_fallback(self):
        text = explain_causal_path("not_a_real_metric")
        self.assertIn("not classified", text)


# ── Packet integration ──────────────────────────────────────────────

def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    s.upsert_deal("ont", name="Ontology Deal", profile={
        "bed_count": 400, "region": "midwest",
        "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
    })
    return s, path


class TestPacketIntegration(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_builder_attaches_ontology_to_profile_metrics(self):
        packet = build_analysis_packet(
            self.store, "ont", skip_simulation=True,
            observed_override={
                "denial_rate": ObservedMetric(value=11.0),
                "days_in_ar": ObservedMetric(value=55.0),
            },
            financials={
                "gross_revenue": 1_000_000_000,
                "net_revenue": 400_000_000,
                "current_ebitda": 32_000_000,
                "claims_volume": 300_000,
            },
        )
        dr = packet.rcm_profile["denial_rate"]
        self.assertEqual(dr.domain, "back_end_claims")
        self.assertIn(dr.financial_pathway, ("mixed", "revenue", "cost", "risk"))
        self.assertIsNotNone(dr.causal_path_summary)
        self.assertIn("denial", dr.causal_path_summary.lower())
        # Mechanism tags populated.
        self.assertIn("rework_cost", dr.mechanism_tags)

    def test_attach_helper_is_idempotent(self):
        profile = {
            "denial_rate": ProfileMetric(value=11.0, source=MetricSource.OBSERVED),
            "not_in_ontology": ProfileMetric(value=3.14, source=MetricSource.OBSERVED),
        }
        _attach_ontology(profile)
        self.assertEqual(profile["denial_rate"].domain, "back_end_claims")
        # Unknown metric leaves ontology fields at defaults.
        self.assertIsNone(profile["not_in_ontology"].domain)
        # Second call doesn't re-append tags.
        _attach_ontology(profile)
        self.assertEqual(
            profile["denial_rate"].mechanism_tags.count("rework_cost"), 1,
        )

    def test_profile_metric_roundtrip_preserves_ontology_fields(self):
        pm = ProfileMetric(
            value=11.0, source=MetricSource.OBSERVED,
            domain="back_end_claims",
            financial_pathway="mixed",
            causal_path_summary="Denial rate sits …",
            mechanism_tags=["rework_cost", "bad_debt_driver"],
        )
        d = pm.to_dict()
        restored = ProfileMetric.from_dict(d)
        self.assertEqual(restored.domain, "back_end_claims")
        self.assertEqual(restored.financial_pathway, "mixed")
        self.assertEqual(restored.mechanism_tags,
                         ["rework_cost", "bad_debt_driver"])
        self.assertIn("Denial rate", restored.causal_path_summary)


if __name__ == "__main__":
    unittest.main()
