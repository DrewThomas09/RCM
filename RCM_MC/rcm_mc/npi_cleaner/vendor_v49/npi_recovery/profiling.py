"""
profiling.py  (v46)
===================

Automatic data profiling: point it at a claims frame and get a per-column read of
what is there before any screen runs. This is the first thing an analyst wants on
a new extract, and it doubles as a data-quality triage: which columns are empty,
which are constant, which are effectively unique keys, which numeric columns have
impossible ranges, which look like dates or codes.

For very large files the SQL profiler in engine.py computes the same core metrics
without loading the file. This module is the in-memory version with a richer read
(inferred semantic type, numeric summary, top values), used inside the pipeline
and for files that fit in memory.

Deterministic and dependency-free.
"""
from __future__ import annotations

import re
import pandas as pd
import numpy as np

_NPI_RE = re.compile(r"^\d{10}$")
_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
_HCPCS_RE = re.compile(r"^[A-Z]\d{4}$")
_ICD_RE = re.compile(r"^[A-Z]\d{2}")
_DATE_HINT = re.compile(r"date|dos|dob", re.I)


def _semantic_type(name, s):
    """A best-effort semantic label from the values and the column name."""
    non_null = s.dropna().astype(str).str.strip()
    if non_null.empty:
        return "empty"
    sample = non_null.head(1000)
    if sample.str.match(_NPI_RE).mean() > 0.8:
        return "npi"
    if sample.str.match(_HCPCS_RE).mean() > 0.8:
        return "hcpcs"
    if sample.str.match(_ICD_RE).mean() > 0.8:
        return "icd10"
    if sample.str.match(_ZIP_RE).mean() > 0.8:
        return "zip"
    # numeric
    num = pd.to_numeric(non_null, errors="coerce")
    if num.notna().mean() > 0.9:
        return "numeric"
    # date
    if _DATE_HINT.search(str(name)):
        dt = pd.to_datetime(non_null, errors="coerce")
        if dt.notna().mean() > 0.7:
            return "date"
    dt = pd.to_datetime(non_null, errors="coerce")
    if dt.notna().mean() > 0.9:
        return "date"
    return "text"


def profile_frame(std: pd.DataFrame, top_k=5) -> pd.DataFrame:
    """One row per column: null rate, cardinality, semantic type, numeric range
    where applicable, and a quality flag."""
    n = len(std)
    rows = []
    for c in std.columns:
        if c.endswith("__original"):
            continue
        s = std[c]
        nn = int(s.notna().sum())
        distinct = int(s.nunique(dropna=True))
        stype = _semantic_type(c, s)
        rng = ""
        if stype == "numeric":
            num = pd.to_numeric(s, errors="coerce")
            if num.notna().any():
                rng = f"[{num.min():.2f}, {num.max():.2f}]"
        # quality flag
        flag = ""
        if nn == 0:
            flag = "empty"
        elif distinct == 1:
            flag = "constant"
        elif n and distinct == n and stype in ("text", "numeric"):
            flag = "unique (key-like)"
        elif nn / n < 0.5 if n else False:
            flag = "mostly null"
        rows.append({
            "column": c, "semantic_type": stype,
            "non_null": nn, "null_pct": round(100.0 * (n - nn) / n, 2) if n else 0.0,
            "distinct": distinct,
            "distinct_pct": round(100.0 * distinct / n, 2) if n else 0.0,
            "numeric_range": rng, "quality_flag": flag,
        })
    out = pd.DataFrame(rows)
    empties = out[out["quality_flag"] == "empty"]["column"].tolist()
    out.attrs["note"] = (
        f"{len(out)} columns profiled over {n:,} rows. "
        + (f"Empty columns: {', '.join(empties)}. " if empties else "")
        + "semantic_type is inferred from values; quality_flag surfaces empty, "
        "constant, mostly-null, and key-like columns.")
    return out


def value_distribution(std: pd.DataFrame, column: str, top_k=15) -> pd.DataFrame:
    """Top values for one column, with counts and shares."""
    if column not in std.columns:
        return pd.DataFrame({"note": [f"column '{column}' not present"]})
    vc = std[column].astype(str).value_counts().head(top_k)
    tot = len(std) or 1
    out = pd.DataFrame({column: vc.index, "count": vc.to_numpy(),
                        "share_pct": (100.0 * vc.to_numpy() / tot).round(1)})
    return out
