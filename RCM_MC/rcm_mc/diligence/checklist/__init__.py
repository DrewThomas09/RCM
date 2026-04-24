"""Diligence Checklist + Open Questions Tracker.

The orchestration layer a PE analyst actually uses day-to-day.
Every item is a partner-readable question ("Has the CCD been
ingested?", "Has Stark compliance been reviewed?") with a
priority (P0/P1/P2), an owner, and — crucially — an optional
automatic-completion check that links the item to an analytic
module. Running the analytic marks the item done without manual
bookkeeping.

Why this is the highest-leverage missing piece:

    Every firm already has a diligence checklist. Partners keep
    it in Word, Excel, Airtable, or their heads. Maintaining it
    by hand across a 3-week engagement is the #1 friction point
    for associates. Automating completion tracking tied to the
    live analytics is what turns the tool into the analyst's
    daily workspace instead of an ad-hoc reporting layer.

Public API::

    from rcm_mc.diligence.checklist import (
        ChecklistItem, ChecklistStatus, DealChecklistState,
        DealObservations, ItemStatus, Priority,
        build_checklist, compute_status,
        open_questions_for_ic_packet,
    )
"""
from __future__ import annotations

from .items import (
    Category, ChecklistItem, Owner, Priority,
    CHECKLIST_ITEMS, build_checklist,
)
from .tracker import (
    ChecklistStatus, DealChecklistState, DealObservations,
    ItemStatus, compute_status, open_questions_for_ic_packet,
    summarize_coverage,
)

__all__ = [
    "CHECKLIST_ITEMS",
    "Category",
    "ChecklistItem",
    "ChecklistStatus",
    "DealChecklistState",
    "DealObservations",
    "ItemStatus",
    "Owner",
    "Priority",
    "build_checklist",
    "compute_status",
    "open_questions_for_ic_packet",
    "summarize_coverage",
]
