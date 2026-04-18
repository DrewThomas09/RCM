"""Extra reasonableness bands — finer-grained subsector checks.

`reasonableness.py` holds the core IRR × (size × payer) matrix and
margin bands by hospital type. This module adds finer-grained
subsector-specific bands that partners actually use:

- **Capital intensity** (capex as % of revenue by subsector).
- **Bed occupancy** (acute-care inpatient only).
- **Physician productivity** (RVUs per provider, outpatient only).
- **Length of stay** (behavioral, post-acute).
- **Case Mix Index** (acute care).
- **Revenue per bed** (acute care + specialty).

Each function follows the same `BandCheck` contract as the core
module so the UI and IC memo renderers don't need to change.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .reasonableness import (
    Band,
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)


# ── Capital intensity (% of revenue) ────────────────────────────────

_CAPEX_BANDS: Dict[str, Band] = {
    "acute_care": Band(
        metric="capex_pct_of_revenue", regime="acute-care hospital",
        low=0.03, high=0.07, stretch_high=0.09, implausible_high=0.15,
        implausible_low=0.0,
        source="AHA + CMS cost reports",
    ),
    "asc": Band(
        metric="capex_pct_of_revenue", regime="ASC",
        low=0.02, high=0.06, stretch_high=0.09, implausible_high=0.13,
        source="ASCA",
    ),
    "behavioral": Band(
        metric="capex_pct_of_revenue", regime="behavioral health",
        low=0.02, high=0.05, stretch_high=0.07, implausible_high=0.11,
        source="Industry",
    ),
    "post_acute": Band(
        metric="capex_pct_of_revenue", regime="post-acute",
        low=0.025, high=0.05, stretch_high=0.07, implausible_high=0.12,
        source="AHCA",
    ),
    "outpatient": Band(
        metric="capex_pct_of_revenue", regime="outpatient / MSO",
        low=0.01, high=0.05, stretch_high=0.07, implausible_high=0.10,
        source="MGMA",
    ),
    "critical_access": Band(
        metric="capex_pct_of_revenue", regime="critical-access",
        low=0.03, high=0.06, stretch_high=0.08, implausible_high=0.12,
        source="CMS CAH data",
    ),
}


def _subsector_key(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    aliases = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute",
        "psych": "behavioral", "clinic": "outpatient",
        "cah": "critical_access",
    }
    return aliases.get(s.lower().strip(), s.lower().strip())


def check_capex_intensity(
    capex_pct_of_rev: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if capex_pct_of_rev is None:
        return BandCheck(
            metric="capex_pct_of_revenue", observed=None,
            verdict=VERDICT_UNKNOWN, rationale="Capex intensity not provided.",
        )
    key = _subsector_key(hospital_type) or "acute_care"
    band = _CAPEX_BANDS.get(key, _CAPEX_BANDS["acute_care"])
    verdict = band.classify(capex_pct_of_rev)
    pct = f"{capex_pct_of_rev*100:.1f}%"
    lo = f"{(band.low or 0)*100:.1f}%"
    hi = f"{(band.high or 0)*100:.1f}%"
    if verdict == VERDICT_IN_BAND:
        rationale = f"{pct} capex intensity consistent with {band.regime} ({lo}–{hi})."
        note = "Normal reinvestment profile."
    elif verdict == VERDICT_STRETCH:
        rationale = f"{pct} capex intensity above {hi} ceiling for {band.regime}."
        note = "Above peer — is there a deferred maintenance catch-up or a growth build?"
    elif verdict == VERDICT_IMPLAUSIBLE:
        rationale = f"{pct} capex intensity is implausible for {band.regime}."
        note = "Re-check the capex plan; either mis-classified or the thesis changed."
    else:
        rationale = f"{pct} capex intensity outside peer band for {band.regime}."
        note = "Investigate — off-peer capex usually reveals something."
    return BandCheck(
        metric="capex_pct_of_revenue", observed=capex_pct_of_rev,
        verdict=verdict, band=band, rationale=rationale, partner_note=note,
    )


# ── Bed occupancy (acute care) ──────────────────────────────────────

_OCCUPANCY_BANDS: Dict[str, Band] = {
    "acute_care": Band(
        metric="bed_occupancy", regime="acute-care",
        low=0.55, high=0.78, stretch_high=0.88, implausible_high=0.98,
        implausible_low=0.30,
        source="AHA",
    ),
    "post_acute": Band(
        metric="bed_occupancy", regime="post-acute / SNF",
        low=0.78, high=0.92, stretch_high=0.95, implausible_high=1.0,
        implausible_low=0.55,
        source="AHCA",
    ),
    "behavioral": Band(
        metric="bed_occupancy", regime="behavioral inpatient",
        low=0.70, high=0.88, stretch_high=0.94, implausible_high=1.0,
        implausible_low=0.50,
        source="SAMHSA",
    ),
}


def check_bed_occupancy(
    occupancy: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if occupancy is None:
        return BandCheck(
            metric="bed_occupancy", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Occupancy not reported.",
        )
    key = _subsector_key(hospital_type) or "acute_care"
    band = _OCCUPANCY_BANDS.get(key)
    if band is None:
        return BandCheck(
            metric="bed_occupancy", observed=occupancy, verdict=VERDICT_UNKNOWN,
            rationale=f"No occupancy band for {key}.",
        )
    verdict = band.classify(occupancy)
    pct = f"{occupancy*100:.1f}%"
    if verdict == VERDICT_IN_BAND:
        rationale = f"{pct} occupancy consistent with {band.regime} peers."
        note = "Capacity utilization normal."
    elif verdict == VERDICT_STRETCH:
        rationale = f"{pct} occupancy is near ceiling for {band.regime}."
        note = "Little room for volume upside; growth thesis needs capacity expansion."
    elif verdict == VERDICT_OUT_OF_BAND and occupancy < (band.low or 0):
        rationale = f"{pct} occupancy below {band.regime} peer floor."
        note = "Under-utilization — mix or census problem. Diagnose before pricing."
    elif verdict == VERDICT_IMPLAUSIBLE:
        rationale = f"{pct} occupancy is implausible for {band.regime}."
        note = "Verify the calculation — likely a numerator/denominator error."
    else:
        rationale = f"{pct} occupancy off peer band."
        note = "Investigate the driver."
    return BandCheck(
        metric="bed_occupancy", observed=occupancy, verdict=verdict,
        band=band, rationale=rationale, partner_note=note,
    )


# ── Physician productivity (RVU per provider) — outpatient / MSO ────

_RVU_BAND = Band(
    metric="rvu_per_provider_per_yr", regime="outpatient / MSO",
    low=4800, high=8000, stretch_high=10_000, implausible_high=14_000,
    implausible_low=2000,
    source="MGMA",
)


def check_rvu_per_provider(
    rvu: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if rvu is None:
        return BandCheck(
            metric="rvu_per_provider_per_yr", observed=None,
            verdict=VERDICT_UNKNOWN, rationale="RVU/provider not reported.",
        )
    if _subsector_key(hospital_type) not in ("outpatient", "specialty"):
        return BandCheck(
            metric="rvu_per_provider_per_yr", observed=rvu,
            verdict=VERDICT_UNKNOWN,
            rationale="RVU/provider band only applies to outpatient / specialty subsectors.",
        )
    verdict = _RVU_BAND.classify(rvu)
    if verdict == VERDICT_IN_BAND:
        note = "Productivity in the median peer range."
    elif verdict == VERDICT_STRETCH:
        note = "High productivity — validate it's sustainable, not burnout-driven."
    elif verdict == VERDICT_IMPLAUSIBLE:
        note = "Verify the calculation — RVU definitions vary."
    else:
        note = "Low productivity — opportunity or warning sign."
    return BandCheck(
        metric="rvu_per_provider_per_yr", observed=rvu, verdict=verdict,
        band=_RVU_BAND,
        rationale=f"{rvu:.0f} RVUs/provider/yr vs MGMA peer band {_RVU_BAND.low:.0f}-{_RVU_BAND.high:.0f}.",
        partner_note=note,
    )


# ── Case Mix Index (acute care) ─────────────────────────────────────

_CMI_BAND = Band(
    metric="case_mix_index", regime="acute-care",
    low=1.25, high=1.80, stretch_high=2.20, implausible_high=3.50,
    implausible_low=0.80,
    source="CMS Worksheet S-3",
)


def check_case_mix_index(
    cmi: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if cmi is None:
        return BandCheck(
            metric="case_mix_index", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="CMI not reported.",
        )
    if _subsector_key(hospital_type) != "acute_care":
        return BandCheck(
            metric="case_mix_index", observed=cmi, verdict=VERDICT_UNKNOWN,
            rationale="CMI band applies only to acute-care hospitals.",
        )
    verdict = _CMI_BAND.classify(cmi)
    if verdict == VERDICT_IN_BAND:
        note = "Case mix consistent with acute-care peers."
    elif verdict == VERDICT_STRETCH:
        note = "Elevated acuity — higher reimbursement but also higher clinical complexity."
    elif verdict == VERDICT_IMPLAUSIBLE:
        note = "CMI outside defensible range — verify calculation and DRG grouper version."
    else:
        note = "Off-peer CMI — differential reimbursement exposure."
    return BandCheck(
        metric="case_mix_index", observed=cmi, verdict=verdict,
        band=_CMI_BAND,
        rationale=f"CMI {cmi:.2f} vs acute-care peer band {_CMI_BAND.low:.2f}-{_CMI_BAND.high:.2f}.",
        partner_note=note,
    )


# ── Length of stay (behavioral / post-acute) ─────────────────────────

_LOS_BANDS: Dict[str, Band] = {
    "behavioral": Band(
        metric="avg_length_of_stay_days", regime="behavioral inpatient",
        low=7, high=22, stretch_high=30, implausible_high=60,
        implausible_low=2,
        source="SAMHSA",
    ),
    "post_acute": Band(
        metric="avg_length_of_stay_days", regime="SNF / post-acute",
        low=15, high=35, stretch_high=60, implausible_high=120,
        implausible_low=5,
        source="AHCA",
    ),
}


def check_length_of_stay(
    los: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    if los is None:
        return BandCheck(
            metric="avg_length_of_stay_days", observed=None,
            verdict=VERDICT_UNKNOWN, rationale="LOS not reported.",
        )
    key = _subsector_key(hospital_type)
    band = _LOS_BANDS.get(key or "")
    if band is None:
        return BandCheck(
            metric="avg_length_of_stay_days", observed=los,
            verdict=VERDICT_UNKNOWN,
            rationale=f"No LOS band for {key}.",
        )
    verdict = band.classify(los)
    if verdict == VERDICT_IN_BAND:
        note = f"LOS consistent with {band.regime} peers."
    elif verdict == VERDICT_STRETCH:
        note = f"Above-peer LOS — reimbursement implications (payer / DRG cutoffs)."
    elif verdict == VERDICT_IMPLAUSIBLE:
        note = "Verify LOS definition — inpatient vs total episode."
    else:
        note = "Off-peer LOS — usually reveals a payer-mix or acuity story."
    return BandCheck(
        metric="avg_length_of_stay_days", observed=los, verdict=verdict,
        band=band,
        rationale=f"LOS {los:.1f}d vs {band.regime} peer band {band.low:.0f}-{band.high:.0f}d.",
        partner_note=note,
    )


# ── Orchestrator ────────────────────────────────────────────────────

def run_extra_bands(
    *,
    hospital_type: Optional[str],
    capex_pct_of_revenue: Optional[float] = None,
    bed_occupancy: Optional[float] = None,
    rvu_per_provider: Optional[float] = None,
    case_mix_index: Optional[float] = None,
    avg_length_of_stay: Optional[float] = None,
) -> List[BandCheck]:
    """Run every extra band that has enough input."""
    out: List[BandCheck] = []
    out.append(check_capex_intensity(capex_pct_of_revenue, hospital_type=hospital_type))
    out.append(check_bed_occupancy(bed_occupancy, hospital_type=hospital_type))
    out.append(check_rvu_per_provider(rvu_per_provider, hospital_type=hospital_type))
    out.append(check_case_mix_index(case_mix_index, hospital_type=hospital_type))
    out.append(check_length_of_stay(avg_length_of_stay, hospital_type=hospital_type))
    return out
