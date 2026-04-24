"""Steward Score — five-factor composite that pattern-matches the
Steward/Prospect/MPT failure mode.

The five factors that co-occurred in Steward (2016 MPT deal →
2024 bankruptcy) and Prospect (2019 Leonard Green/MPT → 2025
bankruptcy):

    1. Lease duration at signing > 15 years
    2. Annual rent escalator > 3%
    3. EBITDAR coverage < 1.4x
    4. Rural or safety-net geography (HCRIS classification)
    5. REIT landlord (MPT, Global Medical REIT, Community
       Healthcare Trust, Omega Healthcare Investors, Healthpeak)

Tier rule (per prompt):
    5 factors → CRITICAL — full Steward pattern
    4 factors → HIGH
    3 factors → MEDIUM
    0-2 factors → LOW (insufficient for the named pattern)
"""
from __future__ import annotations

from typing import List, Optional

from .types import LeaseSchedule, StewardRiskTier, StewardScoreResult, load_content


FACTOR_LEASE_DURATION = "LEASE_DURATION_GT_15Y"
FACTOR_ESCALATOR      = "ESCALATOR_GT_3PCT"
FACTOR_COVERAGE       = "EBITDAR_COVERAGE_LT_1_4X"
FACTOR_GEOGRAPHY      = "RURAL_OR_SAFETY_NET"
FACTOR_REIT_LANDLORD  = "REIT_LANDLORD"

ALL_FACTORS = (
    FACTOR_LEASE_DURATION,
    FACTOR_ESCALATOR,
    FACTOR_COVERAGE,
    FACTOR_GEOGRAPHY,
    FACTOR_REIT_LANDLORD,
)


def _normalize_landlord(name: Optional[str]) -> str:
    return (name or "").strip().lower().replace(".", "").replace(",", "")


def _is_reit_landlord(name: Optional[str]) -> bool:
    if not name:
        return False
    try:
        content = load_content("sale_leaseback_blockers")
    except FileNotFoundError:
        return False
    landlords = content.get("high_risk_reit_landlords") or []
    target = _normalize_landlord(name)
    return any(target == _normalize_landlord(x) or
               _normalize_landlord(x) in target
               for x in landlords)


def compute_steward_score(
    schedule: LeaseSchedule,
    *,
    portfolio_ebitdar_annual_usd: Optional[float] = None,
    portfolio_annual_rent_usd: Optional[float] = None,
    geography: Optional[str] = None,       # 'RURAL', 'SAFETY_NET',
                                            # 'URBAN_ACADEMIC', etc.
) -> StewardScoreResult:
    """Score the lease schedule against the 5-factor Steward
    pattern. Returns the tier + list of factors hit."""
    hits: List[str] = []

    # Factor 1: any lease with term_years > 15.
    if any(int(l.term_years or 0) > 15 for l in schedule.lines):
        hits.append(FACTOR_LEASE_DURATION)

    # Factor 2: any lease with escalator > 3%.
    if any(float(l.escalator_pct or 0) > 0.03 for l in schedule.lines):
        hits.append(FACTOR_ESCALATOR)

    # Factor 3: EBITDAR coverage < 1.4x.
    rent_total = portfolio_annual_rent_usd
    if rent_total is None:
        rent_total = sum(
            float(l.base_rent_annual_usd or 0.0) for l in schedule.lines
        )
    if (portfolio_ebitdar_annual_usd is not None and rent_total and rent_total > 0):
        coverage = float(portfolio_ebitdar_annual_usd) / rent_total
        if coverage < 1.4:
            hits.append(FACTOR_COVERAGE)

    # Factor 4: rural / safety-net geography.
    if geography and geography.upper() in {"RURAL", "SAFETY_NET"}:
        hits.append(FACTOR_GEOGRAPHY)

    # Factor 5: any REIT landlord.
    if any(_is_reit_landlord(l.landlord) for l in schedule.lines):
        hits.append(FACTOR_REIT_LANDLORD)

    count = len(hits)
    if count == 5:
        tier = StewardRiskTier.CRITICAL
        case = "Steward Health Care (2016 MPT sale-leaseback → 2024 bankruptcy)"
        reasoning = (
            "All five Steward-pattern factors present. This target's "
            "lease structure matches Steward's 2016 MPT deal at "
            "time of signing. Steward's outcome: bankruptcy May 2024 "
            "with $9B+ in MPT lease obligations at the center of the "
            "collapse."
        )
    elif count == 4:
        tier = StewardRiskTier.HIGH
        case = "Prospect Medical (2019 Leonard Green/MPT → 2025 bankruptcy)"
        reasoning = (
            "Four of five Steward-pattern factors present. Prospect "
            "Medical matched four factors at time of the 2019 Leonard "
            "Green deal; it filed for bankruptcy in January 2025."
        )
    elif count == 3:
        tier = StewardRiskTier.MEDIUM
        case = None
        reasoning = (
            "Three Steward-pattern factors present. Not yet a named-"
            "case replay; partner should pressure-test the structure."
        )
    elif count in (1, 2):
        tier = StewardRiskTier.LOW
        case = None
        reasoning = f"{count}/5 factors — isolated risk, not pattern."
    elif count == 0:
        tier = StewardRiskTier.LOW
        case = None
        reasoning = "No Steward-pattern factors present."
    else:
        tier = StewardRiskTier.UNKNOWN
        case = None
        reasoning = "Insufficient data."

    return StewardScoreResult(
        tier=tier, factors_hit=hits, factor_count=count,
        matching_case_study=case, reasoning=reasoning,
    )
