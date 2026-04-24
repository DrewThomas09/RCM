"""Physician Economic Unit Analyzer — named per-provider P&L.

Answers the question partners ask every physician-group deal:
"which of these providers are net-negative contributors even at
fair-market comp?"

Combines three public + CCD-derived signals per provider:

    1. Revenue    — collections from the CCD (or reported)
    2. Direct cost — total comp (base + productivity + stipend +
       call + admin)
    3. Allocated overhead — proportional share of roster overhead

Produces a per-provider contribution margin, ranks the roster,
and identifies the loss-making tail. The output is a bridge-
lever input: "drop these named providers at close via retention-
structure → EBITDA +$X."

Why this is unique:
    MGMA / VMG / Chartis produce aggregate comp benchmarks.
    Nobody productizes per-physician economic contribution using
    public-data + CCD. Every partner-facing output is a named
    provider with a specific dollar delta.

Public API::

    from rcm_mc.diligence.physician_eu import (
        EconomicUnitReport, ProviderEconomicUnit,
        RosterOptimization, analyze_roster_eu,
        contribution_margin,
    )
"""
from __future__ import annotations

from .features import (
    ProviderEconomicUnit, allocated_overhead_per_provider,
    compute_economic_unit, contribution_margin,
    direct_cost,
)
from .analyzer import (
    EconomicUnitReport, RosterOptimization,
    analyze_roster_eu,
)

__all__ = [
    "EconomicUnitReport",
    "ProviderEconomicUnit",
    "RosterOptimization",
    "allocated_overhead_per_provider",
    "analyze_roster_eu",
    "compute_economic_unit",
    "contribution_margin",
    "direct_cost",
]
