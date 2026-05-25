"""Snapshot CMS Hospital Change of Ownership → consolidation/transaction signal.

Source: CMS "Skilled Nursing Facility Change of Ownership" (data.cms.gov,
public). BUILD-TIME: fetch the CHOW file and aggregate to hospital
ownership-change counts by state x year (a real M&A/consolidation velocity
signal) + a national-by-year series. Drops the enrollment/NPI identifiers —
keeps only state + effective year for the committed aggregate. Runtime reads
the committed aggregate only.

Honesty: CHOW counts are Medicare-enrolled hospital ownership CHANGES — a
consolidation/transaction-activity signal by geography. NOT a PE-specific flag
(buyer type not classified here), NOT every transaction, NOT provider-specific
performance.

Run: python scripts/ingest_snf_chow.py
"""
from __future__ import annotations
import io, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "hospital_chow"
_URL = ("https://data.cms.gov/sites/default/files/2026-04/"
        "0129df0f-ceda-4b7d-b91a-cc1992e48834/Hospital_CHOW_2026.04.01.csv")


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "120", _URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), dtype=str, encoding="latin-1")
    df.columns = [c.strip().strip('"') for c in df.columns]
    state_col = "ENROLLMENT STATE - BUYER"
    date_col = "EFFECTIVE DATE"
    df["year"] = pd.to_datetime(df[date_col], errors="coerce").dt.year
    df["state"] = df[state_col].astype(str).str.strip().str.upper()
    df = df[(df["state"].str.len() == 2) & df["year"].notna()]
    df["year"] = df["year"].astype(int)

    by_state_year = (df.groupby(["state", "year"]).size()
                     .reset_index(name="chow_count")
                     .sort_values(["state", "year"]))
    by_state_year.to_csv(_OUT / "hospital_chow_state_year.csv", index=False)

    by_year = (df.groupby("year").size().reset_index(name="chow_count")
               .sort_values("year"))
    by_year.to_csv(_OUT / "hospital_chow_national_year.csv", index=False)

    yrs = sorted(df["year"].unique())
    (_OUT / "hospital_chow_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "extract": "Hospital_CHOW_2026.04.01",
        "total_chows": int(len(df)),
        "states": int(df["state"].nunique()),
        "year_min": int(yrs[0]) if yrs else None,
        "year_max": int(yrs[-1]) if yrs else None,
        "source": "CMS Hospital Change of Ownership (public); identifiers dropped",
    }, indent=2))
    print(f"Wrote {len(by_state_year)} state-year rows ({len(df):,} CHOWs, "
          f"{yrs[0]}-{yrs[-1]}) → {_OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
