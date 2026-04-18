"""Red-flag escalation triage — partner attention vs associate level.

Not every red flag needs a partner's 7am call. A senior partner
decides: "I'll take the FCA; you handle the denial trend." This
module takes a list of red flags and triages by the level of
senior attention they need.

Tiers:

- **Partner-immediate** — call in 24 hours; typically legal,
  regulatory, FCA, covenant, clinical-safety incidents.
- **Partner-this-week** — review at next deal-team meeting;
  typically pattern matches, material ops issues.
- **Associate** — track in the diligence tracker; typically
  specific metric gaps.
- **Informational** — note but no action required.

The triage is not severity alone — it's WHO needs to act. A
high-severity RCM issue can be associate-level if the RCM team
has it; a medium-severity legal exposure can be partner-level
because only the partner has legal/reputational authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


TIER_PARTNER_IMMEDIATE = "partner_immediate"
TIER_PARTNER_THIS_WEEK = "partner_this_week"
TIER_ASSOCIATE = "associate"
TIER_INFO = "informational"


@dataclass
class RedFlagInput:
    name: str
    severity: str = "medium"                # "low" / "medium" / "high"
    category: str = "operational"           # legal/regulatory/financial/
                                            # clinical/operational/
                                            # reputational
    specific_situation: Optional[str] = None


@dataclass
class TriageDecision:
    flag_name: str
    tier: str
    escalate_to: str                        # "MD+deal partner" / "associate"
    timeline_hours: int                     # hours to first action
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flag_name": self.flag_name,
            "tier": self.tier,
            "escalate_to": self.escalate_to,
            "timeline_hours": self.timeline_hours,
            "rationale": self.rationale,
        }


@dataclass
class TriageReport:
    decisions: List[TriageDecision] = field(default_factory=list)
    partner_immediate_count: int = 0
    partner_this_week_count: int = 0
    associate_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
            "partner_immediate_count": self.partner_immediate_count,
            "partner_this_week_count": self.partner_this_week_count,
            "associate_count": self.associate_count,
            "partner_note": self.partner_note,
        }


def _triage_one(flag: RedFlagInput) -> TriageDecision:
    # Legal, regulatory, FCA, clinical-safety always partner-level.
    if flag.category in ("legal", "regulatory", "reputational"):
        return TriageDecision(
            flag_name=flag.name,
            tier=TIER_PARTNER_IMMEDIATE,
            escalate_to="deal partner + GC",
            timeline_hours=24,
            rationale=(
                f"{flag.category.title()} category — reputational / "
                "fiduciary authority sits with partner. Associate "
                "does not own these."),
        )
    if flag.category == "clinical" and flag.severity == "high":
        return TriageDecision(
            flag_name=flag.name,
            tier=TIER_PARTNER_IMMEDIATE,
            escalate_to="deal partner + CMO advisor",
            timeline_hours=24,
            rationale=(
                "Clinical-safety incidents escalate to partner for "
                "liability and crisis-comms decisions."),
        )
    if flag.severity == "high" and flag.category == "financial":
        return TriageDecision(
            flag_name=flag.name,
            tier=TIER_PARTNER_THIS_WEEK,
            escalate_to="deal partner",
            timeline_hours=72,
            rationale=(
                "High-severity financial issue: covenant, QofE, or "
                "material number. Partner reviews before next IC "
                "touchpoint."),
        )
    if flag.severity == "high":
        return TriageDecision(
            flag_name=flag.name,
            tier=TIER_PARTNER_THIS_WEEK,
            escalate_to="deal partner",
            timeline_hours=72,
            rationale=(
                "High-severity operational issue — worth a 30-minute "
                "review at the partner level this week."),
        )
    if flag.severity == "medium":
        return TriageDecision(
            flag_name=flag.name,
            tier=TIER_ASSOCIATE,
            escalate_to="deal associate",
            timeline_hours=168,
            rationale=(
                "Associate-level: tracked in the diligence tracker; "
                "escalated if unresolved."),
        )
    return TriageDecision(
        flag_name=flag.name,
        tier=TIER_INFO,
        escalate_to="deal associate",
        timeline_hours=336,
        rationale="Low-severity noted; no immediate action.",
    )


def triage(flags: List[RedFlagInput]) -> TriageReport:
    decisions = [_triage_one(f) for f in flags]
    immediate = sum(1 for d in decisions
                    if d.tier == TIER_PARTNER_IMMEDIATE)
    this_week = sum(1 for d in decisions
                    if d.tier == TIER_PARTNER_THIS_WEEK)
    associate = sum(1 for d in decisions
                    if d.tier == TIER_ASSOCIATE)

    if immediate >= 2:
        note = (f"{immediate} partner-immediate red flags. These "
                "are not queue items; partner should be on the phone "
                "with counsel and the CMO advisor today.")
    elif immediate == 1:
        item = next(d for d in decisions
                     if d.tier == TIER_PARTNER_IMMEDIATE)
        note = (f"One partner-immediate flag: '{item.flag_name}'. "
                "Escalate today; don't wait for the deal-team "
                "meeting.")
    elif this_week >= 2:
        note = (f"{this_week} partner-this-week items. Block partner "
                "time at the next deal-team meeting.")
    elif associate or this_week:
        note = (f"Routine triage: {this_week} partner-this-week + "
                f"{associate} associate-level items.")
    else:
        note = ("No red flags requiring escalation.")

    return TriageReport(
        decisions=decisions,
        partner_immediate_count=immediate,
        partner_this_week_count=this_week,
        associate_count=associate,
        partner_note=note,
    )


def render_triage_markdown(r: TriageReport) -> str:
    lines = [
        "# Red-flag escalation triage",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Partner-immediate (24h): {r.partner_immediate_count}",
        f"- Partner-this-week (72h): {r.partner_this_week_count}",
        f"- Associate (7d): {r.associate_count}",
        "",
        "| Flag | Tier | Escalate to | Timeline | Rationale |",
        "|---|---|---|---:|---|",
    ]
    for d in r.decisions:
        lines.append(
            f"| {d.flag_name} | {d.tier} | {d.escalate_to} | "
            f"{d.timeline_hours}h | {d.rationale} |"
        )
    return "\n".join(lines)
