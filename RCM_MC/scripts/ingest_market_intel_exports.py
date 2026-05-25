#!/usr/bin/env python3
"""Offline ingest — licensed SimplyAnalytics market exports → normalized data.

BUILD-TIME ONLY. Reads the tabular exports (XLSX/CSV) from the licensee folder
(default ``~/Desktop/I_Made_It/``), normalizes them into PEdesk's market-intel
schema, and writes committed CSVs under ``data/market_intel/``. Image-only files
(map screenshots) are LOGGED and SKIPPED — never treated as data (no pixel OCR).

FIPS is preserved as a zero-padded string; 2-digit = state, 5-digit = county.
Values are kept numeric where possible; national percentiles are computed from
real values only. Every value row carries provenance (source_file, variable,
geo, year, unit, source_note). Raw files are not copied into the repo.

Run:  python scripts/ingest_market_intel_exports.py
      python scripts/ingest_market_intel_exports.py --folder /path/to/exports
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "data" / "market_intel"
_DEFAULT_FOLDER = os.path.expanduser("~/Desktop/I_Made_It")
_SOURCE = "SimplyAnalytics (licensed)"
_LICENSE = "LICENSED MARKET DATA DERIVED (SimplyAnalytics); internal use, with provenance."

# header keyword → (variable_id, display_name, category, unit)
_VAR_MAP = [
    (r"65 years and over|age.*65", ("age_65_plus_pct", "% Age 65 and over", "AGE", "pct")),
    (r"median household income", ("median_household_income", "Median Household Income", "INCOME", "usd")),
    (r"private health insurance|with private health", ("private_insurance_pct", "% Private Health Insurance", "INSURANCE", "pct")),
    (r"no health insurance", ("uninsured_pct", "% No Health Insurance", "INSURANCE", "pct")),
    (r"medicaid", ("medicaid_pct", "% Medicaid", "PAYER", "pct")),
]

_DILIGENCE_USE = {
    "age_65_plus_pct": "Senior demand density — higher = more Medicare-age demand.",
    "median_household_income": "Commercial attractiveness — higher = wealthier payer base.",
    "private_insurance_pct": "Payer mix — higher = more commercial reimbursement.",
    "uninsured_pct": "Reimbursement risk — higher = more bad-debt / charity exposure.",
    "medicaid_pct": "Payer mix — higher = more Medicaid reimbursement exposure.",
}


def _classify_var(header: str):
    h = header.lower()
    for pat, meta in _VAR_MAP:
        if re.search(pat, h):
            return meta
    # generic fallback: slugify the header
    slug = re.sub(r"[^a-z0-9]+", "_", h).strip("_")[:40] or "unknown_var"
    return (slug, header.split(",")[0].strip()[:60], "DEMAND_PROXY", "value")


def _year_from(header: str, default: str = "") -> str:
    m = re.search(r"\b(20\d{2})\b", header)
    return m.group(1) if m else default


def _norm_fips(v) -> str:
    s = re.sub(r"\D", "", str(v))
    if not s:
        return ""
    # state = 2 digits, county = 5 digits
    return s.zfill(2) if len(s) <= 2 else s.zfill(5)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=_DEFAULT_FOLDER)
    args = ap.parse_args(argv)
    _OUT.mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.folder, "*")))
    tabular = [f for f in files if f.lower().endswith((".xlsx", ".xls", ".csv"))]
    images = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]

    variables: dict[str, dict] = {}
    state_rows: list[dict] = []
    county_rows: list[dict] = []
    log: list[str] = []

    for path in tabular:
        fname = os.path.basename(path)
        try:
            if path.lower().endswith(".csv"):
                sheets = {"csv": pd.read_csv(path, dtype=str)}
            else:
                xl = pd.ExcelFile(path)
                sheets = {s: pd.read_excel(path, sheet_name=s, dtype=str)
                          for s in xl.sheet_names}
        except Exception as e:  # pragma: no cover
            log.append(f"SKIP {fname}: read error {e}")
            continue

        for sheet, df in sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            cols = {c.lower(): c for c in df.columns}
            fips_col = next((cols[c] for c in cols if c == "fips"), None)
            name_col = next((cols[c] for c in cols if c in ("name", "geography", "area")), None)
            if fips_col is None or name_col is None:
                log.append(f"SKIP {fname}/{sheet}: no Name+FIPS columns")
                continue
            value_cols = [c for c in df.columns if c not in (fips_col, name_col)]
            for vcol in value_cols:
                vid, disp, cat, unit = _classify_var(vcol)
                year = _year_from(vcol)
                variables[vid] = {
                    "variable_id": vid, "display_name": disp, "category": cat,
                    "unit": unit, "year": year, "source": _SOURCE,
                    "geography_level": "state",  # refined below if county rows seen
                    "description": vcol,
                    "diligence_use": _DILIGENCE_USE.get(vid, ""),
                    "caveat": "County values can mask submarket variation; verify source/year.",
                }
                sub = df[[name_col, fips_col, vcol]].copy()
                sub["fips"] = sub[fips_col].map(_norm_fips)
                sub["value"] = pd.to_numeric(sub[vcol], errors="coerce")
                for _, r in sub.iterrows():
                    fips = r["fips"]
                    if not fips or pd.isna(r["value"]):
                        continue
                    level = "state" if len(fips) <= 2 else "county"
                    rec = {
                        "variable_id": vid, "geo_level": level,
                        "geo_name": str(r[name_col]).strip(), "fips": fips,
                        "year": year, "value": float(r["value"]), "unit": unit,
                        "source_file": fname, "source_note": _LICENSE,
                    }
                    (state_rows if level == "state" else county_rows).append(rec)
            log.append(f"OK {fname}/{sheet}: {len(value_cols)} variable(s), {len(df)} rows")

    for f in images:
        log.append(f"IMAGE-ONLY (design ref, skipped): {os.path.basename(f)}")

    # National percentiles per variable+level (real values only).
    def _add_pct(rows: list[dict]) -> None:
        by_var: dict = {}
        for r in rows:
            by_var.setdefault(r["variable_id"], []).append(r)
        for vid, rs in by_var.items():
            s = pd.Series([r["value"] for r in rs])
            ranks = s.rank(pct=True) * 100
            for r, p in zip(rs, ranks):
                r["percentile_national"] = round(float(p), 1)

    _add_pct(state_rows)
    _add_pct(county_rows)
    if county_rows:
        for vid in {r["variable_id"] for r in county_rows}:
            variables[vid]["geography_level"] = "county"

    pd.DataFrame(list(variables.values())).to_csv(_OUT / "market_variables.csv", index=False)
    _write(_OUT / "market_values_state.csv", state_rows)
    _write(_OUT / "market_values_county.csv", county_rows)
    (_OUT / "ingest_log.txt").write_text("\n".join(log) + "\n")

    (_OUT / "market_intel_report.json").write_text(json.dumps({
        "variables": len(variables), "state_values": len(state_rows),
        "county_values": len(county_rows), "tabular_files": len(tabular),
        "image_files_skipped": len(images), "source": _SOURCE,
    }, indent=2))
    print("\n".join(log))
    print(f"Wrote {len(variables)} variables, {len(state_rows)} state + "
          f"{len(county_rows)} county values → {_OUT}")
    return 0


def _write(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    cols = ["variable_id", "geo_level", "geo_name", "fips", "state", "county",
            "year", "value", "unit", "percentile_national", "percentile_state",
            "source_file", "source_note"]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df[cols].to_csv(path, index=False)


if __name__ == "__main__":
    raise SystemExit(main())
