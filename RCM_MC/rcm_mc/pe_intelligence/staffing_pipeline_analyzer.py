"""Staffing pipeline analyzer — hiring + attrition math.

Healthcare services companies live or die on clinician supply.
This module takes current headcount + hiring pipeline + attrition
experience and returns:

- **Net headcount trajectory** over the next 4 quarters.
- **Days-to-fill** weighted by role severity.
- **Attrition cost** — productivity lost per departure.
- **Shortage risk** — whether headcount will drop below a
  floor (e.g., Medicare required minimums at SNFs).

Representative assumptions (partner-tunable):

- Default time-to-fill: 90 days for physicians, 45 for NPs/PAs,
  60 for RNs.
- Default productivity ramp: 6 months to full output.
- Cost per vacant clinician day: $2,500 (lost collections).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DEFAULT_TTF_DAYS = {
    "physician": 90,
    "np_pa": 45,
    "rn": 60,
    "tech": 30,
}

DEFAULT_RAMP_MONTHS = {
    "physician": 6,
    "np_pa": 3,
    "rn": 2,
    "tech": 1,
}


@dataclass
class RoleState:
    role: str                             # "physician" / "np_pa" / "rn" / "tech"
    current_headcount: int
    open_reqs: int                        # active requisitions
    pipeline_candidates: int              # sourced / screened
    offers_extended: int
    quarterly_attrition_rate: float = 0.05
    floor_headcount: Optional[int] = None  # regulatory / contractual floor
    daily_revenue_per_role_m: float = 0.0025  # $2,500/day default


@dataclass
class StaffingFinding:
    role: str
    severity: str                         # "high" / "medium" / "low"
    message: str


@dataclass
class RoleProjection:
    role: str
    current_headcount: int
    q1_projection: int
    q4_projection: int
    below_floor_q: Optional[int] = None   # first quarter below floor (1-4)
    lost_revenue_q1_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "current_headcount": self.current_headcount,
            "q1_projection": self.q1_projection,
            "q4_projection": self.q4_projection,
            "below_floor_q": self.below_floor_q,
            "lost_revenue_q1_m": self.lost_revenue_q1_m,
        }


@dataclass
class StaffingReport:
    projections: List[RoleProjection] = field(default_factory=list)
    findings: List[StaffingFinding] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "projections": [p.to_dict() for p in self.projections],
            "findings": [{"role": f.role, "severity": f.severity,
                           "message": f.message} for f in self.findings],
            "partner_note": self.partner_note,
        }


def _project_role(role: RoleState) -> RoleProjection:
    """Simple 4-quarter projection of headcount."""
    # Quarterly hire yield: assume ~60% of offers convert.
    expected_hires_per_q = int(round(role.offers_extended * 0.60))
    attr_rate = max(0.0, role.quarterly_attrition_rate)

    hc = role.current_headcount
    below = None
    q1 = q4 = hc
    for q in range(1, 5):
        departures = int(round(hc * attr_rate))
        hires = expected_hires_per_q
        hc = max(0, hc + hires - departures)
        if q == 1:
            q1 = hc
        if q == 4:
            q4 = hc
        if role.floor_headcount is not None and below is None:
            if hc < role.floor_headcount:
                below = q

    # Lost revenue: open reqs unfilled × TTF days × daily rev.
    ttf = DEFAULT_TTF_DAYS.get(role.role, 60)
    lost_q1 = (role.open_reqs * ttf * role.daily_revenue_per_role_m)

    return RoleProjection(
        role=role.role,
        current_headcount=role.current_headcount,
        q1_projection=q1, q4_projection=q4,
        below_floor_q=below,
        lost_revenue_q1_m=round(lost_q1, 2),
    )


def analyze_staffing(roles: List[RoleState]) -> StaffingReport:
    projs = [_project_role(r) for r in roles]
    findings: List[StaffingFinding] = []

    for role, proj in zip(roles, projs):
        if proj.below_floor_q is not None:
            findings.append(StaffingFinding(
                role=role.role, severity="high",
                message=(f"{role.role} headcount projected below floor "
                         f"({role.floor_headcount}) in Q{proj.below_floor_q}."),
            ))
        if role.open_reqs > max(3, role.current_headcount // 10):
            findings.append(StaffingFinding(
                role=role.role, severity="medium",
                message=(f"{role.role} has {role.open_reqs} open reqs on "
                         f"{role.current_headcount} current HC — "
                         "material pipeline pressure."),
            ))
        if role.quarterly_attrition_rate >= 0.10:
            findings.append(StaffingFinding(
                role=role.role, severity="high",
                message=(f"{role.role} attrition "
                         f"{role.quarterly_attrition_rate*100:.0f}%/qtr "
                         "is elevated — investigate root cause."),
            ))
        if role.pipeline_candidates < 2 * role.open_reqs:
            findings.append(StaffingFinding(
                role=role.role, severity="medium",
                message=(f"{role.role} pipeline "
                         f"({role.pipeline_candidates} candidates) too thin "
                         f"for {role.open_reqs} open reqs."),
            ))

    high_count = sum(1 for f in findings if f.severity == "high")
    if high_count >= 2:
        note = (f"Staffing is a material deal risk: {high_count} "
                "high-severity findings. Budget for retention, recruiting, "
                "and contingent labor.")
    elif high_count == 1:
        note = "One high-severity staffing issue — address at 100-day plan."
    elif findings:
        note = "Staffing is manageable with active pipeline management."
    else:
        note = "Staffing posture healthy across roles."

    return StaffingReport(
        projections=projs,
        findings=findings,
        partner_note=note,
    )


def render_staffing_markdown(report: StaffingReport) -> str:
    lines = [
        "# Staffing pipeline analysis",
        "",
        f"_{report.partner_note}_",
        "",
        "| Role | Current | Q1 | Q4 | Below floor | Lost rev Q1 |",
        "|---|---:|---:|---:|:-:|---:|",
    ]
    for p in report.projections:
        bf = f"Q{p.below_floor_q}" if p.below_floor_q is not None else "—"
        lines.append(
            f"| {p.role} | {p.current_headcount} | {p.q1_projection} | "
            f"{p.q4_projection} | {bf} | ${p.lost_revenue_q1_m:,.2f}M |"
        )
    if report.findings:
        lines.extend(["", "## Findings", ""])
        for f in report.findings:
            lines.append(f"- **{f.severity.upper()}** {f.role}: {f.message}")
    return "\n".join(lines)
