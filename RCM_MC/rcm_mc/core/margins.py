"""Single source of truth for HCRIS metric plausibility bands.

Lives in ``core`` (not the UI kit) so every layer — UI, ml, finance,
intelligence — validates a hospital operating margin / occupancy against the
SAME band, instead of each surface re-deriving a looser one. The UI kit
(`rcm_mc.ui._chartis_kit`) re-exports these for back-compat, so existing
`from ._chartis_kit import margin_is_plausible` call sites keep working.

These are pure numeric helpers (no UI, no I/O, never raise — they feed partner
surfaces), so they belong below the UI in the dependency graph.
"""
from __future__ import annotations

from typing import Optional

# Realistic operating-margin band for HCRIS-derived hospital records.
# A hospital operating margin = (NPR − opex) / NPR. Outside roughly
# −40%…+30% the filing almost always has incomplete or aggregated
# opex (a parent/CCN rollup, or partial expense lines), so the computed
# margin is a DATA ARTIFACT rather than a real operating result — e.g.
# a $7.86B-NPR record showing 87.9% implies opex ≈ 12% of revenue,
# which is impossible for a real hospital. Callers use this to flag
# such values for review instead of presenting them as confident KPIs.
# Band agreed with the product owner.
MARGIN_PLAUSIBLE_LO = -0.40
MARGIN_PLAUSIBLE_HI = 0.30

# Soft "verify" threshold, ABOVE which an operating margin is still inside the
# hard plausible band (≤+30%) but already in the extreme upper tail of real
# hospital filings — the 95th percentile of HCRIS op margins is ~24%, and the
# median is ~-4%. Values here pass the gate (they may be a real high-margin
# specialty/rehab hospital) but are disproportionately incomplete-opex filing
# artifacts, so a default margin-ranked view that didn't separate them led with
# a wall of ~29% "errors" presented as the best targets. Surfaces use this to
# FLAG such rows "verify" and DEMOTE them below clean values in the default
# ranking — not to hide them. Threshold agreed with the product owner.
MARGIN_SUSPECT_HI = 0.24

# Bed-days available (beds × days in the cost-report period) is the hard
# physical ceiling on inpatient days, so occupancy = patient_days ÷
# bed_days_available cannot exceed ~100% over a full year. A computed value
# meaningfully above that means the FILING is wrong (bed_days_available
# understated — e.g. a partial-period or single-bed-type figure), not that the
# hospital ran over capacity. A small tolerance (5pp) absorbs licensed-vs-
# staffed/observation quirks; beyond it the value is a data artifact, not a
# real KPI. (Real-data check: 29 HCRIS hospitals computed >100%, up to 239%.)
OCCUPANCY_PLAUSIBLE_HI = 1.05


def margin_is_suspect_high(margin: Optional[float]) -> bool:
    """True when an operating-margin fraction is plausible (≤ the +30% hard
    ceiling) but in the suspect upper tail (≥ MARGIN_SUSPECT_HI, ~95th pct of
    real hospitals) — i.e. show it, but flag "verify" and rank it below clean
    values. None / NaN / non-numeric → False (unknown → don't flag; never
    raises — partner UI). Margins already past the hard ceiling are handled by
    margin_flag (they're gated to None), so this deliberately only fires inside
    the kept band."""
    try:
        m = float(margin)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if m != m:  # NaN
        return False
    return MARGIN_SUSPECT_HI <= m <= MARGIN_PLAUSIBLE_HI


def margin_is_plausible(margin: Optional[float]) -> bool:
    """True when an operating-margin *fraction* (0.04 == 4%) falls in
    the realistic band for a real hospital filing. None / non-numeric
    returns True (unknown → don't flag; never raises — partner UI)."""
    try:
        m = float(margin)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return True
    if m != m:  # NaN
        return True
    return MARGIN_PLAUSIBLE_LO <= m <= MARGIN_PLAUSIBLE_HI


def margin_flag(margin: Optional[float]) -> Optional[str]:
    """Classify *why* an operating-margin fraction is implausible, so a
    surface can FLAG it (badge / footnote) instead of silently dropping
    it to "—".

    Returns ``"high"`` when the margin exceeds the plausible ceiling
    (almost always a filing artifact — opex incomplete or a parent-CCN
    rollup, so the margin is impossibly fat), ``"low"`` when it falls
    below the floor (opex >> patient revenue — partial-year or
    state-funded filing), and ``None`` when the margin is plausible OR
    unknown (None / NaN / non-numeric → don't flag; never raises — this
    feeds partner UI). The band is shared with :func:`margin_is_plausible`
    so the verification is identical everywhere a margin is shown."""
    try:
        m = float(margin)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if m != m:  # NaN
        return None
    if m > MARGIN_PLAUSIBLE_HI:
        return "high"
    if m < MARGIN_PLAUSIBLE_LO:
        return "low"
    return None


def margin_is_plausible_series(s):
    """Vectorised :func:`margin_is_plausible` for a pandas Series — True
    where the value is inside the band OR is NaN (unknown → don't flag).
    One source of truth for the band keeps DataFrame-level stats (medians,
    distressed counts) honest and identical to the per-row display gate;
    a looser local band silently let HCRIS filing artifacts (e.g. ±100%
    margins) inflate those headline stats."""
    return (s.between(MARGIN_PLAUSIBLE_LO, MARGIN_PLAUSIBLE_HI)) | (s.isna())


def occupancy_is_plausible(occ: Optional[float]) -> bool:
    """True when an occupancy fraction (0.80 == 80%) is physically possible.

    Flags only the impossibly-HIGH artifacts (> OCCUPANCY_PLAUSIBLE_HI); a
    value at/under the ceiling — including 0 / missing — is left alone (the
    caller decides how to show a genuine zero). None / NaN / non-numeric →
    True (unknown → don't flag; never raises — partner UI)."""
    try:
        v = float(occ)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return True
    if v != v:  # NaN
        return True
    return v <= OCCUPANCY_PLAUSIBLE_HI
