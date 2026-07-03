"""
trend_integrity.py  (v33)
=========================

The report's sharpest unfixed claim: "Code-level exclusion doesn't just shrink
volume, it bends trends: the excluded share moves over time as NDCs rotate through
package changes, labeler changes, and biosimilar entry, which can manufacture
spurious mix shifts in exactly the vendor-agnostic analysis they're retreating to."

This module makes that measurable. It computes the excluded share by period under
the code-level rule and the drug-level rule side by side, decomposes each
molecule's apparent share shift into the part that is an inclusion artifact and
the part that is real movement, and lists the concrete flicker events (a new
biosimilar Q-code entering mid-window, a new NDC appearing under an existing
molecule) that drive the artifact.

Deterministic, offline, hand-rolled pandas only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def inclusion_share_by_period(std_named: pd.DataFrame, *, allowed, year,
                              code_mask, drug_mask) -> pd.DataFrame:
    """Per period: total dollars, dollars kept under the code-level rule, dollars
    kept under the drug-level rule, each excluded share, and the divergence in
    points. A divergence that MOVES across periods is the trend bend."""
    a = _num(allowed)
    yr = pd.Series(np.asarray(year), index=std_named.index)
    cm = pd.Series(np.asarray(code_mask), index=std_named.index).astype(bool)
    dm = pd.Series(np.asarray(drug_mask), index=std_named.index).astype(bool)
    df = pd.DataFrame({"year": yr, "allowed": a.to_numpy(),
                       "code_kept": np.where(cm, a, 0.0),
                       "drug_kept": np.where(dm, a, 0.0)})
    g = df.groupby("year").sum(numeric_only=True).reset_index()
    g["code_excluded_pct"] = np.where(g["allowed"] > 0,
                                      (1 - g["code_kept"] / g["allowed"]) * 100, 0.0).round(1)
    g["drug_excluded_pct"] = np.where(g["allowed"] > 0,
                                      (1 - g["drug_kept"] / g["allowed"]) * 100, 0.0).round(1)
    g["divergence_pts"] = (g["code_excluded_pct"] - g["drug_excluded_pct"]).round(1)
    for c in ("allowed", "code_kept", "drug_kept"):
        g[c] = g[c].round(2)
    g.attrs["divergence_drift_pts"] = (
        round(float(g["divergence_pts"].iloc[-1] - g["divergence_pts"].iloc[0]), 1)
        if len(g) >= 2 else 0.0)
    g.attrs["note"] = (
        "code_excluded_pct minus drug_excluded_pct is the false-exclusion share; if that "
        "divergence drifts across periods, the code-level rule is bending the trend, not just "
        "shrinking the level.")
    return g


def trend_bend_decomposition(std_named: pd.DataFrame, *, allowed, year,
                             code_mask, drug_mask,
                             common_name_col: str = "drug_common_name",
                             top_n: int = 20) -> pd.DataFrame:
    """Per molecule: its share of kept spend in the first and last period under
    both rules. apparent_shift is what the code-level view shows; real_shift is
    what the drug-level view shows; artifact = apparent - real is the mix shift
    the inclusion rule manufactured. Sorted by absolute artifact."""
    a = _num(allowed)
    yr = pd.Series(np.asarray(year), index=std_named.index)
    cm = pd.Series(np.asarray(code_mask), index=std_named.index).astype(bool)
    dm = pd.Series(np.asarray(drug_mask), index=std_named.index).astype(bool)
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns
            else pd.Series("(unknown)", index=std_named.index))
    yrs = sorted(pd.unique(yr.dropna()))
    if len(yrs) < 2:
        return pd.DataFrame({"note": ["need at least two periods to decompose a trend"]})
    y0, y1 = yrs[0], yrs[-1]

    def _shares(mask, y):
        sel = (yr == y) & mask
        tot = float(a[sel].sum())
        if tot <= 0:
            return {}
        s = a[sel].groupby(name[sel]).sum() / tot * 100
        return s.to_dict()

    c0, c1 = _shares(cm, y0), _shares(cm, y1)
    d0, d1 = _shares(dm, y0), _shares(dm, y1)
    mols = set(c0) | set(c1) | set(d0) | set(d1)
    rows = []
    for m in mols:
        app = c1.get(m, 0.0) - c0.get(m, 0.0)
        real = d1.get(m, 0.0) - d0.get(m, 0.0)
        rows.append({"molecule": m,
                     "share_code_first_pct": round(c0.get(m, 0.0), 2),
                     "share_code_last_pct": round(c1.get(m, 0.0), 2),
                     "apparent_shift_pts": round(app, 2),
                     "real_shift_pts": round(real, 2),
                     "artifact_pts": round(app - real, 2)})
    out = (pd.DataFrame(rows)
           .assign(_abs=lambda d: d["artifact_pts"].abs())
           .sort_values("_abs", ascending=False).drop(columns="_abs")
           .head(top_n).reset_index(drop=True))
    out.attrs["note"] = (
        "artifact_pts is the mix shift the code-level inclusion rule manufactured "
        "(apparent minus real). Large artifacts on molecules with biosimilar entry or NDC "
        "rotation are the report's spurious-mix-shift failure, caught before it charts.")
    return out


def flicker_events(std_named: pd.DataFrame, *, year,
                   hcpcs_col: str = "hcpcs", ndc_col: str = "ndc",
                   common_name_col: str = "drug_common_name") -> pd.DataFrame:
    """The concrete drivers: for each molecule, codes and NDCs that first appear
    AFTER the molecule's first period (biosimilar Q-code entry, NDC rotation,
    labeler change). These are the rows a snapshot formulary match starts missing
    mid-window."""
    yr = pd.Series(np.asarray(year), index=std_named.index)
    name = (std_named[common_name_col].astype("string").fillna("(unknown)")
            if common_name_col in std_named.columns
            else pd.Series("(unknown)", index=std_named.index))
    hc = (std_named[hcpcs_col].astype("string").fillna("").str.strip().str.upper()
          if hcpcs_col in std_named.columns else pd.Series("", index=std_named.index))
    nd = (std_named[ndc_col].astype("string").fillna("").str.strip()
          if ndc_col in std_named.columns else pd.Series("", index=std_named.index))

    rows = []
    df = pd.DataFrame({"m": name, "y": yr, "h": hc, "n": nd}).dropna(subset=["y"])
    for m, g in df.groupby("m"):
        first = g["y"].min()
        for h, gg in g[g["h"] != ""].groupby("h"):
            fy = gg["y"].min()
            if fy > first:
                kind = "NEW_BIOSIMILAR_QCODE" if str(h).startswith("Q5") else "NEW_CODE"
                rows.append({"molecule": m, "event": kind, "identifier": h,
                             "molecule_first_period": first, "identifier_first_period": fy})
        for n, gg in g[g["n"] != ""].groupby("n"):
            fy = gg["y"].min()
            if fy > first:
                rows.append({"molecule": m, "event": "NEW_NDC", "identifier": n,
                             "molecule_first_period": first, "identifier_first_period": fy})
    if not rows:
        return pd.DataFrame({"note": ["no mid-window code or NDC entries detected"]})
    out = pd.DataFrame(rows).sort_values(
        ["identifier_first_period", "molecule"]).reset_index(drop=True)
    out.attrs["note"] = (
        "Each row is an identifier that entered after the molecule was already in the panel. "
        "Under a code-level snapshot match these rows fall out of scope on arrival, which is "
        "the mechanism that bends the trend.")
    return out
