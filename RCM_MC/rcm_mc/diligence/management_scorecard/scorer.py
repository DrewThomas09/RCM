"""Per-executive scoring — deterministic, hand-calibrated.

Each of the four dimensions produces a 0–100 score plus a named
reason string the UI surfaces inline. The overall score is a
weighted average, with a red-flag override that clips to 40 when
any single dimension is below 30 — partners need to SEE that
the executive has at least one structural problem, not have it
averaged away.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .profile import (
    ComplevelBand, Executive, ForecastHistory, PriorRole, Role,
)


# Default weighting — partner-adjustable.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "forecast_reliability": 0.35,
    "comp_structure": 0.20,
    "tenure": 0.15,
    "prior_role_reputation": 0.30,
}


# Outcome → reputation score mapping.
_OUTCOME_SCORE: Dict[str, int] = {
    "STRONG_EXIT": 100,
    "STRONG_PUBLIC": 95,
    "IN_PROGRESS": 60,
    "DELISTED": 30,
    "DISTRESSED_SALE": 15,
    "CHAPTER_11": 10,
    "BANKRUPTCY": 0,
    "UNKNOWN": 50,            # neutral prior
}


@dataclass
class RedFlag:
    """One named concern the partner should ask about."""
    dimension: str                 # forecast / comp / tenure / prior
    severity: str                  # LOW / MEDIUM / HIGH / CRITICAL
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ExecutiveScore:
    """Scored output for one executive."""
    executive: Executive
    # Dimension scores
    forecast_reliability: int       # 0–100
    comp_structure: int             # 0–100
    tenure: int                     # 0–100
    prior_role_reputation: int      # 0–100
    # Overall
    overall: int                    # weighted average, red-flag-clipped
    # Named reasons per dimension
    forecast_reason: str
    comp_reason: str
    tenure_reason: str
    prior_reason: str
    # Aggregated concerns
    red_flags: List[RedFlag] = field(default_factory=list)
    # Data-driven haircut recommendation on forecast guidance
    guidance_haircut_pct: Optional[float] = None
    # Confidence — low when history is sparse, high when >= 3 periods
    confidence: str = "MEDIUM"      # LOW / MEDIUM / HIGH

    @property
    def is_red_flag(self) -> bool:
        return any(
            rf.severity in ("HIGH", "CRITICAL") for rf in self.red_flags
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive": self.executive.to_dict(),
            "forecast_reliability": self.forecast_reliability,
            "comp_structure": self.comp_structure,
            "tenure": self.tenure,
            "prior_role_reputation": self.prior_role_reputation,
            "overall": self.overall,
            "forecast_reason": self.forecast_reason,
            "comp_reason": self.comp_reason,
            "tenure_reason": self.tenure_reason,
            "prior_reason": self.prior_reason,
            "red_flags": [rf.to_dict() for rf in self.red_flags],
            "guidance_haircut_pct": self.guidance_haircut_pct,
            "confidence": self.confidence,
        }


# ────────────────────────────────────────────────────────────────────
# Dimension scorers
# ────────────────────────────────────────────────────────────────────

def score_forecast_reliability(
    history: List[ForecastHistory],
) -> Tuple[int, str, Optional[float]]:
    """Return (score_0_100, reason, recommended_haircut_pct).

    Haircut = average miss rate (capped at 25%) — i.e., how much a
    partner should discount FY1 guidance.
    """
    if not history:
        return (
            50,
            "No historical guidance-vs-actual supplied. Score defaults "
            "to neutral; partner reference calls are load-bearing here.",
            None,
        )
    misses = [
        h.miss_pct for h in history
        if h.miss_pct is not None
    ]
    if not misses:
        return (50, "Forecast history present but guidance = 0.", None)
    # Miss-rate metric: how much management OVER-shot guidance, on
    # average.  Beats (positive miss_pct) are clipped to 0 for the
    # reliability calc — management that beats guidance is reliable,
    # not punished.
    underperformance = [max(0.0, -m) for m in misses]
    avg_miss = statistics.mean(underperformance)
    max_miss = max(underperformance)
    # 0% miss → 100; 20%+ → 0; linear between.
    score = max(0, min(100, int(round(100 - (avg_miss / 0.20) * 100))))
    haircut = min(0.25, avg_miss)
    n = len(misses)
    if score >= 90:
        reason = (
            f"Management hit or beat guidance in {n} of "
            f"{n} periods (avg miss {avg_miss*100:+.1f}%). "
            f"Treat guidance as reliable."
        )
    elif score >= 70:
        reason = (
            f"Over {n} periods, management missed by an average "
            f"{avg_miss*100:.1f}% (worst miss {max_miss*100:.1f}%). "
            f"Apply {haircut*100:.0f}% haircut to FY1 guidance."
        )
    elif score >= 40:
        reason = (
            f"Forecast reliability is weak — average miss "
            f"{avg_miss*100:.1f}% across {n} periods. Haircut "
            f"{haircut*100:.0f}% of FY1 guidance and rebuild the "
            f"bottom-up model."
        )
    else:
        reason = (
            f"Management guidance is unreliable: average miss "
            f"{avg_miss*100:.1f}% · worst {max_miss*100:.1f}%. Treat "
            f"their forecast as a narrative, not a basis. Haircut "
            f"{haircut*100:.0f}% + build independent projection."
        )
    return score, reason, haircut


def score_comp_structure(exec_: Executive) -> Tuple[int, str]:
    """Return (score_0_100, reason).

    Scoring rubric:
      - Base comp band: P50 = baseline, P75 = -10, ABOVE_P90 = -40,
        BELOW_P50 = -15
      - Equity rollover: +15
      - Clawback provisions: +10
      - Performance-weighted bonus: +10
    """
    score = 60  # neutral starting point
    parts: List[str] = []
    band = exec_.comp_band
    if band == ComplevelBand.P50:
        score += 10
        parts.append("comp at specialty p50")
    elif band == ComplevelBand.P75:
        parts.append("comp at p75 (above market but defensible)")
    elif band == ComplevelBand.ABOVE_P90:
        score -= 30
        parts.append("comp above p90 — Stark-exposure / retention risk if restructured")
    elif band == ComplevelBand.BELOW_P50:
        score -= 10
        parts.append("comp below p50 — retention risk")
    else:
        parts.append("comp band unknown")

    if exec_.has_equity_rollover:
        score += 15
        parts.append("equity rollover aligns incentives")
    else:
        score -= 10
        parts.append("no equity rollover — incentive gap post-close")

    if exec_.has_clawback_provisions:
        score += 10
        parts.append("clawbacks in place")
    else:
        parts.append("no clawback provisions")

    if exec_.performance_weighted_bonus:
        score += 10
        parts.append("performance-weighted bonus")
    else:
        parts.append("flat bonus structure")

    score = max(0, min(100, score))
    return score, " · ".join(parts).capitalize() + "."


def score_tenure(exec_: Executive) -> Tuple[int, str]:
    """Return (score_0_100, reason).

    5+ years → 100, <1 year → 0, linear between. Years-at-facility
    takes precedence over years-in-role when supplied.
    """
    years = (
        exec_.years_at_facility
        if exec_.years_at_facility is not None
        else exec_.years_in_role
    )
    if years is None:
        return (50, "Tenure unknown — partner reference call required.")
    y = float(years)
    if y >= 5.0:
        return (100, f"{y:.1f} years at facility — stable.")
    if y <= 1.0:
        return (
            int(round(y * 20)),
            f"{y:.1f} years at facility — interim / recent appointment; "
            f"partner should ask why the prior executive left.",
        )
    # Linear: 1yr → 20, 5yr → 100
    score = int(round(20 + (y - 1.0) / 4.0 * 80))
    return (
        score,
        f"{y:.1f} years at facility — partially seasoned but short of "
        f"the 5-year stability benchmark.",
    )


def score_prior_role(
    exec_: Executive,
) -> Tuple[int, str, List[RedFlag]]:
    """Return (score_0_100, reason, red_flags).

    Multiple prior roles are scored on the weighted average of
    outcomes, weighted toward the MOST RECENT role (the signal
    degrades with time).
    """
    flags: List[RedFlag] = []
    if not exec_.prior_roles:
        return (
            50,
            "No prior-role history supplied — partner should request "
            "a CV + independently reference 2 prior employers.",
            flags,
        )
    # Sort most-recent first
    roles = sorted(
        exec_.prior_roles,
        key=lambda p: p.end_year or 0, reverse=True,
    )
    scores: List[float] = []
    weights: List[float] = []
    descriptions: List[str] = []
    for i, pr in enumerate(roles):
        outcome = (pr.outcome or "UNKNOWN").upper()
        raw = _OUTCOME_SCORE.get(outcome, 50)
        # Most recent role gets weight 1.0, older roles decay ×0.6
        weight = 0.6 ** i
        scores.append(raw)
        weights.append(weight)
        descriptions.append(
            f"{pr.employer} ({pr.role}) · "
            f"{outcome.replace('_', ' ').title()}"
        )
        # Red-flag hit: prior role ended in Ch. 11 or bankruptcy.
        if outcome in ("CHAPTER_11", "BANKRUPTCY"):
            flags.append(RedFlag(
                dimension="prior",
                severity="CRITICAL",
                detail=(
                    f"Prior role at {pr.employer} ended in "
                    f"{outcome.replace('_', ' ').title()}. Reference-"
                    f"check this period; ask partner whether this "
                    f"executive was accountable for the outcome."
                ),
            ))
        elif outcome in ("DISTRESSED_SALE", "DELISTED"):
            flags.append(RedFlag(
                dimension="prior",
                severity="HIGH",
                detail=(
                    f"Prior role at {pr.employer} ended in "
                    f"{outcome.replace('_', ' ').title()}. Partner "
                    f"reference required."
                ),
            ))
    weighted_score = (
        sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    )
    score = int(round(weighted_score))
    if score >= 80:
        reason = (
            f"Prior-role track record is strong: "
            f"{', '.join(descriptions[:3])}."
        )
    elif score >= 50:
        reason = (
            f"Prior-role record is mixed: "
            f"{', '.join(descriptions[:3])}."
        )
    else:
        reason = (
            f"Prior-role record carries red flags: "
            f"{', '.join(descriptions[:3])}."
        )
    return score, reason, flags


# ────────────────────────────────────────────────────────────────────
# Overall scorer
# ────────────────────────────────────────────────────────────────────

def _confidence_for(exec_: Executive) -> str:
    """Confidence on the score = breadth of data supplied."""
    periods = len(exec_.forecast_history)
    priors = len(exec_.prior_roles)
    if periods >= 3 and priors >= 2:
        return "HIGH"
    if periods >= 1 or priors >= 1:
        return "MEDIUM"
    return "LOW"


def score_executive(
    exec_: Executive,
    *,
    weights: Optional[Dict[str, float]] = None,
) -> ExecutiveScore:
    """Compute the full scorecard for one executive."""
    weights = weights or DEFAULT_WEIGHTS

    f_score, f_reason, haircut = score_forecast_reliability(
        exec_.forecast_history,
    )
    c_score, c_reason = score_comp_structure(exec_)
    t_score, t_reason = score_tenure(exec_)
    p_score, p_reason, prior_flags = score_prior_role(exec_)

    # Weighted average
    total_weight = sum(weights.values()) or 1.0
    overall_raw = (
        f_score * weights.get("forecast_reliability", 0.35)
        + c_score * weights.get("comp_structure", 0.20)
        + t_score * weights.get("tenure", 0.15)
        + p_score * weights.get("prior_role_reputation", 0.30)
    ) / total_weight

    # Red-flag override: any dimension below 30 caps overall at 40
    # so partners see the structural problem instead of having it
    # averaged away.
    min_dim = min(f_score, c_score, t_score, p_score)
    if min_dim < 30:
        overall_raw = min(overall_raw, 40)

    red_flags: List[RedFlag] = list(prior_flags)
    # Named-dimension red flags
    if f_score < 40 and exec_.forecast_history:
        red_flags.append(RedFlag(
            dimension="forecast", severity="HIGH",
            detail=(
                f"Management forecast reliability is {f_score}/100 — "
                f"treat FY1 guidance with skepticism."
            ),
        ))
    if c_score < 30:
        red_flags.append(RedFlag(
            dimension="comp", severity="HIGH",
            detail=(
                f"Comp structure scores {c_score}/100 — either Stark "
                f"risk (above-FMV) or retention risk (below-FMV) "
                f"needs to be addressed at close."
            ),
        ))
    if t_score < 20 and exec_.years_at_facility is not None:
        red_flags.append(RedFlag(
            dimension="tenure", severity="MEDIUM",
            detail=(
                f"Executive has {exec_.years_at_facility} years at "
                f"facility — partner should understand why the "
                f"predecessor left."
            ),
        ))

    return ExecutiveScore(
        executive=exec_,
        forecast_reliability=f_score,
        comp_structure=c_score,
        tenure=t_score,
        prior_role_reputation=p_score,
        overall=int(round(overall_raw)),
        forecast_reason=f_reason,
        comp_reason=c_reason,
        tenure_reason=t_reason,
        prior_reason=p_reason,
        red_flags=red_flags,
        guidance_haircut_pct=haircut,
        confidence=_confidence_for(exec_),
    )
