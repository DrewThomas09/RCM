"""Exit planning — year-by-year exit preparation roadmap.

Different from `exit_readiness.py` (a one-time scorecard) — this
module generates a forward-looking year-by-year roadmap of exit
preparation milestones for a given hold.

The roadmap front-loads governance + data hygiene in early years,
then shifts to exit-timing and buyer-universe cultivation in later
years.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExitMilestone:
    year: int
    quarter: int
    workstream: str                   # "governance" | "finance" | "commercial" | "operations" | "exit"
    milestone: str
    owner: str = ""
    criticality: str = "P1"           # "P0" | "P1" | "P2"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "quarter": self.quarter,
            "workstream": self.workstream,
            "milestone": self.milestone,
            "owner": self.owner,
            "criticality": self.criticality,
        }


@dataclass
class ExitPlanInputs:
    hold_years: int
    target_exit_type: Optional[str] = None    # "strategic" | "sponsor" | "ipo" | "continuation"
    has_rollup_thesis: Optional[bool] = None
    has_rcm_thesis: Optional[bool] = None
    is_distressed: Optional[bool] = None


@dataclass
class ExitPlan:
    milestones: List[ExitMilestone] = field(default_factory=list)
    target_exit_type: Optional[str] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestones": [m.to_dict() for m in self.milestones],
            "target_exit_type": self.target_exit_type,
            "partner_note": self.partner_note,
        }

    def by_year(self) -> Dict[int, List[ExitMilestone]]:
        out: Dict[int, List[ExitMilestone]] = {}
        for m in self.milestones:
            out.setdefault(m.year, []).append(m)
        for y in out:
            out[y].sort(key=lambda m: (m.quarter, m.criticality))
        return out


# ── Milestone builders ──────────────────────────────────────────────

def _year_1_milestones() -> List[ExitMilestone]:
    return [
        ExitMilestone(year=1, quarter=1, workstream="governance",
                      milestone="Standup monthly close + KPI dashboard",
                      owner="CFO", criticality="P0"),
        ExitMilestone(year=1, quarter=1, workstream="finance",
                      milestone="Engage audit firm for 3yr GAAP review",
                      owner="CFO", criticality="P0"),
        ExitMilestone(year=1, quarter=2, workstream="commercial",
                      milestone="Segment customer/payer P&L detail",
                      owner="COO", criticality="P1"),
        ExitMilestone(year=1, quarter=4, workstream="operations",
                      milestone="Year-1 lever checkpoint + recalibration",
                      owner="operating_partner", criticality="P0"),
    ]


def _mid_years_milestones(hold: int) -> List[ExitMilestone]:
    out: List[ExitMilestone] = []
    mid = max(2, hold // 2)
    out.append(ExitMilestone(
        year=mid, quarter=2, workstream="exit",
        milestone="Identify 5-10 strategic buyer candidates",
        owner="IC_partner", criticality="P1"))
    out.append(ExitMilestone(
        year=mid, quarter=2, workstream="finance",
        milestone="Financial-systems hygiene — close cadence to 7 days",
        owner="CFO", criticality="P1"))
    out.append(ExitMilestone(
        year=mid, quarter=4, workstream="commercial",
        milestone="Mid-hold customer-referenceability review",
        owner="COO", criticality="P2"))
    return out


def _pre_exit_milestones(hold: int) -> List[ExitMilestone]:
    # 12-18 months before exit.
    pre_year = max(2, hold - 2)
    return [
        ExitMilestone(year=pre_year, quarter=1, workstream="exit",
                      milestone="Engage sell-side advisor + QoE firm",
                      owner="IC_partner", criticality="P0"),
        ExitMilestone(year=pre_year, quarter=2, workstream="exit",
                      milestone="Build cleaned data room (dry run)",
                      owner="CFO", criticality="P0"),
        ExitMilestone(year=pre_year, quarter=3, workstream="exit",
                      milestone="Management presentation materials + rehearsal",
                      owner="CEO", criticality="P1"),
        ExitMilestone(year=pre_year, quarter=4, workstream="exit",
                      milestone="CIM draft + buyer-list final",
                      owner="IC_partner", criticality="P0"),
    ]


def _exit_year_milestones(hold: int) -> List[ExitMilestone]:
    return [
        ExitMilestone(year=hold, quarter=1, workstream="exit",
                      milestone="Soft-launch with 3-5 lead strategic buyers",
                      owner="IC_partner", criticality="P0"),
        ExitMilestone(year=hold, quarter=2, workstream="exit",
                      milestone="Formal process launch (IOIs due)",
                      owner="IC_partner", criticality="P0"),
        ExitMilestone(year=hold, quarter=3, workstream="exit",
                      milestone="Management presentations + LOIs",
                      owner="CEO", criticality="P0"),
        ExitMilestone(year=hold, quarter=4, workstream="exit",
                      milestone="SPA negotiation + close",
                      owner="IC_partner", criticality="P0"),
    ]


# ── Orchestrator ────────────────────────────────────────────────────

def build_exit_plan(inputs: ExitPlanInputs) -> ExitPlan:
    """Build a year-by-year exit preparation roadmap."""
    hold = max(3, int(inputs.hold_years))
    milestones: List[ExitMilestone] = []

    milestones.extend(_year_1_milestones())

    # Rollup-specific
    if inputs.has_rollup_thesis:
        milestones.append(ExitMilestone(
            year=1, quarter=2, workstream="operations",
            milestone="Integration officer onboarding + systems-consolidation roadmap",
            owner="COO", criticality="P0"))
        milestones.append(ExitMilestone(
            year=2, quarter=1, workstream="operations",
            milestone="First tuck-in close + integration scorecard",
            owner="integration_officer", criticality="P1"))

    # RCM-specific
    if inputs.has_rcm_thesis:
        milestones.append(ExitMilestone(
            year=1, quarter=2, workstream="operations",
            milestone="RCM program charter + 18-month milestones",
            owner="rcm_lead", criticality="P0"))
        milestones.append(ExitMilestone(
            year=2, quarter=4, workstream="operations",
            milestone="RCM lever checkpoint — 75% of year-2 plan",
            owner="operating_partner", criticality="P1"))

    # Distressed-specific
    if inputs.is_distressed:
        milestones.append(ExitMilestone(
            year=1, quarter=1, workstream="governance",
            milestone="Turnaround plan approval + creditor engagement",
            owner="CEO", criticality="P0"))

    # Mid-years
    if hold >= 4:
        milestones.extend(_mid_years_milestones(hold))

    # Pre-exit
    if hold >= 4:
        milestones.extend(_pre_exit_milestones(hold))

    # Exit year
    milestones.extend(_exit_year_milestones(hold))

    if inputs.target_exit_type == "ipo":
        milestones.append(ExitMilestone(
            year=max(1, hold - 1), quarter=1, workstream="exit",
            milestone="S-1 prep + SOX readiness",
            owner="CFO", criticality="P0"))
        milestones.append(ExitMilestone(
            year=hold, quarter=1, workstream="exit",
            milestone="Investment bank syndicate selection",
            owner="IC_partner", criticality="P0"))

    note = (f"Exit plan assumes {hold}-year hold, target exit type "
            f"{inputs.target_exit_type or 'undetermined'}. Milestones are "
            "indicative — operating-partner edits each quarter.")

    return ExitPlan(
        milestones=milestones,
        target_exit_type=inputs.target_exit_type,
        partner_note=note,
    )


def render_exit_plan_markdown(plan: ExitPlan) -> str:
    lines = [
        "# Exit preparation roadmap",
        "",
        f"**Target exit type:** {plan.target_exit_type or 'undetermined'}",
        "",
        f"_{plan.partner_note}_",
        "",
    ]
    for year, milestones in sorted(plan.by_year().items()):
        lines.extend([f"## Year {year}", ""])
        for m in milestones:
            lines.append(
                f"- **Y{m.year} Q{m.quarter} [{m.criticality}] "
                f"{m.workstream}** — {m.milestone} (owner: {m.owner or '—'})"
            )
        lines.append("")
    return "\n".join(lines)
