"""OPPS vs PFS site-neutral migration simulator.

Given a hospital target with off-campus HOPD revenue, project
erosion under three scenarios (current CY2026 rule / MedPAC all-
ambulatory / full legislative expansion) and overlay 340B
recoupment.

Input is a dict of ``cpt_family`` → annual revenue (or a full
claims list when ``aggregate_by_cpt_family`` is called). Output is
the worst-case (legislative) figure alongside the current-rule
and MedPAC scenarios so the partner can see the dispersion.

Banding (on the ACTIVE scenario):
    GREEN  — erosion < 5% of HOPD revenue
    YELLOW — 5-15%
    RED    — ≥15% (legislative scenario always RED when HOPD
              revenue is material)
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from .packet import RegulatoryBand, SiteNeutralExposure, load_yaml


SCENARIO_NAMES = ("current", "medpac", "legislative")


def _cpt_family_for(cpt: str, ranges: Dict[str, Any]) -> Optional[str]:
    c = str(cpt or "").strip()
    if not c:
        return None
    # Range check against each family's [lo, hi] inclusive.
    for family, bounds in ranges.items():
        if not bounds or len(bounds) < 2:
            continue
        lo, hi = str(bounds[0]), str(bounds[1])
        if lo <= c <= hi:
            return family
    return None


def aggregate_revenue_by_family(
    claims: Sequence[Any],
    *,
    hopd_predicate: Optional[Any] = None,
) -> Dict[str, float]:
    """Sum ``paid_amount`` by CPT family for claims the
    ``hopd_predicate`` accepts. Default predicate flags HOPDs
    via ``is_hopd`` or ``place_of_service == '22'``."""
    content = load_yaml("site_neutral_rules")
    ranges = content.get("cpt_family_ranges") or {}
    out: Dict[str, float] = {}
    for c in claims:
        paid = float(getattr(c, "paid_amount", 0.0) or 0.0)
        if paid <= 0:
            continue
        if hopd_predicate is None:
            pos = str(getattr(c, "place_of_service", "") or "")
            is_hopd = bool(getattr(c, "is_hopd", False)) or pos == "22"
        else:
            is_hopd = hopd_predicate(c)
        if not is_hopd:
            continue
        family = _cpt_family_for(
            getattr(c, "cpt_code", "") or "", ranges,
        )
        if family is None:
            continue
        out[family] = out.get(family, 0.0) + paid
    return out


def simulate_site_neutral_impact(
    *,
    scenario: str = "current",
    hopd_revenue_by_family_usd: Optional[Dict[str, float]] = None,
    hopd_total_revenue_usd: Optional[float] = None,
    include_340b_recoupment: bool = True,
    year_for_recoupment: int = 2026,
) -> SiteNeutralExposure:
    """Compute erosion under one scenario.

    Either pass a per-family dict (preferred — uses the scenario's
    ``affected_cpt_families`` to filter), or pass a portfolio-level
    HOPD total and the erosion % is applied to the whole thing.
    """
    content = load_yaml("site_neutral_rules")
    scenarios = content.get("scenarios") or {}
    if scenario not in scenarios:
        raise ValueError(
            f"unknown scenario {scenario!r}; "
            f"expected one of {sorted(scenarios.keys())}"
        )
    cfg = scenarios[scenario]
    affected = list(cfg.get("affected_cpt_families") or ())
    erosion_pct = float(cfg.get("annual_revenue_erosion_pct", 0) or 0)
    phase_in = int(cfg.get("phase_in_years", 1) or 1)

    if hopd_revenue_by_family_usd:
        addressable = sum(
            float(v) for k, v in hopd_revenue_by_family_usd.items()
            if k in affected
        )
    elif hopd_total_revenue_usd is not None:
        addressable = float(hopd_total_revenue_usd)
    else:
        addressable = 0.0

    erosion_usd = addressable * erosion_pct

    recoupment_usd = 0.0
    if include_340b_recoupment:
        overlay = content.get("recoupment_overlay_340b") or {}
        key = f"cy{year_for_recoupment}_recoupment_pct"
        pct = float(overlay.get(key, 0) or 0)
        recoupment_usd = addressable * pct

    total = erosion_usd + recoupment_usd
    erosion_ratio = (total / addressable) if addressable > 0 else 0.0

    if erosion_ratio >= 0.15:
        band = RegulatoryBand.RED
    elif erosion_ratio >= 0.05:
        band = RegulatoryBand.YELLOW
    elif addressable == 0:
        band = RegulatoryBand.UNKNOWN
    else:
        band = RegulatoryBand.GREEN

    return SiteNeutralExposure(
        scenario=scenario,
        annual_revenue_erosion_usd=total,
        annual_revenue_erosion_pct=erosion_ratio,
        phase_in_years=phase_in,
        affected_cpt_families=affected,
        band=band,
        recoupment_340b_usd=recoupment_usd,
    )


def simulate_all_scenarios(
    *,
    hopd_revenue_by_family_usd: Optional[Dict[str, float]] = None,
    hopd_total_revenue_usd: Optional[float] = None,
    year_for_recoupment: int = 2026,
) -> Dict[str, SiteNeutralExposure]:
    """Return {scenario: exposure} for all three scenarios so a UI
    can render the dispersion band."""
    return {
        s: simulate_site_neutral_impact(
            scenario=s,
            hopd_revenue_by_family_usd=hopd_revenue_by_family_usd,
            hopd_total_revenue_usd=hopd_total_revenue_usd,
            year_for_recoupment=year_for_recoupment,
        )
        for s in SCENARIO_NAMES
    }
