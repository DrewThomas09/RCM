"""Cross-lever dependency adjustment for the v2 value bridge.

Fixes the double-count problem: in the v2 bridge every lever runs
independently, but many levers are *causally linked* through the
:mod:`rcm_mc.domain.econ_ontology` graph. If an analyst models both
``eligibility_denial_rate`` (parent) and ``denial_rate`` (child)
improving simultaneously, the naive sum captures the revenue
recovery from *each* lever as if the other didn't exist — overstating
the real EBITDA lift.

This module walks the lever set in topological order and reduces
each lever's revenue-recovery component by the fraction already
captured by its causal parents. Cost savings and working-capital
effects are *not* adjusted — those pathways don't overlap the same
way revenue recovery does.

Key design choices:

- **Topological walk.** We respect the ontology's DAG — a parent lever
  is always adjusted *before* its children so the child knows what
  was already captured.
- **Magnitude-hint mapping.** Each edge in the ontology carries a
  ``magnitude_hint`` string (``strong`` / ``moderate`` / ``weak``).
  We map those to numeric overlap fractions (0.60 / 0.35 / 0.15).
  Explicit + tunable + partner-defensible.
- **Additive, capped.** With two upstream levers fired, we sum their
  overlap fractions and cap at 0.75 so a heavily-connected child
  doesn't collapse to zero.
- **v2 only.** The v1 bridge (:mod:`rcm_mc.pe.rcm_ebitda_bridge`) is
  untouched; it already over-indexes on uniform research-band
  calibration, and adding dependency math on top would obscure the
  calibration signal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..domain.econ_ontology import CausalGraph, causal_graph
from .value_bridge_v2 import LeverImpact

logger = logging.getLogger(__name__)


# ── Tunable constants ───────────────────────────────────────────────

# Map the ontology's magnitude_hint strings to numeric overlap
# fractions. "Strong" means the parent lever captures 60% of what a
# child lever would recover if the parent weren't modeled; moderate is
# 35%, weak is 15%. These are explicitly tunable and surfaced in the
# audit trail so partners can push back on any specific edge.
_MAGNITUDE_OVERLAP: Dict[str, float] = {
    "strong": 0.60,
    "moderate": 0.35,
    "weak": 0.15,
}

# Safety cap when a child has multiple upstream levers: never zero out
# a lever's revenue component entirely. 0.75 leaves at least 25% of
# the raw revenue even under heavy overlap.
_MAX_TOTAL_OVERLAP = 0.75


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class DependencyAuditRow:
    """One row of the audit trail — what adjustment was applied, why.

    Partners read this alongside the leverage table to see where the
    v2 bridge dampened revenue recovery because of causal overlap.
    """
    lever: str
    raw_impact: float
    adjustment_pct: float               # 0-100, share of revenue dropped
    adjusted_impact: float
    upstream_levers: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever": self.lever,
            "raw_impact": float(self.raw_impact),
            "adjustment_pct": float(self.adjustment_pct),
            "adjusted_impact": float(self.adjusted_impact),
            "upstream_levers": list(self.upstream_levers),
            "explanation": self.explanation,
        }


# ── Public API ─────────────────────────────────────────────────────

def _topological_order(graph: CausalGraph) -> List[str]:
    """Kahn's algorithm on the domain CausalGraph.

    The ``domain.econ_ontology.CausalGraph`` class itself doesn't ship
    a topological-order method — its edges list is small and this
    local implementation keeps the domain module focused on the
    registry. Returns `[]` on cycle.
    """
    in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
    for edge in graph.edges:
        if edge.child in in_degree:
            in_degree[edge.child] = in_degree.get(edge.child, 0) + 1
    queue: List[str] = [nid for nid, d in in_degree.items() if d == 0]
    out: List[str] = []
    # Build child adjacency.
    children: Dict[str, List[str]] = {}
    for edge in graph.edges:
        children.setdefault(edge.parent, []).append(edge.child)
    while queue:
        nid = queue.pop(0)
        out.append(nid)
        for child in children.get(nid, []):
            if child not in in_degree:
                continue
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    if len(out) != len(graph.nodes):
        return []   # cycle
    return out


def topological_lever_order(
    metric_keys: Iterable[str],
    graph: Optional[CausalGraph] = None,
) -> List[str]:
    """Return ``metric_keys`` in a bridge-evaluation order that
    respects causal parents-before-children.

    Metrics not present in the ontology are appended at the end (no
    adjustment applies to them — they're effectively roots).
    """
    graph = graph or causal_graph()
    present = set(metric_keys)
    full_order = _topological_order(graph)
    ordered = [m for m in full_order if m in present]
    # Tail: any keys not in the ontology. Stable within the input.
    tail = [m for m in metric_keys if m not in graph.nodes]
    seen = set(ordered) | set(tail)
    leftovers = [m for m in metric_keys if m not in seen]
    return ordered + tail + leftovers


def _edge_overlap(
    graph: CausalGraph, parent_key: str, child_key: str,
) -> float:
    """Return the numeric overlap fraction for one causal edge, or
    0.0 if the edge doesn't exist in the graph."""
    for edge in graph.edges_into(child_key):
        if edge.parent == parent_key:
            return _MAGNITUDE_OVERLAP.get(
                edge.magnitude_hint or "moderate", 0.35,
            )
    return 0.0


def apply_dependency_adjustment(
    lever_key: str,
    lever_impact: LeverImpact,
    already_captured: Dict[str, LeverImpact],
    graph: Optional[CausalGraph] = None,
) -> Tuple[LeverImpact, DependencyAuditRow]:
    """Adjust one lever's revenue component for overlap with already-
    processed upstream levers. Returns the adjusted impact + an audit row.

    Only ``recurring_revenue_uplift`` is reduced. ``recurring_cost_savings``
    and ``one_time_working_capital_release`` + ``ongoing_financing_benefit``
    are untouched — cost savings and working capital operate through
    independent pathways. ``recurring_ebitda_delta`` is recomputed
    consistently.
    """
    graph = graph or causal_graph()
    raw_total = float(lever_impact.recurring_ebitda_delta)

    # Find upstream levers that are both (a) causal parents per the
    # ontology and (b) already processed in this walk.
    upstream_levers: List[str] = []
    total_overlap = 0.0
    edge_details: List[str] = []
    if lever_key in graph.nodes:
        for edge in graph.edges_into(lever_key):
            if edge.parent not in already_captured:
                continue
            overlap = _edge_overlap(graph, edge.parent, lever_key)
            if overlap <= 0:
                continue
            upstream_levers.append(edge.parent)
            total_overlap += overlap
            edge_details.append(
                f"{edge.parent} ({edge.magnitude_hint}, −{int(overlap*100)}%)"
            )

    total_overlap = min(total_overlap, _MAX_TOTAL_OVERLAP)

    if total_overlap <= 0 or not upstream_levers:
        # No adjustment. Identity audit row for completeness.
        audit = DependencyAuditRow(
            lever=lever_key,
            raw_impact=raw_total,
            adjustment_pct=0.0,
            adjusted_impact=raw_total,
            upstream_levers=[],
            explanation="no upstream levers fired; no adjustment",
        )
        return lever_impact, audit

    adjusted_revenue = lever_impact.recurring_revenue_uplift * (1.0 - total_overlap)
    adjusted_ebitda = (
        adjusted_revenue
        + lever_impact.recurring_cost_savings
        + lever_impact.ongoing_financing_benefit
    )

    # Amend the lever's explanation so the audit trail lives on the
    # impact too (not just in the side-table).
    explanation = (
        lever_impact.explanation
        + f" Adjusted down {int(total_overlap*100)}% for overlap with "
        + ", ".join(upstream_levers) + "."
    )

    # Adjust the provenance tag so downstream can tell this lever was
    # modified by the dependency walk.
    new_provenance = dict(lever_impact.provenance or {})
    new_provenance["dependency_adjusted"] = ",".join(upstream_levers)

    adjusted_impact = replace(
        lever_impact,
        recurring_revenue_uplift=adjusted_revenue,
        recurring_ebitda_delta=adjusted_ebitda,
        explanation=explanation,
        provenance=new_provenance,
    )

    audit = DependencyAuditRow(
        lever=lever_key,
        raw_impact=raw_total,
        adjustment_pct=total_overlap * 100.0,
        adjusted_impact=adjusted_ebitda,
        upstream_levers=list(upstream_levers),
        explanation=(
            "reduced revenue component by "
            f"{int(total_overlap*100)}%: overlap with "
            + "; ".join(edge_details)
        ),
    )
    return adjusted_impact, audit


def walk_dependency(
    lever_impacts: List[LeverImpact],
    graph: Optional[CausalGraph] = None,
) -> Tuple[List[LeverImpact], List[DependencyAuditRow]]:
    """Walk all levers in topological order, apply adjustments, return
    ``(adjusted_impacts, audit_rows)``.

    The returned list preserves the caller's original order so
    downstream renderers don't have to re-sort.
    """
    graph = graph or causal_graph()
    if not lever_impacts:
        return [], []

    by_key: Dict[str, LeverImpact] = {li.metric_key: li for li in lever_impacts}
    order = topological_lever_order(by_key.keys(), graph=graph)

    adjusted_by_key: Dict[str, LeverImpact] = {}
    audit_by_key: Dict[str, DependencyAuditRow] = {}

    for key in order:
        raw = by_key.get(key)
        if raw is None:
            continue
        adjusted, audit = apply_dependency_adjustment(
            key, raw, adjusted_by_key, graph=graph,
        )
        adjusted_by_key[key] = adjusted
        audit_by_key[key] = audit

    adjusted_list = [adjusted_by_key[li.metric_key] for li in lever_impacts
                     if li.metric_key in adjusted_by_key]
    audit_list = [audit_by_key[li.metric_key] for li in lever_impacts
                  if li.metric_key in audit_by_key]
    return adjusted_list, audit_list
