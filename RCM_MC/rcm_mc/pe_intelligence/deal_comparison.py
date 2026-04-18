"""Deal comparison — side-by-side analysis of two PartnerReviews.

Partners frequently evaluate competing deals head-to-head: "which
one gets the check this quarter?" This module compares two reviews
across every PE-intel dimension and surfaces:

- Per-metric deltas (IRR, MOIC, margin, leverage, stress grade).
- Recommendation divergence (one says PROCEED, the other PASS).
- Heuristic / red-flag overlap and uniqueness.
- A blended winner verdict + rationale.

The module is PartnerReview-first — the caller provides two reviews
and the module does the rest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .heuristics import SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .partner_review import PartnerReview


@dataclass
class ComparisonFinding:
    dimension: str
    left_value: Any
    right_value: Any
    winner: str                          # "left" | "right" | "tie" | "n/a"
    commentary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "winner": self.winner,
            "commentary": self.commentary,
        }


@dataclass
class ComparisonResult:
    left_deal_id: str
    right_deal_id: str
    findings: List[ComparisonFinding] = field(default_factory=list)
    left_wins: int = 0
    right_wins: int = 0
    ties: int = 0
    overall_winner: str = "tie"
    overall_commentary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "left_deal_id": self.left_deal_id,
            "right_deal_id": self.right_deal_id,
            "findings": [f.to_dict() for f in self.findings],
            "left_wins": self.left_wins,
            "right_wins": self.right_wins,
            "ties": self.ties,
            "overall_winner": self.overall_winner,
            "overall_commentary": self.overall_commentary,
        }


# ── Per-dimension comparators ───────────────────────────────────────

_HIGHER_IS_BETTER = {
    "projected_irr", "projected_moic", "ebitda_margin",
    "downside_pass_rate", "upside_capture_rate",
    "investability_score", "consolidation_play_score",
}
_LOWER_IS_BETTER = {
    "leverage_multiple", "days_in_ar", "denial_rate",
    "final_writeoff_rate", "n_critical_hits", "n_high_hits",
    "n_covenant_breaches",
}


def _compare_numeric(left: Optional[float], right: Optional[float],
                     dimension: str) -> ComparisonFinding:
    if left is None and right is None:
        return ComparisonFinding(
            dimension=dimension, left_value=None, right_value=None,
            winner="n/a", commentary="Neither value populated.",
        )
    if left is None:
        return ComparisonFinding(
            dimension=dimension, left_value=None, right_value=right,
            winner="right", commentary="Only right has a value.",
        )
    if right is None:
        return ComparisonFinding(
            dimension=dimension, left_value=left, right_value=None,
            winner="left", commentary="Only left has a value.",
        )
    if abs(left - right) < 1e-9:
        return ComparisonFinding(
            dimension=dimension, left_value=left, right_value=right,
            winner="tie", commentary="Equal.",
        )
    if dimension in _LOWER_IS_BETTER:
        winner = "left" if left < right else "right"
    else:
        winner = "left" if left > right else "right"
    return ComparisonFinding(
        dimension=dimension, left_value=left, right_value=right,
        winner=winner,
        commentary=f"Δ = {abs(left - right):.4f}",
    )


def _compare_grade(left: Optional[str], right: Optional[str]) -> ComparisonFinding:
    order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "?": 0, "": 0}
    l = order.get(left or "", 0)
    r = order.get(right or "", 0)
    if l == r:
        winner = "tie" if l > 0 else "n/a"
    else:
        winner = "left" if l > r else "right"
    return ComparisonFinding(
        dimension="stress_robustness_grade",
        left_value=left, right_value=right,
        winner=winner,
        commentary=f"{left or '?'} vs {right or '?'}",
    )


def _compare_recommendation(left: Optional[str],
                            right: Optional[str]) -> ComparisonFinding:
    order = {"PASS": 0, "PROCEED_WITH_CAVEATS": 1, "PROCEED": 2,
             "STRONG_PROCEED": 3}
    l = order.get(left or "", -1)
    r = order.get(right or "", -1)
    if l == r:
        return ComparisonFinding(
            dimension="recommendation", left_value=left, right_value=right,
            winner="tie" if l >= 0 else "n/a",
            commentary="Same recommendation.",
        )
    winner = "left" if l > r else "right"
    return ComparisonFinding(
        dimension="recommendation", left_value=left, right_value=right,
        winner=winner,
        commentary=f"{left} vs {right}",
    )


# ── Orchestrator ────────────────────────────────────────────────────

def compare_reviews(left: PartnerReview, right: PartnerReview) -> ComparisonResult:
    """Run every comparable dimension and return side-by-side findings."""
    findings: List[ComparisonFinding] = []

    # Context-level numeric comparisons.
    lc = left.context_summary or {}
    rc = right.context_summary or {}
    for dim in ("projected_irr", "projected_moic", "ebitda_margin",
                "leverage_multiple", "days_in_ar", "denial_rate",
                "final_writeoff_rate"):
        findings.append(_compare_numeric(lc.get(dim), rc.get(dim), dim))

    # Stress
    ls = left.stress_scenarios or {}
    rs = right.stress_scenarios or {}
    findings.append(_compare_numeric(ls.get("downside_pass_rate"),
                                     rs.get("downside_pass_rate"),
                                     "downside_pass_rate"))
    findings.append(_compare_grade(ls.get("robustness_grade"),
                                   rs.get("robustness_grade")))
    # Covenant-breach count is a lower-is-better so invert by using
    # n_covenant_breaches which is in _LOWER_IS_BETTER.
    findings.append(_compare_numeric(
        ls.get("n_covenant_breaches"),
        rs.get("n_covenant_breaches"),
        "n_covenant_breaches",
    ))

    # Investability score
    li = left.investability or {}
    ri = right.investability or {}
    findings.append(_compare_numeric(li.get("score"), ri.get("score"),
                                     "investability_score"))

    # Market structure
    lm = left.market_structure or {}
    rm = right.market_structure or {}
    findings.append(_compare_numeric(lm.get("consolidation_play_score"),
                                     rm.get("consolidation_play_score"),
                                     "consolidation_play_score"))

    # Severity counts
    lh = left.severity_counts() if hasattr(left, "severity_counts") else {}
    rh = right.severity_counts() if hasattr(right, "severity_counts") else {}
    findings.append(_compare_numeric(lh.get("CRITICAL", 0), rh.get("CRITICAL", 0),
                                     "n_critical_hits"))
    findings.append(_compare_numeric(lh.get("HIGH", 0), rh.get("HIGH", 0),
                                     "n_high_hits"))

    # Recommendation
    findings.append(_compare_recommendation(
        left.narrative.recommendation, right.narrative.recommendation,
    ))

    # Tally.
    l_wins = sum(1 for f in findings if f.winner == "left")
    r_wins = sum(1 for f in findings if f.winner == "right")
    ties = sum(1 for f in findings if f.winner == "tie")

    # Overall winner
    if l_wins > r_wins + 1:
        overall = "left"
    elif r_wins > l_wins + 1:
        overall = "right"
    else:
        overall = "tie"

    # Overall commentary
    name_left = left.deal_name or left.deal_id or "Deal L"
    name_right = right.deal_name or right.deal_id or "Deal R"
    if overall == "left":
        commentary = (f"{name_left} wins on balance ({l_wins} wins vs "
                      f"{r_wins}; {ties} ties).")
    elif overall == "right":
        commentary = (f"{name_right} wins on balance ({r_wins} wins vs "
                      f"{l_wins}; {ties} ties).")
    else:
        commentary = (f"Roughly tied — {name_left} {l_wins} / "
                      f"{name_right} {r_wins} / {ties} ties.")

    return ComparisonResult(
        left_deal_id=left.deal_id,
        right_deal_id=right.deal_id,
        findings=findings,
        left_wins=l_wins,
        right_wins=r_wins,
        ties=ties,
        overall_winner=overall,
        overall_commentary=commentary,
    )


def render_comparison_markdown(result: ComparisonResult) -> str:
    """Partner-friendly markdown comparison table."""
    lines = [
        f"# Deal Comparison: {result.left_deal_id} vs {result.right_deal_id}",
        "",
        f"**Verdict:** {result.overall_commentary}",
        "",
        "| Dimension | Left | Right | Winner |",
        "|---|---|---|---|",
    ]
    for f in result.findings:
        lv = _fmt(f.left_value)
        rv = _fmt(f.right_value)
        lines.append(f"| {f.dimension} | {lv} | {rv} | {f.winner} |")
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}" if abs(v) < 1 else f"{v:.2f}"
    return str(v)
