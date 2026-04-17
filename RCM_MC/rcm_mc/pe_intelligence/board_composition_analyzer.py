"""Board composition analyzer — portco board diversity and fit.

Post-close portco boards typically include:

- **Sponsor seats** — 2-3 usually; partner + junior partner + ops
  partner.
- **Independent directors** — 1-3, typically with healthcare / RCM
  / clinical / operator / public-company experience.
- **Management seats** — CEO, sometimes CFO.
- **Committees** — audit, compensation, and increasingly compliance
  in healthcare.

Partners score:

- **Independent share** — ≥ 25% on a 7-person board typically.
- **Experience coverage** — healthcare ops, clinical, public-co,
  finance.
- **Diversity** — gender + ethnic representation (LP-reported).
- **Committee coverage** — audit + comp + (healthcare) compliance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


REQUIRED_EXPERIENCE_AREAS = ("healthcare_ops", "clinical", "public_co",
                               "finance")
REQUIRED_COMMITTEES = ("audit", "compensation", "compliance")


@dataclass
class BoardMember:
    name: str
    role: str                             # "sponsor" / "independent" /
                                          # "management"
    experience_areas: List[str] = field(default_factory=list)
    is_diverse: bool = False              # partner-declared


@dataclass
class BoardInputs:
    members: List[BoardMember] = field(default_factory=list)
    committees: List[str] = field(default_factory=list)
    is_healthcare: bool = True


@dataclass
class BoardGap:
    area: str
    severity: str
    description: str


@dataclass
class BoardReport:
    total_seats: int
    sponsor_seats: int
    independent_seats: int
    management_seats: int
    independent_pct: float
    diverse_pct: float
    experience_coverage_pct: float
    missing_committees: List[str] = field(default_factory=list)
    gaps: List[BoardGap] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_seats": self.total_seats,
            "sponsor_seats": self.sponsor_seats,
            "independent_seats": self.independent_seats,
            "management_seats": self.management_seats,
            "independent_pct": self.independent_pct,
            "diverse_pct": self.diverse_pct,
            "experience_coverage_pct": self.experience_coverage_pct,
            "missing_committees": list(self.missing_committees),
            "gaps": [{"area": g.area, "severity": g.severity,
                       "description": g.description} for g in self.gaps],
            "partner_note": self.partner_note,
        }


def analyze_board(inputs: BoardInputs) -> BoardReport:
    members = inputs.members
    total = len(members)
    if total == 0:
        return BoardReport(
            total_seats=0, sponsor_seats=0, independent_seats=0,
            management_seats=0, independent_pct=0.0, diverse_pct=0.0,
            experience_coverage_pct=0.0,
            partner_note="No board members provided.",
        )

    sponsor = sum(1 for m in members if m.role == "sponsor")
    independent = sum(1 for m in members if m.role == "independent")
    management = sum(1 for m in members if m.role == "management")
    ind_pct = independent / total
    diverse_pct = sum(1 for m in members if m.is_diverse) / total

    covered = set()
    for m in members:
        covered.update(m.experience_areas)
    req = set(REQUIRED_EXPERIENCE_AREAS)
    coverage = len(covered & req) / len(req)

    # Committees.
    required_committees = set(REQUIRED_COMMITTEES) if inputs.is_healthcare \
        else {"audit", "compensation"}
    missing_committees = sorted(required_committees - set(inputs.committees))

    gaps: List[BoardGap] = []
    if ind_pct < 0.25:
        gaps.append(BoardGap(
            area="independence", severity="high",
            description=(f"Independent share {ind_pct*100:.0f}% below "
                         "25% market standard."),
        ))
    if diverse_pct < 0.20:
        gaps.append(BoardGap(
            area="diversity", severity="medium",
            description=(f"Diverse representation {diverse_pct*100:.0f}% — "
                         "LP reporting threshold often 25%."),
        ))
    for area in req - covered:
        gaps.append(BoardGap(
            area=area, severity="medium",
            description=f"Missing experience: {area}.",
        ))
    for committee in missing_committees:
        gaps.append(BoardGap(
            area=committee, severity="high",
            description=f"{committee} committee not established.",
        ))

    high = sum(1 for g in gaps if g.severity == "high")
    if high >= 2:
        note = (f"Board composition has {high} high-severity gaps. "
                "Address before next LP update.")
    elif gaps:
        note = (f"Board in decent shape; {len(gaps)} minor gap(s) to close.")
    else:
        note = "Board composition is strong — no gaps."

    return BoardReport(
        total_seats=total,
        sponsor_seats=sponsor,
        independent_seats=independent,
        management_seats=management,
        independent_pct=round(ind_pct, 3),
        diverse_pct=round(diverse_pct, 3),
        experience_coverage_pct=round(coverage, 3),
        missing_committees=missing_committees,
        gaps=gaps,
        partner_note=note,
    )


def render_board_markdown(r: BoardReport) -> str:
    lines = [
        "# Board composition analysis",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Seats: {r.total_seats} ({r.sponsor_seats} sponsor, "
        f"{r.independent_seats} independent, {r.management_seats} mgmt)",
        f"- Independent %: {r.independent_pct*100:.1f}%",
        f"- Diverse %: {r.diverse_pct*100:.1f}%",
        f"- Experience coverage: {r.experience_coverage_pct*100:.0f}%",
    ]
    if r.missing_committees:
        lines.append(f"- Missing committees: {', '.join(r.missing_committees)}")
    if r.gaps:
        lines.extend(["", "## Gaps", ""])
        for g in r.gaps:
            lines.append(f"- **{g.severity.upper()}** {g.area}: "
                         f"{g.description}")
    return "\n".join(lines)
