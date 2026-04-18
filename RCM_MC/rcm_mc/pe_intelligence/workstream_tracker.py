"""Workstream tracker — post-close integration workstream dashboard.

After close, operations partners track integration workstreams:
each has an owner, milestones, a target date, and a status. This
module structures the tracker and aggregates the results.

Different from `diligence_tracker.py` (which is pre-close) — this
runs post-close alongside `value_creation_tracker.py` +
`hundred_day_plan.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class WorkstreamMilestone:
    id: str
    title: str
    target_date: Optional[date] = None
    status: str = "pending"        # "pending" | "in_progress" | "done" | "delayed" | "dropped"
    owner: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "target_date": (self.target_date.isoformat()
                             if self.target_date else None),
            "status": self.status,
            "owner": self.owner,
            "notes": self.notes,
        }


@dataclass
class Workstream:
    name: str                      # "rcm" | "it" | "clinical" | "finance" | "hr" | "pmo"
    lead: str = ""
    milestones: List[WorkstreamMilestone] = field(default_factory=list)
    health: str = "green"          # "green" | "amber" | "red"
    last_update: Optional[date] = None
    partner_note: str = ""

    def completion_pct(self) -> float:
        if not self.milestones:
            return 0.0
        done = sum(1 for m in self.milestones if m.status == "done")
        total = sum(1 for m in self.milestones if m.status != "dropped")
        return done / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lead": self.lead,
            "milestones": [m.to_dict() for m in self.milestones],
            "health": self.health,
            "last_update": (self.last_update.isoformat()
                             if self.last_update else None),
            "partner_note": self.partner_note,
            "completion_pct": round(self.completion_pct(), 4),
        }


@dataclass
class WorkstreamReport:
    workstreams: List[Workstream] = field(default_factory=list)
    total_milestones: int = 0
    completed_milestones: int = 0
    delayed_count: int = 0
    overall_completion: float = 0.0
    red_streams: List[str] = field(default_factory=list)
    amber_streams: List[str] = field(default_factory=list)
    partner_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workstreams": [w.to_dict() for w in self.workstreams],
            "total_milestones": self.total_milestones,
            "completed_milestones": self.completed_milestones,
            "delayed_count": self.delayed_count,
            "overall_completion": self.overall_completion,
            "red_streams": list(self.red_streams),
            "amber_streams": list(self.amber_streams),
            "partner_summary": self.partner_summary,
        }


def aggregate_workstreams(
    workstreams: List[Workstream],
) -> WorkstreamReport:
    total = 0
    completed = 0
    delayed = 0
    red: List[str] = []
    amber: List[str] = []
    for w in workstreams:
        for m in w.milestones:
            if m.status == "dropped":
                continue
            total += 1
            if m.status == "done":
                completed += 1
            if m.status == "delayed":
                delayed += 1
        if w.health == "red":
            red.append(w.name)
        elif w.health == "amber":
            amber.append(w.name)
    overall = completed / max(total, 1)

    if red:
        summary = (f"{len(red)} workstream(s) red. Operating-partner "
                   "intervention needed now.")
    elif amber:
        summary = (f"{len(amber)} workstream(s) amber. Monitor weekly "
                   "and raise flags before they go red.")
    elif overall >= 0.80:
        summary = "Integration on track — ≥80% milestones complete."
    else:
        summary = "Integration in early innings — no material flags."

    return WorkstreamReport(
        workstreams=workstreams,
        total_milestones=total,
        completed_milestones=completed,
        delayed_count=delayed,
        overall_completion=round(overall, 4),
        red_streams=red,
        amber_streams=amber,
        partner_summary=summary,
    )


def render_workstream_report_markdown(
    report: WorkstreamReport,
) -> str:
    lines = [
        "# Integration workstream status",
        "",
        f"**Overall completion:** {report.overall_completion*100:.0f}%  ",
        f"**Milestones:** {report.completed_milestones}/{report.total_milestones}  ",
        f"**Delayed:** {report.delayed_count}",
        "",
        f"_{report.partner_summary}_",
        "",
        "## Workstreams",
        "",
        "| Workstream | Lead | Health | Completion |",
        "|---|---|---|---:|",
    ]
    for w in report.workstreams:
        lines.append(
            f"| {w.name} | {w.lead or '—'} | {w.health} | "
            f"{w.completion_pct()*100:.0f}% |"
        )
    return "\n".join(lines)
