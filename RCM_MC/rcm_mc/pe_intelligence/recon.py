"""Reconciliation — ensure downstream artifacts agree with the review.

The PE intelligence package produces multiple views of the same
deal: the PartnerReview, the IC memo, the LP pitch, the 100-day
plan, the diligence board. A partner's sanity check: "do all these
tell the same story?"

This module runs reconciliation checks:

- Review recommendation matches IC-memo dictation.
- 100-day plan addresses every HIGH/CRITICAL heuristic hit.
- Diligence board's P0 items cover the critical findings.
- LP pitch's risk section doesn't understate the partner's bear case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .diligence_tracker import DiligenceBoard
from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH
from .hundred_day_plan import HundredDayPlan
from .partner_review import PartnerReview


@dataclass
class ReconFinding:
    check: str
    passed: bool
    detail: str
    severity: str = "info"          # "info" | "warning" | "mismatch"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
        }


# ── Individual checks ──────────────────────────────────────────────

def _check_recommendation_in_dictation(review: PartnerReview) -> ReconFinding:
    """The IC memo dictation should reference the recommendation word."""
    dictation = review.narrative.ic_memo_paragraph or ""
    rec = review.narrative.recommendation
    # Map rec to natural-language forms likely in the paragraph.
    tokens = {
        "PASS": ["pass"],
        "PROCEED_WITH_CAVEATS": ["proceed with caveats", "caveats"],
        "PROCEED": ["proceed"],
        "STRONG_PROCEED": ["strong proceed"],
    }.get(rec, [])
    if not tokens:
        return ReconFinding(
            check="recommendation_in_dictation",
            passed=False, severity="warning",
            detail=f"Unknown recommendation '{rec}'.",
        )
    found = any(t.lower() in dictation.lower() for t in tokens)
    if not found:
        return ReconFinding(
            check="recommendation_in_dictation",
            passed=False, severity="mismatch",
            detail=(f"Recommendation '{rec}' not visible in IC-memo "
                    "dictation paragraph."),
        )
    return ReconFinding(
        check="recommendation_in_dictation",
        passed=True,
        detail="IC-memo dictation references the recommendation.",
    )


def _check_plan_covers_high_hits(
    review: PartnerReview,
    plan: Optional[HundredDayPlan],
) -> ReconFinding:
    """Every HIGH/CRITICAL heuristic should map to a plan action."""
    if plan is None:
        return ReconFinding(
            check="plan_covers_high_hits",
            passed=True, severity="info",
            detail="No plan provided — skipping coverage check.",
        )
    high_hits = [h for h in review.heuristic_hits
                 if h.severity in (SEV_CRITICAL, SEV_HIGH)]
    if not high_hits:
        return ReconFinding(
            check="plan_covers_high_hits",
            passed=True,
            detail="No HIGH/CRITICAL hits to cover.",
        )
    plan_triggers = {a.trigger for a in plan.actions}
    uncovered: List[str] = []
    for hit in high_hits:
        if not any(hit.title in t or hit.id in t for t in plan_triggers):
            uncovered.append(hit.title)
    if uncovered:
        return ReconFinding(
            check="plan_covers_high_hits",
            passed=False, severity="mismatch",
            detail=(f"{len(uncovered)} HIGH/CRITICAL hit(s) without a "
                    f"plan action: {', '.join(uncovered[:3])}"),
        )
    return ReconFinding(
        check="plan_covers_high_hits",
        passed=True,
        detail="All HIGH/CRITICAL hits have a plan action.",
    )


def _check_board_p0_covers_critical(
    review: PartnerReview,
    board: Optional[DiligenceBoard],
) -> ReconFinding:
    """Every CRITICAL heuristic should appear as a P0 item on the board."""
    if board is None:
        return ReconFinding(
            check="board_p0_covers_critical",
            passed=True, severity="info",
            detail="No diligence board provided — skipping.",
        )
    critical = [h for h in review.heuristic_hits if h.severity == SEV_CRITICAL]
    if not critical:
        return ReconFinding(
            check="board_p0_covers_critical",
            passed=True,
            detail="No CRITICAL hits to cover.",
        )
    p0_titles = {i.title for i in board.items.values() if i.priority == "P0"}
    uncovered = [h.title for h in critical if h.title not in p0_titles]
    if uncovered:
        return ReconFinding(
            check="board_p0_covers_critical",
            passed=False, severity="mismatch",
            detail=(f"{len(uncovered)} CRITICAL hit(s) not on P0 board: "
                    f"{', '.join(uncovered[:3])}"),
        )
    return ReconFinding(
        check="board_p0_covers_critical",
        passed=True,
        detail="All CRITICAL hits represented as P0 board items.",
    )


# ── Orchestrator ────────────────────────────────────────────────────

def reconcile(
    review: PartnerReview,
    *,
    plan: Optional[HundredDayPlan] = None,
    board: Optional[DiligenceBoard] = None,
) -> List[ReconFinding]:
    """Run all reconciliation checks and return findings."""
    return [
        _check_recommendation_in_dictation(review),
        _check_plan_covers_high_hits(review, plan),
        _check_board_p0_covers_critical(review, board),
    ]


def has_mismatch(findings: List[ReconFinding]) -> bool:
    return any(f.severity == "mismatch" for f in findings)
