"""Add-on integration sequencing — order and pace of bolt-on integrations.

Partner statement: "Every roll-up pitches 8-12
bolt-ons but the integration team can actually
swallow 2-3 per year. Sequence them or the 4th
one slips, the 5th slips more, and by bolt-on 7
the team is underwater. Order by integration ease
+ strategic priority; space them out by capacity;
surface the saturation point."

Distinct from:
- `add_on_fit_scorer` — individual deal fit.
- `rollup_arbitrage_math` — MOIC decomposition.
- `ma_integration_scoreboard` — score on integration.

This module **sequences** a bolt-on pipeline by
integration ease × strategic priority, respecting
integration capacity per quarter.

### Output

Per bolt-on: sequence number, assigned quarter,
cumulative load on integration team, saturation
warning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BoltOn:
    name: str
    ebitda_m: float
    integration_ease_0_4: int = 2
    """0-4; 4 = same-platform same-geography tuck-in
    (easy); 0 = different-state different-EHR greenfield."""
    strategic_priority_0_4: int = 2
    already_signed: bool = False


@dataclass
class IntegrationSequencingInputs:
    bolt_ons: List[BoltOn] = field(default_factory=list)
    integration_capacity_per_quarter: int = 1
    hold_quarters: int = 20
    """Hold period in quarters (5yr = 20)."""


@dataclass
class SequencedBoltOn:
    sequence: int
    name: str
    ebitda_m: float
    priority_score: int
    assigned_quarter: int
    saturation_flag: bool


@dataclass
class IntegrationSequencingReport:
    sequence: List[SequencedBoltOn] = field(
        default_factory=list)
    total_ebitda_added_m: float = 0.0
    saturation_quarter: Optional[int] = None
    unplaced_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": [
                {"sequence": s.sequence,
                 "name": s.name,
                 "ebitda_m": s.ebitda_m,
                 "priority_score": s.priority_score,
                 "assigned_quarter": s.assigned_quarter,
                 "saturation_flag": s.saturation_flag}
                for s in self.sequence
            ],
            "total_ebitda_added_m":
                self.total_ebitda_added_m,
            "saturation_quarter":
                self.saturation_quarter,
            "unplaced_count": self.unplaced_count,
            "partner_note": self.partner_note,
        }


def plan_add_on_sequencing(
    inputs: IntegrationSequencingInputs,
) -> IntegrationSequencingReport:
    if not inputs.bolt_ons:
        return IntegrationSequencingReport(
            partner_note=(
                "No bolt-ons provided — sequencing "
                "requires the pipeline list."),
        )

    # Score each bolt-on: higher priority = higher
    # combined (ease + priority). Already-signed
    # bolt-ons ranked ahead (must integrate regardless).
    def score(b: BoltOn) -> int:
        signed_bonus = 8 if b.already_signed else 0
        return (
            signed_bonus +
            b.integration_ease_0_4 +
            b.strategic_priority_0_4
        )

    ranked = sorted(
        inputs.bolt_ons, key=score, reverse=True)

    capacity_per_q = max(
        1, inputs.integration_capacity_per_quarter)
    hold_quarters = inputs.hold_quarters

    sequence: List[SequencedBoltOn] = []
    unplaced = 0
    saturation_quarter: Optional[int] = None
    total_ebitda = 0.0

    # Fill by quarter up to capacity
    for i, b in enumerate(ranked):
        assigned_q = (i // capacity_per_q) + 1
        if assigned_q > hold_quarters:
            unplaced += 1
            if saturation_quarter is None:
                saturation_quarter = hold_quarters + 1
            continue
        total_ebitda += b.ebitda_m
        # Saturation flag: last 1/3 of hold
        saturation = assigned_q > hold_quarters * 2 // 3
        if saturation and saturation_quarter is None:
            saturation_quarter = assigned_q
        sequence.append(SequencedBoltOn(
            sequence=i + 1,
            name=b.name,
            ebitda_m=round(b.ebitda_m, 2),
            priority_score=score(b),
            assigned_quarter=assigned_q,
            saturation_flag=saturation,
        ))

    if unplaced > 0:
        note = (
            f"{unplaced} bolt-on(s) won't fit in hold "
            f"window at capacity "
            f"{capacity_per_q}/quarter. Either "
            "accelerate integration team or drop the "
            "lowest-priority tail."
        )
    elif saturation_quarter is not None:
        note = (
            f"Pipeline fits but saturates team in "
            f"Q{saturation_quarter} "
            f"(last 1/3 of hold). Back-loaded "
            "integrations risk the exit window."
        )
    else:
        note = (
            f"Sequence clean: all "
            f"{len(sequence)} bolt-ons fit with "
            "integration capacity to spare. Execute "
            "on priority order."
        )

    return IntegrationSequencingReport(
        sequence=sequence,
        total_ebitda_added_m=round(total_ebitda, 2),
        saturation_quarter=saturation_quarter,
        unplaced_count=unplaced,
        partner_note=note,
    )


def render_add_on_sequencing_markdown(
    r: IntegrationSequencingReport,
) -> str:
    lines = [
        "# Add-on integration sequencing",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total EBITDA added: "
        f"${r.total_ebitda_added_m:.1f}M",
        f"- Saturation quarter: "
        f"{r.saturation_quarter if r.saturation_quarter else 'none'}",
        f"- Unplaced: {r.unplaced_count}",
        "",
        "| # | Bolt-on | EBITDA | Priority | Quarter | Saturation |",
        "|---|---|---|---|---|---|",
    ]
    for s in r.sequence:
        lines.append(
            f"| {s.sequence} | {s.name} | "
            f"${s.ebitda_m:.1f}M | "
            f"{s.priority_score} | "
            f"Q{s.assigned_quarter} | "
            f"{'⚠' if s.saturation_flag else '—'} |"
        )
    return "\n".join(lines)
