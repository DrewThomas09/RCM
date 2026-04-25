"""Succession-risk register — key-person concentration + impact.

Per-role assessment of:

  concentration_score   how much of the value-creation thesis
                        depends on this single person (0-1)
  departure_impact_mm   $-estimate of EBITDA at risk if this
                        person leaves in year 1 of the hold
  bench_strength        0-5 scoring of internal succession depth
  retention_levers      list of qualitative levers (rollover
                        equity, golden handcuff, etc.)

The register sorts by departure_impact_mm so the partner sees
the highest-impact roles first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .executive import Executive, ManagementTeam


# Role-specific concentration multipliers — what % of the
# typical PE thesis depends on each role being executed well.
_ROLE_CONCENTRATION: Dict[str, float] = {
    "CEO": 0.40,
    "CFO": 0.20,
    "COO": 0.15,
    "CRO": 0.20,
    "CMO": 0.15,
    "CHRO": 0.10,
    "DEFAULT": 0.10,
}


@dataclass
class KeyPersonRisk:
    """One executive's succession risk."""
    person_id: str
    role: str
    concentration_score: float       # 0-1
    departure_impact_mm: float
    bench_strength: float            # 0-5
    retention_levers: List[str] = field(default_factory=list)
    severity: str = "medium"         # low / medium / high


@dataclass
class SuccessionRegister:
    """Team-level register sorted by departure impact."""
    company_name: str
    risks: List[KeyPersonRisk] = field(default_factory=list)
    total_departure_impact_mm: float = 0.0
    high_severity_count: int = 0


def _severity(impact_mm: float, bench_strength: float) -> str:
    if impact_mm >= 5.0 and bench_strength <= 2.0:
        return "high"
    if impact_mm >= 2.0 and bench_strength <= 3.0:
        return "medium"
    return "low"


def _retention_levers(ex: Executive) -> List[str]:
    """Suggest retention levers based on the executive's profile."""
    out: List[str] = []
    if ex.rollover_equity_pct < 0.20:
        out.append("Increase rollover equity above 20% threshold")
    else:
        out.append(f"Rollover equity already at "
                   f"{ex.rollover_equity_pct*100:.0f}%")
    if ex.tenure_years < 3:
        out.append("Stay-bonus over 3-year cliff to lock retention")
    if ex.has_pe_experience:
        out.append(
            "PE experience — partner-style equity grant + board "
            "advisory role")
    return out


def build_succession_register(
    team: ManagementTeam,
    *,
    target_ebitda_mm: float = 50.0,
    bench_strengths: Dict[str, float] = None,
) -> SuccessionRegister:
    """Build the succession-risk register.

    Args:
      team: management team with executives + their attributes.
      target_ebitda_mm: target's run-rate EBITDA — drives
        departure-impact $-estimate.
      bench_strengths: {person_id → bench_strength 0-5}.
        Missing → defaults to 2.5 (average — moderate concern).

    Returns SuccessionRegister sorted by departure_impact_mm
    descending.
    """
    bench_strengths = bench_strengths or {}
    risks: List[KeyPersonRisk] = []

    for ex in team.executives:
        role_upper = ex.role.upper()
        concentration = _ROLE_CONCENTRATION.get(
            role_upper, _ROLE_CONCENTRATION["DEFAULT"])
        # Tenure modifier: longer-tenured executives carry more
        # institutional knowledge → higher concentration.
        if ex.tenure_years >= 7:
            concentration *= 1.30
        elif ex.tenure_years <= 1:
            concentration *= 0.70
        # Direct-reports modifier: bigger team under them →
        # bigger blast radius.
        if ex.direct_reports >= 8:
            concentration *= 1.10

        concentration = max(0.0, min(1.0, concentration))
        # Departure impact: 25% of the role's concentrated EBITDA
        # is at risk in the year-1 transition.
        impact = (target_ebitda_mm * concentration * 0.25)
        bench = bench_strengths.get(ex.person_id, 2.5)
        sev = _severity(impact, bench)

        risks.append(KeyPersonRisk(
            person_id=ex.person_id,
            role=ex.role,
            concentration_score=round(concentration, 3),
            departure_impact_mm=round(impact, 2),
            bench_strength=round(bench, 2),
            retention_levers=_retention_levers(ex),
            severity=sev,
        ))

    risks.sort(key=lambda r: r.departure_impact_mm, reverse=True)
    total_impact = sum(r.departure_impact_mm for r in risks)
    high_count = sum(1 for r in risks if r.severity == "high")

    return SuccessionRegister(
        company_name=team.company_name,
        risks=risks,
        total_departure_impact_mm=round(total_impact, 2),
        high_severity_count=high_count,
    )
