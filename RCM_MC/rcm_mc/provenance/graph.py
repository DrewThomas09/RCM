"""Rich explorable provenance DAG for one deal analysis packet.

Complements :mod:`rcm_mc.analysis.packet` (which carries a simplified
wire-format ``ProvenanceGraph`` that JSON-roundtrips with the rest of
the packet) by providing a richer graph type with typed edges, node
categories (SOURCE / OBSERVED / PREDICTED / CALCULATED / AGGREGATED /
BENCHMARK), and traversal APIs (upstream / downstream / cycle check).

Why two classes with similar names:
- ``rcm_mc.analysis.packet.ProvenanceGraph`` is a **snapshot** — stored
  in the packet JSON, shaped to round-trip cleanly. Simple dict-of-
  nodes + upstream refs by metric name.
- ``rcm_mc.provenance.graph.ProvenanceGraph`` (this module) is an
  **explorer** — built on demand from a packet, offers typed edges +
  traversal methods the UI needs to render an audit trail. Never
  persisted; rebuilt each time an ``/api/provenance`` request arrives.

The rich graph is what the partner's "why is this number 8.2%" click
path interacts with. The packet graph is what cached packets store.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    """Broad category of a provenance node."""
    SOURCE = "SOURCE"              # External raw input (HCRIS row, 990 field)
    OBSERVED = "OBSERVED"          # User- or analyst-entered metric
    PREDICTED = "PREDICTED"        # Output of the ridge / regression layer
    CALCULATED = "CALCULATED"      # Deterministic arithmetic (bridge levers)
    AGGREGATED = "AGGREGATED"      # Cohort aggregate (peer median, P50)
    BENCHMARK = "BENCHMARK"        # External benchmark anchor (HFMA MAP keys)


class EdgeRelationship(str, Enum):
    """Edge label. ``input_to`` is the default; others flag special
    semantics to the UI (e.g., edges of type ``weighted_by`` render as
    dotted lines in the graph view)."""
    INPUT_TO = "input_to"                  # A feeds into B directly
    DERIVED_FROM = "derived_from"          # B is computed from A
    WEIGHTED_BY = "weighted_by"            # A adjusts B's magnitude
    CALIBRATED_AGAINST = "calibrated_against"   # A is the benchmark B was tuned to


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class ProvenanceNode:
    id: str
    label: str
    node_type: NodeType
    value: float
    unit: str = ""
    source: str = ""
    source_detail: str = ""
    confidence: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type.value,
            "value": _json_safe(self.value),
            "unit": self.unit,
            "source": self.source,
            "source_detail": self.source_detail,
            "confidence": _json_safe(self.confidence),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": _json_safe_dict(self.metadata),
        }


@dataclass
class ProvenanceEdge:
    from_node: str
    to_node: str
    relationship: EdgeRelationship = EdgeRelationship.INPUT_TO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "relationship": self.relationship.value,
        }


class ProvenanceGraph:
    """Directed acyclic graph over :class:`ProvenanceNode`s.

    Call ``add_node`` / ``add_edge`` while building; callers should not
    mutate the node/edge collections directly so the has-cycle
    invariant stays enforced.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, ProvenanceNode] = {}
        self.edges: List[ProvenanceEdge] = []
        # Adjacency map: from_node → [(to_node, relationship)]
        self._downstream: Dict[str, List[Tuple[str, EdgeRelationship]]] = {}
        self._upstream: Dict[str, List[Tuple[str, EdgeRelationship]]] = {}

    # ── Mutation ──────────────────────────────────────────────────

    def add_node(self, node: ProvenanceNode) -> ProvenanceNode:
        if not node.id:
            raise ValueError("ProvenanceNode.id must be non-empty")
        self.nodes[node.id] = node
        return node

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        relationship: EdgeRelationship = EdgeRelationship.INPUT_TO,
    ) -> ProvenanceEdge:
        # Tolerate the caller adding an edge before a node — typical
        # during top-down packet construction. We still record it so
        # node ordering doesn't matter.
        edge = ProvenanceEdge(from_node=from_node, to_node=to_node,
                               relationship=relationship)
        self.edges.append(edge)
        self._downstream.setdefault(from_node, []).append((to_node, relationship))
        self._upstream.setdefault(to_node, []).append((from_node, relationship))
        return edge

    # ── Traversal ────────────────────────────────────────────────

    def get_upstream(self, node_id: str, *, max_depth: int = 64) -> List[ProvenanceNode]:
        """Return all upstream nodes reachable from ``node_id``, in
        topological order (roots first). Cycle-safe via a visited set.
        """
        out: List[ProvenanceNode] = []
        seen: Set[str] = set()

        def _walk(nid: str, depth: int) -> None:
            if nid in seen or depth > max_depth:
                return
            seen.add(nid)
            for parent_id, _rel in self._upstream.get(nid, []):
                _walk(parent_id, depth + 1)
                node = self.nodes.get(parent_id)
                if node is not None and node not in out:
                    out.append(node)

        _walk(node_id, 0)
        return out

    def get_downstream(self, node_id: str, *, max_depth: int = 64) -> List[ProvenanceNode]:
        out: List[ProvenanceNode] = []
        seen: Set[str] = set()

        def _walk(nid: str, depth: int) -> None:
            if nid in seen or depth > max_depth:
                return
            seen.add(nid)
            for child_id, _rel in self._downstream.get(nid, []):
                node = self.nodes.get(child_id)
                if node is not None and node not in out:
                    out.append(node)
                _walk(child_id, depth + 1)

        _walk(node_id, 0)
        return out

    def direct_parents(self, node_id: str) -> List[Tuple[ProvenanceNode, EdgeRelationship]]:
        out: List[Tuple[ProvenanceNode, EdgeRelationship]] = []
        for pid, rel in self._upstream.get(node_id, []):
            node = self.nodes.get(pid)
            if node is not None:
                out.append((node, rel))
        return out

    # ── Invariants ───────────────────────────────────────────────

    def has_cycle(self) -> bool:
        """DFS-based cycle detection. Returns True if any node is
        reachable from itself via the edge list.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self.nodes}

        def _dfs(nid: str) -> bool:
            if color.get(nid) == GRAY:
                return True     # back edge → cycle
            if color.get(nid) == BLACK:
                return False
            color[nid] = GRAY
            for child_id, _rel in self._downstream.get(nid, []):
                if child_id in color and _dfs(child_id):
                    return True
            color[nid] = BLACK
            return False

        return any(_dfs(nid) for nid in list(self.nodes))

    def topological_order(self) -> List[str]:
        """Kahn's algorithm. Returns empty list if the graph has a
        cycle (callers use ``has_cycle`` for an explicit check)."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        for edge in self.edges:
            if edge.to_node in in_degree:
                in_degree[edge.to_node] = in_degree.get(edge.to_node, 0) + 1
        queue = [nid for nid, d in in_degree.items() if d == 0]
        out: List[str] = []
        while queue:
            nid = queue.pop(0)
            out.append(nid)
            for child_id, _ in self._downstream.get(nid, []):
                if child_id not in in_degree:
                    continue
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)
        if len(out) != len(self.nodes):
            return []
        return out

    # ── Serialization ────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [self.nodes[nid].to_dict() for nid in sorted(self.nodes.keys())],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # ── Packet-format projection ─────────────────────────────────

    def to_packet_graph(self) -> Any:
        """Flatten into :class:`rcm_mc.analysis.packet.ProvenanceSnapshot`
        for storage in the packet JSON. Edge relationships collapse
        into the parent node list — the rich form is rebuilt on demand
        by :func:`build_rich_graph`.
        """
        from ..analysis.packet import DataNode, ProvenanceSnapshot
        pg = ProvenanceSnapshot()
        for nid, node in self.nodes.items():
            parents = [pid for pid, _ in self._upstream.get(nid, [])]
            pg.add(DataNode(
                metric=nid,
                value=float(node.value) if node.value is not None else 0.0,
                source=node.source or node.node_type.value,
                source_detail=node.source_detail,
                confidence=float(node.confidence if node.confidence is not None else 1.0),
                upstream=parents,
            ))
        return pg


