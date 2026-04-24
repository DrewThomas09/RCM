"""Feature extraction for flight-risk prediction.

Per-provider features derived from (a) the Provider dataclass we
already ingest for physician comp, (b) optional NPI enumeration
date (public — CMS NPI registry), (c) optional local-competitor
count (derived from NPI registry geography filtering), and
(d) specialty FMV benchmark context.

Feature set kept deliberately small (9 dimensions) because the
training data available is observational and sparse; over-
parameterising would overfit. Every feature maps to a plausible
behavioural or structural mechanism behind provider flight.

Feature dimensions (all in [0.0, 1.0] after transformation):

    1. comp_gap_normalized     — |provider comp - FMV p50| / FMV p50
                                 clipped to [0, 1]. High gap = provider
                                 is either way above or way below
                                 market; both directions predict flight.
    2. tenure_short             — short tenure = high flight risk.
                                 0.0 at ≥10 years, 1.0 at ≤1 year.
                                 Linear between.
    3. age_inflection           — peak attrition age brackets are
                                 late-career (≥60) and early-career
                                 (<35). Mid-career flat.
    4. productivity_decline     — year-over-year collections trend
                                 slope. Declining = preparing to leave.
                                 (Supplied by caller; 0 if unknown.)
    5. local_competitor_density — count of same-specialty providers
                                 in CBSA / total-roster-size proxy.
                                 More alternatives = easier to leave.
    6. stark_overlap_flag       — 1.0 if the provider appears in the
                                 existing Stark red-line findings.
                                 Comp that exceeds FMV under Stark is
                                 often unwound at close, triggering
                                 exit.
    7. employment_status_risk   — LOCUM 1.0 · 1099 0.7 · W2 0.3 ·
                                 PARTNER 0.1 (equity holders are
                                 stickiest).
    8. solo_line_revenue_share  — provider's share of total roster
                                 collections. High concentration =
                                 partner-facing retention priority
                                 even if flight probability is
                                 moderate.
    9. specialty_mobility       — surgical subspecialties have higher
                                 flight rates than primary care
                                 (surgeons can plug into any facility;
                                 primary care is patient-panel-bound).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .. import physician_comp
from ..physician_comp.comp_ingester import Provider
from ..physician_comp.fmv_benchmarks import get_benchmark


# Specialty mobility prior — higher = easier for the provider to
# plug into a competitor. Values calibrated against public
# BLS provider-turnover data + MGMA retention surveys.
_SPECIALTY_MOBILITY: Dict[str, float] = {
    # Surgical subspecialties — highly mobile, ambulatory-capable
    "ORTHOPEDIC_SURGERY": 0.75,
    "ORTHO_SURGERY": 0.75,
    "ORTHOPEDICS": 0.75,
    "GENERAL_SURGERY": 0.60,
    "OPHTHALMOLOGY": 0.70,
    "UROLOGY": 0.60,
    "DERMATOLOGY": 0.70,
    "ANESTHESIOLOGY": 0.75,
    "EMERGENCY_MEDICINE": 0.70,
    # Procedural medicine — moderately mobile
    "CARDIOLOGY": 0.55,
    "GASTROENTEROLOGY": 0.55,
    "PULMONOLOGY": 0.45,
    "ONCOLOGY": 0.45,
    "NEUROLOGY": 0.45,
    # Primary care — lower mobility, patient-panel bound
    "FAMILY_MEDICINE": 0.30,
    "INTERNAL_MEDICINE": 0.30,
    "PEDIATRICS": 0.30,
    "OB_GYN": 0.40,
    # Hospital-based / system-locked
    "HOSPITALIST": 0.40,
    "RADIOLOGY": 0.35,
    "PATHOLOGY": 0.30,
    "PSYCHIATRY": 0.40,
}

# Employment status → flight-risk prior. Partners own equity and
# don't leave voluntarily; locums leave routinely.
_EMPLOYMENT_RISK: Dict[str, float] = {
    "PARTNER": 0.10,
    "W2": 0.30,
    "1099": 0.70,
    "LOCUM": 1.00,
    "CONTRACT": 0.75,
}


def _clip01(x: float) -> float:
    if x is None:
        return 0.0
    try:
        f = float(x)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


@dataclass(frozen=True)
class AttritionFeatures:
    """The 9-dimension feature vector used by the flight-risk model.

    ``provenance`` records where each feature came from so the UI
    can surface "this came from FMV benchmark" vs "this was caller-
    supplied metadata".
    """
    comp_gap_normalized: float = 0.0
    tenure_short: float = 0.0
    age_inflection: float = 0.0
    productivity_decline: float = 0.0
    local_competitor_density: float = 0.0
    stark_overlap_flag: float = 0.0
    employment_status_risk: float = 0.3      # default W2
    solo_line_revenue_share: float = 0.0
    specialty_mobility: float = 0.40

    provenance: Dict[str, str] = field(default_factory=dict)

    FEATURE_NAMES: Tuple[str, ...] = (
        "comp_gap_normalized",
        "tenure_short",
        "age_inflection",
        "productivity_decline",
        "local_competitor_density",
        "stark_overlap_flag",
        "employment_status_risk",
        "solo_line_revenue_share",
        "specialty_mobility",
    )

    def as_tuple(self) -> Tuple[float, ...]:
        return (
            self.comp_gap_normalized, self.tenure_short,
            self.age_inflection, self.productivity_decline,
            self.local_competitor_density, self.stark_overlap_flag,
            self.employment_status_risk,
            self.solo_line_revenue_share,
            self.specialty_mobility,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = {n: getattr(self, n) for n in self.FEATURE_NAMES}
        d["provenance"] = dict(self.provenance)
        return d


# ────────────────────────────────────────────────────────────────────
# Component extractors
# ────────────────────────────────────────────────────────────────────

def _comp_gap_normalized(
    provider: Provider,
    *,
    ownership_type: str = "independent",
) -> Tuple[float, Optional[str]]:
    """|provider_comp - FMV_p50| / FMV_p50 clipped to [0, 1].

    The gap is symmetric — below-market comp predicts flight
    (provider can leave for a raise) and above-market comp
    predicts flight (Stark unwind at close often forces exit).
    """
    if not provider.specialty:
        return 0.0, None
    bench = get_benchmark(provider.specialty, ownership_type)
    if bench is None or bench.get("p50", 0) <= 0:
        return 0.0, None
    fmv_p50 = float(bench["p50"])
    gap = abs(provider.total_comp_usd - fmv_p50) / fmv_p50
    return _clip01(gap), f"FMV benchmark {provider.specialty} p50 ${fmv_p50:,.0f}"


def _tenure_short(years_at_facility: Optional[float]) -> float:
    """0.0 at ≥10 years, 1.0 at ≤1 year. Linear between."""
    if years_at_facility is None:
        return 0.5  # unknown → mid-prior
    y = max(0.0, float(years_at_facility))
    if y >= 10.0:
        return 0.0
    if y <= 1.0:
        return 1.0
    return (10.0 - y) / 9.0


def _age_inflection(age_years: Optional[float]) -> float:
    """Inverted-U around peak attrition ages.

    0.0 for the 40-55 sweet-spot; ~0.8 below 35 (early-career
    job-hopping); ~0.9 above 60 (retirement risk); linear at
    intermediate ages.
    """
    if age_years is None:
        return 0.3  # unknown → slight default prior
    a = float(age_years)
    if 40.0 <= a <= 55.0:
        return 0.0
    if a < 40.0:
        # 35 → 0.8, 40 → 0.0
        if a <= 35.0:
            return 0.8
        return 0.8 * (40.0 - a) / 5.0
    # a > 55
    if a >= 65.0:
        return 0.9
    return 0.9 * (a - 55.0) / 10.0


def _productivity_decline_feature(yoy_collections_slope: Optional[float]) -> float:
    """Slope of year-over-year collections change.

    -0.15 or worse → 1.0; 0.0 or better → 0.0; linear between.
    """
    if yoy_collections_slope is None:
        return 0.0
    s = float(yoy_collections_slope)
    if s >= 0.0:
        return 0.0
    if s <= -0.15:
        return 1.0
    return -s / 0.15


def _local_competitor_density(
    local_competitors: Optional[int], roster_size: int,
) -> float:
    """More competitors per roster-size unit = higher flight risk.

    Cap at 10 competitors per roster slot (very competitive market).
    """
    if local_competitors is None or roster_size <= 0:
        return 0.0
    ratio = local_competitors / roster_size / 10.0
    return _clip01(ratio)


def _employment_status_risk(provider: Provider) -> float:
    return _EMPLOYMENT_RISK.get(
        (provider.employment_status or "W2").upper(), 0.40,
    )


def _solo_line_revenue_share(
    provider: Provider, roster_collections_total: float,
) -> float:
    if roster_collections_total <= 0 or provider.collections_annual_usd <= 0:
        return 0.0
    share = provider.collections_annual_usd / roster_collections_total
    # Share of 20% or higher → 1.0 on this feature.
    return _clip01(share / 0.20)


def _specialty_mobility(provider: Provider) -> float:
    return _SPECIALTY_MOBILITY.get(
        (provider.specialty or "").upper(), 0.40,
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def extract_features(
    provider: Provider,
    *,
    years_at_facility: Optional[float] = None,
    age_years: Optional[float] = None,
    yoy_collections_slope: Optional[float] = None,
    local_competitors: Optional[int] = None,
    roster_size: int = 1,
    roster_collections_total: float = 0.0,
    has_stark_overlap: bool = False,
    ownership_type: str = "independent",
) -> AttritionFeatures:
    """Build the 9-dim attrition feature vector for one provider.

    All optional keyword args degrade gracefully to neutral or
    uncertain priors when not supplied.
    """
    provenance: Dict[str, str] = {}

    comp_gap, comp_src = _comp_gap_normalized(
        provider, ownership_type=ownership_type,
    )
    if comp_src:
        provenance["comp_gap_normalized"] = comp_src
    else:
        provenance["comp_gap_normalized"] = "no FMV benchmark for specialty"

    tenure = _tenure_short(years_at_facility)
    provenance["tenure_short"] = (
        "caller.years_at_facility" if years_at_facility is not None
        else "default prior 0.5 (unknown)"
    )

    age_f = _age_inflection(age_years)
    provenance["age_inflection"] = (
        "caller.age_years" if age_years is not None
        else "default prior 0.3 (unknown)"
    )

    prod = _productivity_decline_feature(yoy_collections_slope)
    provenance["productivity_decline"] = (
        "caller.yoy_collections_slope"
        if yoy_collections_slope is not None else "no trend supplied (0.0)"
    )

    lcd = _local_competitor_density(local_competitors, roster_size)
    provenance["local_competitor_density"] = (
        f"{local_competitors} competitors / {roster_size} roster slots"
        if local_competitors is not None else "not supplied (0.0)"
    )

    emp = _employment_status_risk(provider)
    provenance["employment_status_risk"] = (
        f"provider.employment_status={provider.employment_status}"
    )

    solo = _solo_line_revenue_share(provider, roster_collections_total)
    provenance["solo_line_revenue_share"] = (
        f"{provider.collections_annual_usd:,.0f} / "
        f"{roster_collections_total:,.0f} roster total"
    )

    mob = _specialty_mobility(provider)
    provenance["specialty_mobility"] = (
        f"specialty={provider.specialty} mobility prior"
    )

    stark = 1.0 if has_stark_overlap else 0.0
    provenance["stark_overlap_flag"] = (
        "Stark red-line hit" if has_stark_overlap else "no Stark overlap"
    )

    return AttritionFeatures(
        comp_gap_normalized=comp_gap,
        tenure_short=tenure,
        age_inflection=age_f,
        productivity_decline=prod,
        local_competitor_density=lcd,
        stark_overlap_flag=stark,
        employment_status_risk=emp,
        solo_line_revenue_share=solo,
        specialty_mobility=mob,
        provenance=provenance,
    )
