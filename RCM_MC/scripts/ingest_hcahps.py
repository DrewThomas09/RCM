#!/usr/bin/env python3
"""Build-time ingest for CMS HCAHPS patient-experience (state level).

Downloads the public CMS Care Compare "Patient survey (HCAHPS) - State"
dataset and writes a compact, PII-free committed aggregate under
``rcm_mc/data/vendor/hcahps/``:

  • ``hcahps_state.csv``    — one row per state, headline top-box measures
  • ``hcahps_summary.json`` — national (population-unweighted mean across
                              states) + extract metadata

HCAHPS is the official CMS patient-experience survey — already a
state-level top-box percentage, so no PII and no further aggregation
risk. Source: data.cms.gov/provider-data dataset 84jm-wiui.
Run manually to refresh: ``python scripts/ingest_hcahps.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

DATASET_ID = "84jm-wiui"  # Patient survey (HCAHPS) - State
URL = (f"https://data.cms.gov/provider-data/api/1/datastore/query/"
       f"{DATASET_ID}/0/download?format=csv")
OUT_DIR = Path(__file__).resolve().parents[1] / "rcm_mc" / "data" / "vendor" / "hcahps"

# headline top-box HCAHPS measures (measure_id -> human key)
MEASURES = {
    "H_HSP_RATING_9_10": "overall_rating_9_10",      # gave 9-10 overall
    "H_RECMND_DY": "would_definitely_recommend",
    "H_COMP_1_A_P": "nurse_comm_always",
    "H_COMP_2_A_P": "doctor_comm_always",
    "H_COMP_5_A_P": "staff_explained_meds_always",
    "H_COMP_6_Y_P": "given_discharge_info",
    "H_CLEAN_HSP_A_P": "room_always_clean",
    "H_QUIET_HSP_A_P": "always_quiet_night",
}


def _download() -> pd.DataFrame:
    print(f"downloading HCAHPS state ({DATASET_ID}) ...")
    res = subprocess.run(["curl", "-s", "-L", "-m", "180", URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), encoding="latin-1", low_memory=False)
    # CSV headers are spaced Title Case ("HCAHPS Answer Percent"); normalize
    # to snake_case so column lookups match the JSON-API field names.
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    print(f"  {len(df):,} rows, {len(df.columns)} cols")
    return df


def main() -> None:
    df = _download()
    mid_col = "hcahps_measure_id" if "hcahps_measure_id" in df.columns else "measure_id"
    pct_col = "hcahps_answer_percent" if "hcahps_answer_percent" in df.columns else "score"
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")

    sub = df[df[mid_col].isin(MEASURES)]
    # one row per state, headline measures as columns
    pivot = sub.pivot_table(index="state", columns=mid_col, values=pct_col,
                            aggfunc="first")
    pivot = pivot.rename(columns=MEASURES).reset_index()
    # keep only real US states/DC (drop territory/blank noise if any)
    pivot = pivot[pivot["state"].astype(str).str.len() == 2].sort_values("state")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["state"] + [v for v in MEASURES.values() if v in pivot.columns]
    pivot[cols].to_csv(OUT_DIR / "hcahps_state.csv", index=False)
    print(f"  wrote hcahps_state.csv ({len(pivot)} states)")

    national = {v: (round(float(pivot[v].mean()), 1) if v in pivot.columns else None)
                for v in MEASURES.values()}
    end_dates = df.get("end_date")
    summary = {
        "dataset_id": DATASET_ID,
        "source": "CMS Care Compare — Patient survey (HCAHPS), State",
        "extract_date": date.today().isoformat(),
        "survey_period_end": (str(end_dates.dropna().max())
                              if end_dates is not None and end_dates.notna().any() else ""),
        "states": int(len(pivot)),
        "national_mean_pct": national,
        "measures": {v: k for k, v in MEASURES.items()},
    }
    (OUT_DIR / "hcahps_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  wrote hcahps_summary.json (national: {national})")


if __name__ == "__main__":
    main()
