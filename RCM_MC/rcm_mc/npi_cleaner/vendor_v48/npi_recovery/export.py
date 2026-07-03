"""
export.py  (v46)
================

Output flexibility. Through v45 the deliverable was always a workbook, which is
right for a reviewer but wrong for a data pipeline that wants to load the cleaned
claims into a warehouse or hand them to another tool. This module writes any result
frame to Parquet (columnar, compressed, the right format for large data), CSV
(universal), or JSON (for APIs and record-oriented consumers), and can export a
whole run's key frames at once.

Parquet is the default for the cleaned dataset because it round-trips types, is a
fraction of the size of xlsx or CSV, and loads fast; CSV and JSON are there for
consumers that need them. Deterministic.
"""
from __future__ import annotations

import os
import json
import pandas as pd


def _to_parquet_safe(df: pd.DataFrame, path: str):
    """Write parquet, coercing mixed-type object columns to string so a column
    holding both numbers and text (common in a corrections companion) does not
    break the Arrow conversion."""
    safe = df.copy()
    for c in safe.columns:
        if safe[c].dtype == object:
            types = set(type(v).__name__ for v in safe[c].dropna().head(1000))
            if len(types) > 1:
                safe[c] = safe[c].astype(str)
    try:
        safe.to_parquet(path, index=False)
    except Exception:
        # last resort: stringify every object column
        for c in safe.columns:
            if safe[c].dtype == object:
                safe[c] = safe[c].astype(str)
        safe.to_parquet(path, index=False)


def export_frame(df: pd.DataFrame, path: str, fmt: str = None) -> str:
    """Write one frame. Format inferred from the extension unless fmt is given."""
    fmt = (fmt or os.path.splitext(path)[1].lstrip(".")).lower()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if fmt in ("parquet", "pq"):
        _to_parquet_safe(df, path)
    elif fmt in ("csv",):
        df.to_csv(path, index=False)
    elif fmt in ("tsv",):
        df.to_csv(path, index=False, sep="\t")
    elif fmt in ("json",):
        df.to_json(path, orient="records", date_format="iso")
    elif fmt in ("jsonl", "ndjson"):
        df.to_json(path, orient="records", lines=True, date_format="iso")
    else:
        raise ValueError(f"unsupported export format: {fmt}")
    return path


def export_result(result_frames: dict, out_dir: str, fmt: str = "parquet") -> pd.DataFrame:
    """Export a dict of {name: frame} to a directory, one file per frame. Returns
    a manifest of what was written."""
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for name, df in result_frames.items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        path = os.path.join(out_dir, f"{name}.{fmt}")
        try:
            export_frame(df, path, fmt)
            rows.append({"frame": name, "rows": len(df), "path": path,
                         "bytes": os.path.getsize(path)})
        except Exception as e:
            rows.append({"frame": name, "rows": len(df), "path": "",
                         "bytes": 0, "error": str(e)})
    manifest = pd.DataFrame(rows)
    manifest.attrs["note"] = (f"{len(manifest)} frames exported to {out_dir} as {fmt}. "
                              f"Parquet round-trips types and is compact; use it for the "
                              f"cleaned dataset going into a warehouse.")
    return manifest