# ── Builder: rich graph from a DealAnalysisPacket ───────────────────

def build_rich_graph(packet: Any) -> ProvenanceGraph:
    """Construct a :class:`ProvenanceGraph` from a ``DealAnalysisPacket``.

    Deterministic — given the same packet we produce the same graph.
    The ID scheme is:

        observed:<metric>                   — user/analyst/CMS input
        source:<metric>                     — raw external source node
        comparables:selection                — the cohort of peers used
        comparables:feature:<feature_key>    — each feature fed to
                                              comparable selection
        predicted:<metric>                   — ridge / median output
        target:<metric>                      — target metric on the bridge
        bridge:<metric>                      — lever EBITDA impact
        bridge:total                         — total EBITDA impact
        mc:<metric>                          — MC assumption per-metric
        mc:ebitda_p50 / mc:ebitda_p10 / p90  — MC summary bands
        benchmark:<metric>:<percentile>       — registry anchors

    This is intentionally verbose — partners clicking a node need to
    see exactly what kind of object they're staring at.
    """
    g = ProvenanceGraph()
    _add_observed_nodes(g, packet)
    _add_comparable_nodes(g, packet)
    _add_predicted_nodes(g, packet)
    _add_profile_nodes(g, packet)
    _add_bridge_nodes(g, packet)
    _add_mc_nodes(g, packet)
    return g


