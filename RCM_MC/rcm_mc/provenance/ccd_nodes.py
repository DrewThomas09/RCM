"""CCD-derived provenance nodes.

Extends :mod:`rcm_mc.provenance.graph` with the :class:`CCDDerivedMetric`
dataclass — a typed, chain-aware wrapper around a :class:`ProvenanceNode`
whose ``node_type`` is :attr:`NodeType.CCD_DERIVED`.

The wrapper carries the fields required to walk the chain all the way
back to a source row in the original upload:

    memo paragraph  →  packet field  →  bridge lever  →  observed_metric
      →  CCDDerivedMetric  →  KPI aggregation rule  →  canonical claim row
      →  CCD transformation  →  raw source row (file + row number)

Each ``CCDDerivedMetric`` stores:

- ``ingest_id`` — the CCD the metric was computed from
- ``kpi_aggregation_rule`` — short string like "weighted_mean(paid_date - service_date_from)"
- ``qualifying_claim_ids`` — the canonical claim_ids whose rows fed
  this metric (the "AGGREGATED" step of the chain)
- ``transformation_refs`` — a list of ``(source_file, source_row,
  rule_name)`` tuples from the CCD's TransformationLog. Populated by
  :func:`build_from_kpi_result` when a KPI is about to land in the
  packet.

The explainer in :mod:`rcm_mc.provenance.explain` reads these fields
to produce the end-to-end narrative; see :func:`explain_ccd_derived`
below.

Why a dedicated module: the core graph module stays free of any
CCD-specific shape, and partners who never upload a CCD never pay
for this layer at import time. The glue is pulled in lazily by the
explainer when it encounters a :attr:`NodeType.CCD_DERIVED` node.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .graph import (
    EdgeRelationship, NodeType, ProvenanceEdge, ProvenanceGraph,
    ProvenanceNode,
)


# ── Dataclass ──────────────────────────────────────────────────────

@dataclass
class CCDDerivedMetric:
    """A CCD-derived metric's provenance record.

    This is an in-memory wrapper over a ``ProvenanceNode`` — it's not
    a replacement. Callers construct a ``CCDDerivedMetric``, hand the
    ``to_node()`` output to the ``ProvenanceGraph`` builder, and the
    rest of the system treats it as a normal node with
    ``node_type=CCD_DERIVED``. The richer fields are all accessible
    via ``node.metadata``.
    """
    metric_key: str                         # e.g. "days_in_ar"
    label: str                              # partner-facing label
    value: float
    unit: str                               # "days" | "pct" | "usd" | "ratio"

    ingest_id: str                          # CCD identity
    kpi_aggregation_rule: str               # human-readable formula name
    citation: str = ""                      # HFMA MAP / AAPC / etc.

    qualifying_claim_ids: Tuple[str, ...] = ()
    transformation_refs: Tuple[Dict[str, Any], ...] = ()

    # Chain-walk anchors — the explainer uses these to climb back.
    kpi_source_detail: str = ""             # the ObservedMetric source_detail
    sample_size: int = 0
    temporal_validity: Optional[Dict[str, Any]] = None

    # Confidence piggy-backs on the node. Always 1.0 for CCD-derived
    # values per the session-2 bridge contract, but we carry it
    # explicitly in case a later session downgrades (e.g., Tuva-
    # enriched marts with lower coverage).
    confidence: float = 1.0

    def node_id(self) -> str:
        """Stable node id: ``ccd::<metric_key>``."""
        return f"ccd::{self.metric_key}"

    def source_node_id(self) -> str:
        """Stable id of the upstream CCD ``SOURCE`` node."""
        return f"ccd_source::{self.ingest_id}"

    # ------- construction + serialisation --------------------------

    def to_node(self) -> ProvenanceNode:
        """Materialise this record as a :class:`ProvenanceNode` with
        every field tucked into ``metadata`` so the explainer can
        retrieve the chain without a sidecar lookup."""
        return ProvenanceNode(
            id=self.node_id(),
            label=self.label,
            node_type=NodeType.CCD_DERIVED,
            value=self.value,
            unit=self.unit,
            source="CCD",
            source_detail=self.kpi_source_detail,
            confidence=self.confidence,
            metadata={
                "metric_key": self.metric_key,
                "ingest_id": self.ingest_id,
                "kpi_aggregation_rule": self.kpi_aggregation_rule,
                "citation": self.citation,
                "qualifying_claim_ids": list(self.qualifying_claim_ids),
                "transformation_refs": [
                    dict(r) for r in self.transformation_refs
                ],
                "sample_size": int(self.sample_size),
                "temporal_validity": self.temporal_validity or {},
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Graph-builder helpers ──────────────────────────────────────────

def attach_ccd_source(
    graph: ProvenanceGraph,
    *,
    ingest_id: str,
    source_files: Sequence[str],
    content_hash: Optional[str] = None,
) -> str:
    """Add (or idempotently return) the CCD ``SOURCE`` node's id for
    ``ingest_id``. Every CCD-derived metric node points to this single
    source via a ``DERIVED_FROM`` edge."""
    node_id = f"ccd_source::{ingest_id}"
    if node_id in graph.nodes:
        return node_id
    graph.nodes[node_id] = ProvenanceNode(
        id=node_id,
        label=f"CCD {ingest_id}",
        node_type=NodeType.SOURCE,
        value=0.0,
        source="CCD",
        source_detail=f"Canonical Claims Dataset ingest_id={ingest_id}",
        metadata={
            "ingest_id": ingest_id,
            "source_files": list(source_files),
            "content_hash": content_hash,
        },
    )
    return node_id


def attach_ccd_derived(
    graph: ProvenanceGraph, derived: CCDDerivedMetric,
) -> str:
    """Add a :class:`CCDDerivedMetric` to ``graph``. Creates the
    node + the edge to the CCD source. Returns the new node id."""
    # Attach the source first (idempotent).
    src_id = attach_ccd_source(
        graph,
        ingest_id=derived.ingest_id,
        source_files=[],  # filled in earlier by the CCD ingester
    )
    node = derived.to_node()
    graph.nodes[node.id] = node
    graph.edges.append(ProvenanceEdge(
        from_node=src_id, to_node=node.id,
        relationship=EdgeRelationship.DERIVED_FROM,
    ))
    return node.id


# ── Explainer for CCD_DERIVED nodes ────────────────────────────────

def explain_ccd_derived(
    graph: ProvenanceGraph, node: ProvenanceNode,
) -> str:
    """Human-readable explanation walking the chain back to source.

    Called from :mod:`rcm_mc.provenance.explain` when the node's type
    is :attr:`NodeType.CCD_DERIVED`. Produces a multi-sentence
    paragraph naming the KPI rule, the ingest_id, the sample size,
    and up to three source-row references.
    """
    md = node.metadata or {}
    metric_key = str(md.get("metric_key") or node.id)
    rule = str(md.get("kpi_aggregation_rule") or "aggregation rule")
    ingest_id = str(md.get("ingest_id") or "")
    n = int(md.get("sample_size") or 0)
    citation = str(md.get("citation") or "")
    claim_ids = list(md.get("qualifying_claim_ids") or [])
    transformation_refs = list(md.get("transformation_refs") or [])

    value_str = _fmt(node.value, node.unit or "")
    parts: List[str] = []
    parts.append(
        f"{node.label} of {value_str} was computed from the "
        f"Canonical Claims Dataset {ingest_id!r} via the {rule!r} rule"
        + (f" ({citation})" if citation else "")
        + f". Sample size: {n} claim(s)."
    )

    if claim_ids:
        sample = claim_ids[:3]
        more = f" (+{len(claim_ids) - 3} more)" if len(claim_ids) > 3 else ""
        parts.append(
            f"Qualifying claims: {', '.join(sample)}{more}."
        )

    if transformation_refs:
        first = transformation_refs[:3]
        chain_lines: List[str] = []
        for t in first:
            chain_lines.append(
                f"{t.get('source_file', '?')}:"
                f"row {t.get('source_row', '?')} "
                f"[{t.get('rule', '?')}]"
            )
        more = (
            f" (+{len(transformation_refs) - 3} more transformations)"
            if len(transformation_refs) > 3 else ""
        )
        parts.append(
            "Source-row chain: " + " · ".join(chain_lines) + more + "."
        )

    tv = md.get("temporal_validity") or {}
    if tv.get("claims_date_min") and tv.get("claims_date_max"):
        events = tv.get("overlapping_events") or []
        if events:
            names = ", ".join(str(e.get("name", "?")) for e in events[:2])
            parts.append(
                f"Claims window {tv['claims_date_min']} → {tv['claims_date_max']} "
                f"overlaps regulatory event(s): {names}."
            )
        else:
            parts.append(
                f"Claims window {tv['claims_date_min']} → {tv['claims_date_max']} "
                f"with no regulatory discontinuity inside the range."
            )

    return " ".join(parts)


# ── Chain completeness check ───────────────────────────────────────

def chain_is_complete(
    graph: ProvenanceGraph, node_id: str,
) -> Tuple[bool, Optional[str]]:
    """Walk the provenance chain from ``node_id`` upward; return
    ``(ok, missing_link)``. ``missing_link`` names the step where the
    chain breaks — ``None`` when every step resolves.

    Used by the explain endpoint to report "which step dropped the
    chain" when explain-for-ui returns an error.
    """
    if node_id not in graph.nodes:
        return False, f"unknown node id {node_id!r}"
    node = graph.nodes[node_id]
    if node.node_type != NodeType.CCD_DERIVED:
        # Not a CCD-derived node — chain ends normally.
        return True, None
    md = node.metadata or {}
    if not md.get("ingest_id"):
        return False, (
            f"CCDDerivedMetric {node_id!r} is missing ingest_id — cannot "
            f"chain back to the CCD source"
        )
    if not md.get("kpi_aggregation_rule"):
        return False, (
            f"CCDDerivedMetric {node_id!r} is missing kpi_aggregation_rule — "
            f"cannot explain the metric's formula"
        )
    if not md.get("qualifying_claim_ids"):
        return False, (
            f"CCDDerivedMetric {node_id!r} carries zero qualifying_claim_ids — "
            f"the KPI→claim-row step of the chain is broken"
        )
    src_id = f"ccd_source::{md['ingest_id']}"
    if src_id not in graph.nodes:
        return False, (
            f"CCDDerivedMetric {node_id!r} references CCD source "
            f"{src_id!r} which is not in the provenance graph"
        )
    # Transformation refs are best-effort — a CCD that had no raw
    # source rows (e.g., synthetic test data) legitimately has an
    # empty list. Don't fail the chain on that.
    return True, None


# ── Tiny formatting helper (kept local to avoid circular import) ──

def _fmt(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value * 100:,.1f}%"
    if unit == "days":
        return f"{value:,.1f}d"
    if unit == "usd":
        return f"${value:,.2f}"
    return f"{value:,.3f}"
