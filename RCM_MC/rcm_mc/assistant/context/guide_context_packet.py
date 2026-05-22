"""PEdesk Guide context-packet builder (read-only).

Assembles, for a given route, every piece of *structured* context the
future PEdesk Guide assistant needs to explain the page: the page
context, the metric and data-source contexts it links to, deterministic
suggested questions, the read-only behavioral policy, known limitations,
and an honest quality grade.

This layer reads the existing registries and lookup helpers only. It
modifies nothing, runs no model, performs no RAG, persists no memory,
and makes no recommendation. It never invents formulas or data lineage —
anything it cannot resolve is recorded in ``missing_context_notes``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .get_data_source_context import get_data_source_context
from .get_metric_context import get_metric_context
from .get_page_context import get_page_context
from .guide_prompt_policy import policy_as_dict
from .suggested_questions import get_suggested_questions_for_page
from .types import (
    DataSourceContext,
    FormulaConfidence,
    MetricContext,
    PageContext,
    SourceConfidence,
)

_NEEDS = "Needs source documentation."

# context_quality vocabulary
QUALITY_STRONG = "strong"
QUALITY_PARTIAL = "partial"
QUALITY_PLACEHOLDER = "placeholder"
QUALITY_MISSING = "missing"

_FALLBACK = "No PEdesk Guide context has been documented for this page yet."

# Core fields that, when undocumented, signal a placeholder-grade page.
_CORE_FIELDS = (
    "outputs",
    "key_metrics",
    "data_sources",
    "model_logic_summary",
    "diligence_use_cases",
)


@dataclass
class GuideContextPacket:
    """All structured context the Guide needs to explain one page."""

    route: str
    normalized_route: str
    found_page_context: bool
    page_context: Optional[PageContext]
    metric_contexts: List[MetricContext]
    data_source_contexts: List[DataSourceContext]
    suggested_questions: List[str]
    read_only_policy: Dict[str, object]
    known_limitations: List[str]
    context_quality: str
    missing_context_notes: List[str] = field(default_factory=list)
    fallback_message: Optional[str] = None


def _field_is_missing(value: object) -> bool:
    """True when a context field is empty or still says it needs docs."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or _NEEDS in value
    if isinstance(value, (list, tuple)):
        if not value:
            return True
        return all(_field_is_missing(v) for v in value)
    return False


def _resolve_metrics(
    ctx: PageContext,
) -> Tuple[List[MetricContext], List[str]]:
    """Resolve metric contexts from explicit metric_ids, else conservative
    label matching against key_metrics. Returns (contexts, notes)."""
    contexts: List[MetricContext] = []
    notes: List[str] = []
    seen = set()

    metric_ids = list(getattr(ctx, "metric_ids", None) or [])
    if metric_ids:
        for mid in metric_ids:
            r = get_metric_context(mid)
            if r.found and r.context and r.metric_id not in seen:
                contexts.append(r.context)
                seen.add(r.metric_id)
            elif not r.found:
                notes.append(
                    f"Linked metric id '{mid}' is not in the metric registry."
                )
        return contexts, notes

    # No explicit links — try conservative matching from the page's
    # human-readable key_metrics labels (never guess beyond a registered
    # alias; a miss is recorded, not invented).
    for label in (ctx.key_metrics or []):
        if not label or label == _NEEDS:
            continue
        r = get_metric_context(label)
        if r.found and r.context and r.metric_id not in seen:
            contexts.append(r.context)
            seen.add(r.metric_id)
        elif not r.found:
            notes.append(
                f"Key metric '{label}' could not be matched to a documented "
                "metric."
            )

    if not contexts:
        notes.append("No metric contexts could be linked for this page.")
    return contexts, notes