def _add_observed_nodes(g: ProvenanceGraph, packet: Any) -> None:
    for metric, om in (packet.observed_metrics or {}).items():
        source_label = om.source or "USER_INPUT"
        node_type = (NodeType.SOURCE if source_label in ("HCRIS", "IRS990", "CARE_COMPARE")
                     else NodeType.OBSERVED)
        g.add_node(ProvenanceNode(
            id=f"observed:{metric}",
            label=f"Observed {_pretty(metric)}",
            node_type=node_type,
            value=float(om.value),
            unit=_unit_for(metric),
            source=source_label,
            source_detail=om.source_detail or f"Provided by {source_label}",
            confidence=1.0,
            metadata={"quality_flags": list(om.quality_flags or [])},
        ))


def _add_comparable_nodes(g: ProvenanceGraph, packet: Any) -> None:
    cs = packet.comparables
    if cs is None or not getattr(cs, "peers", None):
        return
    # One aggregate node for the cohort, plus a node per feature used.
    g.add_node(ProvenanceNode(
        id="comparables:selection",
        label=f"Comparable cohort ({len(cs.peers)} peers)",
        node_type=NodeType.AGGREGATED,
        value=float(len(cs.peers)),
        unit="hospitals",
        source="comparable_finder",
        source_detail=(
            f"Top {len(cs.peers)} peers by weighted similarity. "
            f"Features: {', '.join(cs.features_used or [])}"
        ),
        confidence=0.9 if len(cs.peers) >= 10 else 0.6,
        metadata={
            "weights": dict(cs.weights or {}),
            "features_used": list(cs.features_used or []),
            "robustness_check": dict(cs.robustness_check or {}),
        },
    ))
    # Feature nodes — each feeds into the selection.
    for feat in cs.features_used or []:
        feat_id = f"comparables:feature:{feat}"
        if feat_id not in g.nodes:
            g.add_node(ProvenanceNode(
                id=feat_id,
                label=f"Similarity feature: {feat}",
                node_type=NodeType.SOURCE,
                value=float((cs.weights or {}).get(feat) or 0.0),
                unit="weight",
                source="comparable_finder",
                source_detail=f"Weight in similarity score: "
                              f"{(cs.weights or {}).get(feat) or 0.0:.2f}",
                confidence=1.0,
            ))
        g.add_edge(feat_id, "comparables:selection",
                    EdgeRelationship.WEIGHTED_BY)


