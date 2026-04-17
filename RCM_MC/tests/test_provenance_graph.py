"""Tests for the rich provenance graph + explain layer.

Acceptance criteria from the build spec:
- Graph has no cycles
- Every predicted metric has upstream edges
- Every bridge output traces to RCM inputs (observed or predicted)
- ``explain_metric`` produces coherent text citing the value
- ``explain_for_ui`` returns valid structured data with upstream list
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.packet import (
    ComparableHospital,
    ComparableSet,
    EBITDABridgeResult,
    HospitalProfile,
    MetricImpact,
    ObservedMetric,
    PercentileSet,
    PredictedMetric,
    ProfileMetric,
    SectionStatus,
    SimulationSummary,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.provenance.explain import (
    _resolve_metric_id,
    explain_for_ui,
    explain_metric,
)
from rcm_mc.provenance.graph import (
    EdgeRelationship,
    NodeType,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    build_rich_graph,
)


# ── Fixtures ─────────────────────────────────────────────────────────

def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


def _stub_packet(
    observed: dict = None,
    predicted: dict = None,
    bridge: EBITDABridgeResult = None,
    comparables: ComparableSet = None,
    profile: HospitalProfile = None,
    simulation: SimulationSummary = None,
):
    """Tiny packet-shaped stub for unit-testing the rich graph.

    We build a real ``DealAnalysisPacket`` to exercise the same code
    paths the API uses.
    """
    from rcm_mc.analysis.packet import DealAnalysisPacket
    packet = DealAnalysisPacket(deal_id="stub", deal_name="Stub Hospital")
    if profile is not None:
        packet.profile = profile
    if observed is not None:
        packet.observed_metrics = observed
    if predicted is not None:
        packet.predicted_metrics = predicted
    if comparables is not None:
        packet.comparables = comparables
    if bridge is not None:
        packet.ebitda_bridge = bridge
    if simulation is not None:
        packet.simulation = simulation
    return packet


def _simple_bridge() -> EBITDABridgeResult:
    return EBITDABridgeResult(
        current_ebitda=30_000_000, target_ebitda=41_000_000,
        total_ebitda_impact=11_000_000,
        per_metric_impacts=[
            MetricImpact(
                metric_key="denial_rate", current_value=12.0, target_value=5.0,
                revenue_impact=9_800_000, cost_impact=-630_000,
                ebitda_impact=10_430_000, margin_impact_bps=260.7,
                upstream_metrics=["denial_rate", "net_revenue", "total_claims_volume"],
            ),
            MetricImpact(
                metric_key="days_in_ar", current_value=55.0, target_value=45.0,
                revenue_impact=0, cost_impact=-570_000,
                ebitda_impact=570_000, working_capital_impact=10_000_000,
                upstream_metrics=["days_in_ar", "net_revenue"],
            ),
        ],
        status=SectionStatus.OK,
        waterfall_data=[("Current EBITDA", 30_000_000), ("Target EBITDA", 41_000_000)],
        ev_impact_at_multiple={"10x": 110_000_000, "12x": 132_000_000},
    )


# ── ProvenanceGraph plumbing ────────────────────────────────────────

class TestGraphBasics(unittest.TestCase):
    def test_add_node_and_edge(self):
        g = ProvenanceGraph()
        g.add_node(ProvenanceNode(
            id="a", label="A", node_type=NodeType.OBSERVED, value=1.0,
        ))
        g.add_node(ProvenanceNode(
            id="b", label="B", node_type=NodeType.CALCULATED, value=2.0,
        ))
        g.add_edge("a", "b")
        self.assertEqual(len(g.nodes), 2)
        self.assertEqual(len(g.edges), 1)
        self.assertEqual(g.edges[0].relationship, EdgeRelationship.INPUT_TO)

    def test_add_node_requires_id(self):
        g = ProvenanceGraph()
        with self.assertRaises(ValueError):
            g.add_node(ProvenanceNode(
                id="", label="", node_type=NodeType.OBSERVED, value=0.0,
            ))

    def test_has_cycle_detects_self_loop(self):
        g = ProvenanceGraph()
        g.add_node(ProvenanceNode(id="a", label="A",
                                    node_type=NodeType.OBSERVED, value=0.0))
        g.add_edge("a", "a")
        self.assertTrue(g.has_cycle())

    def test_dag_has_no_cycle(self):
        g = ProvenanceGraph()
        for i in ("a", "b", "c", "d"):
            g.add_node(ProvenanceNode(
                id=i, label=i, node_type=NodeType.OBSERVED, value=0.0,
            ))
        g.add_edge("a", "b")
        g.add_edge("a", "c")
        g.add_edge("b", "d")
        g.add_edge("c", "d")
        self.assertFalse(g.has_cycle())

    def test_topological_order(self):
        g = ProvenanceGraph()
        for i in ("a", "b", "c"):
            g.add_node(ProvenanceNode(
                id=i, label=i, node_type=NodeType.OBSERVED, value=0.0,
            ))
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        order = g.topological_order()
        self.assertEqual(order, ["a", "b", "c"])

    def test_topological_empty_on_cycle(self):
        g = ProvenanceGraph()
        g.add_node(ProvenanceNode(id="a", label="a",
                                    node_type=NodeType.OBSERVED, value=0.0))
        g.add_node(ProvenanceNode(id="b", label="b",
                                    node_type=NodeType.OBSERVED, value=0.0))
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        self.assertEqual(g.topological_order(), [])

    def test_get_upstream_and_downstream(self):
        g = ProvenanceGraph()
        for i in ("a", "b", "c"):
            g.add_node(ProvenanceNode(
                id=i, label=i, node_type=NodeType.OBSERVED, value=0.0,
            ))
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        up = [n.id for n in g.get_upstream("c")]
        down = [n.id for n in g.get_downstream("a")]
        self.assertIn("a", up)
        self.assertIn("b", up)
        self.assertIn("b", down)
        self.assertIn("c", down)


# ── build_rich_graph from a stub packet ─────────────────────────────

class TestBuildRichGraph(unittest.TestCase):
    def test_graph_is_acyclic(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0),
                      "days_in_ar": ObservedMetric(value=55.0)},
            bridge=_simple_bridge(),
            profile=HospitalProfile(payer_mix={"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15}),
        )
        g = build_rich_graph(packet)
        self.assertFalse(g.has_cycle(), "rich graph must be a DAG")

    def test_every_predicted_metric_has_upstream_edges(self):
        packet = _stub_packet(
            observed={"days_in_ar": ObservedMetric(value=55.0),
                      "clean_claim_rate": ObservedMetric(value=88.0)},
            predicted={"denial_rate": PredictedMetric(
                value=11.5, ci_low=9.0, ci_high=14.0, method="ridge_regression",
                r_squared=0.72, n_comparables_used=25,
                provenance_chain=["days_in_ar", "clean_claim_rate"],
            )},
            comparables=ComparableSet(
                peers=[ComparableHospital(id="p1", similarity_score=0.9)],
                features_used=["bed_count", "region"],
                weights={"bed_count": 0.25, "region": 0.20},
            ),
        )
        g = build_rich_graph(packet)
        pred_id = "predicted:denial_rate"
        self.assertIn(pred_id, g.nodes)
        parents = g.direct_parents(pred_id)
        self.assertTrue(parents)
        # At least one edge back to an observed feature.
        observed_parents = [p for p, _ in parents
                            if p.node_type == NodeType.OBSERVED]
        self.assertTrue(observed_parents)

    def test_every_bridge_output_traces_to_rcm_inputs(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0),
                      "days_in_ar": ObservedMetric(value=55.0),
                      "net_revenue": ObservedMetric(value=400_000_000)},
            bridge=_simple_bridge(),
            profile=HospitalProfile(),
        )
        g = build_rich_graph(packet)
        for impact_id in ("bridge:denial_rate", "bridge:days_in_ar"):
            self.assertIn(impact_id, g.nodes)
            upstream = g.get_upstream(impact_id)
            ids = {n.id for n in upstream}
            # Every lever's trace reaches at least one observed RCM input.
            self.assertTrue(
                any(i.startswith("observed:") for i in ids),
                f"{impact_id} has no observed ancestor (upstream={ids})",
            )

    def test_bridge_total_rolls_up_all_levers(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0)},
            bridge=_simple_bridge(),
        )
        g = build_rich_graph(packet)
        self.assertIn("bridge:total", g.nodes)
        parents = {p.id for p, _ in g.direct_parents("bridge:total")}
        self.assertEqual(parents, {"bridge:denial_rate", "bridge:days_in_ar"})

    def test_comparable_features_feed_into_selection(self):
        packet = _stub_packet(
            comparables=ComparableSet(
                peers=[ComparableHospital(id="p1", similarity_score=0.9)],
                features_used=["bed_count", "payer_mix"],
                weights={"bed_count": 0.25, "payer_mix": 0.25},
            ),
        )
        g = build_rich_graph(packet)
        self.assertIn("comparables:selection", g.nodes)
        self.assertIn("comparables:feature:bed_count", g.nodes)
        parents = [p.id for p, _ in g.direct_parents("comparables:selection")]
        self.assertIn("comparables:feature:bed_count", parents)
        self.assertIn("comparables:feature:payer_mix", parents)

    def test_mc_nodes_present_when_simulation_ok(self):
        packet = _stub_packet(
            bridge=_simple_bridge(),
            simulation=SimulationSummary(
                n_sims=2000, seed=42,
                ebitda_uplift=PercentileSet(p10=5e6, p50=10e6, p90=15e6),
                status=SectionStatus.OK,
                variance_contribution_by_metric={"denial_rate": 0.6, "days_in_ar": 0.4},
            ),
        )
        g = build_rich_graph(packet)
        for band in ("p10", "p50", "p90"):
            self.assertIn(f"mc:ebitda_{band}", g.nodes)
        # And bridge:total feeds all three.
        downstream = {n.id for n in g.get_downstream("bridge:total")}
        self.assertTrue(downstream & {"mc:ebitda_p10", "mc:ebitda_p50", "mc:ebitda_p90"})


# ── Explanation ─────────────────────────────────────────────────────

class TestExplain(unittest.TestCase):
    def test_resolve_metric_id_prefers_observed(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0)},
            predicted={"denial_rate": PredictedMetric(
                value=11.5, ci_low=9.0, ci_high=14.0, method="ridge",
                r_squared=0.5, n_comparables_used=10,
            )},
        )
        g = build_rich_graph(packet)
        nid = _resolve_metric_id(g, "denial_rate")
        self.assertEqual(nid, "observed:denial_rate")

    def test_explain_observed_quotes_value_and_source(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(
                value=12.5, source="HCRIS",
                source_detail="HCRIS 2023 CCN 360180",
            )},
        )
        g = build_rich_graph(packet)
        text = explain_metric(g, "denial_rate")
        self.assertIn("12.5%", text)
        self.assertIn("HCRIS", text)

    def test_explain_predicted_mentions_method_and_ci(self):
        packet = _stub_packet(
            observed={"days_in_ar": ObservedMetric(value=55.0)},
            predicted={"net_collection_rate": PredictedMetric(
                value=94.2, ci_low=91.8, ci_high=96.6,
                method="ridge_regression", r_squared=0.81,
                n_comparables_used=47, coverage_target=0.9,
                provenance_chain=["days_in_ar"],
            )},
        )
        g = build_rich_graph(packet)
        text = explain_metric(g, "net_collection_rate")
        self.assertIn("94.2%", text)
        self.assertIn("47", text)
        self.assertIn("0.81", text)
        self.assertIn("91.8%", text)
        self.assertIn("96.6%", text)

    def test_explain_bridge_lever_quotes_revenue_and_cost(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0)},
            bridge=_simple_bridge(),
        )
        g = build_rich_graph(packet)
        text = explain_metric(g, "bridge:denial_rate")
        # $10.4M, $9.8M revenue, $630K cost savings — at least one of
        # these dollar figures must appear.
        self.assertTrue(any(tok in text for tok in ("$10.4M", "$9.8M", "$630K")),
                        f"text missing dollar figures: {text}")
        self.assertIn("bps", text)

    def test_explain_for_ui_returns_structured_payload(self):
        packet = _stub_packet(
            observed={"denial_rate": ObservedMetric(value=12.0)},
            bridge=_simple_bridge(),
        )
        g = build_rich_graph(packet)
        payload = explain_for_ui(g, "bridge:denial_rate")
        self.assertEqual(payload["metric"], "bridge:denial_rate")
        self.assertEqual(payload["node_id"], "bridge:denial_rate")
        self.assertIn("explanation_short", payload)
        self.assertIn("explanation_full", payload)
        self.assertIn("upstream", payload)
        self.assertIn("confidence", payload)
        self.assertIsInstance(payload["upstream"], list)

    def test_explain_missing_metric_returns_fallback(self):
        packet = _stub_packet(observed={"denial_rate": ObservedMetric(value=12.0)})
        g = build_rich_graph(packet)
        text = explain_metric(g, "no_such_metric")
        self.assertIn("No provenance", text)

    def test_explain_for_ui_missing_metric_has_error(self):
        packet = _stub_packet(observed={"denial_rate": ObservedMetric(value=12.0)})
        g = build_rich_graph(packet)
        payload = explain_for_ui(g, "no_such_metric")
        self.assertIn("error", payload)


# ── Packet integration ────────────────────────────────────────────

class TestPacketIntegration(unittest.TestCase):
    def test_packet_provenance_populated_by_builder(self):
        """After the full builder runs, packet.provenance (the simple
        flattened form) contains the rich graph's observed/bridge nodes."""
        store, path = _temp_store()
        try:
            store.upsert_deal("t", name="T", profile={
                "bed_count": 400,
                "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
            })
            packet = build_analysis_packet(
                store, "t", skip_simulation=True,
                observed_override={
                    "denial_rate": ObservedMetric(value=11.0),
                    "days_in_ar": ObservedMetric(value=55.0),
                },
                target_metrics={"denial_rate": 7.0, "days_in_ar": 45.0},
                financials={
                    "gross_revenue": 1_000_000_000, "net_revenue": 400_000_000,
                    "current_ebitda": 32_000_000, "claims_volume": 300_000,
                },
            )
            # Flat form (packet.provenance) carries rich-graph IDs.
            self.assertIn("observed:denial_rate", packet.provenance.nodes)
            self.assertIn("bridge:denial_rate", packet.provenance.nodes)
            self.assertIn("bridge:total", packet.provenance.nodes)
            # And rebuilding the rich graph from the packet succeeds
            # with matching node ids.
            rich = build_rich_graph(packet)
            self.assertTrue(rich.nodes)
            self.assertFalse(rich.has_cycle())
            # Rebuilt graph has at least the same key bridge nodes.
            for key in ("observed:denial_rate", "bridge:denial_rate",
                         "bridge:total"):
                self.assertIn(key, rich.nodes)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
