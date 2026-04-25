"""Scope 1/2/3 carbon accounting for healthcare facilities.

Healthcare is materially more carbon-intensive than the average
service-sector business — anesthetic gases (sevoflurane, N2O),
dialysis water consumption, ED 24/7 operations all show up.

Scope 1 (direct):
  • Natural gas heating: 0.18 kgCO2e / kWh
  • Diesel fleet: 2.68 kgCO2e / liter
  • Anesthetic gases: sevoflurane 130 kgCO2e/kg, isoflurane 510,
    N2O 298 kgCO2e/kg (100-yr GWP)

Scope 2 (purchased electricity):
  • Grid emission factor by state. Texas 0.42, Illinois 0.40,
    California 0.21, NY 0.21 kgCO2e/kWh (2024 EIA).

Scope 3 (supply chain):
  • Purchased medical supplies, business travel, waste. Modeled
    as 2.5× Scope 1+2 for hospitals (median; range 1.5–4×).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class FacilityType(str, Enum):
    HOSPITAL = "hospital"
    ASC = "asc"             # ambulatory surgery
    DIALYSIS = "dialysis"
    PHYSICIAN = "physician_office"
    BEHAVIORAL = "behavioral_health"
    HOME_HEALTH = "home_health"


@dataclass
class Facility:
    facility_id: str
    name: str
    facility_type: FacilityType
    state: str = ""
    sq_ft: int = 0
    annual_kwh: float = 0.0          # Scope 2 input
    annual_natgas_kwh: float = 0.0   # Scope 1 from heating
    fleet_diesel_l: float = 0.0      # Scope 1 from fleet
    sevoflurane_kg: float = 0.0      # Anesthetic — Scope 1
    n2o_kg: float = 0.0
    procedures_per_year: int = 0
    inpatient_beds: int = 0


@dataclass
class CarbonFootprint:
    facility_id: str
    scope_1_kgco2e: float
    scope_2_kgco2e: float
    scope_3_kgco2e: float
    total_kgco2e: float
    intensity_per_sqft: float = 0.0
    intensity_per_procedure: float = 0.0
    breakdown: Dict[str, float] = None


# State-level grid emission factors (kg CO2e per kWh)
_STATE_GRID_FACTOR = {
    "TX": 0.42, "IL": 0.40, "CA": 0.21, "NY": 0.21,
    "FL": 0.43, "PA": 0.36, "NJ": 0.21, "OH": 0.55,
    "WV": 0.78, "VA": 0.31, "GA": 0.41,
}
_DEFAULT_GRID_FACTOR = 0.40


# Scope 3 multiplier on Scope 1+2 by facility type
_SCOPE_3_MULTIPLIER = {
    FacilityType.HOSPITAL:    2.5,
    FacilityType.ASC:         1.8,
    FacilityType.DIALYSIS:    2.2,
    FacilityType.PHYSICIAN:   1.5,
    FacilityType.BEHAVIORAL:  1.4,
    FacilityType.HOME_HEALTH: 1.6,
}


def compute_scope_1_2_3(
    facility: Facility,
) -> CarbonFootprint:
    """Compute Scope 1/2/3 emissions for a single facility."""
    # ── Scope 1 ──
    s1_natgas = facility.annual_natgas_kwh * 0.18
    s1_diesel = facility.fleet_diesel_l * 2.68
    s1_sevo = facility.sevoflurane_kg * 130.0
    s1_n2o = facility.n2o_kg * 298.0
    scope_1 = s1_natgas + s1_diesel + s1_sevo + s1_n2o

    # ── Scope 2 ──
    grid_factor = _STATE_GRID_FACTOR.get(
        facility.state.upper(), _DEFAULT_GRID_FACTOR)
    scope_2 = facility.annual_kwh * grid_factor

    # ── Scope 3 ──
    multiplier = _SCOPE_3_MULTIPLIER.get(facility.facility_type, 2.0)
    scope_3 = (scope_1 + scope_2) * multiplier

    total = scope_1 + scope_2 + scope_3

    return CarbonFootprint(
        facility_id=facility.facility_id,
        scope_1_kgco2e=round(scope_1, 1),
        scope_2_kgco2e=round(scope_2, 1),
        scope_3_kgco2e=round(scope_3, 1),
        total_kgco2e=round(total, 1),
        intensity_per_sqft=(round(total / facility.sq_ft, 3)
                            if facility.sq_ft else 0.0),
        intensity_per_procedure=(
            round(total / facility.procedures_per_year, 3)
            if facility.procedures_per_year else 0.0),
        breakdown={
            "natural_gas_heating": round(s1_natgas, 1),
            "fleet_diesel": round(s1_diesel, 1),
            "sevoflurane": round(s1_sevo, 1),
            "n2o": round(s1_n2o, 1),
            "purchased_electricity": round(scope_2, 1),
            "scope_3_supply_chain": round(scope_3, 1),
        },
    )


def aggregate_portfolio_footprint(
    facilities: List[Facility],
) -> Dict[str, float]:
    """Sum across the portfolio."""
    s1 = s2 = s3 = total = 0.0
    for f in facilities:
        cf = compute_scope_1_2_3(f)
        s1 += cf.scope_1_kgco2e
        s2 += cf.scope_2_kgco2e
        s3 += cf.scope_3_kgco2e
        total += cf.total_kgco2e
    return {
        "scope_1_kgco2e": round(s1, 1),
        "scope_2_kgco2e": round(s2, 1),
        "scope_3_kgco2e": round(s3, 1),
        "total_kgco2e": round(total, 1),
        "facility_count": len(facilities),
    }
