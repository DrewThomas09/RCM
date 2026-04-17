"""Plain-English explanations over the rich provenance graph.

``explain_metric`` returns one or two paragraphs a partner can read
without context. ``explain_for_ui`` returns the same information as a
structured dict so the UI can render a popover with labeled upstream
links.

Design: the explainer is deliberately dumb about the *math* — it
reads node metadata (R², method, n_comparables, margin_impact_bps,
…) and templates them into prose. Keeping the narrative logic here
instead of in each producer module means the phrasing stays consistent
when a new node type is added. The producers just need to populate
``metadata`` correctly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .graph import (
    EdgeRelationship,
    NodeType,
    ProvenanceGraph,
    ProvenanceNode,
)


# ── Value formatting ────────────────────────────────────────────────

def _fmt(value: float, unit: str) -> str:
    if value is None:
        return "n/a"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if unit == "pct":
        return f"{v:.1f}%"
    if unit == "days":
        return f"{v:.0f} days"
    if unit == "USD":
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v / 1e3:,.0f}K"
        return f"${v:,.0f}"
    if unit == "index":
        return f"{v:.2f}"
    if unit == "hospitals":
        return f"{v:.0f} hospitals"
    if unit == "fraction":
        return f"{v*100:.1f}%"
    if unit == "weight":
        return f"{v:.2f}"
    return f"{v:.2f}"


def _summarize_parent(node: ProvenanceNode) -> str:
    """Short '<label> (<value>, <source>)' clause used in lists."""
    value_str = _fmt(node.value, node.unit)
    src = (node.source or "").replace("_", " ")
    return f"{node.label.lower()} ({value_str}, {src})"


# ── Explanation templates ───────────────────────────────────────────

def _explain_observed(node: ProvenanceNode) -> str:
    value_str = _fmt(node.value, node.unit)
    source = node.source or "USER_INPUT"
    if source in ("HCRIS", "IRS990", "CARE_COMPARE", "UTILIZATION"):
        return (
            f"{node.label} of {value_str} was pulled from the "
            f"{source} dataset: {node.source_detail or source}."
        )
    return (
        f"{node.label} of {value_str} was provided directly as an "
        f"observed input to the analysis."
    )


def _explain_predicted(node: ProvenanceNode, upstream: List[ProvenanceNode]) -> str:
    md = node.metadata or {}
    value_str = _fmt(node.value, node.unit)
    method = md.get("method") or "ridge_regression"
    n = int(md.get("n_comparables_used") or 0)
    r2 = float(md.get("r_squared") or 0.0)
    ci_low = md.get("ci_low")
    ci_high = md.get("ci_high")
    cov = int(round(100 * float(md.get("coverage_target") or 0.9)))

    feature_nodes = [p for p in upstream if p.node_type == NodeType.OBSERVED]
    feature_desc = (
        f"The prediction used {len(feature_nodes)} input features: "
        + ", ".join(_summarize_parent(f) for f in feature_nodes[:6])
        + ("…" if len(feature_nodes) > 6 else "")
        + "."
    ) if feature_nodes else ""

    ci_desc = ""
    if ci_low is not None and ci_high is not None:
        ci_desc = (
            f" The {cov}% confidence interval is ["
            f"{_fmt(ci_low, node.unit)}, {_fmt(ci_high, node.unit)}], "
            f"computed via split conformal prediction on the calibration set."
        )

    fit_desc = (
        f" was predicted using {method.replace('_', ' ')} "
        f"(R²={r2:.2f}) trained on {n} comparable hospitals."
    )
    return (
        f"{node.label} of {value_str}{fit_desc} {feature_desc}{ci_desc}".strip()
    )


def _explain_calculated(
    node: ProvenanceNode, upstream: List[ProvenanceNode],
) -> str:
    md = node.metadata or {}
    value_str = _fmt(node.value, node.unit)

    # Bridge-lever special case: richer prose that quotes the lever
    # delta + revenue vs cost split.
    if node.id.startswith("bridge:") and node.id != "bridge:total":
        lever = node.id[len("bridge:"):]
        rev = md.get("revenue_impact") or 0.0
        cost = md.get("cost_impact") or 0.0
        rev_str = _fmt(rev, "USD")
        cost_saved = _fmt(-cost, "USD") if cost < 0 else _fmt(cost, "USD")
        direction = "savings" if cost < 0 else "cost"
        parent_clauses = ", ".join(_summarize_parent(p) for p in upstream[:4])
        margin_bps = md.get("margin_impact_bps") or 0.0
        wc = md.get("working_capital_impact") or 0.0
        wc_clause = (
            f" Working capital released (one-time): {_fmt(wc, 'USD')}."
            if wc else ""
        )
        return (
            f"EBITDA impact from the {lever.replace('_', ' ')} lever: "
            f"{value_str}. Composed of {rev_str} revenue and "
            f"{cost_saved} {direction}. Margin impact: {margin_bps:.0f} bps. "
            f"Inputs: {parent_clauses}.{wc_clause}"
        )

    if node.id == "bridge:total":
        ev_mult = md.get("ev_impact_at_multiple") or {}
        ev_clause = ""
        if ev_mult:
            ev_bits = ", ".join(f"{k} → {_fmt(v, 'USD')}"
                                 for k, v in list(ev_mult.items())[:3])
            ev_clause = f" At exit multiples: {ev_bits}."
        margin = md.get("margin_improvement_bps") or 0
        return (
            f"Total EBITDA impact of {value_str} is the sum of "
            f"{len(upstream)} per-lever impacts. Margin improvement: "
            f"{margin} bps.{ev_clause}"
        )

    if node.id.startswith("mc:ebitda_"):
        n_sims = (md.get("n_sims") or 0)
        band = node.id.split("_")[-1].upper()
        return (
            f"Monte Carlo {band} EBITDA of {value_str} — the "
            f"distribution summary statistic from {n_sims} simulations "
            f"over the composite (prediction × execution) uncertainty."
        )

    # Generic calculated node fallback.
    parents = ", ".join(_summarize_parent(p) for p in upstream[:4])
    return (
        f"{node.label} of {value_str}: {node.source_detail or 'calculated'}. "
        f"Inputs: {parents}."
    )


def _explain_aggregated(node: ProvenanceNode) -> str:
    value_str = _fmt(node.value, node.unit)
    return f"{node.label}: {value_str}. {node.source_detail}".strip()


def _explain_benchmark(node: ProvenanceNode) -> str:
    value_str = _fmt(node.value, node.unit)
    return (
        f"{node.label} benchmark of {value_str} sourced from "
        f"{node.source or 'registry'}: {node.source_detail}."
    )


# ── Public API ──────────────────────────────────────────────────────

def _resolve_metric_id(graph: ProvenanceGraph, metric_key: str) -> Optional[str]:
    """Map a user-friendly metric key (e.g., "denial_rate") to an
    actual node id in the graph. Preference order:
    ``observed:<key>`` > ``predicted:<key>`` > ``bridge:<key>`` >
    exact match.
    """
    for prefix in ("observed:", "predicted:", "bridge:", "target:",
                    "mc:", "comparables:"):
        nid = f"{prefix}{metric_key}"
        if nid in graph.nodes:
            return nid
    if metric_key in graph.nodes:
        return metric_key
    return None


def explain_metric(graph: ProvenanceGraph, metric_key: str) -> str:
    """Walk the graph backwards from the metric node to its sources,
    emitting a one-to-three sentence explanation.

    Never raises — returns a fallback string if the metric is unknown.
    """
    nid = _resolve_metric_id(graph, metric_key)
    if nid is None:
        return (
            f"No provenance entry found for {metric_key!r}. The metric "
            f"may not have been produced in this analysis run."
        )
    node = graph.nodes[nid]
    parents = [p for p, _rel in graph.direct_parents(nid)]
    nt = node.node_type
    if nt == NodeType.OBSERVED or nt == NodeType.SOURCE:
        return _explain_observed(node)
    if nt == NodeType.PREDICTED:
        return _explain_predicted(node, parents)
    if nt == NodeType.CALCULATED:
        return _explain_calculated(node, parents)
    if nt == NodeType.AGGREGATED:
        return _explain_aggregated(node)
    if nt == NodeType.BENCHMARK:
        return _explain_benchmark(node)
    # Unknown node type — fall back to a generic summary.
    return f"{node.label}: {_fmt(node.value, node.unit)}."


def explain_for_ui(graph: ProvenanceGraph, metric_key: str) -> Dict[str, Any]:
    """Structured explanation for the UI popover.

    Shape::
        {
            "metric": <metric_key>,
            "node_id": <resolved node id>,
            "value": <float>,
            "unit": <str>,
            "explanation_short": <one-line>,
            "explanation_full": <prose from explain_metric>,
            "upstream": [ {id, label, value, unit, source, relationship} ],
            "method": <source field>,
            "confidence": <0..1 or None>
        }
    """
    nid = _resolve_metric_id(graph, metric_key)
    if nid is None:
        return {
            "metric": metric_key,
            "error": "metric not found in provenance graph",
        }
    node = graph.nodes[nid]
    full = explain_metric(graph, metric_key)
    parents_with_rel = graph.direct_parents(nid)
    upstream_payload: List[Dict[str, Any]] = []
    for parent, rel in parents_with_rel[:10]:
        upstream_payload.append({
            "id": parent.id,
            "label": parent.label,
            "value": parent.value,
            "unit": parent.unit,
            "source": parent.source,
            "relationship": rel.value,
        })

    # Short explanation: use the label + value + direction for the UI.
    short = f"{node.label}: {_fmt(node.value, node.unit)}"
    if node.node_type == NodeType.CALCULATED and node.id.startswith("bridge:") \
            and node.id != "bridge:total":
        md = node.metadata or {}
        rev = md.get("revenue_impact") or 0.0
        cost = md.get("cost_impact") or 0.0
        if rev and not cost:
            short = f"{node.label}: {_fmt(rev, 'USD')} revenue lift"
        elif cost and not rev:
            short = f"{node.label}: {_fmt(-cost, 'USD')} cost savings"
    return {
        "metric": metric_key,
        "node_id": node.id,
        "value": node.value,
        "unit": node.unit,
        "explanation_short": short,
        "explanation_full": full,
        "upstream": upstream_payload,
        "method": node.source,
        "confidence": node.confidence,
        "node_type": node.node_type.value,
        "metadata": node.metadata or {},
    }