def _add_predicted_nodes(g: ProvenanceGraph, packet: Any) -> None:
    for metric, pm in (packet.predicted_metrics or {}).items():
        nid = f"predicted:{metric}"
        method = pm.method or "ridge_regression"
        g.add_node(ProvenanceNode(
            id=nid,
            label=f"Predicted {_pretty(metric)}",
            node_type=NodeType.PREDICTED,
            value=float(pm.value),
            unit=_unit_for(metric),
            source=method,
            source_detail=(
                f"{method} from {pm.n_comparables_used} comparables "
                f"(R²={pm.r_squared:.2f}). 90% CI "
                f"[{pm.ci_low:.2f}, {pm.ci_high:.2f}]."
            ),
            confidence=max(0.0, min(1.0, float(pm.r_squared))),
            metadata={
                "method": method,
                "r_squared": float(pm.r_squared),
                "n_comparables_used": int(pm.n_comparables_used),
                "ci_low": float(pm.ci_low),
                "ci_high": float(pm.ci_high),
                "coverage_target": float(pm.coverage_target or 0.9),
                "reliability_grade": pm.reliability_grade or "",
                "feature_importances": dict(pm.feature_importances or {}),
            },
        ))
        # Edge from the cohort selection node.
        if "comparables:selection" in g.nodes:
            g.add_edge("comparables:selection", nid,
                        EdgeRelationship.DERIVED_FROM)
        # Edges from each provenance_chain entry (observed features).
        for upstream_metric in pm.provenance_chain or []:
            up_id = f"observed:{upstream_metric}"
            if up_id in g.nodes:
                g.add_edge(up_id, nid, EdgeRelationship.INPUT_TO)


def _add_profile_nodes(g: ProvenanceGraph, packet: Any) -> None:
    """Hospital profile fields used by the bridge (payer mix)."""
    profile = packet.profile
    if profile is None:
        return
    if profile.payer_mix:
        total = sum(float(v or 0.0) for v in profile.payer_mix.values())
        for payer, frac in profile.payer_mix.items():
            g.add_node(ProvenanceNode(
                id=f"profile:payer_mix:{payer}",
                label=f"Payer mix — {payer}",
                node_type=NodeType.OBSERVED,
                value=float(frac or 0.0),
                unit="fraction" if total <= 1.5 else "pct",
                source="USER_INPUT",
                source_detail=f"Payer mix entry for {payer}",
                confidence=1.0,
            ))


def _add_bridge_nodes(g: ProvenanceGraph, packet: Any) -> None:
    br = packet.ebitda_bridge
    if br is None or not br.per_metric_impacts:
        return
    # One node per lever's EBITDA impact.
    impact_ids: List[str] = []
    for imp in br.per_metric_impacts:
        lever = imp.metric_key
        # Target node (the level we're shooting for).
        target_id = f"target:{lever}"
        if target_id not in g.nodes:
            g.add_node(ProvenanceNode(
                id=target_id,
                label=f"Target {_pretty(lever)}",
                node_type=NodeType.AGGREGATED,
                value=float(imp.target_value),
                unit=_unit_for(lever),
                source="moderate_tier_recommendation",
                source_detail=(
                    f"Moderate-tier target for {_pretty(lever)} "
                    f"= {imp.target_value}"
                ),
                confidence=0.7,
            ))
        impact_id = f"bridge:{lever}"
        g.add_node(ProvenanceNode(
            id=impact_id,
            label=f"EBITDA impact — {_pretty(lever)}",
            node_type=NodeType.CALCULATED,
            value=float(imp.ebitda_impact),
            unit="USD",
            source="rcm_ebitda_bridge",
            source_detail=(
                f"Delta {imp.current_value:.2f} → {imp.target_value:.2f}"
            ),
            confidence=0.8,
            metadata={
                "revenue_impact": float(imp.revenue_impact),
                "cost_impact": float(imp.cost_impact),
                "margin_impact_bps": float(imp.margin_impact_bps),
                "working_capital_impact": float(imp.working_capital_impact),
                "upstream_metrics": list(imp.upstream_metrics or []),
            },
        ))
        impact_ids.append(impact_id)
        # Edges: observed (or predicted) lever → target → impact.
        observed_id = f"observed:{lever}"
        predicted_id = f"predicted:{lever}"
        if observed_id in g.nodes:
            g.add_edge(observed_id, impact_id, EdgeRelationship.INPUT_TO)
        elif predicted_id in g.nodes:
            g.add_edge(predicted_id, impact_id, EdgeRelationship.INPUT_TO)
        g.add_edge(target_id, impact_id, EdgeRelationship.INPUT_TO)
        # Bridge depends on upstream_metrics (from the bridge's
        # ``upstream_metrics`` list) — link them too so the rich graph
        # shows ``net_revenue`` and ``total_claims_volume`` as inputs.
        for upstream_metric in imp.upstream_metrics or []:
            obs_id = f"observed:{upstream_metric}"
            if obs_id in g.nodes and obs_id != impact_id:
                g.add_edge(obs_id, impact_id, EdgeRelationship.WEIGHTED_BY)
            # Also cover profile fields like payer_mix.medicare → same
            # bridge lever when relevant.
            if upstream_metric == "payer_mix":
                for payer_node in [n for n in g.nodes
                                    if n.startswith("profile:payer_mix:")]:
                    g.add_edge(payer_node, impact_id,
                                EdgeRelationship.WEIGHTED_BY)
    # Roll-up total_ebitda_impact node.
    if br.total_ebitda_impact != 0 or impact_ids:
        g.add_node(ProvenanceNode(
            id="bridge:total",
            label="Total EBITDA impact",
            node_type=NodeType.CALCULATED,
            value=float(br.total_ebitda_impact),
            unit="USD",
            source="rcm_ebitda_bridge",
            source_detail="Sum of per-lever EBITDA impacts",
            confidence=0.8,
            metadata={
                "new_ebitda_margin": float(br.new_ebitda_margin),
                "margin_improvement_bps": int(br.margin_improvement_bps),
                "working_capital_released": float(br.working_capital_released),
                "ev_impact_at_multiple": dict(br.ev_impact_at_multiple or {}),
            },
        ))
        for iid in impact_ids:
            g.add_edge(iid, "bridge:total", EdgeRelationship.INPUT_TO)


