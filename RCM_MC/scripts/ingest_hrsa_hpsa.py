#!/usr/bin/env python3
"""Snapshot HRSA Primary-Care HPSA → state-level shortage index (aggregated).

Source: HRSA Data Warehouse — Health Professional Shortage Areas (Primary Care),
public. BUILD-TIME: fetch the full detail file, keep DESIGNATED rows, aggregate
to state (it's 78k rows raw → ~60-row state index). Runtime reads the committed
aggregate only (no live API). Missing stays empty/NaN.

Run: python scripts/ingest_hrsa_hpsa.py
"""
from __future__ import annotations
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import io, pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "hrsa"
_URL = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "90", _URL],
                         capture_output=True, text=True, check=True)
    df = pd.read_csv(io.StringIO(res.stdout), dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df["HPSA Score"] = pd.to_numeric(df["HPSA Score"], errors="coerce")
    df["HPSA Designation Population"] = pd.to_numeric(
        df["HPSA Designation Population"], errors="coerce")
    act = df[df["HPSA Status"].astype(str).str.contains("Designated", case=False, na=False)]
    g = act.groupby("Primary State Abbreviation").agg(
        designated_pc_hpsas=("HPSA ID", "nunique"),
        median_hpsa_score=("HPSA Score", "median"),
        max_hpsa_score=("HPSA Score", "max"),
        population_in_shortage=("HPSA Designation Population", "sum"),
    ).reset_index().rename(columns={"Primary State Abbreviation": "state"})
    g = g[g["state"].astype(str).str.len() == 2].sort_values(
        "designated_pc_hpsas", ascending=False)
    g["discipline"] = "Primary Care"
    g["source_id"] = "hrsa_hpsa_pc"
    out = _OUT / "hrsa_hpsa_pc_by_state.csv"
    g.to_csv(out, index=False)
    (_OUT / "hrsa_hpsa_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "discipline": "Primary Care", "states": len(g),
        "raw_designated_rows": int(len(act)),
        "source": "HRSA Data Warehouse HPSA (Primary Care), public",
    }, indent=2))
    print(f"Wrote {len(g)} state rows → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
