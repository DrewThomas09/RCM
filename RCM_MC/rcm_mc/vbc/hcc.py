"""CMS-HCC V28 risk scoring.

Models the Medicare Advantage / ACO REACH risk-adjustment math.
HCC (Hierarchical Condition Categories) is the dominant
risk-adjustment system for capitated revenue: each beneficiary
gets a risk score, and capitation revenue = base PMPM × risk
score × eligibility months.

V28 changed the model in PY2024 — phasing out 2,000+ HCCs from
V24, re-weighting coding intensity, and changing the demographic
factor scheme. CMS phases V28 in over three years:

    PY2024:  33% V28 / 67% V24
    PY2025:  67% V28 / 33% V24
    PY2026: 100% V28
    PY2027+: 100% V28 (steady state)

For ACOs and MA-focused targets, the V28 transition is a real
revenue cliff — typical mid-acuity panels lose 1.5–3% of
capitation per year during phase-in. This module models that
explicitly so diligence packets can flag at-risk targets.

The HCC weights here are the *category-level* weights from
the published 2026 V28 model. We do not implement the full
9,000+ ICD → HCC crosswalk — that's a downstream loader.
For diligence at the cohort level, category-level weights are
sufficient and dramatically more interpretable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


# ── V28 phase-in weights (per CMS final rule) ───────────────────

V28_PHASE_IN: Dict[int, float] = {
    2023: 0.00,
    2024: 0.33,
    2025: 0.67,
    2026: 1.00,
    2027: 1.00,
    2028: 1.00,
    2029: 1.00,
    2030: 1.00,
}


def _v28_phase(year: int) -> float:
    """Look up V28 phase-in for ``year`` with safe extrapolation:
    years before 2023 → 0%, years after 2030 → 100% (steady state)."""
    if year in V28_PHASE_IN:
        return V28_PHASE_IN[year]
    if year < 2023:
        return 0.0
    return 1.0


# ── Demographic factor (V28 community, non-dual aged) ───────────
#
# Source: CMS-HCC V28 community segment, non-dual aged, 2026 final.
# Females are slightly heavier than males at most age bands.

_AGE_BRACKETS = (
    (0,  64,  0.000),  # under-65 not modeled here
    (65, 69,  0.331),
    (70, 74,  0.398),
    (75, 79,  0.502),
    (80, 84,  0.612),
    (85, 89,  0.745),
    (90, 200, 0.880),
)


def _age_bracket_factor(age: float, female: bool) -> float:
    for lo, hi, factor in _AGE_BRACKETS:
        if lo <= age <= hi:
            base = factor
            return base * (1.05 if female else 1.0)
    return 0.0


# ── Category-level HCC weights (V28 + V24 for blending) ─────────
#
# Hand-curated from the published category models. Used at the
# category granularity (e.g. "HCC_DM" for diabetes), not raw
# 4-digit HCC codes — partner reads "diabetes adds 0.13" not
# "HCC_19 adds 0.10499".

@dataclass(frozen=True)
class HCCWeights:
    v24: float
    v28: float


# Common chronic conditions seen in MA / ACO populations.
_HCC_CATEGORIES: Dict[str, HCCWeights] = {
    "HCC_DM_NO_COMP":  HCCWeights(v24=0.105, v28=0.166),  # Diabetes, no complications
    "HCC_DM_COMP":     HCCWeights(v24=0.302, v28=0.302),  # Diabetes w/ complications
    "HCC_CHF":         HCCWeights(v24=0.331, v28=0.331),  # Heart failure
    "HCC_VASC":        HCCWeights(v24=0.295, v28=0.000),  # Peripheral vascular — REMOVED in V28
    "HCC_COPD":        HCCWeights(v24=0.328, v28=0.335),  # COPD
    "HCC_CKD_3":       HCCWeights(v24=0.069, v28=0.000),  # CKD stage 3 — REMOVED in V28
    "HCC_CKD_4":       HCCWeights(v24=0.289, v28=0.292),  # CKD stage 4
    "HCC_CKD_5":       HCCWeights(v24=0.412, v28=0.420),  # CKD stage 5/ESRD
    "HCC_DEPRESSION":  HCCWeights(v24=0.346, v28=0.347),  # Major depression
    "HCC_DEMENTIA":    HCCWeights(v24=0.346, v28=0.354),  # Dementia
    "HCC_RA":          HCCWeights(v24=0.421, v28=0.000),  # Rheumatoid — REMOVED in V28
    "HCC_CANCER_LO":   HCCWeights(v24=0.179, v28=0.180),  # Lower-acuity cancer
    "HCC_CANCER_HI":   HCCWeights(v24=2.659, v28=2.700),  # Metastatic
    "HCC_STROKE":      HCCWeights(v24=0.220, v28=0.222),  # Stroke
    "HCC_PARALYSIS":   HCCWeights(v24=0.475, v28=0.475),  # Paralysis
    "HCC_PSYCH":       HCCWeights(v24=0.305, v28=0.310),  # Schizophrenia/severe psych
}


def compute_hcc_score(
    age: float,
    female: bool,
    hcc_distribution: Dict[str, float],
    *,
    payment_year: int = 2026,
    dual_eligible: bool = False,
    originally_disabled: bool = False,
    coding_intensity_factor: float = 0.941,  # CMS PY2026 = 5.9% reduction
) -> float:
    """Compute the cohort-average risk score for a single member
    profile. Combines:

        demographic factor (age × sex)
        + Σ (HCC weight × prevalence)
        + dual-eligible adjustment
        + originally-disabled adjustment
        × coding intensity factor (5.9% reduction in PY2026)

    The result is the multiplier on base PMPM capitation revenue.
    A "1.0" score means the panel is exactly average — a 1.4 score
    means 40% above average, hence 40% more capitation revenue.

    The V28 transition is handled by blending V28 and V24 weights
    according to ``V28_PHASE_IN[payment_year]``. By PY2026 the
    blend is 100% V28 — V24 weights are kept here only so backtests
    against historical PMPMs reproduce.
    """
    blend_v28 = _v28_phase(payment_year)
    blend_v24 = 1.0 - blend_v28

    # Demographic component
    demo = _age_bracket_factor(age, female)
    if dual_eligible:
        demo += 0.18  # CMS V28 dual-aged add-on (community segment)
    if originally_disabled:
        demo += 0.06  # OREC add-on

    # HCC component — blend V28 and V24 weights, weighted by prevalence
    hcc_sum = 0.0
    for hcc_code, prevalence in (hcc_distribution or {}).items():
        weights = _HCC_CATEGORIES.get(hcc_code)
        if not weights:
            continue
        blended = (weights.v28 * blend_v28
                   + weights.v24 * blend_v24)
        hcc_sum += blended * float(prevalence)

    raw = demo + hcc_sum
    return raw * coding_intensity_factor
