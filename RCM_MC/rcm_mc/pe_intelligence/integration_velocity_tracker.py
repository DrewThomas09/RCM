"""Integration velocity tracker — 100-day plan on-pace check.

Partner statement: "The 100-day plan matters only if we
hit the milestones on schedule. At day 45, I want to
know: are we ahead, behind, or off-track? One data point
per milestone, one number for the plan."

Distinct from:
- `hundred_day_plan` / `one_hundred_day_plan_from_packet` —
  generators.
- `day_one_action_plan` — day-1 readiness.
- `ma_integration_scoreboard` — per-bolt-on health across
  a platform.

This module measures **velocity** on a single deal's
100-day plan: given milestone-level targets + actuals,
compute on-pace / behind / at-risk / off-track.

### Milestone fields

Each milestone has:
- `name`
- `target_day` (days from close, 0-100)
- `actual_day` (None if not yet complete)
- `is_critical_path` (bool)
- `owner`
- `status` — planned / in_progress / complete / at_risk

### Velocity math

- **On-pace %** = milestones completed by target day.
- **Days ahead / behind** — weighted by critical-path.
- **At-risk count** — incomplete milestones past target
  with no revised completion date.

### Tier ladder

- **on_pace** — ≥ 90% of milestones due-to-date complete,
  no critical-path slip.
- **behind** — 70-90%, critical-path ≤ 1 slip.
- **at_risk** — < 70%, OR ≥ 2 critical-path slips.
- **off_track** — < 50% OR ≥ 3 critical-path slips → ops
  committee escalation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Milestone:
    name: str
    target_day: int
    actual_day: Optional[int] = None
    is_critical_path: bool = False
    owner: str = ""
    status: str = "planned"     # planned / in_progress /
                                 # complete / at_risk


@dataclass
class VelocityInputs:
    milestones: List[Milestone] = field(default_factory=list)
    current_day: int = 0         # days since close


@dataclass
class VelocityReport:
    tier: str
    current_day: int
    milestones_due_to_date: int
    milestones_complete: int
    on_pace_pct: float           # 0-1
    critical_path_slips: int
    at_risk_count: int
    escalation_list: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "current_day": self.current_day,
            "milestones_due_to_date":
                self.milestones_due_to_date,
            "milestones_complete": self.milestones_complete,
            "on_pace_pct": self.on_pace_pct,
            "critical_path_slips":
                self.critical_path_slips,
            "at_risk_count": self.at_risk_count,
            "escalation_list": list(self.escalation_list),
            "partner_note": self.partner_note,
        }


def track_integration_velocity(
    inputs: VelocityInputs,
) -> VelocityReport:
    due_to_date = [
        m for m in inputs.milestones
        if m.target_day <= inputs.current_day
    ]
    complete_due = [
        m for m in due_to_date
        if m.status == "complete" or m.actual_day is not None
    ]
    # Empty / nothing-due-yet = trivially on-pace.
    if len(due_to_date) == 0:
        on_pace_pct = 1.0
    else:
        on_pace_pct = len(complete_due) / len(due_to_date)
    # Critical-path slips: critical, due-to-date, not
    # complete.
    cp_slips = sum(
        1 for m in due_to_date
        if m.is_critical_path and m.status != "complete"
    )
    at_risk = sum(
        1 for m in inputs.milestones
        if m.status == "at_risk"
    )
    # Escalations: critical-path slips + at-risk items.
    escalations: List[str] = []
    for m in inputs.milestones:
        if (m.is_critical_path and
                m.status != "complete" and
                m.target_day <= inputs.current_day):
            escalations.append(
                f"[critical] {m.name} — due day "
                f"{m.target_day}, current day "
                f"{inputs.current_day}, owner: "
                f"{m.owner or 'unassigned'}"
            )
        elif m.status == "at_risk":
            escalations.append(
                f"[at-risk] {m.name} — target day "
                f"{m.target_day}, owner: "
                f"{m.owner or 'unassigned'}"
            )

    # Tier ladder.
    if on_pace_pct < 0.50 or cp_slips >= 3:
        tier = "off_track"
        note = (
            f"Off-track: {on_pace_pct*100:.0f}% of due "
            f"milestones complete, {cp_slips} critical-"
            "path slip(s). Partner: ops-committee "
            "escalation; CEO / COO meeting this week."
        )
    elif on_pace_pct < 0.70 or cp_slips >= 2:
        tier = "at_risk"
        note = (
            f"At risk: {on_pace_pct*100:.0f}% of due "
            f"milestones complete, {cp_slips} critical "
            "slip(s). Partner: week-over-week ops "
            "review until back on pace."
        )
    elif on_pace_pct < 0.90 or cp_slips >= 1:
        tier = "behind"
        note = (
            f"Behind: {on_pace_pct*100:.0f}% of due "
            f"complete, {cp_slips} critical slip. "
            "Partner: owner accountability check on "
            "flagged milestones."
        )
    else:
        tier = "on_pace"
        note = (
            f"On pace: {on_pace_pct*100:.0f}% of due "
            f"milestones complete, no critical slips. "
            "Partner: proceed; normal cadence."
        )

    return VelocityReport(
        tier=tier,
        current_day=inputs.current_day,
        milestones_due_to_date=len(due_to_date),
        milestones_complete=len(complete_due),
        on_pace_pct=round(on_pace_pct, 3),
        critical_path_slips=cp_slips,
        at_risk_count=at_risk,
        escalation_list=escalations,
        partner_note=note,
    )


def render_velocity_markdown(
    r: VelocityReport,
) -> str:
    lines = [
        "# Integration velocity",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Current day: {r.current_day}",
        f"- Due to date: {r.milestones_due_to_date}",
        f"- Complete: {r.milestones_complete}",
        f"- On-pace: {r.on_pace_pct*100:.1f}%",
        f"- Critical-path slips: {r.critical_path_slips}",
        f"- At-risk items: {r.at_risk_count}",
        "",
    ]
    if r.escalation_list:
        lines.append("## Escalations")
        lines.append("")
        for e in r.escalation_list:
            lines.append(f"- {e}")
    return "\n".join(lines)
