"""Portfolio dashboard — aggregate view across multiple PartnerReviews.

Partners looking at the whole book want one place that answers:

- How many deals at each recommendation? (pipeline → close)
- Weighted-average investability + regime distribution.
- Which deals need attention (critical hits, red bands)?
- Sector / payer / state concentration.

This is the "desk view" — a single dashboard dict + markdown render.
Compatible with any PartnerReview from `partner_review.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import SEV_CRITICAL, SEV_HIGH
from .partner_review import PartnerReview


@dataclass
class PortfolioDashboard:
    n_deals: int
    recommendation_counts: Dict[str, int] = field(default_factory=dict)
    avg_investability: Optional[float] = None
    regime_counts: Dict[str, int] = field(default_factory=dict)
    posture_counts: Dict[str, int] = field(default_factory=dict)
    sector_counts: Dict[str, int] = field(default_factory=dict)
    state_counts: Dict[str, int] = field(default_factory=dict)
    deals_with_critical: List[str] = field(default_factory=list)
    deals_with_high_3plus: List[str] = field(default_factory=list)
    avg_stress_grade: Optional[str] = None
    partner_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_deals": self.n_deals,
            "recommendation_counts": dict(self.recommendation_counts),
            "avg_investability": self.avg_investability,
            "regime_counts": dict(self.regime_counts),
            "posture_counts": dict(self.posture_counts),
            "sector_counts": dict(self.sector_counts),
            "state_counts": dict(self.state_counts),
            "deals_with_critical": list(self.deals_with_critical),
            "deals_with_high_3plus": list(self.deals_with_high_3plus),
            "avg_stress_grade": self.avg_stress_grade,
            "partner_summary": self.partner_summary,
        }


def _avg_grade(grades: List[str]) -> Optional[str]:
    if not grades:
        return None
    rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1, "?": 0}
    score = sum(rank.get(g, 0) for g in grades) / len(grades)
    # Round back to nearest.
    for letter in ("A", "B", "C", "D", "F"):
        if score >= rank[letter] - 0.5:
            return letter
    return "F"


def build_portfolio_dashboard(
    reviews: List[PartnerReview],
) -> PortfolioDashboard:
    """Aggregate multiple PartnerReviews into a desk-view dashboard."""
    n = len(reviews)
    rec_counts: Dict[str, int] = {}
    regime_counts: Dict[str, int] = {}
    posture_counts: Dict[str, int] = {}
    sector_counts: Dict[str, int] = {}
    state_counts: Dict[str, int] = {}
    investabilities: List[float] = []
    grades: List[str] = []
    critical_ids: List[str] = []
    high_ids: List[str] = []

    for r in reviews:
        rec = r.narrative.recommendation
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
        regime = (r.regime or {}).get("regime")
        if regime:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        posture = (r.operating_posture or {}).get("posture")
        if posture:
            posture_counts[posture] = posture_counts.get(posture, 0) + 1
        ctx = r.context_summary or {}
        sector = ctx.get("hospital_type")
        if sector:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        state = ctx.get("state")
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
        inv = (r.investability or {}).get("score")
        if inv is not None:
            try:
                investabilities.append(float(inv))
            except (TypeError, ValueError):
                pass
        grade = (r.stress_scenarios or {}).get("robustness_grade")
        if grade:
            grades.append(grade)
        if any(h.severity == SEV_CRITICAL for h in r.heuristic_hits):
            critical_ids.append(r.deal_id or r.deal_name or "(unnamed)")
        high_count = sum(1 for h in r.heuristic_hits if h.severity == SEV_HIGH)
        if high_count >= 3:
            high_ids.append(r.deal_id or r.deal_name or "(unnamed)")

    avg_inv = (sum(investabilities) / len(investabilities)
               if investabilities else None)
    avg_grade = _avg_grade(grades)

    if n == 0:
        summary = "No deals in portfolio."
    elif critical_ids:
        summary = (f"{len(critical_ids)} deal(s) with CRITICAL flag — "
                   "top priority for partner attention.")
    elif high_ids:
        summary = (f"{len(high_ids)} deal(s) with 3+ HIGH flags. "
                   "Schedule focused diligence review.")
    else:
        summary = (f"{n} deal(s) in portfolio — no critical flags, "
                   "standard ops cadence.")

    return PortfolioDashboard(
        n_deals=n,
        recommendation_counts=rec_counts,
        avg_investability=round(avg_inv, 2) if avg_inv is not None else None,
        regime_counts=regime_counts,
        posture_counts=posture_counts,
        sector_counts=sector_counts,
        state_counts=state_counts,
        deals_with_critical=critical_ids,
        deals_with_high_3plus=high_ids,
        avg_stress_grade=avg_grade,
        partner_summary=summary,
    )


def render_portfolio_dashboard_markdown(
    dashboard: PortfolioDashboard,
) -> str:
    lines = [
        "# Portfolio dashboard",
        "",
        f"**Deals:** {dashboard.n_deals}  ",
        f"**Avg investability:** {dashboard.avg_investability or 'n/a'}  ",
        f"**Avg stress grade:** {dashboard.avg_stress_grade or 'n/a'}",
        "",
        f"_{dashboard.partner_summary}_",
        "",
        "## Recommendation mix",
    ]
    for rec, n in sorted(dashboard.recommendation_counts.items(),
                         key=lambda kv: -kv[1]):
        lines.append(f"- {rec}: {n}")
    lines.extend(["", "## Regime mix"])
    for regime, n in sorted(dashboard.regime_counts.items(),
                            key=lambda kv: -kv[1]):
        lines.append(f"- {regime}: {n}")
    lines.extend(["", "## Posture mix"])
    for posture, n in sorted(dashboard.posture_counts.items(),
                             key=lambda kv: -kv[1]):
        lines.append(f"- {posture}: {n}")
    lines.extend(["", "## Sector concentration"])
    for sector, n in sorted(dashboard.sector_counts.items(),
                            key=lambda kv: -kv[1]):
        lines.append(f"- {sector}: {n}")
    if dashboard.deals_with_critical:
        lines.extend(["", "## Deals with CRITICAL flags", ""])
        for d in dashboard.deals_with_critical:
            lines.append(f"- {d}")
    if dashboard.deals_with_high_3plus:
        lines.extend(["", "## Deals with ≥ 3 HIGH flags", ""])
        for d in dashboard.deals_with_high_3plus:
            lines.append(f"- {d}")
    return "\n".join(lines)
