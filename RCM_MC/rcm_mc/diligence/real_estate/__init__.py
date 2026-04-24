"""Real-estate and lease-economics subpackage (Prompt H).

The "Steward module" — targets the sale-leaseback blind spot that
produced Steward (2016 MPT → 2024 bankruptcy), Prospect (2019
Leonard Green → 2025), and the REIT-backed hospital platforms
quantified by the BMJ December 2025 study as 5x closure risk.

Five submodules:

    lease_waterfall.py                 PV + rent-share + EBITDAR
                                        coverage across properties
    steward_score.py                   5-factor composite pattern
    capex_deferred_maintenance.py      Asset age + backlog estimate
    sale_leaseback_blocker.py          MA/CT/PA feasibility matrix
    specialty_rent_benchmarks.py       p25/p50/p75 rent bands by
                                        specialty

Both the regulatory package and this one form the
"Bankruptcy-Survivor Pack" that Prompt I packages as a screening
artifact.
"""
from __future__ import annotations

from .capex_deferred_maintenance import compute_capex_wall
from .lease_waterfall import compute_lease_waterfall
from .sale_leaseback_blocker import sale_leaseback_feasibility
from .specialty_rent_benchmarks import (
    classify_rent_share, get_rent_benchmark, rent_is_suicidal,
    VALID_SPECIALTIES,
)
from .steward_score import (
    ALL_FACTORS, FACTOR_COVERAGE, FACTOR_ESCALATOR,
    FACTOR_GEOGRAPHY, FACTOR_LEASE_DURATION, FACTOR_REIT_LANDLORD,
    compute_steward_score,
)
from .types import (
    CapexWall, LeaseLine, LeaseSchedule, LeaseWaterfall,
    PropertyRentSummary, SaleLeasebackBlocker, StewardRiskTier,
    StewardScoreResult,
)

__all__ = [
    "ALL_FACTORS",
    "CapexWall",
    "FACTOR_COVERAGE",
    "FACTOR_ESCALATOR",
    "FACTOR_GEOGRAPHY",
    "FACTOR_LEASE_DURATION",
    "FACTOR_REIT_LANDLORD",
    "LeaseLine",
    "LeaseSchedule",
    "LeaseWaterfall",
    "PropertyRentSummary",
    "SaleLeasebackBlocker",
    "StewardRiskTier",
    "StewardScoreResult",
    "VALID_SPECIALTIES",
    "classify_rent_share",
    "compute_capex_wall",
    "compute_lease_waterfall",
    "compute_steward_score",
    "get_rent_benchmark",
    "rent_is_suicidal",
    "sale_leaseback_feasibility",
]
