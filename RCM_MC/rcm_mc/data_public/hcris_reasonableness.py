"""HCRIS-row reasonableness guards run at ingestion time.

PEDESK Phase 3 (Week 3, Model Retraining). The Reasonableness Matrix
and Stress Grid logic in ``pe_intelligence/`` were already correct
deal-level checkers, but they ran *downstream* of HCRIS ingestion —
every page renderer was responsible for filtering its own junk rows.
That gave us a screen-by-screen patchwork (predictive_screener has a
``data_quality_ok`` flag, market_data has its own opex<2*rev clamp,
hold_analysis just trusts the numbers) and let database-error rows
flow into aggregations as if they were real signals. The partner-
visible symptom: "False Precision" headlines anchored on a hospital
whose HCRIS opex was 100× revenue, or whose bed count was 14,000.

This module hard-pipes the same matrix into the HCRIS load path. One
chokepoint, one source of truth, every page benefits without
changing its renderer.

Outputs:

  - ``hcris_quality_flags(df)`` returns the same dataframe with three
    new columns: ``dq_flags`` (semicolon-joined codes), ``dq_severity``
    ("ok" | "warn" | "drop"), ``dq_dropped`` (bool — convenience
    duplicate of ``dq_severity == "drop"``).
  - ``scrub_hcris(df)`` returns the dataframe with ``dq_severity ==
    "drop"`` rows removed. Default behaviour for production callers.
  - ``last_scrub_summary()`` returns a counter dict for the admin
    page so the operator sees how many rows were dropped per check
    on the most recent load.

The check matrix is keyed by short uppercase codes (``OPEX_GT_2X_NPR``,
``BEDS_OUT_OF_BAND``, etc.) so telemetry, audit logs, and the admin
page all reference the same identifiers.
"""
from __future__ import annotations

import threading
from collections import Counter
from typing import Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Reasonableness matrix — keyed by code
# ---------------------------------------------------------------------------
#
# Each entry is (severity, description). Severity:
#   "drop" — row is structurally implausible; downstream code should never
#             see it (e.g., opex 100x revenue is a data-entry error, not a
#             distressed hospital).
#   "warn" — row is plausible but unusual; downstream code may want to
#             label it (e.g., very large hospital).

CHECK_MATRIX: Dict[str, tuple] = {
    # ── Drop tier — structural impossibility ───────────────────────────
    "NEGATIVE_NPR":         ("drop", "net_patient_revenue is negative"),
    "NEGATIVE_OPEX":        ("drop", "operating_expenses is negative"),
    "OPEX_GT_2X_NPR":       ("drop", "operating_expenses > 2× net_patient_revenue (data entry error)"),
    "BEDS_OUT_OF_BAND":     ("drop", "beds < 1 or > 5000 (CMS CCN range cap is ~3000)"),
    "PATIENT_DAYS_NEGATIVE":("drop", "total_patient_days is negative"),
    "GROSS_LT_NET":         ("drop", "gross_patient_revenue < net_patient_revenue (impossible by construction)"),
    "MEDICARE_DAYS_GT_TOTAL":("drop", "medicare_days > total_patient_days (impossible)"),
    "MEDICAID_DAYS_GT_TOTAL":("drop", "medicaid_days > total_patient_days (impossible)"),
    "MEDICARE_PLUS_MEDICAID_GT_TOTAL": ("drop", "medicare_days + medicaid_days > total_patient_days"),
    "REVENUE_BELOW_FLOOR":  ("drop", "net_patient_revenue < $100K (likely missing-data filing)"),
    # ── Warn tier — plausible but unusual ──────────────────────────────
    "BEDS_VERY_LARGE":      ("warn", "beds > 1500 (unusual; possible system-level misallocation)"),
    "MARGIN_EXTREME":       ("warn", "operating margin < -50% or > +50% (unusual but possible)"),
    "OCCUPANCY_GT_100":     ("warn", "implied occupancy > 100% (overflow / accounting timing)"),
    "REVENUE_PER_BED_EXTREME": ("warn", "revenue per bed below $50K or above $5M (sanity-check rate or beds)"),
    "ZERO_PATIENT_DAYS":    ("warn", "total_patient_days is zero (filing without service activity)"),
    "MEDICARE_PCT_GT_95":   ("warn", "medicare day pct > 95% (rare but possible at LTACH/IRF/CAH)"),
    "ALLOWANCE_RATIO_EXTREME":("warn", "(gross-net)/gross outside [0.20, 0.80]"),
}


