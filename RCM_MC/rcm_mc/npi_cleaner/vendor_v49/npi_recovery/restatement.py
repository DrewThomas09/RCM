"""
restatement.py  (v34)
=====================

Anticipated issue: the refresh that moves a shipped number. Claims vendors
restate: a Komodo or VRDC re-delivery adds late claims, reprices adjustments,
and last month's molecule totals shift under a chart that already went to the
client. The meeting line this preempts: "why does the same query give a
different number this week."

Diff the current build's molecule rollup against the prior build's exported
rollup CSV: per-molecule deltas, restatements beyond tolerance, new and dropped
molecules, and the single worst mover. Point --prior-rollup at last run's
Common_Name_Rollup export and every refresh becomes an audited event instead of
a mystery.

Deterministic and offline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _rollup_from(obj, *, name_col_candidates=("drug_common_name", "molecule", "common_name"),
                 val_col_candidates=("allowed", "allowed_amt", "dollars", "total_allowed")) -> dict:
    df = None
    if isinstance(obj, dict):
        return {str(k): float(v) for k, v in obj.items()}
    if isinstance(obj, pd.DataFrame):
        df = obj
    elif obj is not None and Path(str(obj)).exists():
        try:
            df = pd.read_csv(obj)
        except Exception:
            return {}
    if df is None or df.empty:
        return {}
    cols = {c.strip().lower(): c for c in df.columns}
    nc = next((cols[c] for c in name_col_candidates if c in cols), df.columns[0])
    vc = next((cols[c] for c in val_col_candidates if c in cols), None)
    if vc is None:
        nums = [c for c in df.columns if c != nc
                and pd.to_numeric(df[c], errors="coerce").notna().any()]
        if not nums:
            return {}
        vc = nums[0]
    g = (pd.to_numeric(df[vc], errors="coerce").fillna(0.0)
         .groupby(df[nc].astype("string").fillna("(unknown)")).sum())
    return {str(k): float(v) for k, v in g.items()}


def restatement_diff(prior, std_named: pd.DataFrame, *, allowed,
                     common_name_col: str = "drug_common_name",
                     tolerance_pct: float = 1.0) -> pd.DataFrame:
    """Per molecule: prior dollars, current dollars, delta, percent, status
    (STABLE / RESTATED / NEW / DROPPED)."""
    prev = _rollup_from(prior)
    if not prev:
        return pd.DataFrame({"note": ["supply prior_rollup (last run's Common_Name_Rollup "
                                      "CSV) to audit run-over-run restatements"]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns
            else pd.Series("(unknown)", index=std_named.index))
    cur = {str(k): float(v) for k, v in a.groupby(name).sum().items()}
    keys = sorted(set(prev) | set(cur))
    rows = []
    for k in keys:
        p, c = prev.get(k, 0.0), cur.get(k, 0.0)
        delta = c - p
        pct = (delta / p * 100) if p > 0 else np.nan
        if p == 0 and c > 0:
            status = "NEW (absent from prior run)"
        elif c == 0 and p > 0:
            status = "DROPPED (absent from current run)"
        elif pd.notna(pct) and abs(pct) > tolerance_pct:
            status = "RESTATED (beyond {:.0f} pct tolerance)".format(tolerance_pct)
        else:
            status = "STABLE"
        rows.append({"molecule": k, "prior_allowed": round(p, 2),
                     "current_allowed": round(c, 2), "delta": round(delta, 2),
                     "delta_pct": (round(pct, 2) if pd.notna(pct) else np.nan),
                     "status": status})
    out = (pd.DataFrame(rows)
           .assign(_abs=lambda d: d["delta"].abs())
           .sort_values("_abs", ascending=False).drop(columns="_abs")
           .reset_index(drop=True))
    n_re = int((out["status"].str.startswith("RESTATED")).sum())
    total_prev, total_cur = sum(prev.values()), sum(cur.values())
    out.attrs["n_restated"] = n_re
    out.attrs["total_delta"] = round(total_cur - total_prev, 2)
    worst = out.iloc[0] if len(out) else None
    out.attrs["note"] = (
        "{} molecule(s) restated beyond {:.0f} percent; panel total moved {} run over run. "
        "Worst mover: {} ({:+,.0f}). Cite this table whenever a shipped number changes."
        .format(n_re, tolerance_pct, out.attrs["total_delta"],
                (worst["molecule"] if worst is not None else "n/a"),
                (worst["delta"] if worst is not None else 0.0)))
    return out
