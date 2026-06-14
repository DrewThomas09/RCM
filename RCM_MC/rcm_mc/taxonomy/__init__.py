"""Healthcare-subsector taxonomy — the modular, subsector-aware layer.

A dermatology roll-up, an ASC, a home-health agency, and an MA plan are
diligenced with fundamentally different metrics, reimbursement mechanics, data
sources, and exhibits. This package codifies that as a ~55-subsector map across
six groupings, each wired to its own KPI pack, billing codes, public datasets,
2025-26 thesis/risks, and CDD exhibit templates — the Stage-1 "subsector
taxonomy object" the rest of the workbench reads to specialise its generic
TAM/PVM/payer-mix toolkit per subsector.

It crosswalks to what already exists: the four first-class
:class:`rcm_mc.verticals.registry.Vertical` metric registries
(HOSPITAL/ASC/MSO/BEHAVIORAL_HEALTH) via ``Subsector.vertical``, and the NPPES
PE-vertical tags in :mod:`rcm_mc.data_public.nucc_taxonomy` via
``Subsector.nucc_verticals`` (so a subsector turns into a live provider-supply
count). Pure data + frozen dataclasses — no network, no SQLite.

Public API::

    from rcm_mc.taxonomy import (
        Grouping, KPI, Subsector,
        all_subsectors, by_id, by_grouping, groupings, grouping_counts,
        search, central_subsectors, by_vertical, by_nucc_vertical,
    )
"""
from __future__ import annotations

from .models import Grouping, KPI, Subsector
from .registry import (
    all_subsectors,
    by_grouping,
    by_id,
    by_nucc_vertical,
    by_vertical,
    central_subsectors,
    grouping_counts,
    groupings,
    search,
)

__all__ = [
    "Grouping",
    "KPI",
    "Subsector",
    "all_subsectors",
    "by_id",
    "by_grouping",
    "groupings",
    "grouping_counts",
    "search",
    "central_subsectors",
    "by_vertical",
    "by_nucc_vertical",
]
