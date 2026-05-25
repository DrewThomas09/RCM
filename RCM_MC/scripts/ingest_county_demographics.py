#!/usr/bin/env python3
"""Build-time ingest for county demographics (market intelligence).

Pulls the healthcare-market-relevant demographic variables that the Census
ACS supplies, via the public **County Health Rankings & Roadmaps** analytic
file. CHR sources these demographics from the U.S. Census Bureau (ACS /
Population Estimates / SAHIE / SAIPE) and republishes them keyless in one
CSV — so we get the ACS-derived variables without a Census API key (the
direct ``api.census.gov`` ACS endpoint now requires an API key, which is a
secret we will not commit).

Writes PII-free committed aggregates under
``rcm_mc/data/vendor/county_demographics/``:

  • ``county_demographics.csv`` — one row per county (5-digit FIPS preserved)
  • ``demographics_state.csv``  — one row per state, population-weighted
  • ``demographics_summary.json`` — national + extract metadata

CHR data is freely redistributable with attribution (County Health Rankings
& Roadmaps, University of Wisconsin Population Health Institute). ACS-derived
values are SURVEY estimates. Run manually to refresh:
``python scripts/ingest_county_demographics.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

CHR_YEAR = "2024"
URL = (f"https://www.countyhealthrankings.org/sites/default/files/media/"
       f"document/analytic_data{CHR_YEAR}.csv")
OUT_DIR = (Path(__file__).resolve().parents[1] / "rcm_mc" / "data"
           / "vendor" / "county_demographics")

# CHR column header (stable string) -> human key. Values are fractions
# (0–1) for the percent measures and absolute for population/income.
COLS = {
    "Population raw value": "population",
    "% 65 and Older raw value": "pct_age_65_plus",
    "Median Household Income raw value": "median_household_income",
    "Children in Poverty raw value": "child_poverty_rate",
    "Uninsured raw value": "uninsured_rate",
    "% Non-Hispanic White raw value": "pct_white_nh",
    "% Non-Hispanic Black raw value": "pct_black_nh",
    "% Hispanic raw value": "pct_hispanic",
    "% Rural raw value": "pct_rural",
}
_PCT_KEYS = {"pct_age_65_plus", "child_poverty_rate", "uninsured_rate",
             "pct_white_nh", "pct_black_nh", "pct_hispanic", "pct_rural"}


def _download() -> pd.DataFrame:
    print(f"downloading County Health Rankings {CHR_YEAR} analytic data ...")
    res = subprocess.run(["curl", "-s", "-L", "-m", "180", URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), encoding="latin-1",
                     dtype=str, low_memory=False)
    # CHR ships a second header row of long descriptions; drop any row whose
    # FIPS isn't a real 5-digit code (also drops state/national summary rows).
    fips_col = "5-digit FIPS Code"
    df = df[df[fips_col].astype(str).str.fullmatch(r"\d{5}")]
    # county FIPS end in nonzero county part; state rows are NN000.
    df = df[~df[fips_col].astype(str).str.endswith("000")]
    print(f"  {len(df):,} counties")
    return df


def _wmean(values: pd.Series, weights: pd.Series) -> float | None:
    m = values.notna() & weights.notna()
    if not m.any():
        return None
    v, w = values[m], weights[m]
    return round(float((v * w).sum() / w.sum()), 4) if w.sum() else None


def main() -> None:
    df = _download()
    out = pd.DataFrame({
        "county_fips": df["5-digit FIPS Code"].astype(str),
        "state": df["State Abbreviation"].astype(str),
        "county_name": df["Name"].astype(str),
    })
    for src, key in COLS.items():
        out[key] = pd.to_numeric(df[src], errors="coerce")  # NaN preserves missingness
    out = out[out["state"].str.fullmatch(r"[A-Z]{2}")].sort_values("county_fips")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_DIR / "county_demographics.csv", index=False)
    print(f"  wrote county_demographics.csv ({len(out)} counties)")

    # ── state aggregate (population-weighted for rates; pop summed) ──
    keys = list(COLS.values())
    rows = []
    for st, g in out.groupby("state"):
        row = {"state": st, "counties": int(len(g)),
               "population": int(g["population"].fillna(0).sum())}
        for k in keys:
            if k == "population":
                continue
            row[k] = _wmean(g[k], g["population"])
        rows.append(row)
    state_df = pd.DataFrame(rows).sort_values("state").reset_index(drop=True)
    state_df.to_csv(OUT_DIR / "demographics_state.csv", index=False)
    print(f"  wrote demographics_state.csv ({len(state_df)} states)")

    national = {"population": int(out["population"].fillna(0).sum())}
    for k in keys:
        if k == "population":
            continue
        national[k] = _wmean(out[k], out["population"])
    summary = {
        "chr_year": CHR_YEAR,
        "source": "County Health Rankings & Roadmaps (UW Population Health Institute)",
        "underlying_sources": "U.S. Census Bureau — ACS / Population Estimates / SAHIE / SAIPE",
        "note": ("Census ACS demographics delivered via the keyless CHR analytic "
                 "file; direct api.census.gov ACS now requires an API key."),
        "extract_date": date.today().isoformat(),
        "counties": int(len(out)),
        "states": int(state_df["state"].nunique()),
        "national": national,
        "columns": COLS,
        "pct_keys_are_fractions": sorted(_PCT_KEYS),
    }
    (OUT_DIR / "demographics_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  wrote demographics_summary.json (pop {national['population']:,}, "
          f"65+ {national['pct_age_65_plus']}, uninsured {national['uninsured_rate']})")


if __name__ == "__main__":
    main()
