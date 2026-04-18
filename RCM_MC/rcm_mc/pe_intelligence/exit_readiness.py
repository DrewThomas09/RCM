"""Exit readiness — pre-exit-process checklist.

A deal is ready to exit when:
- Financial reporting is audit-ready (GAAP reviewed, 3 years).
- The RCM / operating story is visible in monthly numbers.
- KPIs are trending favorably in the last 2-4 quarters.
- Data room is organized by functional area.
- Quality of earnings hooks are identified (add-backs, one-times).
- Buyer-universe is mapped.

This module takes a :class:`HeuristicContext` plus an
:class:`ExitReadinessInputs` signal bag and produces a readiness
score (0-100) with per-dimension component findings.

The score is a partner-facing heuristic — a 70-point deal is
"good enough to soft-launch"; an 85-point deal is "hire the banker."
It is not a predictive model and not calibrated on historical data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import HeuristicContext


@dataclass
class ExitReadinessInputs:
    """Signal bag for exit-readiness scoring.

    All fields optional. Missing fields degrade the score but do not
    zero it — the idea is to reflect what we know today.
    """
    has_audited_financials_3yr: Optional[bool] = None
    has_trailing_12mo_kpis: Optional[bool] = None
    data_room_organized: Optional[bool] = None
    quality_of_earnings_prepared: Optional[bool] = None
    ebitda_trending_up_last_2q: Optional[bool] = None
    margin_trending_up_last_2q: Optional[bool] = None
    buyer_universe_mapped: Optional[bool] = None
    management_retained_through_close: Optional[bool] = None
    legal_litigation_clean: Optional[bool] = None
    ebitda_adj_recon_documented: Optional[bool] = None
    # Performance vs plan (fraction, e.g. 0.95 = missing plan by 5%).
    ebitda_vs_plan: Optional[float] = None
    revenue_vs_plan: Optional[float] = None


# ── Dimensions ───────────────────────────────────────────────────────

@dataclass
class ReadinessFinding:
    dimension: str
    score: int              # 0-100 contribution (clamp max at 100)
    weight: float           # 0.0-1.0, relative importance
    status: str             # "ready" | "partial" | "not_ready" | "unknown"
    commentary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "status": self.status,
            "commentary": self.commentary,
        }


def _yn_score(val: Optional[bool], ready_commentary: str,
              not_ready_commentary: str, unknown_commentary: str,
              dimension: str, weight: float) -> ReadinessFinding:
    if val is True:
        return ReadinessFinding(dimension=dimension, score=100, weight=weight,
                                status="ready", commentary=ready_commentary)
    if val is False:
        return ReadinessFinding(dimension=dimension, score=0, weight=weight,
                                status="not_ready", commentary=not_ready_commentary)
    return ReadinessFinding(dimension=dimension, score=50, weight=weight,
                            status="unknown", commentary=unknown_commentary)


def _performance_score(
    value: Optional[float],
    dimension: str,
    weight: float,
) -> ReadinessFinding:
    """Performance vs plan: 1.0 = on plan, 1.05 = beat, 0.95 = miss."""
    if value is None:
        return ReadinessFinding(
            dimension=dimension, score=50, weight=weight, status="unknown",
            commentary="Performance vs plan not reported.",
        )
    if value >= 1.03:
        return ReadinessFinding(
            dimension=dimension, score=100, weight=weight, status="ready",
            commentary=f"Beating plan by {(value-1)*100:.1f}% — buyer-positive.",
        )
    if value >= 0.97:
        return ReadinessFinding(
            dimension=dimension, score=80, weight=weight, status="ready",
            commentary=f"Tracking plan within {abs(value-1)*100:.1f}%.",
        )
    if value >= 0.92:
        return ReadinessFinding(
            dimension=dimension, score=55, weight=weight, status="partial",
            commentary=f"Missing plan by {(1-value)*100:.1f}% — buyers will question assumptions.",
        )
    return ReadinessFinding(
        dimension=dimension, score=15, weight=weight, status="not_ready",
        commentary=f"Missing plan by {(1-value)*100:.1f}% — materially compromises exit story.",
    )


# ── Score assembly ───────────────────────────────────────────────────

@dataclass
class ExitReadinessReport:
    score: int                      # 0-100 aggregate
    verdict: str                    # "ready" | "soft_launch" | "not_ready"
    findings: List[ReadinessFinding] = field(default_factory=list)
    headline: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
            "headline": self.headline,
            "partner_note": self.partner_note,
        }


def _verdict(score: int) -> str:
    if score >= 85:
        return "ready"
    if score >= 65:
        return "soft_launch"
    return "not_ready"


def _headline(score: int) -> str:
    if score >= 85:
        return "Deal is exit-ready. Engage banker."
    if score >= 65:
        return "Deal is soft-launch ready — shore up 2-3 gaps before formal process."
    return "Deal is not exit-ready. Address core gaps before hiring banker."


def _partner_note(score: int) -> str:
    if score >= 85:
        return "Move fast — the window doesn't stay open forever."
    if score >= 65:
        return "Fix the partials first. Banker meetings without clean data rooms burn calories."
    return "Pushing into exit at this readiness level is a discounted outcome. Don't."


def score_exit_readiness(
    ctx: HeuristicContext,
    inputs: ExitReadinessInputs,
) -> ExitReadinessReport:
    """Score a deal's exit readiness."""
    findings: List[ReadinessFinding] = []

    findings.append(_yn_score(
        inputs.has_audited_financials_3yr,
        "3-year GAAP-audited financials in hand.",
        "No 3-year audit trail — banker can't run competitive process.",
        "Audit status unknown.",
        dimension="audited_financials", weight=0.15,
    ))

    findings.append(_yn_score(
        inputs.has_trailing_12mo_kpis,
        "Monthly TTM KPIs maintained.",
        "Missing monthly KPI history — buyers can't see the trend.",
        "KPI reporting cadence unknown.",
        dimension="kpi_reporting", weight=0.10,
    ))

    findings.append(_yn_score(
        inputs.data_room_organized,
        "Data room is organized and complete.",
        "Data room not organized — will cost weeks of diligence.",
        "Data-room status unknown.",
        dimension="data_room", weight=0.10,
    ))

    findings.append(_yn_score(
        inputs.quality_of_earnings_prepared,
        "QoE prepared; add-backs and one-times documented.",
        "No QoE — buyer will commission their own and find surprises.",
        "QoE status unknown.",
        dimension="quality_of_earnings", weight=0.12,
    ))

    findings.append(_yn_score(
        inputs.ebitda_trending_up_last_2q,
        "EBITDA trending up in last 2 quarters.",
        "EBITDA flat or declining — buyers will discount the forecast.",
        "Trend unknown.",
        dimension="ebitda_trend", weight=0.12,
    ))

    findings.append(_yn_score(
        inputs.margin_trending_up_last_2q,
        "Margin trending up in last 2 quarters.",
        "Margin flat or declining — eroding operating-story credibility.",
        "Margin trend unknown.",
        dimension="margin_trend", weight=0.08,
    ))

    findings.append(_yn_score(
        inputs.buyer_universe_mapped,
        "Buyer universe mapped — strategic + sponsor list in hand.",
        "Buyer universe not mapped — process will start slow.",
        "Buyer mapping status unknown.",
        dimension="buyer_universe", weight=0.08,
    ))

    findings.append(_yn_score(
        inputs.management_retained_through_close,
        "Management committed to transition through close.",
        "Management uncertain — retention risk kills price.",
        "Management retention status unknown.",
        dimension="management_retention", weight=0.08,
    ))

    findings.append(_yn_score(
        inputs.legal_litigation_clean,
        "No material pending litigation.",
        "Material litigation pending — buyers require indemnity or escrow.",
        "Litigation status unknown.",
        dimension="legal_clean", weight=0.05,
    ))

    findings.append(_yn_score(
        inputs.ebitda_adj_recon_documented,
        "EBITDA adjustment reconciliation documented.",
        "Adjustment recon missing — buyers will re-cut EBITDA.",
        "EBITDA adjustment documentation unknown.",
        dimension="ebitda_adjustments", weight=0.04,
    ))

    findings.append(_performance_score(
        inputs.ebitda_vs_plan, dimension="ebitda_vs_plan", weight=0.05,
    ))
    findings.append(_performance_score(
        inputs.revenue_vs_plan, dimension="revenue_vs_plan", weight=0.03,
    ))

    total_weight = sum(f.weight for f in findings)
    if total_weight <= 0:
        total_weight = 1.0
    score = int(round(sum(f.score * f.weight for f in findings) / total_weight))
    # Clamp.
    score = max(0, min(score, 100))

    verdict = _verdict(score)
    return ExitReadinessReport(
        score=score,
        verdict=verdict,
        findings=findings,
        headline=_headline(score),
        partner_note=_partner_note(score),
    )