def _add_mc_nodes(g: ProvenanceGraph, packet: Any) -> None:
    sim = packet.simulation
    if sim is None or sim.status.value != "OK":
        return
    # Summary bands on EBITDA uplift.
    for band in ("p10", "p50", "p90"):
        val = getattr(sim.ebitda_uplift, band, 0.0)
        nid = f"mc:ebitda_{band}"
        g.add_node(ProvenanceNode(
            id=nid,
            label=f"MC EBITDA {band.upper()}",
            node_type=NodeType.CALCULATED,
            value=float(val),
            unit="USD",
            source="monte_carlo",
            source_detail=f"{sim.n_sims} simulations, seed {sim.seed}",
            confidence=0.75 if sim.n_sims >= 2000 else 0.6,
            metadata={"n_sims": int(sim.n_sims),
                      "variance_contribution": dict(sim.variance_contribution_by_metric or {})},
        ))
        if "bridge:total" in g.nodes:
            g.add_edge("bridge:total", nid, EdgeRelationship.DERIVED_FROM)
    # Per-metric variance contribution nodes as edges weighted to each
    # lever's ebitda_pX node. A full Sobol-style view would emit one
    # node per metric; we keep it tight with edges instead.
    for metric, share in (sim.variance_contribution_by_metric or {}).items():
        impact_id = f"bridge:{metric}"
        if impact_id in g.nodes:
            for band in ("p10", "p50", "p90"):
                g.add_edge(impact_id, f"mc:ebitda_{band}",
                            EdgeRelationship.WEIGHTED_BY)


# ── Helpers ─────────────────────────────────────────────────────────

def _pretty(metric: str) -> str:
    return metric.replace("_", " ")


_UNITS = {
    # Pct-scale rate metrics
    "denial_rate": "pct", "final_denial_rate": "pct",
    "appeals_overturn_rate": "pct", "clean_claim_rate": "pct",
    "net_collection_rate": "pct", "first_pass_resolution_rate": "pct",
    "ar_over_90_pct": "pct", "bad_debt_rate": "pct",
    "patient_payment_yield": "pct", "autopost_rate": "pct",
    "claim_rejection_rate": "pct", "insurance_verification_rate": "pct",
    "late_charge_pct": "pct", "coding_accuracy_rate": "pct",
    "cost_to_collect": "pct", "avoidable_denial_pct": "pct",
    "ebitda_margin": "pct",
    # Day counts
    "days_in_ar": "days", "dnfb_days": "days", "charge_lag_days": "days",
    # Indices
    "case_mix_index": "index",
    # Dollars
    "gross_revenue": "USD", "net_revenue": "USD",
    "current_ebitda": "USD", "total_operating_expenses": "USD",
}


def _unit_for(metric: str) -> str:
    return _UNITS.get(metric, "")


def _json_safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    return v


def _json_safe_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out[k] = _json_safe_dict(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [_json_safe(x) for x in v]
        else:
            out[k] = _json_safe(v)
    return out
