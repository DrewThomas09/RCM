#!/usr/bin/env python3
"""Snapshot CMS FFS Public Provider Enrollment → provider-supply counts.

Source: CMS "Medicare Fee-For-Service Public Provider Enrollment" extract
(data.cms.gov, public). BUILD-TIME: stream the national per-enrollment file
reading ONLY the non-PII columns (provider type + state), and aggregate to
provider-supply counts by state x provider_type and a national-by-type total.
ALL PII (NPI, names, IDs) is dropped at ingest — never read into memory beyond
the two needed columns. Runtime reads the committed aggregate only.

This is Medicare-enrolled provider SUPPLY by geography — a real density signal
for market/diligence context. Not a quality measure; not every provider (FFS
Medicare-enrolled only).

Run: python scripts/ingest_provider_supply.py
"""
from __future__ import annotations
import io, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "provider_supply"
_URL = ("https://data.cms.gov/sites/default/files/2026-05/"
        "9b0dd033-8c63-4e52-b9b0-0cabdb5db198/PPEF_Enrollment_Extract_2026.04.01.csv")


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    # Stream via curl to a pipe; read only the two non-PII columns in chunks.
    res = subprocess.run(["curl", "-sS", "-m", "240", _URL],
                         capture_output=True, check=True)  # bytes (file isn't UTF-8)
    buf = io.BytesIO(res.stdout)
    counts = {}  # (state, ptype) -> count
    reader = pd.read_csv(buf, usecols=["PROVIDER_TYPE_DESC", "STATE_CD"],
                         dtype=str, chunksize=100_000, encoding="latin-1")
    rows = 0
    for chunk in reader:
        rows += len(chunk)
        chunk = chunk.dropna(subset=["PROVIDER_TYPE_DESC", "STATE_CD"])
        for (st, pt), n in chunk.groupby(["STATE_CD", "PROVIDER_TYPE_DESC"]).size().items():
            counts[(str(st).strip(), str(pt).strip())] = counts.get((str(st).strip(), str(pt).strip()), 0) + int(n)

    recs = [{"state": st, "provider_type": pt, "enrolled_count": c}
            for (st, pt), c in counts.items() if len(st) == 2]
    df = pd.DataFrame(recs).sort_values(["state", "enrolled_count"],
                                        ascending=[True, False])
    df.to_csv(_OUT / "provider_supply_state_type.csv", index=False)

    # National by provider type
    nat = (df.groupby("provider_type")["enrolled_count"].sum()
           .sort_values(ascending=False).reset_index())
    nat.to_csv(_OUT / "provider_supply_national_type.csv", index=False)

    (_OUT / "provider_supply_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "extract": "PPEF_Enrollment_Extract_2026.04.01",
        "raw_rows": rows, "states": int(df["state"].nunique()),
        "provider_types": int(df["provider_type"].nunique()),
        "total_enrollments": int(df["enrolled_count"].sum()),
        "source": "CMS FFS Public Provider Enrollment (public); PII dropped at ingest",
    }, indent=2))
    print(f"Wrote {len(df)} state x type rows ({rows:,} raw enrollments, "
          f"PII dropped) → {_OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
