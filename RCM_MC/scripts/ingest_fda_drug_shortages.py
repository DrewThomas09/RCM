#!/usr/bin/env python3
"""Snapshot the openFDA drug-shortage dataset into a normalized CSV.

Source: openFDA (FDA) drug-shortages endpoint — PUBLIC DOMAIN (CC0). This is a
BUILD-TIME snapshot: the script fetches the public dataset once and writes a
committed CSV (`rcm_mc/data/vendor/drug_data/fda_drug_shortages.csv`). PEdesk's
runtime reads the committed snapshot — it never calls the API live (consistent
with the no-runtime-network rule).

Honesty: missing fields stay empty (never invented); the snapshot date is
recorded; every row carries source_id. Re-run to refresh the snapshot.

Run (offline / build-time)::

    python scripts/ingest_fda_drug_shortages.py
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "drug_data"
_ENDPOINT = "https://api.fda.gov/drug/shortages.json"
_FIELDS = ["generic_name", "company_name", "therapeutic_category", "dosage_form",
           "status", "availability", "package_ndc", "initial_posting_date",
           "update_date", "update_type"]


def _get(url: str) -> Dict[str, Any]:
    """Build-time GET via curl (portable across SSL-store quirks; this is an
    offline ingest tool, not runtime)."""
    res = subprocess.run(["curl", "-sS", "-m", "30", url],
                         capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def _fetch_all(page: int = 1000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    skip = 0
    while True:
        data = _get(f"{_ENDPOINT}?limit={page}&skip={skip}")
        results = data.get("results", [])
        out.extend(results)
        total = data.get("meta", {}).get("results", {}).get("total", len(out))
        skip += page
        print(f"  fetched {len(out)}/{total}", file=sys.stderr)
        if skip >= total or not results:
            break
    return out


def _norm(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):          # therapeutic_category arrives as a list
        return "; ".join(str(x) for x in v)
    return str(v).strip()


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    recs = _fetch_all()
    rows = []
    for r in recs:
        row = {f: _norm(r.get(f)) for f in _FIELDS}
        row["source_id"] = "openfda_drug_shortages"
        rows.append(row)
    out = _OUT / "fda_drug_shortages.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_FIELDS + ["source_id"])
        w.writeheader()
        w.writerows(rows)
    report = {
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "rows": len(rows),
        "source": "openFDA drug/shortages (public domain / CC0)",
        "missingness_pct": {
            f: round(100 * sum(1 for r in rows if not r[f]) / len(rows), 1)
            for f in _FIELDS} if rows else {},
    }
    (_OUT / "fda_drug_shortages_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote {len(rows)} rows → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
