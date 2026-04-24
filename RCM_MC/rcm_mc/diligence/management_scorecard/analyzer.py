"""Team-level orchestrator.

Takes a roster of executives, scores each, aggregates into a
``ManagementReport`` with:

    - aggregate overall score (weighted by role importance —
      CEO + CFO drive more weight than CHRO)
    - red-flag roll-up across executives
    - EBITDA-bridge haircut recommendation (takes the CEO's /
      CFO's forecast-reliability haircut as the team-level signal
      when both are scored; falls back to whoever is scored)
    - summary narrative keyed off aggregate score
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .profile import Executive, Role
from .scorer import (
    DEFAULT_WEIGHTS, ExecutiveScore, RedFlag, score_executive,
)


# Role-level weight on the team-aggregate score. CEO + CFO are
# load-bearing for forecast + strategy; COO for operational
# delivery.  CCO/CMO/CHRO are supporting.
_ROLE_WEIGHT: Dict[Role, float] = {
    Role.CEO: 0.35,
    Role.CFO: 0.25,
    Role.COO: 0.20,
    Role.CCO: 0.08,
    Role.CMO: 0.07,
    Role.CHRO: 0.03,
    Role.OTHER: 0.02,
}


@dataclass
class BridgeHaircutInput:
    """Partner-facing recommendation that flows into the bridge.

    ``recommended_haircut_pct``: fraction to shave off management's
    stated FY1 EBITDA guidance. Typical: 0–25%.
    ``dollar_adjustment_usd``: ``guidance × haircut`` when guidance
    is supplied.
    """
    recommended_haircut_pct: float = 0.0
    dollar_adjustment_usd: Optional[float] = None
    source_executives: List[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ManagementReport:
    """Roster-level scorecard."""
    scores: List[ExecutiveScore] = field(default_factory=list)
    team_size: int = 0
    aggregate_overall: int = 0                # 0–100
    aggregate_confidence: str = "MEDIUM"
    red_flag_count: int = 0
    critical_flag_count: int = 0
    bridge_haircut: Optional[BridgeHaircutInput] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_size": self.team_size,
            "aggregate_overall": self.aggregate_overall,
            "aggregate_confidence": self.aggregate_confidence,
            "red_flag_count": self.red_flag_count,
            "critical_flag_count": self.critical_flag_count,
            "scores": [s.to_dict() for s in self.scores],
            "bridge_haircut": (
                self.bridge_haircut.to_dict()
                if self.bridge_haircut else None
            ),
            "summary": self.summary,
        }

    @property
    def has_critical_flags(self) -> bool:
        return self.critical_flag_count > 0


# ────────────────────────────────────────────────────────────────────
# Team aggregation
# ────────────────────────────────────────────────────────────────────

def _aggregate_confidence(confidences: List[str]) -> str:
    if not confidences:
        return "LOW"
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    avg = sum(rank[c] for c in confidences) / len(confidences)
    if avg >= 1.5:
        return "HIGH"
    if avg >= 0.8:
        return "MEDIUM"
    return "LOW"


def _compute_haircut(
    scores: List[ExecutiveScore],
    guidance_ebitda_usd: Optional[float],
) -> Optional[BridgeHaircutInput]:
    """CEO + CFO forecast-reliability haircuts dominate. Use
    max(ceo_haircut, cfo_haircut) when both present; else use
    whichever is supplied."""
    ceo_haircut: Optional[float] = None
    cfo_haircut: Optional[float] = None
    ceo_name: Optional[str] = None
    cfo_name: Optional[str] = None
    confidences: List[str] = []
    for s in scores:
        if s.guidance_haircut_pct is None:
            continue
        confidences.append(s.confidence)
        if s.executive.role == Role.CEO:
            ceo_haircut = s.guidance_haircut_pct
            ceo_name = s.executive.name
        elif s.executive.role == Role.CFO:
            cfo_haircut = s.guidance_haircut_pct
            cfo_name = s.executive.name

    candidates = [h for h in (ceo_haircut, cfo_haircut) if h is not None]
    if not candidates:
        return None
    haircut = max(candidates)
    sources = [n for n in (ceo_name, cfo_name) if n]
    dollar_adj: Optional[float] = None
    if guidance_ebitda_usd and guidance_ebitda_usd > 0:
        dollar_adj = guidance_ebitda_usd * haircut
    confidence = _aggregate_confidence(confidences)
    if haircut >= 0.15:
        narrative = (
            f"Apply {haircut*100:.0f}% haircut to FY1 EBITDA guidance. "
            f"CEO/CFO historical miss rate supports a material "
            f"downward adjustment; do NOT accept management's base case."
        )
    elif haircut >= 0.05:
        narrative = (
            f"Apply {haircut*100:.0f}% haircut to FY1 guidance — "
            f"modest management-reliability discount. Use the haircut "
            f"version as the bridge base case."
        )
    else:
        narrative = (
            f"Management has hit guidance reliably. No material "
            f"haircut required; treat FY1 base case as defensible."
        )
    return BridgeHaircutInput(
        recommended_haircut_pct=haircut,
        dollar_adjustment_usd=dollar_adj,
        source_executives=sources,
        confidence=confidence,
        narrative=narrative,
    )


def _summary_for(
    aggregate: int, n_critical: int, n_total_flags: int,
    haircut: Optional[BridgeHaircutInput],
) -> str:
    if n_critical > 0:
        base = (
            f"⚠ {n_critical} CRITICAL red flag"
            f"{'s' if n_critical != 1 else ''} across the executive "
            f"team. Partner reference calls and legal-review sign-off "
            f"are blocking items."
        )
    elif n_total_flags >= 3:
        base = (
            f"{n_total_flags} red flags flagged across the team. "
            f"Bundle these as open questions in the IC packet; "
            f"request partner sign-off before proceeding."
        )
    elif aggregate >= 80:
        base = (
            f"Team aggregate score {aggregate}/100 — strong. Management "
            f"is a thesis enabler, not a risk."
        )
    elif aggregate >= 60:
        base = (
            f"Team aggregate {aggregate}/100 — solid but not elite. "
            f"Mid-case EBITDA assumptions are defensible."
        )
    else:
        base = (
            f"Team aggregate {aggregate}/100 — material management "
            f"risk. Treat guidance skeptically and build an independent "
            f"bottom-up projection."
        )
    if haircut and haircut.recommended_haircut_pct >= 0.10:
        base += (
            f" Apply {haircut.recommended_haircut_pct*100:.0f}% haircut "
            f"to FY1 EBITDA guidance per CEO/CFO historical miss rate."
        )
    return base


def analyze_team(
    executives: Sequence[Executive],
    *,
    guidance_ebitda_usd: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> ManagementReport:
    """Score every executive + aggregate into a team report."""
    executives = list(executives)
    if not executives:
        return ManagementReport(
            scores=[], team_size=0, aggregate_overall=0,
            aggregate_confidence="LOW",
            summary="No executives supplied — partner reference diligence is load-bearing.",
        )

    scores = [score_executive(e, weights=weights) for e in executives]

    # Role-weighted aggregate
    total_w = 0.0
    weighted_sum = 0.0
    for s in scores:
        w = _ROLE_WEIGHT.get(s.executive.role, _ROLE_WEIGHT[Role.OTHER])
        total_w += w
        weighted_sum += s.overall * w
    aggregate = int(round(weighted_sum / total_w)) if total_w > 0 else 0

    # Red-flag roll-up
    all_flags: List[RedFlag] = []
    for s in scores:
        all_flags.extend(s.red_flags)
    n_flags = len(all_flags)
    n_critical = sum(1 for rf in all_flags if rf.severity == "CRITICAL")

    agg_confidence = _aggregate_confidence([s.confidence for s in scores])

    haircut = _compute_haircut(scores, guidance_ebitda_usd)
    summary = _summary_for(aggregate, n_critical, n_flags, haircut)

    return ManagementReport(
        scores=scores,
        team_size=len(executives),
        aggregate_overall=aggregate,
        aggregate_confidence=agg_confidence,
        red_flag_count=n_flags,
        critical_flag_count=n_critical,
        bridge_haircut=haircut,
        summary=summary,
    )
