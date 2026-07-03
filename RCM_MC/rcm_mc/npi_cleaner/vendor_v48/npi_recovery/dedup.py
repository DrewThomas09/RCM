"""
dedup.py  (v34)
===============

Anticipated issue: adjustment and reversal rows inflating or deflating totals.
Claims extracts routinely carry the original claim, a full or partial reversal
(negative allowed), and a resubmission. Summed naively, the drug is counted twice
or the reversal nets against the wrong period. The team's pull reconciles to a
control total today; the first refresh that includes adjustment cycles will not,
and the meeting line will be "the same query gives a different number now."

This module quantifies the exposure without touching a row: exact duplicates,
reversal pairs, and the gross versus net delta. Applying the netting is opt-in
(apply_netting), honoring the house rule that no tab drops or merges rows without
an explicit ask.

Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_KEY_COLS = ["billing_npi", "hcpcs", "ndc", "date", "payer"]


def _keyframe(std: pd.DataFrame, allowed, units) -> pd.DataFrame:
    df = pd.DataFrame(index=std.index)
    for c in _KEY_COLS:
        df[c] = (std[c].astype("string").fillna("").str.strip().str.upper()
                 if c in std.columns else "")
    df["allowed"] = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    df["units"] = pd.to_numeric(units, errors="coerce").fillna(0.0)
    return df


def netting_audit(std: pd.DataFrame, *, allowed, units) -> pd.DataFrame:
    """Report-only: exact duplicate rows (same key, same signed amount), reversal
    pairs (same key, offsetting amounts), and the gross vs net picture."""
    df = _keyframe(std, allowed, units)
    key = df[_KEY_COLS].agg("|".join, axis=1)

    gross = float(df["allowed"].sum())
    neg = float(df.loc[df["allowed"] < 0, "allowed"].sum())
    n_neg = int((df["allowed"] < 0).sum())

    dup_key = key + "|" + df["allowed"].round(2).astype(str)
    dup_counts = dup_key.value_counts()
    dup_extra = dup_counts[dup_counts > 1]
    dup_rows = int((dup_extra - 1).sum())
    amt = df["allowed"].round(2)
    per_dup = amt.groupby(dup_key).first()
    dup_dollars = float(((dup_extra - 1) * per_dup.reindex(dup_extra.index)).sum())

    matched_reversal = 0.0
    n_pairs = 0
    for k, g in df[df["allowed"] != 0].groupby(key.rename("k")):
        pos = sorted(g.loc[g["allowed"] > 0, "allowed"].round(2).tolist())
        negs = sorted((-g.loc[g["allowed"] < 0, "allowed"]).round(2).tolist())
        i = j = 0
        while i < len(pos) and j < len(negs):
            if abs(pos[i] - negs[j]) < 0.005:
                matched_reversal += pos[i]
                n_pairs += 1
                i += 1
                j += 1
            elif pos[i] < negs[j]:
                i += 1
            else:
                j += 1

    net = gross
    rows = [
        {"metric": "gross allowed (as summed today)", "value": round(gross, 2)},
        {"metric": "negative-amount rows (reversals/adjustments)", "value": n_neg},
        {"metric": "negative dollars", "value": round(neg, 2)},
        {"metric": "reversal pairs matched on key (original + offset)", "value": n_pairs},
        {"metric": "dollars in matched reversal pairs (net zero, gross double)",
         "value": round(matched_reversal, 2)},
        {"metric": "exact duplicate rows beyond first occurrence", "value": dup_rows},
        {"metric": "duplicate dollars at risk of double count", "value": round(dup_dollars, 2)},
        {"metric": "net allowed after removing exact duplicates",
         "value": round(net - dup_dollars, 2)},
    ]
    out = pd.DataFrame(rows)
    out.attrs["duplicate_dollars"] = round(dup_dollars, 2)
    out.attrs["reversal_pair_dollars"] = round(matched_reversal, 2)
    out.attrs["note"] = (
        "Report-only; no rows were dropped or merged. Matched reversal pairs already net to "
        "zero in the sum but double the gross activity; exact duplicates inflate the sum "
        "itself. Apply netting only via the opt-in flag.")
    return out


def apply_netting(std: pd.DataFrame, *, allowed_col: str = "allowed_amt",
                  units_col: str = "units") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Opt-in: drop exact duplicate rows beyond the first occurrence and drop
    matched reversal pairs (both legs). Returns (netted_std, audit). Unmatched
    negatives are kept, visibly, because forcing them against the wrong original
    is worse than showing them."""
    if not std.index.is_unique:
        # positional safety: duplicate labels would let one .loc write hit
        # several rows and drop the wrong legs
        std = std.reset_index(drop=True)
    a = pd.to_numeric(std.get(allowed_col, 0), errors="coerce").fillna(0.0)
    u = pd.to_numeric(std.get(units_col, 0), errors="coerce").fillna(0.0)
    df = _keyframe(std, a, u)
    key = df[_KEY_COLS].agg("|".join, axis=1)
    dup_key = key + "|" + df["allowed"].round(2).astype(str)
    keep = ~dup_key.duplicated(keep="first")

    drop_pairs = pd.Series(False, index=std.index)
    for k, g in df[keep & (df["allowed"] != 0)].groupby(key.rename("k")):
        pos = g[g["allowed"] > 0].sort_values("allowed")
        negs = g[g["allowed"] < 0].assign(_m=lambda d: -d["allowed"]).sort_values("_m")
        i = j = 0
        pi, ni = pos.index.tolist(), negs.index.tolist()
        pv = pos["allowed"].round(2).tolist()
        nv = negs["_m"].round(2).tolist()
        while i < len(pv) and j < len(nv):
            if abs(pv[i] - nv[j]) < 0.005:
                drop_pairs.loc[pi[i]] = True
                drop_pairs.loc[ni[j]] = True
                i += 1
                j += 1
            elif pv[i] < nv[j]:
                i += 1
            else:
                j += 1

    final_keep = keep & ~drop_pairs
    netted = std.loc[final_keep].copy()
    audit = pd.DataFrame([
        {"metric": "rows in", "value": int(len(std))},
        {"metric": "exact duplicates dropped", "value": int((~keep).sum())},
        {"metric": "reversal-pair rows dropped (both legs)", "value": int(drop_pairs.sum())},
        {"metric": "rows out", "value": int(len(netted))},
        {"metric": "allowed in", "value": round(float(a.sum()), 2)},
        {"metric": "allowed out", "value": round(float(a[final_keep].sum()), 2)},
    ])
    audit.attrs["note"] = ("Opt-in netting applied: duplicates beyond first occurrence and "
                           "matched reversal pairs removed; unmatched negatives retained.")
    return netted, audit
