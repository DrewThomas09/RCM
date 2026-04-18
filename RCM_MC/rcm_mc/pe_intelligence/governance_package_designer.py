"""Governance package designer — close-date control architecture.

Partner statement: "The board seats are the first
question. The reserved matters are the second. The
rollover protections are the third. Get the first two
right and I can live with the third. Get the third
wrong and the rollover is a litigation seed."

Distinct from `board_composition_analyzer` (scores a
filled board) and `board_memo` (board-meeting format).
This module **designs** the close-date governance
package across four dimensions:

1. **Board composition** — seats by class (sponsor /
   independent / management).
2. **Committees** — audit / comp / compliance /
   nominating.
3. **Reserved matters** — sponsor consent required.
4. **Rollover protections** — tag-along, drag-along,
   preemption, info rights.

### Inputs that drive the design

- Deal shape (platform vs. add-on).
- Sponsor equity share at close (50-100%).
- Rollover equity share (0-30%).
- Subsector (healthcare = always compliance committee).
- Management has pre-existing equity / option-pool.
- LP pressure (first fund / seasoned).

### Output

Recommended package per dimension + partner-voice
commentary on trade-offs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GovernanceInputs:
    platform_tier: str = "platform"          # platform / hybrid / add_on
    sponsor_equity_pct: float = 0.80
    rollover_equity_pct: float = 0.15
    subsector: str = "healthcare_services"
    management_has_preexisting_equity: bool = False
    lp_pressure_level: str = "moderate"      # light / moderate / heavy


@dataclass
class BoardSeats:
    sponsor_seats: int
    independent_seats: int
    management_seats: int
    total_seats: int


@dataclass
class Committee:
    name: str
    sponsor_chair: bool
    rationale: str


@dataclass
class ReservedMatter:
    matter: str
    threshold: str
    rationale: str


@dataclass
class RolloverProtection:
    protection: str
    triggered_by: str


@dataclass
class GovernanceReport:
    board: BoardSeats
    committees: List[Committee] = field(default_factory=list)
    reserved_matters: List[ReservedMatter] = field(default_factory=list)
    rollover_protections: List[RolloverProtection] = field(
        default_factory=list
    )
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "board": {
                "sponsor_seats": self.board.sponsor_seats,
                "independent_seats": self.board.independent_seats,
                "management_seats": self.board.management_seats,
                "total_seats": self.board.total_seats,
            },
            "committees": [
                {"name": c.name,
                 "sponsor_chair": c.sponsor_chair,
                 "rationale": c.rationale}
                for c in self.committees
            ],
            "reserved_matters": [
                {"matter": m.matter,
                 "threshold": m.threshold,
                 "rationale": m.rationale}
                for m in self.reserved_matters
            ],
            "rollover_protections": [
                {"protection": p.protection,
                 "triggered_by": p.triggered_by}
                for p in self.rollover_protections
            ],
            "partner_note": self.partner_note,
        }


def design_governance_package(
    inputs: GovernanceInputs,
) -> GovernanceReport:
    # Board sizing.
    if inputs.platform_tier == "platform":
        total = 7
        sponsor = 3
        independent = 3
        management = 1
    elif inputs.platform_tier == "hybrid":
        total = 6
        sponsor = 3
        independent = 2
        management = 1
    else:  # add-on
        total = 5
        sponsor = 3
        independent = 1
        management = 1

    # If rollover large (≥ 20%), add a management seat.
    if inputs.rollover_equity_pct >= 0.20:
        management += 1
        total += 1

    board = BoardSeats(
        sponsor_seats=sponsor,
        independent_seats=independent,
        management_seats=management,
        total_seats=total,
    )

    # Committees.
    committees: List[Committee] = [
        Committee(
            name="audit",
            sponsor_chair=True,
            rationale=(
                "Sponsor-chaired audit; independent director "
                "as financial expert."
            ),
        ),
        Committee(
            name="compensation",
            sponsor_chair=True,
            rationale=(
                "Sponsor-chaired comp; management-led "
                "plans require committee approval."
            ),
        ),
    ]
    if "healthcare" in inputs.subsector.lower() or \
            inputs.subsector in (
                "hospital_general",
                "specialty_physician_practice",
                "behavioral_health",
                "home_health",
                "hospice",
                "ambulatory_surgery_center",
                "clinical_lab",
                "dental_office",
                "urgent_care",
                "durable_medical_equipment",
            ):
        committees.append(Committee(
            name="compliance",
            sponsor_chair=False,  # independent-chaired
            rationale=(
                "Healthcare compliance committee; "
                "independent-chaired to preserve "
                "governance best-practice + regulatory "
                "signal."
            ),
        ))
    committees.append(Committee(
        name="nominating",
        sponsor_chair=True,
        rationale=(
            "Sponsor-chaired nominating; controls board-"
            "composition evolution."
        ),
    ))

    # Reserved matters.
    reserved: List[ReservedMatter] = [
        ReservedMatter(
            matter="strategic_m_and_a",
            threshold=">$10M EV or any material asset class",
            rationale=(
                "Any material M&A requires sponsor "
                "consent."
            ),
        ),
        ReservedMatter(
            matter="leverage_change",
            threshold="any",
            rationale=(
                "Any change to debt instruments requires "
                "sponsor consent."
            ),
        ),
        ReservedMatter(
            matter="ceo_or_cfo_hire",
            threshold="any",
            rationale=(
                "C-suite hire / termination requires "
                "sponsor consent."
            ),
        ),
        ReservedMatter(
            matter="annual_operating_plan",
            threshold="annual",
            rationale=(
                "Annual OP approved by sponsor; "
                "provides thesis-discipline anchor."
            ),
        ),
        ReservedMatter(
            matter="capital_raise",
            threshold="any",
            rationale=(
                "Any equity / debt raise requires "
                "sponsor consent; preserves cap table "
                "control."
            ),
        ),
        ReservedMatter(
            matter="related_party_transactions",
            threshold="> $250K",
            rationale=(
                "Related-party contracts require "
                "committee review."
            ),
        ),
        ReservedMatter(
            matter="regulatory_settlement",
            threshold="> $500K or reputation-affecting",
            rationale=(
                "Material regulatory settlements "
                "require sponsor consent."
            ),
        ),
    ]

    # Rollover protections.
    protections: List[RolloverProtection] = []
    if inputs.rollover_equity_pct > 0:
        protections.append(RolloverProtection(
            protection="tag_along_rights",
            triggered_by=(
                "Sponsor sells > 5% of equity; rollover "
                "can sell pro-rata at same price / terms."
            ),
        ))
        protections.append(RolloverProtection(
            protection="drag_along_rights",
            triggered_by=(
                "Sponsor sale of majority → rollover "
                "dragged at same price. Applies only at "
                "bona fide sale."
            ),
        ))
        protections.append(RolloverProtection(
            protection="preemption_on_new_issuance",
            triggered_by=(
                "Any dilutive issuance; rollover can "
                "maintain % ownership."
            ),
        ))
        protections.append(RolloverProtection(
            protection="information_rights",
            triggered_by=(
                "Monthly financials + quarterly board "
                "materials."
            ),
        ))
    if inputs.rollover_equity_pct >= 0.20:
        protections.append(RolloverProtection(
            protection="liquidity_option_year_5",
            triggered_by=(
                "Put right to sponsor at fair market "
                "value if no exit by Y5."
            ),
        ))

    # Partner commentary.
    platform_phrase = {
        "platform": "platform-class deal; board +"
                    " committees sized for scale",
        "hybrid": "hybrid deal; modest governance "
                  "depth",
        "add_on": "add-on folded into existing platform; "
                  "minimal governance add",
    }.get(inputs.platform_tier, "")

    if inputs.rollover_equity_pct >= 0.20:
        rollover_phrase = (
            f"Rollover {inputs.rollover_equity_pct*100:.0f}% "
            "requires full protection package (tag / drag / "
            "preemption / info / liquidity)."
        )
    elif inputs.rollover_equity_pct > 0:
        rollover_phrase = (
            f"Rollover {inputs.rollover_equity_pct*100:.0f}%; "
            "standard protection package (tag / drag / "
            "preemption / info)."
        )
    else:
        rollover_phrase = "No rollover — no minority protections required."

    note = (
        f"{platform_phrase.capitalize()}. "
        f"{len(reserved)} reserved matters. "
        f"{rollover_phrase}"
    )

    return GovernanceReport(
        board=board,
        committees=committees,
        reserved_matters=reserved,
        rollover_protections=protections,
        partner_note=note,
    )


def render_governance_markdown(r: GovernanceReport) -> str:
    lines = [
        "# Governance package — close-date design",
        "",
        f"_{r.partner_note}_",
        "",
        "## Board",
        "",
        f"- Sponsor seats: {r.board.sponsor_seats}",
        f"- Independent seats: {r.board.independent_seats}",
        f"- Management seats: {r.board.management_seats}",
        f"- Total: {r.board.total_seats}",
        "",
        "## Committees",
        "",
    ]
    for c in r.committees:
        chair = "Sponsor" if c.sponsor_chair else "Independent"
        lines.append(f"- **{c.name}** (chair: {chair}) — "
                     f"{c.rationale}")
    lines.append("")
    lines.append("## Reserved matters (sponsor consent)")
    lines.append("")
    for m in r.reserved_matters:
        lines.append(f"- **{m.matter}** ({m.threshold}) — "
                     f"{m.rationale}")
    lines.append("")
    lines.append("## Rollover protections")
    lines.append("")
    if r.rollover_protections:
        for p in r.rollover_protections:
            lines.append(f"- **{p.protection}** — "
                         f"{p.triggered_by}")
    else:
        lines.append("None (no rollover).")
    return "\n".join(lines)
