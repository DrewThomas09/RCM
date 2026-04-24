"""Regulatory Calendar × Thesis Kill-Switch.

Every PE healthcare deal dies on a regulatory surprise the firm
knew was coming. CMS / OIG / FTC / DOJ / CMS IDR all publish their
rule-making calendars publicly. Nobody productizes them against
a specific target's thesis drivers.

This module does three things:

    1. Maintains a curated library of upcoming regulatory events
       with publish-date schedules, affected specialties, and
       expected revenue/margin impact
    2. Maps each event to the target's thesis drivers given its
       specialty × geography × payer mix × MA exposure
    3. Identifies which drivers get KILLED (>50% impairment) vs
       DAMAGED (10-50%) vs UNAFFECTED, with the specific date each
       kill takes effect

Demo moment:
    A partner sees a gantt chart showing their thesis driver #1
    (MA margin lift) dying on April 12, 2026 when CMS V28 final
    rule publishes. That specific-date specificity is the demo
    output no other diligence tool produces.

Public API::

    from rcm_mc.diligence.regulatory_calendar import (
        KillSwitchVerdict, RegulatoryEvent, ThesisDriver,
        ThesisImpact, analyze_regulatory_exposure,
        upcoming_events,
    )
"""
from __future__ import annotations

from .calendar import (
    REGULATORY_EVENTS, RegulatoryEvent, events_for_specialty,
    upcoming_events,
)
from .impact_mapper import (
    DriverCategory, ThesisDriver, ThesisImpact,
    map_event_to_drivers, DEFAULT_THESIS_DRIVERS,
)
from .killswitch import (
    KillSwitchVerdict, RegulatoryExposureReport,
    analyze_regulatory_exposure,
)

__all__ = [
    "DEFAULT_THESIS_DRIVERS",
    "DriverCategory",
    "KillSwitchVerdict",
    "REGULATORY_EVENTS",
    "RegulatoryEvent",
    "RegulatoryExposureReport",
    "ThesisDriver",
    "ThesisImpact",
    "analyze_regulatory_exposure",
    "events_for_specialty",
    "map_event_to_drivers",
    "upcoming_events",
]