def _resolve_sources(
    ctx: PageContext,
) -> Tuple[List[DataSourceContext], List[str]]:
    """Resolve data-source contexts from explicit data_source_ids, else
    conservative label matching against data_sources."""
    contexts: List[DataSourceContext] = []
    notes: List[str] = []
    seen = set()

    source_ids = list(getattr(ctx, "data_source_ids", None) or [])
    if source_ids:
        for sid in source_ids:
            r = get_data_source_context(sid)
            if r.found and r.context and r.source_id not in seen:
                contexts.append(r.context)
                seen.add(r.source_id)
            elif not r.found:
                notes.append(
                    f"Linked data-source id '{sid}' is not in the data-source "
                    "registry."
                )
        return contexts, notes

    for label in (ctx.data_sources or []):
        if not label or label == _NEEDS:
            continue
        r = get_data_source_context(label)
        if r.found and r.context and r.source_id not in seen:
            contexts.append(r.context)
            seen.add(r.source_id)
        elif not r.found:
            notes.append(
                f"Data source '{label}' could not be matched to a documented "
                "source."
            )

    if not contexts:
        notes.append("No data-source contexts could be linked for this page.")
    return contexts, notes


def _major_fields_missing(ctx: PageContext) -> bool:
    missing = sum(
        1 for name in _CORE_FIELDS if _field_is_missing(getattr(ctx, name, None))
    )
    return missing >= 3


def _compute_quality(
    ctx: PageContext,
    metrics: List[MetricContext],
    sources: List[DataSourceContext],
) -> str:
    has_linked_context = bool(metrics or sources)
    sc = ctx.source_confidence

    if sc == SourceConfidence.NEEDS_VALIDATION:
        return QUALITY_PLACEHOLDER
    if (
        sc in (SourceConfidence.DOCUMENTED, SourceConfidence.INFERRED_FROM_PAGE)
        and has_linked_context
    ):
        return QUALITY_STRONG
    if _major_fields_missing(ctx):
        return QUALITY_PLACEHOLDER
    return QUALITY_PARTIAL


def _known_limitations(
    ctx: PageContext, metrics: List[MetricContext]
) -> List[str]:
    lims = [l for l in (ctx.limitations or []) if l and l != _NEEDS]
    if any(
        m.formula_confidence == FormulaConfidence.NEEDS_VALIDATION
        for m in metrics
    ):
        note = "Some formulas need source documentation."
        if note not in lims:
            lims.append(note)
    return lims


def _missing_notes(
    ctx: PageContext,
    resolution_notes: List[str],
) -> List[str]:
    notes = list(resolution_notes)
    if _field_is_missing(ctx.model_logic_summary):
        notes.append("Model logic / mechanics need source documentation.")
    if ctx.source_confidence == SourceConfidence.NEEDS_VALIDATION:
        notes.append(
            "Page context is a placeholder awaiting source validation."
        )
    return notes


def build_guide_context_packet(route: str) -> GuideContextPacket:
    """Assemble the read-only Guide context packet for ``route``."""
    result = get_page_context(route)
    normalized = result.normalized_route
    ctx = result.context
    policy = policy_as_dict()
    questions = get_suggested_questions_for_page(ctx)

    if ctx is None:
        return GuideContextPacket(
            route=route,
            normalized_route=normalized,
            found_page_context=False,
            page_context=None,
            metric_contexts=[],
            data_source_contexts=[],
            suggested_questions=questions,
            read_only_policy=policy,
            known_limitations=[],
            context_quality=QUALITY_MISSING,
            missing_context_notes=[
                "No PEdesk Guide page context is documented for this route."
            ],
            fallback_message=result.fallback_message or _FALLBACK,
        )

    metric_contexts, metric_notes = _resolve_metrics(ctx)
    data_source_contexts, source_notes = _resolve_sources(ctx)

    return GuideContextPacket(
        route=route,
        normalized_route=normalized,
        found_page_context=True,
        page_context=ctx,
        metric_contexts=metric_contexts,
        data_source_contexts=data_source_contexts,
        suggested_questions=questions,
        read_only_policy=policy,
        known_limitations=_known_limitations(ctx, metric_contexts),
        context_quality=_compute_quality(
            ctx, metric_contexts, data_source_contexts
        ),
        missing_context_notes=_missing_notes(
            ctx, metric_notes + source_notes
        ),
        fallback_message=None,
    )