def get_check_severity(code: str) -> str:
    return CHECK_MATRIX.get(code, ("warn", ""))[0]


# ---------------------------------------------------------------------------
# Last-load summary, lock-protected for thread-safe access
# ---------------------------------------------------------------------------

_LAST_SUMMARY_LOCK = threading.Lock()
_LAST_SUMMARY: Dict[str, int] = {}


def last_scrub_summary() -> Dict[str, int]:
    """Return the last load's scrub summary keyed by check code.

    The admin / data-sources page reads this to display "X rows
    dropped on most recent load: OPEX_GT_2X_NPR=12, BEDS_OUT_OF_BAND=3, …".
    """
    with _LAST_SUMMARY_LOCK:
        return dict(_LAST_SUMMARY)


def _set_summary(counter: Counter) -> None:
    with _LAST_SUMMARY_LOCK:
        global _LAST_SUMMARY
        _LAST_SUMMARY = dict(counter)


# ---------------------------------------------------------------------------
# Per-row check engine (vectorised over a DataFrame)
# ---------------------------------------------------------------------------


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Return ``df[name]`` as a numeric Series aligned to ``df.index``.

    When the column is absent we return an all-NaN Series sharing the
    dataframe's index, so vectorised comparisons against other columns
    (``medicaid_days > days * 1.01``) don't raise
    ``ValueError: Can only compare identically-labeled Series objects``
    on inputs that don't carry every HCRIS column. Real HCRIS data has
    all columns populated; this defensive helper exists for partial
    fixtures (tests, slim extracts, sparse joins).
    """
    if name in df.columns:
        return _to_num(df[name])
    return pd.Series([float("nan")] * len(df), index=df.index, dtype=float)


def hcris_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with ``dq_flags`` / ``dq_severity`` / ``dq_dropped`` columns.

    Pure-vectorised pandas. Does not modify the input. Idempotent —
    if the columns already exist, they're recomputed in case caller
    enriched the row in between.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    npr = _col(out, "net_patient_revenue")
    opex = _col(out, "operating_expenses")
    beds = _col(out, "beds")
    days = _col(out, "total_patient_days")
    bed_days = _col(out, "bed_days_available")
    gpr = _col(out, "gross_patient_revenue")
    medicare_days = _col(out, "medicare_days")
    medicaid_days = _col(out, "medicaid_days")

    # Build per-check boolean masks. ``True`` means the check fired
    # (row is suspect). NaN-safe via ``fillna(False)``.
    masks: Dict[str, pd.Series] = {}
    masks["NEGATIVE_NPR"] = (npr < 0).fillna(False)
    masks["NEGATIVE_OPEX"] = (opex < 0).fillna(False)
    masks["OPEX_GT_2X_NPR"] = ((npr > 0) & (opex > npr * 2)).fillna(False)
    masks["BEDS_OUT_OF_BAND"] = ((beds < 1) | (beds > 5000)).fillna(False)
    masks["PATIENT_DAYS_NEGATIVE"] = (days < 0).fillna(False)
    masks["GROSS_LT_NET"] = ((gpr > 0) & (npr > 0) & (gpr < npr)).fillna(False)
    masks["MEDICARE_DAYS_GT_TOTAL"] = (
        (medicare_days > 0) & (days > 0) & (medicare_days > days * 1.01)
    ).fillna(False)
    masks["MEDICAID_DAYS_GT_TOTAL"] = (
        (medicaid_days > 0) & (days > 0) & (medicaid_days > days * 1.01)
    ).fillna(False)
    masks["MEDICARE_PLUS_MEDICAID_GT_TOTAL"] = (
        (days > 0)
        & ((medicare_days.fillna(0) + medicaid_days.fillna(0)) > days * 1.05)
    ).fillna(False)
    masks["REVENUE_BELOW_FLOOR"] = (npr.notna() & (npr < 100_000)).fillna(False)

    # Warn tier
    masks["BEDS_VERY_LARGE"] = (beds > 1500).fillna(False)
    margin = ((npr - opex) / npr.replace(0, pd.NA)).fillna(0)
    masks["MARGIN_EXTREME"] = ((margin < -0.5) | (margin > 0.5)).fillna(False)
    occupancy = (days / bed_days.replace(0, pd.NA)).fillna(0)
    masks["OCCUPANCY_GT_100"] = (occupancy > 1.05).fillna(False)
    rev_per_bed = (npr / beds.replace(0, pd.NA)).fillna(0)
    masks["REVENUE_PER_BED_EXTREME"] = (
        ((rev_per_bed < 50_000) | (rev_per_bed > 5_000_000))
        & (beds > 0) & (npr > 0)
    ).fillna(False)
    masks["ZERO_PATIENT_DAYS"] = ((days == 0) & npr.notna() & (npr > 0)).fillna(False)
    medicare_pct = (medicare_days / days.replace(0, pd.NA)).fillna(0)
    masks["MEDICARE_PCT_GT_95"] = (medicare_pct > 0.95).fillna(False)
    allowance_ratio = ((gpr - npr) / gpr.replace(0, pd.NA)).fillna(0.45)
    masks["ALLOWANCE_RATIO_EXTREME"] = (
        ((allowance_ratio < 0.20) | (allowance_ratio > 0.80))
        & (gpr > 0)
    ).fillna(False)

    # Aggregate per-row flags + severity. Severity is the most-severe
    # of the firing checks.
    n = len(out)
    flags_per_row: List[List[str]] = [[] for _ in range(n)]
    severity_per_row: List[str] = ["ok"] * n

    for code, mask in masks.items():
        sev = get_check_severity(code)
        for idx in mask[mask].index:
            pos = out.index.get_loc(idx)
            flags_per_row[pos].append(code)
            if sev == "drop" and severity_per_row[pos] != "drop":
                severity_per_row[pos] = "drop"
            elif sev == "warn" and severity_per_row[pos] == "ok":
                severity_per_row[pos] = "warn"

    out["dq_flags"] = ["; ".join(flist) for flist in flags_per_row]
    out["dq_severity"] = severity_per_row
    out["dq_dropped"] = out["dq_severity"] == "drop"
    return out


def scrub_hcris(df: pd.DataFrame, *, keep_warnings: bool = True) -> pd.DataFrame:
    """Return ``df`` with ``dq_severity == "drop"`` rows removed.

    The default for production callers — every downstream page (the
    Predictive Screener, State Heatmap, Distress page, Hold Analysis,
    etc.) sees only rows that have passed structural plausibility
    checks. ``keep_warnings`` defaults to True so partner-visible
    "unusual but plausible" rows (very-large hospitals, extreme
    margins) stay visible with their flag for inspection.

    Updates the module-level scrub summary so the admin page can
    show a per-load breakdown.
    """
    if df is None or df.empty:
        return df
    flagged = hcris_quality_flags(df)
    counter: Counter = Counter()
    for flag_str in flagged["dq_flags"]:
        if not flag_str:
            continue
        for code in flag_str.split("; "):
            counter[code] += 1
    counter["_TOTAL_DROPPED"] = int(flagged["dq_dropped"].sum())
    counter["_TOTAL_WARNED"] = int((flagged["dq_severity"] == "warn").sum())
    counter["_TOTAL_OK"] = int((flagged["dq_severity"] == "ok").sum())
    counter["_INPUT_ROWS"] = int(len(df))
    _set_summary(counter)

    out = flagged[~flagged["dq_dropped"]]
    if not keep_warnings:
        out = out[out["dq_severity"] == "ok"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def is_clean(row: Dict) -> bool:
    """Single-row gate — returns True when the row passes all drop-tier checks.

    Used by callers that operate on dicts (e.g., row-by-row
    processors that don't go through the dataframe scrub).
    """
    if row is None:
        return False
    df = pd.DataFrame([row])
    flagged = hcris_quality_flags(df)
    return not bool(flagged.iloc[0]["dq_dropped"])


def explain_drops() -> List[Dict[str, str]]:
    """Return the check matrix as ``[{code, severity, description}, …]``
    for the admin / methodology page."""
    return [
        {"code": code, "severity": sev, "description": desc}
        for code, (sev, desc) in CHECK_MATRIX.items()
    ]
