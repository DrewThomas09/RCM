"""Management team assessment.

Partners sign off on *teams*, not just businesses. Pre-close, the
management question is: "does this team win?" Post-close, it is:
"does this team execute the thesis?"

This module scores a management team across six dimensions, each
with a 0-100 component and partner-voice commentary. Output is a
:class:`ManagementScore` with composite, per-dimension findings, and
a recommendation on seat-adds / replacements.

Dimensions:
1. **CEO** — tenure, industry experience, operator vs finance background.
2. **CFO** — PE experience, LBO-close readiness.
3. **COO / operational depth** — does the operating bench exist?
4. **RCM / billing leadership** — named RCM owner; program experience.
5. **Clinical leadership** — CMO presence, quality track record.
6. **Incentive alignment** — equity rollover, options coverage of top 20.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ManagementInputs:
    """Signal bag for the assessment."""
    ceo_tenure_years: Optional[float] = None
    ceo_healthcare_years: Optional[float] = None
    ceo_pe_experience: Optional[bool] = None
    ceo_operator_background: Optional[bool] = None

    cfo_pe_experience: Optional[bool] = None
    cfo_tenure_years: Optional[float] = None
    cfo_lbo_close_experience: Optional[bool] = None

    coo_present: Optional[bool] = None
    operating_bench_depth: Optional[int] = None    # count of L2 leaders

    rcm_leader_named: Optional[bool] = None
    rcm_program_experience: Optional[bool] = None

    cmo_present: Optional[bool] = None
    quality_star_rating: Optional[float] = None

    equity_rollover_pct: Optional[float] = None    # fraction, e.g. 0.20
    top20_with_options_pct: Optional[float] = None


@dataclass
class DimensionScore:
    name: str
    score: int                            # 0-100
    status: str                           # "strong" | "adequate" | "weak" | "unknown"
    commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "status": self.status,
            "commentary": self.commentary,
        }


@dataclass
class ManagementScore:
    overall: int
    status: str                           # "strong" | "adequate" | "concerns" | "replace"
    dimensions: List[DimensionScore] = field(default_factory=list)
    recommendation: str = ""
    seat_adds: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "status": self.status,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "recommendation": self.recommendation,
            "seat_adds": list(self.seat_adds),
        }


# ── Scorers ─────────────────────────────────────────────────────────

def _ceo_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.ceo_tenure_years is not None:
        # 3-7 years is the sweet spot for sponsor-owned businesses.
        if 3 <= inputs.ceo_tenure_years <= 10:
            components.append(85)
        elif inputs.ceo_tenure_years < 1:
            components.append(40)
        elif inputs.ceo_tenure_years > 15:
            components.append(55)
        else:
            components.append(65)
    if inputs.ceo_healthcare_years is not None:
        components.append(95 if inputs.ceo_healthcare_years >= 10
                          else 70 if inputs.ceo_healthcare_years >= 5
                          else 50)
    if inputs.ceo_pe_experience is not None:
        components.append(90 if inputs.ceo_pe_experience else 55)
    if inputs.ceo_operator_background is not None:
        components.append(85 if inputs.ceo_operator_background else 60)

    if not components:
        return DimensionScore(name="ceo", score=50, status="unknown",
                              commentary="Insufficient CEO information.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if inputs.ceo_tenure_years is not None and inputs.ceo_tenure_years < 1:
        notes.append("CEO is new — transition risk.")
    if inputs.ceo_pe_experience is False:
        notes.append("CEO has no prior sponsor-backed experience — coach required.")
    if inputs.ceo_operator_background is False:
        notes.append("CEO is non-operator — partner with a strong COO.")
    commentary = (" ".join(notes) or
                  _default_commentary("CEO", status))
    return DimensionScore(name="ceo", score=score, status=status,
                          commentary=commentary)


def _cfo_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.cfo_pe_experience is not None:
        components.append(90 if inputs.cfo_pe_experience else 50)
    if inputs.cfo_tenure_years is not None:
        components.append(80 if 2 <= inputs.cfo_tenure_years <= 8 else 55)
    if inputs.cfo_lbo_close_experience is not None:
        components.append(95 if inputs.cfo_lbo_close_experience else 60)
    if not components:
        return DimensionScore(name="cfo", score=50, status="unknown",
                              commentary="Insufficient CFO information.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if inputs.cfo_pe_experience is False:
        notes.append("CFO lacks PE experience — covenant reporting discipline unknown.")
    if inputs.cfo_lbo_close_experience is False:
        notes.append("CFO hasn't closed an LBO before — expect onboarding cost.")
    commentary = (" ".join(notes) or _default_commentary("CFO", status))
    return DimensionScore(name="cfo", score=score, status=status, commentary=commentary)


def _operational_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.coo_present is not None:
        components.append(85 if inputs.coo_present else 35)
    if inputs.operating_bench_depth is not None:
        if inputs.operating_bench_depth >= 5:
            components.append(90)
        elif inputs.operating_bench_depth >= 3:
            components.append(70)
        elif inputs.operating_bench_depth >= 1:
            components.append(55)
        else:
            components.append(30)
    if not components:
        return DimensionScore(name="operational", score=50, status="unknown",
                              commentary="Operating bench depth unknown.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if inputs.coo_present is False:
        notes.append("No COO — operating thesis depends entirely on CEO bandwidth.")
    if (inputs.operating_bench_depth is not None
            and inputs.operating_bench_depth < 3):
        notes.append("Thin bench — single-point-of-failure risk at L2.")
    commentary = (" ".join(notes) or _default_commentary("Operating team", status))
    return DimensionScore(name="operational", score=score, status=status,
                          commentary=commentary)


def _rcm_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.rcm_leader_named is not None:
        components.append(85 if inputs.rcm_leader_named else 35)
    if inputs.rcm_program_experience is not None:
        components.append(90 if inputs.rcm_program_experience else 50)
    if not components:
        return DimensionScore(name="rcm_leadership", score=50, status="unknown",
                              commentary="RCM leadership status unknown.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if inputs.rcm_leader_named is False:
        notes.append("No named RCM owner — thesis at risk from day 1.")
    if inputs.rcm_program_experience is False:
        notes.append("RCM lead lacks program experience — operating partner assist needed.")
    commentary = (" ".join(notes) or _default_commentary("RCM leader", status))
    return DimensionScore(name="rcm_leadership", score=score, status=status,
                          commentary=commentary)


def _clinical_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.cmo_present is not None:
        components.append(85 if inputs.cmo_present else 45)
    if inputs.quality_star_rating is not None:
        s = float(inputs.quality_star_rating)
        if s >= 4.0:
            components.append(90)
        elif s >= 3.0:
            components.append(70)
        elif s >= 2.0:
            components.append(45)
        else:
            components.append(25)
    if not components:
        return DimensionScore(name="clinical", score=50, status="unknown",
                              commentary="Clinical leadership unknown.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if inputs.cmo_present is False:
        notes.append("No CMO — quality oversight depends on facility medical directors.")
    if (inputs.quality_star_rating is not None and
            inputs.quality_star_rating < 3.0):
        notes.append("Star rating below 3 — VBP penalty + reputational drag.")
    commentary = (" ".join(notes) or _default_commentary("Clinical leader", status))
    return DimensionScore(name="clinical", score=score, status=status,
                          commentary=commentary)


def _alignment_score(inputs: ManagementInputs) -> DimensionScore:
    components: List[int] = []
    if inputs.equity_rollover_pct is not None:
        r = float(inputs.equity_rollover_pct)
        if r > 1.5:
            r /= 100.0
        if r >= 0.20:
            components.append(90)
        elif r >= 0.10:
            components.append(70)
        elif r >= 0.05:
            components.append(55)
        else:
            components.append(35)
    if inputs.top20_with_options_pct is not None:
        p = float(inputs.top20_with_options_pct)
        if p > 1.5:
            p /= 100.0
        if p >= 0.80:
            components.append(90)
        elif p >= 0.50:
            components.append(70)
        else:
            components.append(45)
    if not components:
        return DimensionScore(name="alignment", score=50, status="unknown",
                              commentary="Incentive alignment unknown.")
    score = int(round(sum(components) / len(components)))
    status = _status_for(score)
    notes = []
    if (inputs.equity_rollover_pct is not None
            and float(inputs.equity_rollover_pct) < 0.05):
        notes.append("Low equity rollover — management is cashing out, not buying in.")
    if (inputs.top20_with_options_pct is not None
            and float(inputs.top20_with_options_pct) < 0.50):
        notes.append("Most of top-20 lack options — wide alignment is absent.")
    commentary = (" ".join(notes) or _default_commentary("Incentive alignment", status))
    return DimensionScore(name="alignment", score=score, status=status,
                          commentary=commentary)


def _status_for(score: int) -> str:
    if score >= 75:
        return "strong"
    if score >= 55:
        return "adequate"
    if score >= 30:
        return "weak"
    return "unknown"


def _default_commentary(name: str, status: str) -> str:
    return {
        "strong": f"{name} is a strength — underwrite at full credit.",
        "adequate": f"{name} is acceptable — watch for slippage post-close.",
        "weak": f"{name} is a concern — seat-add or replacement planning required.",
    }.get(status, f"{name} status unknown.")


# ── Composite ───────────────────────────────────────────────────────

_WEIGHTS = {
    "ceo": 0.25,
    "cfo": 0.15,
    "operational": 0.20,
    "rcm_leadership": 0.15,
    "clinical": 0.10,
    "alignment": 0.15,
}


def score_management(inputs: ManagementInputs) -> ManagementScore:
    """Score a management team across six dimensions + composite."""
    dims = [
        _ceo_score(inputs),
        _cfo_score(inputs),
        _operational_score(inputs),
        _rcm_score(inputs),
        _clinical_score(inputs),
        _alignment_score(inputs),
    ]
    overall = int(round(
        sum(d.score * _WEIGHTS.get(d.name, 0.0) for d in dims)
        / max(sum(_WEIGHTS.values()), 1e-9)
    ))
    # Composite status.
    if overall >= 80:
        status = "strong"
        rec = "Team is credible — fund as modeled."
    elif overall >= 65:
        status = "adequate"
        rec = "Team is workable; plan 1-2 seat-adds to close gaps."
    elif overall >= 50:
        status = "concerns"
        rec = "Material team concerns — budget for 2-3 replacements in first 12 months."
    else:
        status = "replace"
        rec = "Team inadequate for thesis — underwriting assumes CEO/COO replacement."
    # Seat adds.
    seat_adds: List[str] = []
    for d in dims:
        if d.status == "weak":
            seat_adds.append(f"Strengthen {d.name.replace('_', ' ')}.")
    return ManagementScore(
        overall=overall,
        status=status,
        dimensions=dims,
        recommendation=rec,
        seat_adds=seat_adds,
    )
