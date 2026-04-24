"""Tracker — compute per-item status from observable deal state.

The tracker is stateless (for now): given a
:class:`DealObservations` snapshot describing what has / has not
been run against the deal, it emits a
:class:`DealChecklistState` with per-item status. Partners can
layer manual overrides on top (``manual_completed_ids``,
``manual_blocked_ids``) when automation can't see a real-world
event (a management reference call, a legal sign-off).

No persistence layer is assumed — the UI rebuilds the state on
every render. When the engagement-store lands, this module will
grow a ``load_state(engagement_id)`` path; today it's pure
function so it tests cleanly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .items import (
    CHECKLIST_ITEMS, Category, ChecklistItem, Owner, Priority,
)


class ItemStatus(str, Enum):
    """Per-item rollup."""
    DONE = "DONE"
    IN_PROGRESS = "IN_PROGRESS"
    OPEN = "OPEN"
    BLOCKED = "BLOCKED"


@dataclass
class DealObservations:
    """What is observable about the deal's diligence state.

    Each field corresponds to ``auto_check_key`` values in
    :mod:`rcm_mc.diligence.checklist.items`. A field that's
    ``True`` marks the linked checklist item DONE automatically;
    ``False`` leaves it OPEN; ``None`` means unknown (treated as
    OPEN for P0 items, IN_PROGRESS for P1/P2 with an owner).
    """
    # Phase 1: Pre-NDA
    bankruptcy_scan_run: Optional[bool] = None
    deal_autopsy_run: Optional[bool] = None
    sector_sentiment_reviewed: Optional[bool] = None

    # Phase 2: CCD + benchmarks
    ccd_ingested: Optional[bool] = None
    hfma_days_in_ar_computed: Optional[bool] = None
    hfma_denial_rate_computed: Optional[bool] = None
    hfma_ar_aging_computed: Optional[bool] = None
    hfma_cost_to_collect_computed: Optional[bool] = None
    hfma_nrr_computed: Optional[bool] = None
    cohort_liquidation_computed: Optional[bool] = None
    denial_pareto_computed: Optional[bool] = None
    qor_waterfall_computed: Optional[bool] = None

    # Phase 2b: Predictive
    denial_prediction_run: Optional[bool] = None
    physician_attrition_run: Optional[bool] = None

    # Phase 3: Risk workbench
    regulatory_calendar_run: Optional[bool] = None
    hcris_xray_run: Optional[bool] = None
    payer_stress_run: Optional[bool] = None
    cpom_run: Optional[bool] = None
    nsa_run: Optional[bool] = None
    steward_run: Optional[bool] = None
    team_run: Optional[bool] = None
    antitrust_run: Optional[bool] = None
    cyber_run: Optional[bool] = None
    ma_v28_run: Optional[bool] = None
    physician_comp_fmv_run: Optional[bool] = None
    labor_referral_run: Optional[bool] = None
    patient_pay_run: Optional[bool] = None

    # Phase 4: Financial
    ebitda_bridge_built: Optional[bool] = None
    deal_mc_run: Optional[bool] = None
    covenant_stress_run: Optional[bool] = None
    counterfactual_run: Optional[bool] = None
    market_intel_run: Optional[bool] = None
    working_capital_peg_set: Optional[bool] = None

    # Phase 5: Deliverables
    qoe_memo_generated: Optional[bool] = None
    ic_packet_assembled: Optional[bool] = None

    def as_dict(self) -> Dict[str, Optional[bool]]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ChecklistStatus:
    """Per-item status envelope returned by the tracker."""
    item: ChecklistItem
    status: ItemStatus
    # Partner-provided note visible on the item row (optional).
    note: Optional[str] = None
    # Derived convenience fields
    @property
    def is_open_p0(self) -> bool:
        return (
            self.status in (ItemStatus.OPEN, ItemStatus.BLOCKED)
            and self.item.priority == Priority.P0
        )

    @property
    def is_open_p1(self) -> bool:
        return (
            self.status in (ItemStatus.OPEN, ItemStatus.BLOCKED)
            and self.item.priority == Priority.P1
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item.item_id,
            "phase": self.item.phase,
            "category": self.item.category.value,
            "priority": self.item.priority.value,
            "question": self.item.question,
            "default_owner": self.item.default_owner.value,
            "evidence_url": self.item.evidence_url,
            "completion_criteria": self.item.completion_criteria,
            "auto_check_key": self.item.auto_check_key,
            "status": self.status.value,
            "note": self.note,
        }


@dataclass
class DealChecklistState:
    """Roster-level output — every item with its current status."""
    items: List[ChecklistStatus] = field(default_factory=list)
    # Aggregate counts
    total: int = 0
    done: int = 0
    in_progress: int = 0
    open_: int = 0
    blocked: int = 0
    # P0/P1-specific open counts (blocking IC)
    open_p0: int = 0
    open_p1: int = 0
    # Coverage = share of P0 items that are DONE
    p0_coverage: float = 0.0
    total_coverage: float = 0.0

    def by_category(self) -> Dict[Category, List[ChecklistStatus]]:
        out: Dict[Category, List[ChecklistStatus]] = {}
        for s in self.items:
            out.setdefault(s.item.category, []).append(s)
        return out

    def by_phase(self) -> Dict[int, List[ChecklistStatus]]:
        out: Dict[int, List[ChecklistStatus]] = {}
        for s in self.items:
            out.setdefault(s.item.phase, []).append(s)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "done": self.done,
            "in_progress": self.in_progress,
            "open": self.open_,
            "blocked": self.blocked,
            "open_p0": self.open_p0,
            "open_p1": self.open_p1,
            "p0_coverage": self.p0_coverage,
            "total_coverage": self.total_coverage,
            "items": [s.to_dict() for s in self.items],
        }


# ────────────────────────────────────────────────────────────────────
# Status compute
# ────────────────────────────────────────────────────────────────────

def _status_for(
    item: ChecklistItem,
    obs: DealObservations,
    manual_completed: Set[str],
    manual_blocked: Set[str],
    manual_in_progress: Set[str],
) -> ItemStatus:
    """Resolve a single item's status.

    Precedence (highest first):
        1. Manual override — BLOCKED takes priority over COMPLETED
           over IN_PROGRESS.
        2. Auto-check — if the observable is True → DONE; False →
           OPEN; None + auto_check_key exists → OPEN.
        3. No auto_check_key → OPEN (manual-only item).
    """
    if item.item_id in manual_blocked:
        return ItemStatus.BLOCKED
    if item.item_id in manual_completed:
        return ItemStatus.DONE
    if item.item_id in manual_in_progress:
        return ItemStatus.IN_PROGRESS
    if item.auto_check_key is None:
        return ItemStatus.OPEN
    raw = getattr(obs, item.auto_check_key, None)
    if raw is True:
        return ItemStatus.DONE
    if raw is False:
        return ItemStatus.OPEN
    # None — unknown state.  For P0 items treat as OPEN (safer),
    # for P1/P2 leave as OPEN too — "not sure" is never assumed
    # done.
    return ItemStatus.OPEN


def compute_status(
    observations: Optional[DealObservations] = None,
    *,
    manual_completed_ids: Optional[Set[str]] = None,
    manual_blocked_ids: Optional[Set[str]] = None,
    manual_in_progress_ids: Optional[Set[str]] = None,
    item_notes: Optional[Dict[str, str]] = None,
) -> DealChecklistState:
    """Compute the live checklist state.

    ``manual_*`` sets carry item_ids for override behaviour —
    these let a partner mark a manual-only item (reference calls,
    legal sign-off) done.

    ``item_notes`` is a per-item note string — visible in the UI
    as a partner annotation.
    """
    observations = observations or DealObservations()
    manual_completed = manual_completed_ids or set()
    manual_blocked = manual_blocked_ids or set()
    manual_in_progress = manual_in_progress_ids or set()
    item_notes = item_notes or {}

    statuses: List[ChecklistStatus] = []
    counts = {
        ItemStatus.DONE: 0,
        ItemStatus.IN_PROGRESS: 0,
        ItemStatus.OPEN: 0,
        ItemStatus.BLOCKED: 0,
    }
    open_p0 = 0
    open_p1 = 0
    p0_total = 0
    p0_done = 0

    for item in CHECKLIST_ITEMS:
        status = _status_for(
            item, observations,
            manual_completed, manual_blocked, manual_in_progress,
        )
        counts[status] += 1
        if item.priority == Priority.P0:
            p0_total += 1
            if status == ItemStatus.DONE:
                p0_done += 1
        if status in (ItemStatus.OPEN, ItemStatus.BLOCKED):
            if item.priority == Priority.P0:
                open_p0 += 1
            elif item.priority == Priority.P1:
                open_p1 += 1
        statuses.append(ChecklistStatus(
            item=item,
            status=status,
            note=item_notes.get(item.item_id),
        ))

    total = len(statuses)
    return DealChecklistState(
        items=statuses,
        total=total,
        done=counts[ItemStatus.DONE],
        in_progress=counts[ItemStatus.IN_PROGRESS],
        open_=counts[ItemStatus.OPEN],
        blocked=counts[ItemStatus.BLOCKED],
        open_p0=open_p0,
        open_p1=open_p1,
        p0_coverage=(p0_done / p0_total) if p0_total > 0 else 0.0,
        total_coverage=(counts[ItemStatus.DONE] / total)
            if total > 0 else 0.0,
    )


def summarize_coverage(state: DealChecklistState) -> str:
    """Produce a one-sentence summary of the state for UI hero +
    IC memo."""
    if state.total == 0:
        return "No checklist items configured."
    if state.p0_coverage >= 1.0 and state.open_p1 == 0:
        return (
            f"All {state.total} diligence items covered — ready for IC."
        )
    if state.open_p0 == 0:
        return (
            f"All P0 items covered ({state.done}/{state.total} total). "
            f"{state.open_p1} P1 items remain — assign owners before IC."
        )
    return (
        f"{state.open_p0} P0 items still open + {state.open_p1} P1 — "
        f"P0 coverage {state.p0_coverage*100:.0f}%. "
        f"Do not schedule IC until P0 = 100%."
    )


# ────────────────────────────────────────────────────────────────────
# IC Packet integration
# ────────────────────────────────────────────────────────────────────

@dataclass
class OpenQuestion:
    """Shape consumed by the IC Packet open-questions section."""
    priority: str          # P0 | P1
    question: str
    owner: str
    category: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def open_questions_for_ic_packet(
    state: DealChecklistState,
    *,
    include_p2: bool = False,
) -> List[OpenQuestion]:
    """Return the list of still-open items formatted for the IC
    Packet Open-Questions section.

    Sorted by priority (P0 → P1 → P2), then phase (so screening
    items appear first, deliverables last).
    """
    out: List[OpenQuestion] = []
    for s in state.items:
        if s.status not in (ItemStatus.OPEN, ItemStatus.BLOCKED):
            continue
        if s.item.priority == Priority.P2 and not include_p2:
            continue
        out.append(OpenQuestion(
            priority=s.item.priority.value,
            question=s.item.question,
            owner=s.item.default_owner.value,
            category=s.item.category.value,
        ))
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    # Grab phase from the underlying items in a parallel pass
    phase_by_q: Dict[str, int] = {
        s.item.question: s.item.phase for s in state.items
    }
    out.sort(key=lambda q: (
        priority_rank.get(q.priority, 99),
        phase_by_q.get(q.question, 99),
    ))
    return out
