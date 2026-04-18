"""Diligence workstream tracker.

During diligence a deal team runs multiple parallel workstreams:
financial, commercial, operational, legal, IT, regulatory. Each has
owners, deadlines, and "critical findings" that may change the bid.

This module is a lightweight tracker — not a CRM. It answers:

- What's the current status of each workstream?
- Which workstreams are blocking IC?
- Which findings have been flagged and by whom?
- What's the overall diligence completion %?

It pairs with the :mod:`partner_review` output: the review's
heuristic hits suggest new workstream items; the tracker records
what's been done.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


# ── Status vocabulary ───────────────────────────────────────────────

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_BLOCKED = "blocked"
STATUS_COMPLETE = "complete"
STATUS_DROPPED = "dropped"

ALL_STATUSES = (STATUS_NOT_STARTED, STATUS_IN_PROGRESS,
                STATUS_BLOCKED, STATUS_COMPLETE, STATUS_DROPPED)


# ── Workstreams ─────────────────────────────────────────────────────

WORKSTREAMS = (
    "financial",
    "commercial",
    "operational",
    "legal",
    "it",
    "regulatory",
    "quality_of_earnings",
    "hr_benefits",
    "tax",
    "environmental",
    "insurance",
)


# ── Dataclasses ─────────────────────────────────────────────────────

@dataclass
class DiligenceItem:
    id: str
    workstream: str
    title: str
    owner: str = ""                          # "JD" / email / team
    status: str = STATUS_NOT_STARTED
    priority: str = "P1"                     # "P0" | "P1" | "P2"
    due_date: Optional[date] = None
    blocker: str = ""                        # populated when status == BLOCKED
    finding: str = ""                        # the answer once status == COMPLETE
    is_critical: bool = False                # critical findings can shift bid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workstream": self.workstream,
            "title": self.title,
            "owner": self.owner,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "blocker": self.blocker,
            "finding": self.finding,
            "is_critical": self.is_critical,
        }


@dataclass
class DiligenceBoard:
    """A collection of DiligenceItems keyed by item id."""
    items: Dict[str, DiligenceItem] = field(default_factory=dict)
    deal_id: str = ""
    deal_name: str = ""

    def add(self, item: DiligenceItem) -> None:
        self.items[item.id] = item

    def update_status(self, item_id: str, status: str,
                      *, blocker: str = "", finding: str = "") -> None:
        if item_id not in self.items:
            raise KeyError(item_id)
        item = self.items[item_id]
        item.status = status
        if blocker:
            item.blocker = blocker
        if finding:
            item.finding = finding

    def by_workstream(self) -> Dict[str, List[DiligenceItem]]:
        out: Dict[str, List[DiligenceItem]] = {}
        for item in self.items.values():
            out.setdefault(item.workstream, []).append(item)
        for ws in out:
            out[ws].sort(key=lambda i: (_priority_rank(i.priority),
                                         _status_rank(i.status)))
        return out

    def completion_pct(self) -> float:
        if not self.items:
            return 0.0
        # Dropped items don't count toward either numerator or denominator.
        effective = [i for i in self.items.values() if i.status != STATUS_DROPPED]
        if not effective:
            return 0.0
        done = sum(1 for i in effective if i.status == STATUS_COMPLETE)
        return done / len(effective)

    def critical_open(self) -> List[DiligenceItem]:
        return [i for i in self.items.values()
                if i.is_critical and i.status not in (STATUS_COMPLETE, STATUS_DROPPED)]

    def blockers(self) -> List[DiligenceItem]:
        return [i for i in self.items.values() if i.status == STATUS_BLOCKED]

    def is_ic_ready(self) -> bool:
        """IC-ready means every P0 is complete and no critical blockers."""
        for i in self.items.values():
            if i.priority == "P0" and i.status != STATUS_COMPLETE:
                return False
            if i.is_critical and i.status == STATUS_BLOCKED:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "items": {k: v.to_dict() for k, v in self.items.items()},
        }


def _priority_rank(p: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2}.get(p, 3)


def _status_rank(s: str) -> int:
    return {
        STATUS_BLOCKED: 0,
        STATUS_NOT_STARTED: 1,
        STATUS_IN_PROGRESS: 2,
        STATUS_COMPLETE: 3,
        STATUS_DROPPED: 4,
    }.get(s, 5)


# ── Board from PartnerReview heuristic hits ─────────────────────────

def _ws_for_hit(hit_id: str, category: str) -> str:
    """Map a heuristic hit to a likely workstream."""
    direct = {
        "aggressive_denial_improvement": "operational",
        "ar_days_above_peer": "operational",
        "denial_rate_elevated": "operational",
        "writeoff_rate_high": "operational",
        "contract_labor_dependency": "hr_benefits",
        "case_mix_missing": "operational",
        "insufficient_data_coverage": "financial",
        "covenant_headroom_tight": "financial",
        "leverage_too_high_govt_mix": "financial",
        "multiple_expansion_carrying_return": "financial",
        "moic_cagr_too_high": "financial",
        "small_deal_mega_irr": "financial",
        "medicare_heavy_multiple_ceiling": "commercial",
        "capitation_vbc_uses_ffs_growth": "commercial",
        "state_medicaid_volatility": "regulatory",
        "prior_regulatory_action": "regulatory",
        "340b_margin_dependency": "regulatory",
        "known_rate_cliff_in_hold": "regulatory",
        "ehr_migration_planned": "it",
        "hold_too_short_for_rcm": "financial",
        "margin_expansion_too_fast": "financial",
        "payer_concentration_risk": "commercial",
        "service_line_concentration": "commercial",
        "covid_relief_unwind": "quality_of_earnings",
        "critical_access_reimbursement": "regulatory",
        "teaching_hospital_complexity": "regulatory",
        "quality_score_below_peer": "regulatory",
        "debt_maturity_in_hold": "financial",
        "ar_reduction_aggressive": "operational",
    }
    if hit_id in direct:
        return direct[hit_id]
    # Fall back to category
    cat_map = {
        "VALUATION": "financial",
        "OPERATIONS": "operational",
        "STRUCTURE": "financial",
        "PAYER": "commercial",
        "DATA": "operational",
        "REGULATORY": "regulatory",
        "FINANCIAL": "financial",
    }
    return cat_map.get(category, "operational")


def board_from_review(review: Any) -> DiligenceBoard:
    """Build an initial DiligenceBoard from a PartnerReview.

    Each heuristic hit becomes a diligence item. Hit severity maps to
    priority: CRITICAL → P0, HIGH → P0, MEDIUM → P1, LOW → P2.
    """
    # Lazy import to avoid a circular reference on package load.
    from .partner_review import PartnerReview  # noqa: F401

    deal_id = getattr(review, "deal_id", "")
    deal_name = getattr(review, "deal_name", "")
    board = DiligenceBoard(deal_id=deal_id, deal_name=deal_name)
    sev_to_prio = {"CRITICAL": "P0", "HIGH": "P0",
                   "MEDIUM": "P1", "LOW": "P2", "INFO": "P2"}
    for i, hit in enumerate(getattr(review, "heuristic_hits", []) or [], start=1):
        ws = _ws_for_hit(hit.id, hit.category)
        item = DiligenceItem(
            id=f"{ws}_{hit.id}",
            workstream=ws,
            title=hit.title,
            owner="",
            status=STATUS_NOT_STARTED,
            priority=sev_to_prio.get(hit.severity, "P1"),
            is_critical=(hit.severity in ("CRITICAL", "HIGH")),
        )
        board.add(item)
    return board


# ── Rendering ───────────────────────────────────────────────────────

def render_board_markdown(board: DiligenceBoard) -> str:
    """Render a DiligenceBoard as Markdown."""
    name = board.deal_name or board.deal_id or "Deal"
    lines: List[str] = [
        f"# Diligence Board — {name}",
        "",
        f"**Completion:** {board.completion_pct()*100:.0f}%  ",
        f"**Critical open:** {len(board.critical_open())}  ",
        f"**Blockers:** {len(board.blockers())}  ",
        f"**IC-ready:** {'yes' if board.is_ic_ready() else 'no'}",
        "",
    ]
    grouped = board.by_workstream()
    for ws in WORKSTREAMS:
        items = grouped.get(ws, [])
        if not items:
            continue
        lines.append(f"## {ws.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Priority | Status | Owner | Item | Finding / Blocker |")
        lines.append("|:--------:|:------:|:------|:-----|:-----------------|")
        for item in items:
            cell = item.finding or item.blocker or ""
            lines.append(
                f"| {item.priority} | {item.status} | {item.owner or '—'} | "
                f"{item.title} | {cell} |"
            )
        lines.append("")
    return "\n".join(lines)
