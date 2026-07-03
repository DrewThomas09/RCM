"""
vrdc_suppression.py  (v32)
==========================

The analytical headline the meeting notes buried. A CMS VRDC export blinds any
cell below 11 beneficiaries (small-cell suppression), but the same export also
carries unsuppressed AGGREGATE totals, because an aggregate clears the disclosure
threshold even when its component cells do not. Evan's 0:03 insight follows
directly: those totals are the reconciliation target for any gap-fill, and

    suppression hides distribution, not volume.

Imputation can only redistribute a fixed aggregate across the blinded cells. It
cannot create volume the aggregate does not contain. So if the unsuppressed
Option Care total is already too low, a perfect gap-fill reconstructs a number
that is already wrong, and the deficit sits upstream of suppression, in the pull.

This module makes that argument computable in four steps:

  1. detect_suppression       flag the blinded cells (marker, or count < 11).
  2. reconcile_scope          per aggregation scope: visible sum, the unsuppressed
                              aggregate (the ceiling), the suppressed residual
                              (mass hidden by suppression), and the cell count.
  3. impute_suppressed_cells  fill the blinded cells so they sum EXACTLY to the
                              residual. A scope with one suppressed cell is
                              recovered exactly (complementary suppression); a
                              scope with several distributes the residual by an
                              optional weight, capped so no cell implies >= 11
                              beneficiaries. Every filled value is flagged.
  4. ceiling_report           reconstructed total (= the aggregate ceiling) vs an
                              external expected total (management, Komodo). The
                              part imputation can close is the residual; the part
                              it CANNOT close is the irreducible upstream deficit.

Everything is deterministic and offline: hand-rolled numpy, no solver, no model.
Nothing is invented above the aggregate; unfillable scopes are reported, never
forced.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SUPPRESSION_THRESHOLD = 11  # CMS cell-suppression floor: counts of 1..10 blinded


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def detect_suppression(df: pd.DataFrame, *, value_col: str,
                       count_col: str | None = None,
                       suppressed_flag: str | None = None,
                       threshold: int = SUPPRESSION_THRESHOLD,
                       markers=("*", "S", "DS", "N/A", "NA", "-", "")) -> pd.DataFrame:
    """Add a boolean `_is_suppressed` per row. A cell is suppressed when an explicit
    flag says so, when its value is a known suppression marker or non-numeric, or
    when a present beneficiary count is between 1 and threshold-1 inclusive. A cell
    with a genuine numeric value and a count >= threshold is not suppressed."""
    out = df.copy()
    n = len(out)
    supp = np.zeros(n, dtype=bool)

    if suppressed_flag and suppressed_flag in out.columns:
        supp |= out[suppressed_flag].map(
            lambda x: str(x).strip().lower() in ("1", "true", "yes", "y", "suppressed", "s")).to_numpy()

    raw = out[value_col]
    val = _num(raw)
    is_blank_marker = raw.map(
        lambda x: (str(x).strip() in markers) or (str(x).strip().upper() in ("*", "S", "DS")))
    supp |= (val.isna() & (is_blank_marker | raw.isna())).to_numpy()

    if count_col and count_col in out.columns:
        cnt = _num(out[count_col])
        # a positive count below the threshold marks a suppressed-by-rule cell
        supp |= ((cnt >= 1) & (cnt < threshold)).fillna(False).to_numpy()
        # a cell whose count is itself blank/suppressed while value is blank
        supp |= (cnt.isna() & val.isna()).to_numpy()

    out["_is_suppressed"] = supp
    out["_value_num"] = val
    return out


def reconcile_scope(df: pd.DataFrame, *, value_col: str, scope_cols,
                    total_col: str | None = None, scope_total=None,
                    count_col: str | None = None,
                    threshold: int = SUPPRESSION_THRESHOLD) -> pd.DataFrame:
    """Per aggregation scope (the group defined by scope_cols) report the visible
    sum, the unsuppressed aggregate total (the ceiling), the suppressed residual
    the gap-fill must distribute, and the suppressed-cell count.

    The aggregate total comes from total_col (a per-row column repeating the scope
    total) or from scope_total ({scope_key: total} or a scalar). When neither is
    supplied the visible sum is the only available anchor and residual is reported
    as unknown."""
    work = df
    if "_is_suppressed" not in work.columns:
        work = detect_suppression(work, value_col=value_col, count_col=count_col,
                                  threshold=threshold)
    scope_cols = list(scope_cols)
    val = work["_value_num"] if "_value_num" in work.columns else _num(work[value_col])
    g = work.assign(_v=val).groupby(scope_cols, dropna=False)

    rows = []
    for key, idx in g.groups.items():
        sub = work.loc[idx]
        vis = float(_num(sub.loc[~sub["_is_suppressed"], value_col]).fillna(0).sum())
        n_supp = int(sub["_is_suppressed"].sum())
        n_cells = int(len(sub))

        agg = np.nan
        if total_col and total_col in sub.columns:
            agg = float(_num(sub[total_col]).dropna().iloc[0]) if _num(sub[total_col]).notna().any() else np.nan
        elif isinstance(scope_total, dict):
            k = key if not isinstance(key, tuple) or len(scope_cols) > 1 else key
            agg = float(scope_total.get(key, scope_total.get(str(key), np.nan)))
        elif scope_total is not None:
            agg = float(scope_total)

        residual = (agg - vis) if not np.isnan(agg) else np.nan
        rows.append({
            **({scope_cols[0]: key} if len(scope_cols) == 1 else
               {c: k for c, k in zip(scope_cols, (key if isinstance(key, tuple) else (key,)))}),
            "n_cells": n_cells,
            "n_suppressed": n_supp,
            "visible_sum": round(vis, 2),
            "aggregate_total_ceiling": (round(agg, 2) if not np.isnan(agg) else np.nan),
            "suppressed_residual": (round(residual, 2) if not np.isnan(residual) else np.nan),
            "exact_recoverable": bool(n_supp == 1 and not np.isnan(residual)),
            "residual_negative_flag": bool((not np.isnan(residual)) and residual < -0.5),
        })
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "aggregate_total_ceiling is the unsuppressed total; a gap-fill cannot exceed it. "
        "suppressed_residual = ceiling - visible_sum is the mass hidden by suppression and "
        "redistributable across the blinded cells. exact_recoverable scopes have a single "
        "suppressed cell and are recovered exactly (complementary suppression). "
        "residual_negative_flag means visible cells already exceed the stated total, i.e. the "
        "total or the cell mapping is wrong.")
    return out


def impute_suppressed_cells(df: pd.DataFrame, *, value_col: str, scope_cols,
                            total_col: str | None = None, scope_total=None,
                            weight_col: str | None = None,
                            count_col: str | None = None,
                            per_bene_rate: float | None = None,
                            threshold: int = SUPPRESSION_THRESHOLD) -> pd.DataFrame:
    """Fill the blinded cells so each scope sums exactly to its aggregate ceiling.

    Single-suppressed scopes are recovered exactly. Multi-suppressed scopes split
    the residual across their blinded cells by weight_col (else evenly). When a
    per-bene dollar rate is supplied, each filled cell is capped at
    (threshold-1) * rate so no imputed cell implies >= 11 beneficiaries; any mass
    that cannot fit under the caps is left in `_residual_unallocated` rather than
    forced. Adds `value_filled` (visible value or imputed) and `_imputed`."""
    work = df
    if "_is_suppressed" not in work.columns:
        work = detect_suppression(work, value_col=value_col, count_col=count_col,
                                  threshold=threshold)
    work = work.copy()
    scope_cols = list(scope_cols)
    val = work["_value_num"] if "_value_num" in work.columns else _num(work[value_col])
    filled = val.to_numpy(dtype=float).copy()
    imputed = np.zeros(len(work), dtype=bool)
    unalloc = {}

    # resolve the scope ceiling the same way reconcile_scope does
    def _agg_for(sub, key):
        if total_col and total_col in sub.columns and _num(sub[total_col]).notna().any():
            return float(_num(sub[total_col]).dropna().iloc[0])
        if isinstance(scope_total, dict):
            return float(scope_total.get(key, scope_total.get(str(key), np.nan)))
        if scope_total is not None:
            return float(scope_total)
        return np.nan

    positions = {i: p for p, i in enumerate(work.index)}
    for key, idx in work.groupby(scope_cols, dropna=False).groups.items():
        sub = work.loc[idx]
        agg = _agg_for(sub, key)
        if np.isnan(agg):
            continue
        vis = float(_num(sub.loc[~sub["_is_suppressed"], value_col]).fillna(0).sum())
        residual = agg - vis
        supp_idx = list(sub.index[sub["_is_suppressed"]])
        if not supp_idx or residual <= 0:
            continue
        if len(supp_idx) == 1:
            p = positions[supp_idx[0]]
            filled[p] = round(residual, 4)
            imputed[p] = True
            continue
        # multiple suppressed cells: weight then cap
        if weight_col and weight_col in sub.columns:
            w = _num(sub.loc[supp_idx, weight_col]).fillna(0).to_numpy(dtype=float)
            if w.sum() <= 0:
                w = np.ones(len(supp_idx))
        else:
            w = np.ones(len(supp_idx))
        share = w / w.sum() * residual
        if per_bene_rate and per_bene_rate > 0:
            cap = (threshold - 1) * per_bene_rate
            share = np.minimum(share, cap)
            leftover = residual - float(share.sum())
            if leftover > 0.5:
                unalloc[str(key)] = round(leftover, 2)
        for j, ix in enumerate(supp_idx):
            p = positions[ix]
            filled[p] = round(float(share[j]), 4)
            imputed[p] = True

    work["value_filled"] = filled
    work["_imputed"] = imputed
    work.attrs["note"] = (
        "value_filled equals the visible value where present, else the imputed share. "
        "Single-suppressed scopes are exact (complementary recovery); multi-suppressed "
        "scopes distribute the residual by weight and are capped so no imputed cell implies "
        ">= {} beneficiaries. Mass that cannot fit under the caps is left unallocated, not "
        "forced.".format(threshold))
    work.attrs["residual_unallocated"] = unalloc
    return work


def ceiling_report(*, reconstructed_total, external_expected,
                   visible_sum=None, suppressed_residual=None,
                   entity_label: str = "target") -> pd.DataFrame:
    """The load-bearing summary: what gap-filling can and cannot fix. The
    reconstructed total equals the unsuppressed aggregate ceiling. Whatever an
    external expected total exceeds that ceiling by is the irreducible deficit
    that sits UPSTREAM of suppression (entity roster, claim-type scope, book
    structure), because no redistribution of a fixed aggregate can reach it."""
    recon = float(reconstructed_total or 0.0)
    rows = [{"line": f"reconstructed total = unsuppressed ceiling ({entity_label})",
             "amount": round(recon, 2)}]
    if visible_sum is not None:
        rows.append({"line": "  of which visible (unsuppressed cells)", "amount": round(float(visible_sum), 2)})
    if suppressed_residual is not None:
        rows.append({"line": "  of which recoverable by gap-fill (suppressed residual)",
                     "amount": round(float(suppressed_residual), 2)})

    verdict = "NO EXTERNAL TARGET"
    if external_expected is not None and float(external_expected) > 0:
        ext = float(external_expected)
        deficit = ext - recon
        rows.append({"line": f"external expected total ({entity_label})", "amount": round(ext, 2)})
        rows.append({"line": "ceiling as % of expected",
                     "amount": round(recon / ext * 100, 1)})
        rows.append({"line": "irreducible upstream deficit (gap-fill CANNOT close)",
                     "amount": round(deficit, 2)})
        if suppressed_residual is not None:
            rows.append({"line": "  for scale: redistributable mass (gap-fill CAN move)",
                         "amount": round(float(suppressed_residual), 2)})
        if deficit <= 0:
            verdict = "CEILING MEETS EXPECTED"
        elif suppressed_residual is not None and float(suppressed_residual) > 0:
            ratio = deficit / max(float(suppressed_residual), 1e-9)
            verdict = ("UPSTREAM DEFICIT DOMINATES" if ratio >= 1.0
                       else "MIXED: deficit and suppression comparable")
        else:
            verdict = "UPSTREAM DEFICIT"

    out = pd.DataFrame(rows)
    out.attrs["verdict"] = verdict
    out.attrs["note"] = (
        "Gap-filling redistributes the suppressed residual only; it cannot exceed the "
        "unsuppressed ceiling. A positive upstream deficit is not fixable by imputation and "
        "points to the pull (entity roster, claim-type scope, or genuine FFS book structure). "
        "Verdict: {}.".format(verdict))
    return out
