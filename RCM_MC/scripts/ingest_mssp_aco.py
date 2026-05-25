#!/usr/bin/env python3
"""Snapshot the CMS Medicare Shared Savings Program (MSSP) ACO Participants file.

Source: data.cms.gov — "Accountable Care Organization Participants" public-use
file (PY2026). Public data. BUILD-TIME snapshot → committed CSV; runtime reads
the snapshot only (no live API call).

Privacy: the source includes ACO executive/contact PII (names, emails, phones).
This ingest DROPS those columns and keeps only analytic fields (ACO, participant
org, service area, track, risk, dates, public website). Missing stays empty.

Run (offline / build-time)::

    python scripts/ingest_mssp_aco.py
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "cms_aco"
_URL = ("https://data.cms.gov/sites/default/files/2026-01/"
        "453bc69c-61a4-4030-8d03-e33895fd1cfd/"
        "PY2026_Medicare_Shared_Savings_Program_Participants.csv")

# source header -> canonical (analytic columns only; PII intentionally excluded)
_KEEP = {
    "ACO_ID": "aco_id", "ACO_Name": "aco_name", "Par_LBN": "participant_org",
    "ACO_Service_Area": "service_area", "Agreement_Period_Num": "agreement_period",
    "Initial_Start_Date": "initial_start_date", "Current_Start_Date": "current_start_date",
    "BASIC_Track": "basic_track", "BASIC_Track_Level": "basic_track_level",
    "ENHANCED_Track": "enhanced_track", "High_Revenue_ACO": "high_revenue_aco",
    "Low_Revenue_ACO": "low_revenue_aco",
    "ACO_Public_Reporting_Website": "public_website",
}


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "90", _URL],
                         capture_output=True, text=True, check=True)
    import io
    reader = csv.DictReader(io.StringIO(res.stdout))
    # normalize header whitespace/BOM
    fieldmap = {}
    for h in (reader.fieldnames or []):
        fieldmap[h] = _KEEP.get(h.strip().lstrip("﻿"))
    out_cols = list(_KEEP.values()) + ["source_id"]
    rows = []
    for r in reader:
        row = {}
        for h, canon in fieldmap.items():
            if canon:
                v = (r.get(h) or "").strip()
                row[canon] = v
        if not row.get("aco_id"):
            continue
        row["source_id"] = "cms_mssp_aco_py2026"
        rows.append(row)
    out = _OUT / "mssp_aco_participants.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols)
        w.writeheader()
        w.writerows(rows)
    n_aco = len({r["aco_id"] for r in rows})
    report = {
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "rows": len(rows), "distinct_acos": n_aco,
        "source": "CMS data.cms.gov MSSP ACO Participants (public)",
        "pii_dropped": ["exec/contact names, emails, phones"],
        "missingness_pct": {
            c: round(100 * sum(1 for r in rows if not r.get(c)) / len(rows), 1)
            for c in _KEEP.values()} if rows else {},
    }
    (_OUT / "mssp_aco_report.json").write_text(json.dumps(report, indent=2))
    print(f"Wrote {len(rows)} participant rows ({n_aco} ACOs) → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
