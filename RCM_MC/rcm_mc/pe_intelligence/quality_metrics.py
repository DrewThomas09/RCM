"""Quality metrics — CMS Star, readmissions, HCAHPS → VBP $ impact.

Healthcare reimbursement is increasingly quality-linked:

- **CMS Star Rating** — 1..5 stars. Triggers VBP payment adjustments
  (~2% of Medicare revenue).
- **Readmission rate** — penalized under HRRP (up to 3% Medicare
  cut).
- **HCAHPS patient-experience scores** — linked to VBP and CMS Stars.
- **Hospital-acquired conditions (HAC)** — bottom-quartile get 1%
  Medicare cut under HAC Reduction Program.

This module scores quality metrics and estimates the $ impact of
penalty / bonus schedules on Medicare revenue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityInputs:
    cms_star_rating: Optional[float] = None        # 1..5
    readmission_percentile: Optional[float] = None  # 0..100 (lower is better)
    hcahps_percentile: Optional[float] = None       # 0..100 (higher is better)
    hac_program_bottom_quartile: Optional[bool] = None
    mortality_percentile: Optional[float] = None    # 0..100 (lower is better)
    annual_medicare_revenue: Optional[float] = None


@dataclass
class QualityImpact:
    metric: str
    observed: Any
    score: float                                    # 0..1
    estimated_payment_impact: float                 # $, negative = penalty
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "observed": self.observed,
            "score": self.score,
            "estimated_payment_impact": self.estimated_payment_impact,
            "partner_note": self.partner_note,
        }


@dataclass
class QualityProfile:
    per_metric: List[QualityImpact] = field(default_factory=list)
    composite_score: float = 0.0                    # 0..1
    total_payment_impact: float = 0.0               # $
    verdict: str = ""                               # leader / average / drag
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_metric": [m.to_dict() for m in self.per_metric],
            "composite_score": self.composite_score,
            "total_payment_impact": self.total_payment_impact,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


# ── Per-metric scorers ─────────────────────────────────────────────

def _score_stars(stars: Optional[float],
                 medicare_rev: Optional[float]) -> Optional[QualityImpact]:
    if stars is None:
        return None
    s = float(stars)
    # Score: linear 0..1 from 1-star (0) to 5-star (1).
    score = max(0.0, min(1.0, (s - 1) / 4))
    # VBP-like bands: 4+ get ~1% bonus, 2- get ~2% cut.
    if medicare_rev is None or medicare_rev <= 0:
        impact = 0.0
    elif s >= 4.0:
        impact = medicare_rev * 0.01
    elif s >= 3.0:
        impact = 0.0
    elif s >= 2.0:
        impact = -medicare_rev * 0.01
    else:
        impact = -medicare_rev * 0.02
    if s >= 4.0:
        note = "Top-quartile star rating — VBP bonus territory."
    elif s >= 3.0:
        note = "Average star rating — roughly payment-neutral."
    else:
        note = "Below-average stars — VBP penalty exposure."
    return QualityImpact(
        metric="cms_star_rating",
        observed=s,
        score=score,
        estimated_payment_impact=impact,
        partner_note=note,
    )


def _score_readmission(pct: Optional[float],
                       medicare_rev: Optional[float]) -> Optional[QualityImpact]:
    if pct is None:
        return None
    p = float(pct)
    # Lower is better — invert for the 0..1 score.
    score = max(0.0, min(1.0, (100 - p) / 100))
    # HRRP penalties up to 3% for worst-quartile hospitals.
    if medicare_rev is None or medicare_rev <= 0:
        impact = 0.0
    elif p >= 75:
        impact = -medicare_rev * 0.03
    elif p >= 50:
        impact = -medicare_rev * 0.015
    elif p >= 25:
        impact = -medicare_rev * 0.005
    else:
        impact = 0.0
    if p >= 75:
        note = "Worst-quartile readmissions — maximum HRRP penalty."
    elif p >= 50:
        note = "Above-median readmissions — partial HRRP penalty."
    else:
        note = "Below-median readmissions — no HRRP penalty."
    return QualityImpact(
        metric="readmission_percentile",
        observed=p,
        score=score,
        estimated_payment_impact=impact,
        partner_note=note,
    )


def _score_hcahps(pct: Optional[float],
                  medicare_rev: Optional[float]) -> Optional[QualityImpact]:
    if pct is None:
        return None
    p = float(pct)
    score = max(0.0, min(1.0, p / 100))
    # HCAHPS contributes ~25% of VBP score, so ~0.5% Medicare impact at
    # worst quartile.
    if medicare_rev is None or medicare_rev <= 0:
        impact = 0.0
    elif p >= 75:
        impact = medicare_rev * 0.005
    elif p >= 50:
        impact = 0.0
    elif p >= 25:
        impact = -medicare_rev * 0.002
    else:
        impact = -medicare_rev * 0.005
    note = ("Strong patient experience." if p >= 75
            else "Average patient experience." if p >= 50
            else "Below-average HCAHPS — VBP drag.")
    return QualityImpact(
        metric="hcahps_percentile",
        observed=p,
        score=score,
        estimated_payment_impact=impact,
        partner_note=note,
    )


def _score_hac(is_bottom: Optional[bool],
               medicare_rev: Optional[float]) -> Optional[QualityImpact]:
    if is_bottom is None:
        return None
    score = 0.30 if is_bottom else 0.80
    impact = 0.0
    if is_bottom and medicare_rev:
        impact = -medicare_rev * 0.01
    note = ("Bottom-quartile HAC — 1% Medicare cut." if is_bottom
            else "Not in HAC penalty zone.")
    return QualityImpact(
        metric="hac_program",
        observed=is_bottom,
        score=score,
        estimated_payment_impact=impact,
        partner_note=note,
    )


def _score_mortality(pct: Optional[float],
                     medicare_rev: Optional[float]) -> Optional[QualityImpact]:
    if pct is None:
        return None
    p = float(pct)
    score = max(0.0, min(1.0, (100 - p) / 100))
    # Mortality contributes to Stars but isn't directly penalized;
    # assume 0.2% impact from stars cascade on bad mortality.
    impact = 0.0
    if medicare_rev and p >= 75:
        impact = -medicare_rev * 0.003
    note = ("High mortality — drags Stars over time."
            if p >= 75 else "Mortality within peer range.")
    return QualityImpact(
        metric="mortality_percentile",
        observed=p,
        score=score,
        estimated_payment_impact=impact,
        partner_note=note,
    )


# ── Profile orchestrator ──────────────────────────────────────────

def analyze_quality_profile(inputs: QualityInputs) -> QualityProfile:
    """Score each quality metric + aggregate composite + $ impact."""
    scorers = [
        _score_stars(inputs.cms_star_rating, inputs.annual_medicare_revenue),
        _score_readmission(inputs.readmission_percentile,
                           inputs.annual_medicare_revenue),
        _score_hcahps(inputs.hcahps_percentile,
                      inputs.annual_medicare_revenue),
        _score_hac(inputs.hac_program_bottom_quartile,
                   inputs.annual_medicare_revenue),
        _score_mortality(inputs.mortality_percentile,
                         inputs.annual_medicare_revenue),
    ]
    per_metric = [s for s in scorers if s is not None]
    if not per_metric:
        return QualityProfile(
            verdict="unknown",
            partner_note="No quality metrics provided.",
        )
    composite = sum(m.score for m in per_metric) / len(per_metric)
    total_impact = sum(m.estimated_payment_impact for m in per_metric)

    if composite >= 0.75:
        verdict = "leader"
        note = ("Quality leader — VBP bonuses accrue. Retention and "
                "referral flywheel helps the ramp.")
    elif composite >= 0.50:
        verdict = "average"
        note = "Quality in the middle of the pack. No tailwind, no drag."
    else:
        verdict = "drag"
        note = ("Quality drags reimbursement. VBP and HRRP penalties "
                "aggregate to a measurable revenue hit.")

    return QualityProfile(
        per_metric=per_metric,
        composite_score=round(composite, 4),
        total_payment_impact=round(total_impact, 2),
        verdict=verdict,
        partner_note=note,
    )


def render_quality_profile_markdown(profile: QualityProfile) -> str:
    lines = [
        "# Quality metrics profile",
        "",
        f"**Verdict:** {profile.verdict}  ",
        f"**Composite score:** {profile.composite_score:.2f}  ",
        f"**Total estimated payment impact:** ${profile.total_payment_impact:,.0f}",
        "",
        f"_{profile.partner_note}_",
        "",
        "| Metric | Observed | Score | Payment impact |",
        "|---|---:|---:|---:|",
    ]
    for m in profile.per_metric:
        lines.append(
            f"| {m.metric} | {m.observed} | {m.score:.2f} | "
            f"${m.estimated_payment_impact:,.0f} |"
        )
    return "\n".join(lines)
