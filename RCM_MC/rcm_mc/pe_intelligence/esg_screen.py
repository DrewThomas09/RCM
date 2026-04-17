"""ESG screen — exclusions + scoring + reporting readiness.

LPs increasingly require ESG diligence output:

- **Exclusions** — categorical (tobacco, firearms, short-term
  detention, fossil-fuel-primary, animal testing-primary).
- **Reporting readiness** — does the target have the data
  infrastructure to report on scope-1/2 emissions, DEI metrics,
  worker-safety incidents?
- **Transition opportunity** — is there a named path to ESG-linked
  value creation?

Output: a 0..100 ESG score + exclusion flags + reporting gap list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ESGInputs:
    # Exclusions
    tobacco_exposure: Optional[bool] = None
    firearms_exposure: Optional[bool] = None
    short_term_detention: Optional[bool] = None
    fossil_fuel_primary: Optional[bool] = None
    controversial_weapons: Optional[bool] = None

    # E/S/G scores (0..1 where higher is better)
    environmental_score: Optional[float] = None
    social_score: Optional[float] = None
    governance_score: Optional[float] = None

    # Reporting readiness
    scope1_emissions_tracked: Optional[bool] = None
    scope2_emissions_tracked: Optional[bool] = None
    dei_metrics_tracked: Optional[bool] = None
    worker_safety_tracked: Optional[bool] = None
    board_diversity_pct: Optional[float] = None


@dataclass
class ESGFlag:
    category: str
    severity: str                   # "exclusion" | "warning" | "info"
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class ESGReport:
    score: int                      # 0..100
    grade: str                      # A..F
    exclusion_flags: List[ESGFlag] = field(default_factory=list)
    reporting_gaps: List[str] = field(default_factory=list)
    is_excluded: bool = False       # any hard exclusion triggered
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "exclusion_flags": [f.to_dict() for f in self.exclusion_flags],
            "reporting_gaps": list(self.reporting_gaps),
            "is_excluded": self.is_excluded,
            "partner_note": self.partner_note,
        }


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 72:
        return "B"
    if score >= 58:
        return "C"
    if score >= 42:
        return "D"
    return "F"


def _exclusions(inputs: ESGInputs) -> List[ESGFlag]:
    flags: List[ESGFlag] = []
    if inputs.tobacco_exposure:
        flags.append(ESGFlag("tobacco", "exclusion",
                             "Tobacco exposure — standard LP exclusion."))
    if inputs.firearms_exposure:
        flags.append(ESGFlag("firearms", "exclusion",
                             "Firearms manufacturing — standard LP exclusion."))
    if inputs.short_term_detention:
        flags.append(ESGFlag("short_term_detention", "exclusion",
                             "Short-term detention — broadly excluded."))
    if inputs.fossil_fuel_primary:
        flags.append(ESGFlag("fossil_fuel_primary", "exclusion",
                             "Primary fossil-fuel exposure — excluded by most LPs."))
    if inputs.controversial_weapons:
        flags.append(ESGFlag("controversial_weapons", "exclusion",
                             "Controversial weapons — categorically excluded."))
    return flags


def _reporting_gaps(inputs: ESGInputs) -> List[str]:
    gaps: List[str] = []
    if inputs.scope1_emissions_tracked is False:
        gaps.append("No scope-1 emissions tracking.")
    if inputs.scope2_emissions_tracked is False:
        gaps.append("No scope-2 emissions tracking.")
    if inputs.dei_metrics_tracked is False:
        gaps.append("No DEI metrics tracked.")
    if inputs.worker_safety_tracked is False:
        gaps.append("No worker-safety reporting.")
    return gaps


def _composite_esg(inputs: ESGInputs) -> float:
    components: List[float] = []
    if inputs.environmental_score is not None:
        components.append(float(inputs.environmental_score))
    if inputs.social_score is not None:
        components.append(float(inputs.social_score))
    if inputs.governance_score is not None:
        components.append(float(inputs.governance_score))
    # Board diversity
    if inputs.board_diversity_pct is not None:
        bd = float(inputs.board_diversity_pct)
        if bd > 1.5:
            bd /= 100.0
        # Partner-prudent: 30%+ = full marks.
        components.append(max(0.0, min(1.0, bd / 0.30)))
    # Reporting completeness
    reporting_bits = [
        inputs.scope1_emissions_tracked,
        inputs.scope2_emissions_tracked,
        inputs.dei_metrics_tracked,
        inputs.worker_safety_tracked,
    ]
    known = [b for b in reporting_bits if b is not None]
    if known:
        components.append(sum(1 for b in known if b) / len(known))
    if not components:
        return 0.50
    return sum(components) / len(components)


def screen_esg(inputs: ESGInputs) -> ESGReport:
    """Produce an ESG screen report from structured inputs."""
    exclusions = _exclusions(inputs)
    gaps = _reporting_gaps(inputs)
    composite = _composite_esg(inputs)

    # Exclusion zeros out the score.
    is_excluded = len(exclusions) > 0
    if is_excluded:
        score = 0
        note = (f"{len(exclusions)} LP exclusion(s) triggered — do not "
                "underwrite without explicit LP waiver.")
    else:
        # Reporting-gap penalty (5 points per gap, capped).
        base = int(round(composite * 100))
        penalty = min(25, 5 * len(gaps))
        score = max(0, base - penalty)
        if score >= 85:
            note = ("Top-quartile ESG profile — supports LP reporting and "
                    "potential ESG-linked financing.")
        elif score >= 60:
            note = ("Adequate ESG profile; address reporting gaps to "
                    "strengthen LP position.")
        else:
            note = ("Weak ESG profile. Close reporting gaps pre-close and "
                    "name an ESG workstream in the 100-day plan.")

    return ESGReport(
        score=score,
        grade=_grade(score),
        exclusion_flags=exclusions,
        reporting_gaps=gaps,
        is_excluded=is_excluded,
        partner_note=note,
    )


def render_esg_markdown(report: ESGReport) -> str:
    lines = [
        "# ESG screen",
        "",
        f"**Score:** {report.score}/100  ",
        f"**Grade:** {report.grade}  ",
        f"**Excluded:** {'yes' if report.is_excluded else 'no'}",
        "",
        f"_{report.partner_note}_",
    ]
    if report.exclusion_flags:
        lines.extend(["", "## Exclusion flags", ""])
        for f in report.exclusion_flags:
            lines.append(f"- [{f.severity.upper()}] {f.category}: {f.detail}")
    if report.reporting_gaps:
        lines.extend(["", "## Reporting gaps", ""])
        for g in report.reporting_gaps:
            lines.append(f"- {g}")
    return "\n".join(lines)
