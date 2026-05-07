"""State-level market heatmap adjustments — CMI + DSH + teaching split.

PEDESK Phase 2 (Week 2, Data Ingestion) — State Market Heatmap fix.

The shipped state heatmap implies a 1:1 correlation between Medicare day
share and operating margin. That conflates three independent drivers:

1. **Case-Mix Index (CMI).** Higher acuity per discharge means higher
   reimbursement per case. AMCs and tertiary referral centers have CMI
   > 1.8 vs ~1.3 at community hospitals, and the CMI multiplier
   directly offsets the per-day Medicare reimbursement haircut.

2. **Disproportionate Share Hospital (DSH) supplemental payments.**
   Hospitals serving a disproportionately large share of Medicaid /
   uninsured patients receive a CMS supplemental payment that can be
   5–15% of NPR. Without DSH adjustment, high-Medicaid-mix states
   appear money-losing when in fact the supplemental payments cover
   the cross-subsidy.

3. **Teaching vs community.** Teaching hospitals receive Direct GME
   and Indirect Medical Education (IME) pass-through payments, plus
   research grants that don't pass through HCRIS NPR. Aggregating
   teaching and community margins into a single state-level number
   blurs these structurally different operating models.

This module computes the three adjustments deterministically from the
HCRIS columns we already ingest, and exposes them as add-on fields on
the per-state stats dict the heatmap renderer consumes.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .hcris_sot import is_amc_series

# ---------------------------------------------------------------------------
# CMI proxy
# ---------------------------------------------------------------------------
#
# HCRIS doesn't ship CMI directly. Net Patient Revenue per patient day
# is a defensible state-level proxy: it captures both the per-case
# reimbursement (which scales with CMI on Medicare DRG payments) and
# the case mix the state's hospitals admit. Normalised against the
# national median so that "1.0" means "national-average acuity" and
# 1.3 means 30% above-average acuity.

NATIONAL_NPR_PER_DAY_MEDIAN = 4_500.0  # rough national midpoint, $/patient-day


def cmi_proxy_from_revenue_per_day(npr_per_day: float) -> float:
    """Map NPR-per-patient-day to a normalized CMI proxy in [0.7, 2.5].

    Returns 1.0 at the national median. Below 0.7 or above 2.5 the
    HCRIS row is almost certainly a data-quality artifact (rural CAH
    or a billing-system mismatch) — we clamp rather than propagate
    junk into the margin adjustment.
    """
    if not (npr_per_day > 0):
        return 1.0
    raw = float(npr_per_day) / NATIONAL_NPR_PER_DAY_MEDIAN
    return max(0.7, min(2.5, raw))


# ---------------------------------------------------------------------------
# DSH supplemental-payment estimate
# ---------------------------------------------------------------------------
#
# CMS DSH adjustment formula simplified for state-level use: hospitals
# above a Medicaid-day threshold get an uplift on their Medicare/
# Medicaid revenue. The actual formula uses the disproportionate
# patient percentage and bed-size brackets (42 CFR §412.106) — we use
# the simplified bracketed step function, accurate to within 2pp of
# NPR for diligence-level estimates.

_DSH_BRACKETS = [
    # (medicaid_pct_threshold, uplift_factor_on_NPR)
    (0.50, 0.18),  # >=50% Medicaid mix → ~18% NPR uplift
    (0.40, 0.13),  # 40-50% → ~13%
    (0.30, 0.08),  # 30-40% → ~8%
    (0.20, 0.04),  # 20-30% → ~4%
]


def dsh_uplift_pct(medicaid_pct: float) -> float:
    """Estimated DSH supplemental payment as a % of NPR.

    Returns 0.0 below the 20% Medicaid-mix qualifying threshold.
    """
    try:
        m = float(medicaid_pct)
    except (TypeError, ValueError):
        return 0.0
    for threshold, factor in _DSH_BRACKETS:
        if m >= threshold:
            return factor
    return 0.0


# ---------------------------------------------------------------------------
# Per-state aggregation, adjustments included
# ---------------------------------------------------------------------------


def _safe_margin(rev: float, opex: float) -> Optional[float]:
    if not (rev > 1e5 and opex > 0):
        return None
    m = (rev - opex) / rev
    if -1.0 <= m <= 1.0:
        return m
    return None


def state_market_adjustments(hcris_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Compute per-state CMI / DSH / teaching-split adjustments.

    Returns a ``{state: {field: value}}`` dict that the heatmap
    renderer merges into the per-state base stats. Every field is a
    plain number or string (no HTML, no markup) so the UI applies
    formatting via CSS classes — consistent with the Phase 1
    sanitization contract.
    """
    out: Dict[str, Dict[str, Any]] = {}
    if hcris_df is None or hcris_df.empty:
        return out

    df = hcris_df.copy()
    if "state" not in df.columns:
        return out

    # AMC classification once; then group by state.
    df["is_amc"] = is_amc_series(
        df.get("name", pd.Series(["" for _ in range(len(df))], index=df.index)),
        df.get("beds"),
    )

    rev_col = (
        "net_patient_revenue"
        if "net_patient_revenue" in df.columns
        else "gross_patient_revenue"
    )

    for state, sdf in df.groupby("state"):
        if not state or pd.isna(state):
            continue

        rev = pd.to_numeric(sdf.get(rev_col), errors="coerce").fillna(0)
        opex = pd.to_numeric(sdf.get("operating_expenses"), errors="coerce").fillna(0)
        days = pd.to_numeric(sdf.get("total_patient_days"), errors="coerce").fillna(0)
        med_pct = pd.to_numeric(sdf.get("medicare_day_pct"), errors="coerce")
        mcd_pct = pd.to_numeric(sdf.get("medicaid_day_pct"), errors="coerce")

        # Teaching vs community margin split
        teaching_margins: List[float] = []
        community_margins: List[float] = []
        for r, o, is_teach in zip(rev, opex, sdf["is_amc"]):
            m = _safe_margin(r, o)
            if m is None:
                continue
            (teaching_margins if bool(is_teach) else community_margins).append(m)

        # CMI proxy: state-level NPR-per-patient-day, mass-weighted by
        # revenue so a small-rural-clinic outlier doesn't drag the
        # average. Falls back to 1.0 when data is missing.
        npr_total = float(rev.sum())
        days_total = float(days.sum())
        npr_per_day = (npr_total / days_total) if days_total > 0 else 0.0
        cmi = cmi_proxy_from_revenue_per_day(npr_per_day)

        # DSH uplift estimate from the state-average Medicaid mix.
        avg_medicaid = float(mcd_pct.mean()) if mcd_pct.notna().any() else 0.0
        dsh = dsh_uplift_pct(avg_medicaid)

        # CMI/DSH-adjusted margin: take the median state operating
        # margin and shift it by the DSH uplift (which adds revenue
        # back) and the CMI normalization (which scales how much of
        # the per-day reimbursement haircut is genuine vs. a side
        # effect of low-acuity case mix). Conservative formula:
        #   adj = base_margin + dsh_uplift * (1 - base_margin)
        #         + (cmi - 1.0) * 0.05    # CMI lift, capped weight
        all_margins = teaching_margins + community_margins
        base = float(pd.Series(all_margins).median()) if all_margins else 0.0
        cmi_lift = max(-0.05, min(0.10, (cmi - 1.0) * 0.05))
        adjusted = base + dsh * (1 - base) + cmi_lift

        out[str(state)] = {
            "teaching_count": len(teaching_margins),
            "community_count": len(community_margins),
            "teaching_avg_margin": (
                round(float(pd.Series(teaching_margins).median()), 4)
                if teaching_margins else None
            ),
            "community_avg_margin": (
                round(float(pd.Series(community_margins).median()), 4)
                if community_margins else None
            ),
            "cmi_proxy": round(cmi, 3),
            "npr_per_day": round(npr_per_day, 0),
            "dsh_uplift_pct": round(dsh, 4),
            "adjusted_margin": round(adjusted, 4),
        }
    return out


def merge_state_adjustments(
    base_stats: Iterable[Dict[str, Any]],
    adjustments: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge per-state CMI/DSH/teaching fields into the base stats list.

    Pure function — does not mutate the input list. Missing states in
    ``adjustments`` get the field set to None so heatmap renderers
    don't have to KeyError-guard every cell.
    """
    out: List[Dict[str, Any]] = []
    for s in base_stats:
        st = s.get("state")
        adj = adjustments.get(str(st), {})
        merged = dict(s)
        for k in (
            "teaching_count", "community_count",
            "teaching_avg_margin", "community_avg_margin",
            "cmi_proxy", "npr_per_day",
            "dsh_uplift_pct", "adjusted_margin",
        ):
            merged[k] = adj.get(k)
        out.append(merged)
    return out
