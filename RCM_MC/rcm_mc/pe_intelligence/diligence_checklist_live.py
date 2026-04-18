"""Live diligence checklist — what the packet answers vs what needs MI.

Partners need a workable diligence checklist. For each canonical
item, the system should know:

- Is this **answered by packet** (a data-derivable question)?
- Does it **need management interview** (culture / intent / plan)?
- Does it **need third-party verification** (QofE, legal, clinical
  quality)?

This module walks a canonical 30-item diligence list against the
packet-derived context dict. Each item emits a status:

- `answered` — packet tells us.
- `needs_mi` — has to come from management.
- `needs_third_party` — QofE / legal / clinical.
- `stale` — packet has data but it is > 90 days old.
- `missing` — no data and no interview planned.

Output: a prioritized list with a partner note on how close we are
to IC-ready.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ChecklistItem:
    name: str
    category: str                         # "financial"/"clinical"/"legal"/"ops"
    description: str
    source: str                           # "packet" / "mi" / "third_party"


CANONICAL_ITEMS: List[ChecklistItem] = [
    # Financial.
    ChecklistItem("historical_ebitda_trend", "financial",
                  "3-year EBITDA trajectory with one-time adjustments",
                  "packet"),
    ChecklistItem("qofe_final", "financial",
                  "Final QofE with supported adjustments",
                  "third_party"),
    ChecklistItem("revenue_by_payer", "financial",
                  "Revenue % by payer class and top payer identity",
                  "packet"),
    ChecklistItem("nwc_normalized", "financial",
                  "Normalized NWC target and peg",
                  "third_party"),
    ChecklistItem("capex_history", "financial",
                  "3-year capex by category (maintenance vs growth)",
                  "packet"),
    ChecklistItem("debt_maturity_schedule", "financial",
                  "Tranche-level maturity + rate + covenants",
                  "packet"),
    ChecklistItem("recurring_vs_onetime_split", "financial",
                  "EBITDA split into recurring + one-time",
                  "packet"),

    # Clinical.
    ChecklistItem("cms_survey_history", "clinical",
                  "CMS survey findings over 3 years",
                  "packet"),
    ChecklistItem("quality_measures", "clinical",
                  "HEDIS/CMS quality scores by site",
                  "packet"),
    ChecklistItem("clinical_leadership_plan", "clinical",
                  "Named clinical leadership + retention plans",
                  "mi"),
    ChecklistItem("quality_improvement_program", "clinical",
                  "Documented QI program + recent changes",
                  "mi"),
    ChecklistItem("open_regulatory_actions", "clinical",
                  "Open DOJ/OIG/state investigations",
                  "third_party"),

    # Legal.
    ChecklistItem("material_litigation", "legal",
                  "Material litigation including whistleblower",
                  "third_party"),
    ChecklistItem("fca_exposure", "legal",
                  "False Claims Act exposure review",
                  "third_party"),
    ChecklistItem("stark_kickback_review", "legal",
                  "Stark + anti-kickback compliance review",
                  "third_party"),
    ChecklistItem("ma_history", "legal",
                  "Prior acquisitions + representations survive",
                  "packet"),
    ChecklistItem("environmental_review", "legal",
                  "Phase I/II environmental on owned property",
                  "third_party"),

    # Operations.
    ChecklistItem("denial_rate_trend", "ops",
                  "12-month denial rate trend + by payer",
                  "packet"),
    ChecklistItem("days_in_ar_trend", "ops",
                  "DAR trend by payer class",
                  "packet"),
    ChecklistItem("staffing_pipeline", "ops",
                  "Open reqs by role + time-to-fill",
                  "packet"),
    ChecklistItem("management_succession", "ops",
                  "Named succession for CEO / CFO / CMO",
                  "mi"),
    ChecklistItem("it_systems_inventory", "ops",
                  "EHR / billing / HR systems age + vendor",
                  "packet"),
    ChecklistItem("cybersecurity_posture", "ops",
                  "SOC 2 / HITRUST / recent pen test",
                  "third_party"),
    ChecklistItem("integration_playbook", "ops",
                  "Documented integration playbook for bolt-ons",
                  "mi"),

    # Strategy.
    ChecklistItem("thesis_validation", "financial",
                  "Thesis pillars validated against peer data",
                  "packet"),
    ChecklistItem("management_growth_plan", "ops",
                  "Management's 3-year growth plan + assumptions",
                  "mi"),
    ChecklistItem("pipeline_of_bolt_ons", "ops",
                  "Named bolt-on pipeline with LOI status",
                  "mi"),
    ChecklistItem("exit_preparation", "financial",
                  "Exit readiness assessment + strategic buyer list",
                  "mi"),
    ChecklistItem("covenant_headroom", "financial",
                  "Current covenant levels + headroom",
                  "packet"),
    ChecklistItem("insurance_coverage", "legal",
                  "Professional liability + cyber + D&O tower",
                  "third_party"),
]


@dataclass
class ChecklistStatus:
    item: ChecklistItem
    status: str                           # "answered"/"needs_mi"/
                                          # "needs_third_party"/"stale"/
                                          # "missing"
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.item.name,
            "category": self.item.category,
            "description": self.item.description,
            "source": self.item.source,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class ChecklistReport:
    items: List[ChecklistStatus] = field(default_factory=list)
    answered_count: int = 0
    mi_open_count: int = 0
    third_party_open_count: int = 0
    stale_count: int = 0
    missing_count: int = 0
    ic_ready_pct: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "answered_count": self.answered_count,
            "mi_open_count": self.mi_open_count,
            "third_party_open_count": self.third_party_open_count,
            "stale_count": self.stale_count,
            "missing_count": self.missing_count,
            "ic_ready_pct": self.ic_ready_pct,
            "partner_note": self.partner_note,
        }


def _status(item: ChecklistItem,
             ctx: Dict[str, Any]) -> ChecklistStatus:
    # Keys expected in ctx: packet_fields (set), mi_scheduled (set),
    # mi_complete (set), third_party_complete (set), stale_fields (set).
    packet_fields = set(ctx.get("packet_fields", []))
    mi_complete = set(ctx.get("mi_complete", []))
    mi_scheduled = set(ctx.get("mi_scheduled", []))
    tp_complete = set(ctx.get("third_party_complete", []))
    stale = set(ctx.get("stale_fields", []))

    if item.source == "packet":
        if item.name in stale:
            return ChecklistStatus(item, "stale",
                                    "Packet data > 90 days old")
        if item.name in packet_fields:
            return ChecklistStatus(item, "answered",
                                    "Packet answers this item")
        return ChecklistStatus(item, "missing",
                                "No packet data and no MI scheduled")
    if item.source == "mi":
        if item.name in mi_complete:
            return ChecklistStatus(item, "answered",
                                    "MI completed")
        if item.name in mi_scheduled:
            return ChecklistStatus(item, "needs_mi",
                                    "MI scheduled")
        return ChecklistStatus(item, "missing",
                                "MI not scheduled")
    if item.source == "third_party":
        if item.name in tp_complete:
            return ChecklistStatus(item, "answered",
                                    "Third-party report received")
        return ChecklistStatus(item, "needs_third_party",
                                "Third-party report outstanding")
    return ChecklistStatus(item, "missing", "Unknown source type")


def walk_checklist(ctx: Dict[str, Any]) -> ChecklistReport:
    statuses = [_status(i, ctx) for i in CANONICAL_ITEMS]
    total = len(statuses)
    answered = sum(1 for s in statuses if s.status == "answered")
    mi_open = sum(1 for s in statuses if s.status == "needs_mi")
    tp_open = sum(1 for s in statuses if s.status == "needs_third_party")
    stale = sum(1 for s in statuses if s.status == "stale")
    missing = sum(1 for s in statuses if s.status == "missing")
    ic_ready_pct = answered / total if total > 0 else 0.0

    if ic_ready_pct >= 0.90:
        note = (f"{answered}/{total} answered ({ic_ready_pct*100:.0f}%). "
                "IC-ready. Remaining items can close in final-IC pass.")
    elif ic_ready_pct >= 0.70:
        note = (f"{answered}/{total} answered ({ic_ready_pct*100:.0f}%). "
                f"{mi_open} MI + {tp_open} third-party open. Target 2-3 "
                "weeks to IC-ready.")
    else:
        note = (f"Only {ic_ready_pct*100:.0f}% answered. {missing} "
                "missing-both items require either MI scheduling or "
                "third-party engagement.")

    return ChecklistReport(
        items=statuses,
        answered_count=answered,
        mi_open_count=mi_open,
        third_party_open_count=tp_open,
        stale_count=stale,
        missing_count=missing,
        ic_ready_pct=round(ic_ready_pct, 4),
        partner_note=note,
    )


def render_checklist_markdown(r: ChecklistReport) -> str:
    lines = [
        "# Live diligence checklist",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Answered: {r.answered_count}",
        f"- Needs MI: {r.mi_open_count}",
        f"- Needs third-party: {r.third_party_open_count}",
        f"- Stale: {r.stale_count}",
        f"- Missing: {r.missing_count}",
        f"- IC-ready: {r.ic_ready_pct*100:.0f}%",
        "",
        "| Item | Category | Source | Status | Detail |",
        "|---|---|---|---|---|",
    ]
    for s in r.items:
        lines.append(
            f"| {s.item.name} | {s.item.category} | {s.item.source} | "
            f"{s.status} | {s.detail} |"
        )
    return "\n".join(lines)
