"""Auditor view — produce a full decision-audit-trail for a review.

Regulators and LPs sometimes ask: "why did this deal get a `PASS`?"
or "how did you justify the exit multiple?" Six months later the
answer has to be reproducible from the record.

This module produces a structured decision audit trail for a
:class:`PartnerReview`. Every recommendation input — every fired
heuristic, every band check verdict, every narrative choice — is
catalogued with the trigger values that caused it.

Output is JSON-serializable, intended to be stored alongside the
packet in the audit log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from .partner_review import PartnerReview


@dataclass
class AuditEntry:
    source: str                         # "heuristic" | "band" | "narrative" | "context"
    ref: str                            # heuristic id / band metric / narrative key
    severity: str = ""                  # matches source's severity type
    value: Any = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        # Coerce value for JSON safety (lists/dicts pass through; others
        # become repr strings).
        try:
            json_safe_value = self.value
            import json
            json.dumps(json_safe_value)
        except Exception:
            json_safe_value = repr(self.value)
        return {
            "source": self.source,
            "ref": self.ref,
            "severity": self.severity,
            "value": json_safe_value,
            "explanation": self.explanation,
        }


@dataclass
class AuditTrail:
    deal_id: str
    deal_name: str
    generated_at: str
    recommendation: str
    entries: List[AuditEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "generated_at": self.generated_at,
            "recommendation": self.recommendation,
            "entries": [e.to_dict() for e in self.entries],
        }


def build_audit_trail(review: PartnerReview) -> AuditTrail:
    """Construct a comprehensive audit trail from a PartnerReview."""
    entries: List[AuditEntry] = []

    # Context snapshot — one entry per non-null context field.
    for key, value in (review.context_summary or {}).items():
        if value is None or value == {} or value == []:
            continue
        entries.append(AuditEntry(
            source="context", ref=key, value=value,
            explanation=f"Context input: {key}",
        ))

    # Band checks
    for band in review.reasonableness_checks:
        entries.append(AuditEntry(
            source="band",
            ref=band.metric,
            severity=band.verdict,
            value=band.observed,
            explanation=band.rationale,
        ))

    # Heuristic hits
    for hit in review.heuristic_hits:
        entries.append(AuditEntry(
            source="heuristic",
            ref=hit.id,
            severity=hit.severity,
            value=dict(hit.trigger_values),
            explanation=hit.finding,
        ))

    # Narrative decisions
    entries.append(AuditEntry(
        source="narrative",
        ref="recommendation",
        severity=review.narrative.recommendation,
        value=review.narrative.recommendation,
        explanation=review.narrative.recommendation_rationale,
    ))
    entries.append(AuditEntry(
        source="narrative",
        ref="headline",
        value=review.narrative.headline,
        explanation="Partner's bottom-line sentence.",
    ))
    entries.append(AuditEntry(
        source="narrative",
        ref="bull_case",
        value=review.narrative.bull_case,
    ))
    entries.append(AuditEntry(
        source="narrative",
        ref="bear_case",
        value=review.narrative.bear_case,
    ))

    return AuditTrail(
        deal_id=review.deal_id,
        deal_name=review.deal_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        recommendation=review.narrative.recommendation,
        entries=entries,
    )


def filter_entries(
    trail: AuditTrail,
    *,
    source: str = "",
    severity: str = "",
) -> List[AuditEntry]:
    """Filter the trail by source type and/or severity."""
    out = trail.entries
    if source:
        out = [e for e in out if e.source == source]
    if severity:
        out = [e for e in out if e.severity == severity]
    return list(out)


def summarize_trail(trail: AuditTrail) -> Dict[str, Any]:
    """Summary view: counts by source + top severity per category."""
    by_source: Dict[str, int] = {}
    for e in trail.entries:
        by_source[e.source] = by_source.get(e.source, 0) + 1
    return {
        "deal_id": trail.deal_id,
        "recommendation": trail.recommendation,
        "total_entries": len(trail.entries),
        "counts_by_source": by_source,
    }
