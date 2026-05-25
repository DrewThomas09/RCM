#!/usr/bin/env python3
"""Build-time ingest for CDC PLACES county SDOH/health-equity measures.

Downloads the public CDC PLACES "County Data (GIS Friendly Format)"
release, then writes two compact, PII-free committed aggregates under
``rcm_mc/data/vendor/cdc_places/``:

  • ``places_equity_state.csv``   — one row per state, population-weighted
                                     crude prevalence for the equity measures
  • ``places_equity_summary.json``— national population-weighted prevalence
                                     + extract metadata

PLACES is model-based county estimates (BRFSS + ACS), full-population.
No PII — these are already population-level prevalence rates. Only the
small normalized aggregate is committed; the raw 3,143-row file is not.

Source: chronicdata.cdc.gov / data.cdc.gov dataset i46a-9kgh (2025 release).
Run manually when refreshing: ``python scripts/ingest_cdc_places.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

DATASET_ID = "i46a-9kgh"  # PLACES: County Data (GIS Friendly Format), 2025 release
RELEASE = "2025"
URL = f"https://data.cdc.gov/api/views/{DATASET_ID}/rows.csv?accessType=DOWNLOAD"
OUT_DIR = Path(__file__).resolve().parents[1] / "rcm_mc" / "data" / "vendor" / "cdc_places"

# Equity / SDOH measures (crude prevalence column -> human label).
MEASURES = {
    "access2_crudeprev": "uninsured_18_64",       # no health insurance, 18-64
    "ghlth_crudeprev": "fair_poor_health",        # fair/poor general health
    "mhlth_crudeprev": "poor_mental_health",      # frequent mental distress
    "phlth_crudeprev": "poor_physical_health",
    "checkup_crudeprev": "routine_checkup",       # had a checkup (access proxy)
    "foodinsecu_crudeprev": "food_insecurity",
    "foodstamp_crudeprev": "snap_participation",
    "shututility_crudeprev": "utility_shutoff_threat",
    "lacktrpt_crudeprev": "lack_transportation",
    "emotionspt_crudeprev": "lack_emotional_support",
    "depression_crudeprev": "depression",
    "diabetes_crudeprev": "diabetes",
    "obesity_crudeprev": "obesity",
}


def _download() -> pd.DataFrame:
    print(f"downloading PLACES {RELEASE} ({DATASET_ID}) ...")
    # capture bytes (some CDC exports are not clean UTF-8) then decode latin-1.
    res = subprocess.run(["curl", "-s", "-L", "-m", "240", URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), encoding="latin-1", low_memory=False)
    print(f"  {len(df):,} county rows, {len(df.columns)} cols")
    return df


def _wmean(values: pd.Series, weights: pd.Series) -> float | None:
    m = values.notna() & weights.notna()
    if not m.any():
        return None
    v, w = values[m], weights[m]
    if w.sum() == 0:
        return None
    return round(float((v * w).sum() / w.sum()), 2)


def main() -> None:
    df = _download()
    df.columns = [c.lower() for c in df.columns]
    pop = pd.to_numeric(df["totalpopulation"], errors="coerce")
    cols_present = [c for c in MEASURES if c in df.columns]
    for c in cols_present:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # ── state-level population-weighted prevalence ──
    rows = []
    for st, g in df.groupby("stateabbr"):
        gpop = pd.to_numeric(g["totalpopulation"], errors="coerce")
        row = {"state": st, "counties": int(len(g)),
               "population": int(gpop.fillna(0).sum())}
        for c in cols_present:
            row[MEASURES[c]] = _wmean(g[c], gpop)
        rows.append(row)
    state_df = pd.DataFrame(rows).sort_values("state").reset_index(drop=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state_df.to_csv(OUT_DIR / "places_equity_state.csv", index=False)
    print(f"  wrote places_equity_state.csv ({len(state_df)} states)")

    # ── national population-weighted prevalence ──
    national = {MEASURES[c]: _wmean(df[c], pop) for c in cols_present}
    summary = {
        "release": RELEASE,
        "dataset_id": DATASET_ID,
        "source": "CDC PLACES: County Data (GIS Friendly Format)",
        "extract_date": date.today().isoformat(),
        "counties": int(len(df)),
        "states": int(df["stateabbr"].nunique()),
        "total_population": int(pop.fillna(0).sum()),
        "national_prevalence_pct": national,
        "measures": {MEASURES[c]: c for c in cols_present},
    }
    (OUT_DIR / "places_equity_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  wrote places_equity_summary.json (national: {national})")


if __name__ == "__main__":
    main()