def summarize_context_packet(packet: GuideContextPacket) -> str:
    """Compact human-readable dump of a packet (debugging only — NOT the
    Guide's eventual answer)."""
    lines = ["PEdesk Guide context packet"]
    lines.append(f"Route: {packet.normalized_route}")
    title = packet.page_context.title if packet.page_context else "(no documented context)"
    lines.append(f"Page: {title}")
    lines.append(f"Quality: {packet.context_quality}")

    metric_ids = [m.metric_id for m in packet.metric_contexts]
    source_ids = [s.source_id for s in packet.data_source_contexts]
    lines.append("Metrics: " + (", ".join(metric_ids) if metric_ids else "(none)"))
    lines.append(
        "Data sources: " + (", ".join(source_ids) if source_ids else "(none)")
    )

    if packet.known_limitations:
        lines.append("Limitations:")
        lines.extend(f"- {l}" for l in packet.known_limitations)

    if packet.suggested_questions:
        lines.append("Suggested questions:")
        lines.extend(f"- {q}" for q in packet.suggested_questions)

    if packet.fallback_message:
        lines.append(f"Note: {packet.fallback_message}")

    return "\n".join(lines)


def _page_context_to_dict(ctx: PageContext) -> Dict[str, object]:
    return {
        "route": ctx.route,
        "title": ctx.title,
        "category": ctx.category.value,
        "short_description": ctx.short_description,
        "primary_purpose": ctx.primary_purpose,
        "intended_users": list(ctx.intended_users),
        "common_questions": list(ctx.common_questions),
        "inputs": list(ctx.inputs),
        "outputs": list(ctx.outputs),
        "key_metrics": list(ctx.key_metrics),
        "data_sources": list(ctx.data_sources),
        "model_logic_summary": ctx.model_logic_summary,
        "why_it_matters": ctx.why_it_matters,
        "diligence_use_cases": list(ctx.diligence_use_cases),
        "interpretation_guidance": list(ctx.interpretation_guidance),
        "limitations": list(ctx.limitations),
        "related_routes": list(ctx.related_routes),
        "source_confidence": ctx.source_confidence.value,
        "data_confidence": ctx.data_confidence.value,
        "notes_for_assistant": list(ctx.notes_for_assistant),
    }


def _metric_context_to_dict(m: MetricContext) -> Dict[str, object]:
    return {
        "metric_id": m.metric_id,
        "label": m.label,
        "definition": m.definition,
        "formula": m.formula,
        "formula_confidence": m.formula_confidence.value,
        "why_it_matters": m.why_it_matters,
        "diligence_interpretation": m.diligence_interpretation,
        "caveats": list(m.caveats),
    }


def _data_source_context_to_dict(s: DataSourceContext) -> Dict[str, object]:
    return {
        "source_id": s.source_id,
        "label": s.label,
        "description": s.description,
        "source_type": s.source_type.value,
        "update_cadence": s.update_cadence,
        "freshness_lag": s.freshness_lag,
        "used_for": list(s.used_for),
        "strengths": list(s.strengths),
        "limitations": list(s.limitations),
        "provenance_notes": s.provenance_notes,
    }


def packet_to_dict(packet: GuideContextPacket) -> Dict[str, object]:
    """JSON-safe dict view of a GuideContextPacket.

    Enums become their string values; dataclasses become plain dicts.
    Only the fields the debug endpoint exposes are included — internal
    link ids and the full dataclass surface are intentionally trimmed.
    Pure transform; reads nothing and mutates nothing.
    """
    return {
        "route": packet.route,
        "normalized_route": packet.normalized_route,
        "found_page_context": packet.found_page_context,
        "context_quality": packet.context_quality,
        "fallback_message": packet.fallback_message,
        "page_context": (
            _page_context_to_dict(packet.page_context)
            if packet.page_context is not None
            else None
        ),
        "metric_contexts": [
            _metric_context_to_dict(m) for m in packet.metric_contexts
        ],
        "data_source_contexts": [
            _data_source_context_to_dict(s) for s in packet.data_source_contexts
        ],
        "suggested_questions": list(packet.suggested_questions),
        "read_only_policy": packet.read_only_policy,
        "known_limitations": list(packet.known_limitations),
        "missing_context_notes": list(packet.missing_context_notes),
    }
