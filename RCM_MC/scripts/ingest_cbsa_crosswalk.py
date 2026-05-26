#!/usr/bin/env python3
"""Build-time ingest for the OMB CBSA <-> county delineation crosswalk.

Pulls the public U.S. Census Bureau delineation file (which encodes OMB's
July-2023 Core-Based Statistical Area definitions) — keyless, no API key, a
static published spreadsheet. We commit only a compact, PII-free crosswalk so
the CBSA demographics loader can map our in-repo county demographics up to
metro/micro areas at runtime with NO network call.

Writes ``rcm_mc/data/vendor/cbsa_crosswalk/cbsa_county_crosswalk.csv``:
  • county_fips (5-digit) · cbsa_code · cbsa_title · area_type (Metro/Micro)
    · central_outlying

Source: Census Bureau, Population Division, based on OMB Bulletin 23-01 (July
2023 delineations). Freely redistributable U.S. government work. Run manually
to refresh: ``python scripts/ingest_cbsa_crosswalk.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

VINTAGE = "2023"
URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    f"reference-files/{VINTAGE}/delineation-files/list1_{VINTAGE}.xlsx"
)
OUT_DIR = (Path(__file__).resolve().parents[1] / "rcm_mc" / "data"
           / "vendor" / "cbsa_crosswalk")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching OMB {VINTAGE} delineation: {URL}")
    # Shell out to curl (system trust store) — matches the other ingest scripts
    # and sidesteps urllib's missing-CA issue on some build hosts.
    res = subprocess.run(["curl", "-sS", "-L", "-m", "120", URL],
                         capture_output=True, check=True)

    # Row 0-1 are title rows; the real header is on row index 2.
    df = pd.read_excel(io.BytesIO(res.stdout), header=2, dtype=str)
    df = df.dropna(subset=["CBSA Code", "FIPS State Code", "FIPS County Code"])
    df = df[df["CBSA Code"].str.match(r"^\d{5}$", na=False)]

    out = pd.DataFrame({
        "county_fips": (df["FIPS State Code"].str.zfill(2)
                        + df["FIPS County Code"].str.zfill(3)),
        "cbsa_code": df["CBSA Code"].str.strip(),
        "cbsa_title": df["CBSA Title"].str.strip(),
        "area_type": df["Metropolitan/Micropolitan Statistical Area"]
            .str.replace(" Statistical Area", "", regex=False).str.strip(),
        "central_outlying": df["Central/Outlying County"].fillna("").str.strip(),
    }).drop_duplicates("county_fips").sort_values(["cbsa_code", "county_fips"])

    csv_path = OUT_DIR / "cbsa_county_crosswalk.csv"
    out.to_csv(csv_path, index=False)

    meta = {
        "vintage": VINTAGE,
        "source": "U.S. Census Bureau / OMB Bulletin 23-01 (July 2023 CBSA delineations)",
        "source_url": URL,
        "counties": int(out["county_fips"].nunique()),
        "cbsas": int(out["cbsa_code"].nunique()),
        "metros": int((out["area_type"] == "Metropolitan").sum()),
        "micros": int((out["area_type"] == "Micropolitan").sum()),
        "ingested_at": datetime.now(timezone.utc).date().isoformat(),
    }
    (OUT_DIR / "cbsa_crosswalk_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {len(out):,} county→CBSA rows "
          f"({meta['cbsas']} CBSAs) → {csv_path}")


if __name__ == "__main__":
    main()
