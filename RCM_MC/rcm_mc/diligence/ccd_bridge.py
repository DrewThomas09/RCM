"""CCD → packet bridge.

The one place where the Phase 1 output (CCD + transformation log +
Phase 2 KPIs) meets the existing Phase 4 packet builder. Callers
that already run ``build_analysis_packet(...)`` invoke this shim
first to convert CCD-derived KPIs into the ``observed_metrics`` dict
the builder expects, and to produce the matching provenance nodes.

Why a dedicated module: keeping the CCD logic out of
``analysis/packet_builder.py`` means the builder stays agnostic to
where observed metrics came from. A partner running without a CCD
gets the same behaviour they always got; a partner *with* a CCD gets
CCD-derived metrics threaded in at the right priority tier.

Priority order implemented here (spec §A):

    OVERRIDE (explicit analyst number) > CCD > PARTNER_INPUT > PREDICTED

Override wins because an analyst typed it on purpose. CCD beats
partner YAML because a claims-level computation is always more
defensible than a summary number. Partner YAML beats predicted
because a partner-supplied number exists; the predictor is only used
when nothing else is available.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from ..analysis.packet import MetricSource, ObservedMetric
from ..provenance.graph import (
    EdgeRelationship, NodeType, ProvenanceEdge, ProvenanceNode,
)
from .benchmarks.kpi_engine import KPIBundle, KPIResult


# ── Confidence weighting ────────────────────────────────────────────

CONFIDENCE_OVERRIDE = 1.0
CONFIDENCE_CCD = 1.0
CONFIDENCE_PARTNER_YAML = 0.7
# PREDICTED confidence is variable — set by the conformal margin
# caller-side. The number here is a *fallback* for callers that
# don't pass a margin.
CONFIDENCE_PREDICTED_FALLBACK = 0.5


# ── KPI → packet metric key mapping ─────────────────────────────────
#
# Packet-side metric keys follow the ``RCM_METRIC_REGISTRY`` vocabulary
# used by the completeness layer. Kept as an explicit map rather than
# a guess-the-name lookup so a registry rename doesn't silently drop
# CCD-derived metrics.
_KPI_TO_METRIC_KEY: Dict[str, str] = {
    "Days in A/R": "days_in_ar",
    "First-Pass Denial Rate": "initial_denial_rate",
    "A/R Aging > 90 Days": "ar_aging_over_90_days",
    "Cost to Collect": "cost_to_collect",
    "Net Revenue Realization": "net_revenue_realization",
    "Service → Bill Lag (median days)": "lag_service_to_bill_days",
    "Bill → Cash Lag (median days)": "lag_bill_to_cash_days",
}


# ── Result shape ────────────────────────────────────────────────────

@dataclass
class CCDBridgeOutput:
    """What the bridge hands back to ``build_analysis_packet``."""
    observed_metrics: Dict[str, ObservedMetric] = field(default_factory=dict)
    provenance_nodes: List[ProvenanceNode] = field(default_factory=list)
    provenance_edges: List[ProvenanceEdge] = field(default_factory=list)
    skipped_kpis: List[Tuple[str, str]] = field(default_factory=list)

    def as_override_dict(self) -> Dict[str, Any]:
        """Return a dict the caller can pass as
        ``build_analysis_packet(..., override=...)``. Matches the
        existing override shape: ``{metric_key: value}`` with floats
        already coerced. Used when the caller wants the cleanest
        possible override entry point."""
        return {k: v.value for k, v in self.observed_metrics.items()}


# ── Public API ──────────────────────────────────────────────────────

def kpis_to_observed(
    bundle: KPIBundle,
    ccd: Any,
    *,
    confidence: float = CONFIDENCE_CCD,
    source_detail_prefix: str = "CCD:",
) -> CCDBridgeOutput:
    """Convert a :class:`KPIBundle` into ``ObservedMetric`` instances
    + matching provenance nodes.

    KPIs with ``value is None`` are skipped (not coerced to 0 — that
    would be fabrication). Each skipped KPI lands in
    ``skipped_kpis`` with its reason for the UI's "insufficient
    data" label.
    """
    out = CCDBridgeOutput()
    ingest_id = getattr(ccd, "ingest_id", "unknown-ccd")

    kpis = _collect_kpis(bundle)
    for kpi in kpis:
        metric_key = _KPI_TO_METRIC_KEY.get(kpi.name)
        if metric_key is None:
            # Not in the packet's metric registry vocabulary — skip.
            # We don't silently invent a key; the UI can surface the
            # KPI directly without the packet round-trip.
            out.skipped_kpis.append((kpi.name, "no registry mapping"))
            continue
        if kpi.value is None:
            out.skipped_kpis.append(
                (kpi.name, kpi.reason or "unknown reason")
            )
            continue

        quality_flags: List[str] = []
        if kpi.temporal.overlapping_events:
            quality_flags.append("temporal_validity_overlap")
        if kpi.temporal.warnings:
            quality_flags.append("temporal_warning")

        om = ObservedMetric(
            value=float(kpi.value),
            source=MetricSource.CCD.value,
            source_detail=(
                f"{source_detail_prefix}{ingest_id} · "
                f"{kpi.citation} · n={kpi.sample_size}"
            ),
            as_of_date=bundle.as_of_date,
            quality_flags=quality_flags,
            confidence=confidence,
        )
        out.observed_metrics[metric_key] = om

        # One provenance node per CCD-derived metric. Metadata carries
        # the qualifying claim IDs + temporal validity so the explain
        # endpoint can drill all the way back to source rows.
        node_id = f"ccd::{metric_key}"
        out.provenance_nodes.append(ProvenanceNode(
            id=node_id,
            label=kpi.name,
            node_type=NodeType.CCD_DERIVED,
            value=float(kpi.value),
            unit=kpi.unit,
            source="CCD",
            source_detail=om.source_detail,
            confidence=confidence,
            metadata={
                "ingest_id": ingest_id,
                "sample_size": kpi.sample_size,
                "qualifying_claim_ids": list(kpi.qualifying_claim_ids),
                "temporal_validity": kpi.temporal.to_dict(),
                "citation": kpi.citation,
                "numerator": kpi.numerator,
                "denominator": kpi.denominator,
                "ccd_transformation_log_ref": f"{ingest_id}::log",
            },
        ))

        # Edge: CCD source → packet observed-metric node.
        source_node_id = f"ccd_source::{ingest_id}"
        out.provenance_edges.append(ProvenanceEdge(
            from_node=source_node_id,
            to_node=node_id,
            relationship=EdgeRelationship.DERIVED_FROM,
        ))

    # A single SOURCE node stands in for the whole CCD — edges from
    # each KPI point back to it. Metadata keeps the full transformation
    # log hash so the explain endpoint can fetch the log on demand.
    out.provenance_nodes.append(ProvenanceNode(
        id=f"ccd_source::{ingest_id}",
        label=f"CCD {ingest_id}",
        node_type=NodeType.SOURCE,
        value=0.0,
        source="CCD",
        source_detail=f"Canonical Claims Dataset ingest_id={ingest_id}",
        metadata={
            "ingest_id": ingest_id,
            "source_files": list(getattr(ccd, "source_files", [])),
            "content_hash": ccd.content_hash() if hasattr(ccd, "content_hash")
                            else None,
        },
    ))
    return out


# ── Merge helpers (priority order) ──────────────────────────────────

def merge_observed_sources(
    *,
    override: Optional[Mapping[str, float]] = None,
    ccd: Optional[Mapping[str, ObservedMetric]] = None,
    partner_yaml: Optional[Mapping[str, ObservedMetric]] = None,
    predicted: Optional[Mapping[str, ObservedMetric]] = None,
) -> Dict[str, ObservedMetric]:
    """Merge the four sources into a single observed-metrics dict,
    applying the priority order from the spec.

    The caller passes raw-value dicts (override is usually a flat
    ``{key: float}`` — what analysts type in a form) or full
    ``ObservedMetric`` dicts (for CCD / YAML / predicted which already
    carry provenance). The result is a clean ``{key: ObservedMetric}``
    map ready for ``build_analysis_packet``.
    """
    out: Dict[str, ObservedMetric] = {}

    if predicted:
        for k, v in predicted.items():
            out[k] = _with_source(v, MetricSource.PREDICTED.value,
                                  default_confidence=CONFIDENCE_PREDICTED_FALLBACK)

    if partner_yaml:
        for k, v in partner_yaml.items():
            out[k] = _with_source(v, MetricSource.EXTRACTED.value,
                                  default_confidence=CONFIDENCE_PARTNER_YAML)

    if ccd:
        for k, v in ccd.items():
            out[k] = _with_source(v, MetricSource.CCD.value,
                                  default_confidence=CONFIDENCE_CCD)

    if override:
        for k, val in override.items():
            out[k] = ObservedMetric(
                value=float(val),
                source=MetricSource.OBSERVED.value,
                source_detail="analyst_override",
                confidence=CONFIDENCE_OVERRIDE,
            )

    return out


def _with_source(
    om: ObservedMetric, source: str, *, default_confidence: float,
) -> ObservedMetric:
    """Return a copy with ``source`` set — preserves existing
    confidence when present, substitutes ``default_confidence`` when
    the input's confidence is the dataclass default of 1.0 for tiers
    below OVERRIDE."""
    # If the caller already set a deliberate confidence (anything
    # other than 1.0), respect it; otherwise fill from the default.
    if om.confidence == 1.0 and source != MetricSource.CCD.value:
        conf = default_confidence
    else:
        conf = om.confidence
    return ObservedMetric(
        value=om.value, source=source, source_detail=om.source_detail,
        as_of_date=om.as_of_date, quality_flags=list(om.quality_flags),
        confidence=conf,
    )


def _collect_kpis(bundle: KPIBundle) -> List[KPIResult]:
    return [
        bundle.days_in_ar, bundle.first_pass_denial_rate,
        bundle.ar_aging_over_90, bundle.cost_to_collect,
        bundle.net_revenue_realization, bundle.lag_service_to_bill,
        bundle.lag_bill_to_cash,
    ]
