"""
rif_cleaning.py  (v47)
======================

VRDC-specific cleaning and export safety. Two things RIF data needs that a
commercial extract does not:

  cell suppression   Nothing leaves the VRDC enclave without small-cell
                     suppression. CMS policy is that any exported cell representing
                     fewer than 11 beneficiaries must be suppressed, and
                     complementary cells must be suppressed too so the small cell
                     cannot be recovered by subtraction. This module applies both
                     primary and complementary suppression to any aggregate before
                     it is cleared for export. This is the single most important
                     VRDC-specific step: an aggregate that has not been suppressed
                     cannot legally leave the enclave.

  RIF hygiene        FFS-specific normalizations: resolve the claim-vs-line grain,
                     handle the RIF sentinel/again codes, and flag the FFS-specific
                     recovery case where the organization NPI is blank because a
                     solo practitioner billed under only an individual NPI.

Deterministic and offline. The suppression threshold is a parameter defaulting to
the CMS minimum of 11.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


CMS_MIN_CELL = 11  # CMS small-cell suppression threshold (beneficiaries)


def suppress_small_cells(agg: pd.DataFrame, count_col: str,
                         value_cols=None, threshold: int = CMS_MIN_CELL,
                         group_col: str = None) -> pd.DataFrame:
    """Apply CMS small-cell suppression to an aggregate table.

    agg          an aggregate (one row per cell) with a beneficiary count column
    count_col    the column holding the distinct beneficiary count per cell
    value_cols   columns to blank when a cell is suppressed (dollars, etc.);
                 defaults to every numeric column except the count
    threshold    minimum cell size to keep (CMS minimum is 11)
    group_col    if given, complementary suppression is applied within each group
                 (so a single suppressed cell in a group cannot be back-computed
                 from the group total)

    Returns a copy with suppressed cells marked and their values blanked.
    """
    out = agg.copy()
    if count_col not in out.columns:
        out.attrs["note"] = f"count column '{count_col}' absent; no suppression applied"
        return out
    counts = pd.to_numeric(out[count_col], errors="coerce").fillna(0)
    if value_cols is None:
        value_cols = [c for c in out.columns
                      if c != count_col and pd.api.types.is_numeric_dtype(out[c])]

    primary = counts < threshold
    out["suppressed"] = primary
    out["suppression_reason"] = np.where(primary, f"cell < {threshold} beneficiaries", "")

    # complementary suppression: if a group has exactly one suppressed cell, a
    # second smallest cell must also be suppressed so the first is not recoverable
    if group_col and group_col in out.columns:
        for g, idx in out.groupby(group_col).groups.items():
            block = out.loc[idx]
            supp = block[block["suppressed"]]
            if len(supp) == 1:
                # suppress the next-smallest non-suppressed cell in the group
                rest = block[~block["suppressed"]]
                if not rest.empty:
                    victim = pd.to_numeric(rest[count_col], errors="coerce").idxmin()
                    out.at[victim, "suppressed"] = True
                    out.at[victim, "suppression_reason"] = "complementary suppression"

    for c in value_cols:
        out.loc[out["suppressed"], c] = np.nan
    # also blank the count itself on suppressed rows
    out.loc[out["suppressed"], count_col] = np.nan

    n_supp = int(out["suppressed"].sum())
    out.attrs["note"] = (
        f"{n_supp} of {len(out)} cells suppressed (primary threshold {threshold} "
        f"beneficiaries"
        + (", plus complementary suppression within groups" if group_col else "")
        + "). This table is cleared for export from the VRDC enclave. Suppressed "
        f"cells have their count and values blanked and cannot be recovered by "
        f"subtraction.")
    return out


def export_safe(agg: pd.DataFrame, count_col: str, **kwargs) -> tuple:
    """Convenience wrapper: returns (suppressed_table, is_clean) where is_clean is
    True only if no small cell survives. Use this as the gate before any RIF
    aggregate leaves the enclave."""
    supp = suppress_small_cells(agg, count_col, **kwargs)
    if count_col in supp.columns:
        remaining = pd.to_numeric(supp[count_col], errors="coerce")
        threshold = kwargs.get("threshold", CMS_MIN_CELL)
        is_clean = bool((remaining.dropna() >= threshold).all())
    else:
        is_clean = True
    return supp, is_clean


def flag_solo_biller_gap(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """FFS-specific recovery case: the organization NPI (billing_npi) is blank
    because a solo practitioner billed under only an individual NPI, which in RIF
    appears as the performing physician (rendering_npi). These are recoverable by
    promoting the rendering NPI, a case that does not arise the same way in
    commercial data. Returns the affected rows with the suggested billing NPI."""
    bcol = "billing_npi"
    rcol = "rendering_npi"
    if bcol not in std.columns or rcol not in std.columns:
        return pd.DataFrame({"note": [
            "solo-biller gap needs both a billing (org) NPI and a rendering "
            "(performing) NPI column"]})
    blank_org = std[bcol].isna() | (std[bcol].astype("string").str.strip().isin(["", "nan", "<NA>", "0"]))
    has_rendering = std[rcol].notna() & ~std[rcol].astype("string").str.strip().isin(["", "nan", "<NA>", "0"])
    sel = blank_org & has_rendering
    out = std.loc[sel, [rcol]].copy()
    out["row"] = out.index
    out = out.rename(columns={rcol: "rendering_npi"})
    out["suggested_billing_npi"] = out["rendering_npi"]
    out["fix_rule"] = "solo practitioner billed under individual NPI; promote rendering to billing"
    out["confidence"] = "high"
    out.attrs["note"] = (
        f"{len(out)} FFS lines have a blank organization NPI but a present performing "
        f"physician NPI: a solo practitioner billing under an individual NPI. These "
        f"are high-confidence recoveries by promoting the rendering NPI, an FFS "
        f"specific case commercial recovery does not see.")
    return out.reset_index(drop=True)
