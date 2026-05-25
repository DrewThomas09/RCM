#!/usr/bin/env python3
"""Snapshot CMS Medicare Advantage Geographic Variation PUF → state MA profile.

Source: CMS "Medicare Advantage Geographic Variation - National & State" public
use file (RY2025, data years 2016-2022). BUILD-TIME: fetch the full PUF, keep
the latest data year, and aggregate to a small state-level snapshot of MA
enrollment + the demographic/utilization drivers that matter for risk
adjustment and MA market structure. Runtime reads the committed snapshot only
(no live API). CMS suppression marker ``*`` is treated as MISSING (never 0).

Run: python scripts/ingest_ma_geo_variation.py
"""
from __future__ import annotations
import io, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "ma_geo"
_URL = ("https://data.cms.gov/sites/default/files/2025-06/"
        "a0f6cfe0-b67c-44ef-807d-a901921ed1ee/MA%20GV%20PUF%202016-2022_RY_2025.csv")

# columns we keep (MA enrollment + risk-adjustment demographic drivers +
# headline utilization rates), renamed to friendly snake_case.
_KEEP = {
    "YEAR": "year", "STATE": "state", "BENES_MA_CNT": "ma_enrollment",
    "BENE_AVG_AGE": "avg_age", "BENE_FEML_PCT": "female_pct",
    "BENE_DUAL_PCT": "dual_eligible_pct", "BENE_RACE_WHT_PCT": "race_white_pct",
    "BENE_RACE_BLACK_PCT": "race_black_pct", "BENE_RACE_HSPNC_PCT": "race_hispanic_pct",
    "IP_STAYS_PER_1000_BENES": "ip_stays_per_1000",
    "SNF_DAYS_PER_1000_BENES": "snf_days_per_1000",
    "ER_VISITS_PER_1000_BENES": "er_visits_per_1000",
}


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "120", _URL],
                         capture_output=True, text=True, check=True)
    # CMS uses '*' for suppressed small cells → treat as NaN (never 0).
    df = pd.read_csv(io.StringIO(res.stdout), dtype=str, na_values=["*", ""],
                     low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df = df[[c for c in _KEEP if c in df.columns]].rename(columns=_KEEP)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    latest = int(df["year"].max())
    df = df[df["year"] == latest]
    # state rows only (drop national/blank aggregates); state is 2-letter
    df = df[df["state"].astype(str).str.len() == 2]
    for c in df.columns:
        if c != "state":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("ma_enrollment", ascending=False)
    out = _OUT / "ma_geo_state.csv"
    df.to_csv(out, index=False)

    nat = {
        "data_year": latest,
        "states": int(df["state"].nunique()),
        "total_ma_enrollment": int(df["ma_enrollment"].dropna().sum()),
        "median_dual_pct": round(float(df["dual_eligible_pct"].median()), 4),
        "median_avg_age": round(float(df["avg_age"].median()), 1),
    }
    (_OUT / "ma_geo_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "registry_year": "RY2025", **nat,
        "source": "CMS Medicare Advantage Geographic Variation PUF (public)",
    }, indent=2))
    print(f"Wrote {len(df)} state rows (data year {latest}, "
          f"{nat['total_ma_enrollment']:,} MA enrollees) → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
