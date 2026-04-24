"""Deferred-maintenance / capex-wall detector.

Uses HCRIS fixed-asset data already ingested elsewhere in the
platform. Callers supply:

    gross_fixed_assets_usd     — total gross PPE
    accumulated_depreciation_usd — accumulated depreciation
    annual_depreciation_usd    — current-year depreciation
    useful_life_years          — specialty-appropriate useful life
                                  (hospital ~35y, SNF ~25y, ASC ~15y,
                                  MOB ~30y)
    deferred_backlog_multiplier — multiplier on the "age-vs-useful-life"
                                  ratio to estimate deferred capex
                                  dollars; defaults to 0.5 (a target
                                  at 50% overage implies ~25% of gross
                                  assets are deferred replacements)

Output: average fixed-asset age, deferred-maintenance backlog in
dollars, a replacement-window estimate, and an annualized recovery
profile if the sponsor fixes it over the hold period.
"""
from __future__ import annotations

from typing import List, Optional

from .types import CapexWall


def _severity(age: float, useful_life: float) -> str:
    if useful_life <= 0:
        return "MEDIUM"
    ratio = age / useful_life
    if ratio >= 0.9:
        return "HIGH"
    if ratio >= 0.65:
        return "MEDIUM"
    return "LOW"


def compute_capex_wall(
    *,
    gross_fixed_assets_usd: float,
    accumulated_depreciation_usd: float,
    annual_depreciation_usd: Optional[float] = None,
    useful_life_years: float = 30.0,
    hold_years: int = 5,
    deferred_backlog_multiplier: float = 0.5,
) -> CapexWall:
    """Compute average asset age + deferred backlog estimate.

    Asset age ≈ accumulated_depreciation / annual_depreciation.
    When annual_depreciation isn't supplied, we approximate from
    gross_fixed_assets / useful_life_years (straight-line assumption).
    """
    gfa = max(0.0, float(gross_fixed_assets_usd))
    acc = max(0.0, float(accumulated_depreciation_usd))
    ad = annual_depreciation_usd
    if ad is None or ad <= 0:
        ad = gfa / max(useful_life_years, 1.0)
    age = acc / ad if ad > 0 else 0.0

    # Deferred backlog: when age > useful_life, every year of
    # overage × multiplier × annual_depreciation is the sunk
    # replacement shortfall.
    overage = max(0.0, age - useful_life_years)
    backlog = overage * ad * deferred_backlog_multiplier

    # When age > useful_life, replacement window is now; otherwise
    # it's (useful_life - age).
    window = max(0, int(useful_life_years - age))

    # Distribute the recovery over the hold period (straight-line).
    recovery = [backlog / hold_years] * hold_years if backlog else [0.0] * hold_years

    return CapexWall(
        avg_fixed_asset_age_years=age,
        useful_life_years=useful_life_years,
        deferred_capex_backlog_usd=backlog,
        replacement_window_years=window,
        annual_recovery_profile_usd=recovery,
        severity=_severity(age, useful_life_years),
    )
