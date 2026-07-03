"""
focused_report.py  (v42)
========================

Writes the output for a selectable-fix run: a thin, focused workbook whose first
sheet is always the fixability manifest (what the tool can and cannot fix on this
input), followed by one sheet per fix that was run. This is the opposite of the
old monolithic 100+ sheet workbook: a run does one thing and the output shows
that one thing plus the manifest.

Uses xlsxwriter in constant_memory mode when available (flushes each row so a
multi-GB extract does not blow up memory; the research called openpyxl the write
bottleneck for wide workbooks). Falls back to openpyxl if xlsxwriter is absent.
Optionally drops a Parquet sidecar per result frame for large outputs.
"""
from __future__ import annotations

import os
import pandas as pd


def _sheet_name(key: str, used: set) -> str:
    name = key[:28]
    base, i = name, 1
    while name in used:
        name = f"{base[:25]}_{i}"
        i += 1
    used.add(name)
    return name


def _result_note(df: pd.DataFrame) -> str:
    if hasattr(df, "attrs") and df.attrs.get("note"):
        return str(df.attrs["note"])
    if "note" in getattr(df, "columns", []) and len(df):
        return str(df["note"].iloc[0])
    return ""


def write_focused(path: str, std: pd.DataFrame, manifest: pd.DataFrame,
                  results: dict, source_name: str,
                  parquet_sidecar: bool = False,
                  coverage: pd.DataFrame = None) -> str:
    """Write the manifest + one sheet per result. Returns the path written."""
    engine = "xlsxwriter"
    try:
        import xlsxwriter  # noqa: F401
    except Exception:
        engine = "openpyxl"

    # a compact run summary from the manifest + result row counts
    summ_rows = []
    for _, r in manifest.iterrows():
        ran = r["key"] in results
        res = results.get(r["key"])
        summ_rows.append({
            "fix": r["fix"], "key": r["key"], "group": r["group"],
            "kahn_category": r["kahn_category"], "fixability": r["status"],
            "ran": ran, "flagged_rows": (len(res) if ran and res is not None else ""),
            "result_note": _result_note(res) if ran and res is not None else "",
        })
    summary = pd.DataFrame(summ_rows)

    kwargs = {"engine": engine}
    if engine == "xlsxwriter":
        kwargs["engine_kwargs"] = {"options": {"constant_memory": True,
                                               "in_memory": True}}
    with pd.ExcelWriter(path, **kwargs) as xw:
        # sheet 1: the manifest / run summary
        _about = pd.DataFrame({
            "field": ["source_file", "input_rows", "fixes_run",
                      "supported_fixes", "partial_fixes", "unsupported_fixes"],
            "value": [source_name, len(std), len(results),
                      int((manifest["status"] == "supported").sum()),
                      int((manifest["status"] == "partial").sum()),
                      int((manifest["status"] == "unsupported").sum())],
        })
        _about.to_excel(xw, sheet_name="About", index=False)
        summary.to_excel(xw, sheet_name="Fixability_Manifest", index=False)
        used = {"About", "Fixability_Manifest"}
        if coverage is not None and len(coverage):
            coverage.to_excel(xw, sheet_name="Field_Coverage", index=False)
            used.add("Field_Coverage")
        for key, df in results.items():
            if df is None:
                df = pd.DataFrame({"note": ["(no result)"]})
            # keep sheets bounded; huge flag lists go to a sidecar
            sheet = _sheet_name(key, used)
            if len(df) > 200_000 and parquet_sidecar:
                side = os.path.splitext(path)[0] + f".{key}.parquet"
                try:
                    df.to_parquet(side, index=False)
                    pd.DataFrame({"note": [
                        f"{len(df)} rows written to sidecar {os.path.basename(side)} "
                        f"(too large for a worksheet)."]}).to_excel(
                        xw, sheet_name=sheet, index=False)
                    continue
                except Exception:
                    pass
            df.head(200_000).to_excel(xw, sheet_name=sheet, index=False)
    return path
