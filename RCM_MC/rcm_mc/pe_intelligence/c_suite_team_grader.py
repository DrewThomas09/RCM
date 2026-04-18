"""C-suite team grader — per-seat grade and replace/coach/accept rec.

Partner statement: "The deal is the team. CEO with
PE experience, CFO who's seen a sale process, COO
who runs the operating cadence, CMO if it's
clinical-driven. Each seat gets graded against the
work that has to happen in this hold. If the CFO
has only run private-company books, that's a
diligence gap before close. If the COO has never
managed a multi-site integration, that's a gap
before bolt-on #2. Grade each seat individually,
then call out the gaps."

Distinct from:
- `management_assessment` — generic management read.
- `management_bench_depth_check` — bench breadth.
- `management_first_sitdown` — IC-meeting framing.
- `interim_ceo_bench` (if exists) — interim cover.

This module **grades each seat individually** on
specific PE-healthcare-relevant criteria and outputs
a per-seat verdict.

### Seats and grading criteria

Each seat scored 0-4 on:
1. relevant_industry_experience (years in healthcare)
2. pe_backed_experience (worked under sponsor before)
3. transaction_experience (sale / refinance / recap)
4. specific_to_seat (CEO: vision; CFO: capital
   markets; COO: integration; CMO: clinical quality)

Score = sum (0-16). Letter grade:
- 13-16 → A
- 10-12 → B
- 7-9 → C
- < 7 → D

Per-seat recommendation:
- A → accept
- B → accept_with_coaching
- C → coach_or_replace
- D → replace_at_close
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SEAT_TYPES = ("CEO", "CFO", "COO", "CMO")


@dataclass
class SeatExecutive:
    seat: str
    name: str = ""
    years_in_healthcare: int = 0
    pe_backed_before: bool = False
    transaction_experience: bool = False
    seat_specific_score_0_4: int = 2
    """Per-seat-specific 0-4:
    CEO: vision/strategy clarity
    CFO: capital markets / debt experience
    COO: multi-site / integration experience
    CMO: clinical quality outcomes track record
    """


@dataclass
class CSuiteTeamInputs:
    seats: List[SeatExecutive] = field(default_factory=list)
    deal_archetype: str = ""  # informs criticality


@dataclass
class SeatGrade:
    seat: str
    name: str
    score_0_16: int
    letter_grade: str
    recommendation: str
    diagnostic_lines: List[str] = field(default_factory=list)


@dataclass
class CSuiteTeamReport:
    seats_graded: List[SeatGrade] = field(default_factory=list)
    composite_score: float = 0.0
    composite_letter: str = ""
    seats_to_replace: List[str] = field(default_factory=list)
    seats_to_coach: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seats_graded": [
                {"seat": s.seat,
                 "name": s.name,
                 "score_0_16": s.score_0_16,
                 "letter_grade": s.letter_grade,
                 "recommendation": s.recommendation,
                 "diagnostic_lines":
                     s.diagnostic_lines}
                for s in self.seats_graded
            ],
            "composite_score": self.composite_score,
            "composite_letter": self.composite_letter,
            "seats_to_replace": self.seats_to_replace,
            "seats_to_coach": self.seats_to_coach,
            "partner_note": self.partner_note,
        }


def _industry_score(years: int) -> int:
    if years >= 15:
        return 4
    if years >= 10:
        return 3
    if years >= 5:
        return 2
    if years >= 2:
        return 1
    return 0


def _letter_grade(total: int) -> str:
    if total >= 13:
        return "A"
    if total >= 10:
        return "B"
    if total >= 7:
        return "C"
    return "D"


def _recommendation(letter: str) -> str:
    return {
        "A": "accept",
        "B": "accept_with_coaching",
        "C": "coach_or_replace",
        "D": "replace_at_close",
    }.get(letter, "coach_or_replace")


def _diagnostic_for_seat(seat: SeatExecutive) -> List[str]:
    lines: List[str] = []
    if seat.years_in_healthcare < 5:
        lines.append(
            f"Healthcare experience light "
            f"({seat.years_in_healthcare} yrs) — "
            "domain learning curve in year 1."
        )
    if not seat.pe_backed_before:
        lines.append(
            "First PE-backed role — adjusting to "
            "board cadence, monthly reporting, "
            "lender covenants takes 6-12 months."
        )
    if not seat.transaction_experience:
        lines.append(
            "No prior transaction experience — "
            "expect support need at refi, "
            "recap, or exit."
        )
    if seat.seat_specific_score_0_4 <= 1:
        lines.append(
            f"Seat-specific competency is weak — "
            f"primary gap on {seat.seat} role."
        )
    return lines


def grade_c_suite_team(
    inputs: CSuiteTeamInputs,
) -> CSuiteTeamReport:
    if not inputs.seats:
        return CSuiteTeamReport(
            partner_note=(
                "No C-suite seats provided — verify "
                "the deal team has reviewed the org "
                "chart."
            ),
        )

    grades: List[SeatGrade] = []
    to_replace: List[str] = []
    to_coach: List[str] = []
    for s in inputs.seats:
        ind = _industry_score(s.years_in_healthcare)
        pe = 4 if s.pe_backed_before else 0
        tx = 4 if s.transaction_experience else 0
        spec = max(0, min(4, s.seat_specific_score_0_4))
        total = ind + pe + tx + spec
        letter = _letter_grade(total)
        rec = _recommendation(letter)
        diag = _diagnostic_for_seat(s)
        grades.append(SeatGrade(
            seat=s.seat,
            name=s.name,
            score_0_16=total,
            letter_grade=letter,
            recommendation=rec,
            diagnostic_lines=diag,
        ))
        if rec == "replace_at_close":
            to_replace.append(s.seat)
        elif rec == "coach_or_replace":
            to_coach.append(s.seat)

    composite = (
        sum(g.score_0_16 for g in grades) / len(grades)
    )
    composite_letter = _letter_grade(int(round(composite)))

    if to_replace:
        note = (
            f"{len(to_replace)} seat(s) at D — "
            f"plan to replace at close: "
            f"{', '.join(to_replace)}. Bring named "
            "candidate(s) to closing-conditions list."
        )
    elif to_coach:
        note = (
            f"{len(to_coach)} seat(s) at C — coach or "
            f"replace: {', '.join(to_coach)}. Operating-"
            "partner cadence + 6-month review window."
        )
    elif composite_letter == "A":
        note = (
            f"Strong team (composite {composite:.1f}/16, "
            f"{composite_letter}). Accept as-is; "
            "diligence focus shifts to bench depth and "
            "succession."
        )
    else:
        note = (
            f"Adequate team (composite "
            f"{composite:.1f}/16, {composite_letter}). "
            "Accept with standard PE coaching cadence."
        )

    return CSuiteTeamReport(
        seats_graded=grades,
        composite_score=round(composite, 2),
        composite_letter=composite_letter,
        seats_to_replace=to_replace,
        seats_to_coach=to_coach,
        partner_note=note,
    )


def render_c_suite_team_markdown(
    r: CSuiteTeamReport,
) -> str:
    lines = [
        "# C-suite team grade",
        "",
        f"_Composite: {r.composite_score:.1f}/16 "
        f"(**{r.composite_letter}**)_ — {r.partner_note}",
        "",
        "| Seat | Name | Score | Grade | Recommendation |",
        "|---|---|---|---|---|",
    ]
    for s in r.seats_graded:
        lines.append(
            f"| {s.seat} | {s.name} | {s.score_0_16}/16 "
            f"| {s.letter_grade} | {s.recommendation} |"
        )
    for s in r.seats_graded:
        if s.diagnostic_lines:
            lines.append("")
            lines.append(f"### {s.seat} diagnostics")
            for d in s.diagnostic_lines:
                lines.append(f"- {d}")
    return "\n".join(lines)
