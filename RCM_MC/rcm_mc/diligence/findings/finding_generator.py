"""PE-readable diligence findings from analytics + data confidence.

Turns the analytics marts into a small set of conservative, evidence-
backed findings a PE associate can paste into a workstream (plan
§"DILIGENCE FINDING GENERATION"). Every finding carries evidence,
an estimated (never guaranteed) impact, a confidence band, tailored
follow-ups + document requests, and explicit limitations.

Language rules (enforced by tests): no "guaranteed EBITDA"; impacts are
"estimated" / "potentially preventable" / "requires validation".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..analytics.revenue_leakage import AnalyticsResult
from ..reconciliation.data_confidence import DataConfidenceReport

# Conservative thresholds.
_PREVENTABLE_PCT_OF_CHARGES = 0.02     # ≥2% of charges to surface
_PAYER_DENIAL_CONCENTRATION = 0.40     # one payer ≥40% of denial $
_PROVIDER_OUTLIER_MULTIPLE = 1.5       # ≥1.5× portfolio denial rate
_PROVIDER_MIN_CLAIMS = 10
_CONCENTRATION_RISK = 0.50             # top-1 ≥50% of paid
_MATCH_RATE_FLOOR = 0.70
_DATA_CONFIDENCE_FLOOR = 70
_SMALL_SAMPLE = 30


@dataclass
class Finding:
    finding_type: str
    title: str
    summary: str
    evidence: Dict[str, Any]
    estimated_impact_amount: Optional[float]
    confidence: str                       # "high" | "medium" | "low"
    recommended_follow_up: List[str] = field(default_factory=list)
    document_requests: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


_BASE_CAVEAT = (
    "Directional signal from a static claims snapshot; not guaranteed "
    "EBITDA. Recoverability depends on appeal history, payer contracts, "
    "AR aging, and management workflow — requires validation.")


def _confidence(data_score: int, claim_count: int) -> str:
    if claim_count < _SMALL_SAMPLE:
        return "low"
    if data_score >= 85:
        return "high"
    if data_score >= _DATA_CONFIDENCE_FLOOR:
        return "medium"
    return "low"


def generate_findings(
    analytics: AnalyticsResult,
    confidence_report: DataConfidenceReport,
    *,
    match_result: Optional[Any] = None,
) -> List[Finding]:
    out: List[Finding] = []
    t = analytics.totals
    n = t.claim_count
    base_conf = _confidence(confidence_report.score, n)
    charges = t.gross_charges or 0.0

    # 1 — Potentially preventable leakage.
    if t.potentially_preventable_leakage > 0 and charges > 0 and (
            t.potentially_preventable_leakage / charges >= _PREVENTABLE_PCT_OF_CHARGES):
        pct = t.potentially_preventable_leakage / charges
        out.append(Finding(
            finding_type="potentially_preventable_leakage",
            title="Potentially preventable revenue leakage identified",
            summary=(
                f"An estimated ${t.potentially_preventable_leakage:,.0f} "
                f"({pct * 100:.1f}% of gross charges) sits in likely- or "
                f"possibly-preventable denial categories (authorization, "
                f"coding, eligibility, timely filing). This is an upper-bound "
                f"estimate of operational recovery opportunity, subject to "
                f"validation."),
            evidence={
                "potentially_preventable_leakage": t.potentially_preventable_leakage,
                "gross_charges": charges,
                "denial_dollars": t.denial_dollars,
                "contractual_adjustments_excluded": t.contractual_adjustments,
            },
            estimated_impact_amount=t.potentially_preventable_leakage,
            confidence=base_conf,
            recommended_follow_up=[
                "Request appeal success rates by denial category (last 24 months).",
                "Request prior-authorization workflow + front-office staffing model.",
            ],
            document_requests=[
                "Denial log with initial vs final disposition + 835 reason codes.",
                "AR aging by payer; write-off policy.",
            ],
            limitations=[
                _BASE_CAVEAT,
                "Contractual adjustments are excluded; not counted as leakage.",
            ],
        ))

    # 2 — Payer denial concentration.
    payer_denial_total = sum(p.denial_dollars for p in analytics.by_payer)
    if payer_denial_total > 0 and analytics.by_payer:
        top = analytics.by_payer[0]
        share = top.denial_dollars / payer_denial_total
        if share >= _PAYER_DENIAL_CONCENTRATION and len(analytics.by_payer) >= 2:
            out.append(Finding(
                finding_type="payer_denial_concentration",
                title=f"Denial dollars are concentrated in {top.key}",
                summary=(
                    f"{top.key} accounts for {share * 100:.0f}% of denial "
                    f"dollars (${top.denial_dollars:,.0f}) while representing "
                    f"{top.pct_of_paid * 100:.0f}% of paid volume — a possible "
                    f"payer-specific authorization or documentation friction "
                    f"point, subject to validation."),
                evidence={
                    "payer": top.key, "denial_dollars": top.denial_dollars,
                    "share_of_denial_dollars": round(share, 4),
                    "pct_of_paid": top.pct_of_paid,
                    "denial_rate_dollars": top.denial_rate_dollars,
                },
                estimated_impact_amount=top.denial_dollars,
                confidence=base_conf,
                recommended_follow_up=[
                    f"Request {top.key} denial trend reports + appeal outcomes.",
                    "Request payer-specific authorization requirements.",
                ],
                document_requests=[
                    f"{top.key} contract + fee schedule.",
                    "Denial summary by payer + reason code (24 months).",
                ],
                limitations=[_BASE_CAVEAT],
            ))

    # 3 — Provider denial outlier.
    portfolio_rate = (t.denial_dollars / charges) if charges else 0.0
    for p in analytics.by_provider:
        if (p.claim_count >= _PROVIDER_MIN_CLAIMS and portfolio_rate > 0
                and p.denial_rate_dollars is not None
                and p.denial_rate_dollars >= _PROVIDER_OUTLIER_MULTIPLE * portfolio_rate):
            out.append(Finding(
                finding_type="provider_denial_outlier",
                title=f"Provider {p.key} is a denial-rate outlier",
                summary=(
                    f"Provider {p.key} shows a {p.denial_rate_dollars * 100:.1f}% "
                    f"denial rate by dollars vs a {portfolio_rate * 100:.1f}% "
                    f"snapshot average across {p.claim_count} claims — a "
                    f"possible coding/documentation or credentialing issue, "
                    f"subject to validation."),
                evidence={
                    "provider_npi": p.key, "claim_count": p.claim_count,
                    "denial_rate_dollars": p.denial_rate_dollars,
                    "portfolio_rate": round(portfolio_rate, 4),
                    "denial_dollars": p.denial_dollars,
                },
                estimated_impact_amount=p.denial_dollars,
                confidence=base_conf,
                recommended_follow_up=[
                    "Request coding/documentation audit for this provider.",
                    "Confirm credentialing status across payers.",
                ],
                document_requests=["Provider credentialing documentation; coding audit reports."],
                limitations=[_BASE_CAVEAT],
            ))
            break  # surface the single worst outlier, conservatively

    # 4 — Concentration risk (payer).
    if analytics.payer_concentration_top1_pct >= _CONCENTRATION_RISK and analytics.by_payer:
        top = max(analytics.by_payer, key=lambda g: g.pct_of_paid)
        out.append(Finding(
            finding_type="payer_concentration_risk",
            title="Payer concentration risk",
            summary=(
                f"{top.key} represents {top.pct_of_paid * 100:.0f}% of paid "
                f"dollars — a concentration risk if reimbursement terms or the "
                f"relationship change."),
            evidence={"payer": top.key, "pct_of_paid": top.pct_of_paid},
            estimated_impact_amount=None,
            confidence=base_conf,
            recommended_follow_up=["Request payer mix by month; contract renewal calendar."],
            document_requests=["Top payer contracts + renewal dates."],
            limitations=[_BASE_CAVEAT],
        ))

    # 5 — Low 837<->835 match rate.
    match_pct = confidence_report.metrics.get("submitted_matched_pct")
    if match_pct is not None and match_pct < _MATCH_RATE_FLOOR:
        out.append(Finding(
            finding_type="low_match_rate",
            title="Low submitted-to-remittance match rate",
            summary=(
                f"Only {match_pct * 100:.0f}% of submitted claims matched to "
                f"remittance records. Financial conclusions are limited to the "
                f"matched subset; the gap may reflect missing files or data "
                f"quality, not necessarily lost revenue."),
            evidence={"submitted_matched_pct": match_pct},
            estimated_impact_amount=None,
            confidence="low",
            recommended_follow_up=["Request the complete 835 remittance set for the period."],
            document_requests=["Full 835 remittance files matching the submitted 837 window."],
            limitations=["A low match rate is a data-completeness issue, not a leakage finding."],
        ))

    # 6 — Weak data quality.
    if confidence_report.score < _DATA_CONFIDENCE_FLOOR:
        out.append(Finding(
            finding_type="weak_data_quality",
            title="Data quality limits conclusions",
            summary=(
                f"Data Confidence Score is {confidence_report.score}/100. Treat "
                f"all downstream figures as directional pending better data."),
            evidence={"data_confidence_score": confidence_report.score,
                      "issue_count": len(confidence_report.issues)},
            estimated_impact_amount=None,
            confidence="low",
            recommended_follow_up=["Request cleaner exports for the flagged gaps."],
            document_requests=[],
            limitations=["Findings derived from low-confidence data require re-validation."],
        ))

    return out
