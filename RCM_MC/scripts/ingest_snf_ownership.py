"""Snapshot CMS SNF All Owners → nursing-home ownership-complexity aggregate.

Source: CMS "Skilled Nursing Facility All Owners" (data.cms.gov, public).
BUILD-TIME: fetch the owner-level file (~280k rows, owner PII), aggregate per
facility (by ENROLLMENT ID) to ownership-STRUCTURE metrics, and commit only the
national PII-free aggregate. ALL owner names/identifiers are dropped — only
per-facility counts/flags are kept, then summarized nationally.

This is a real corporate-complexity / chain-ownership signal for nursing-home
diligence (owners per facility, organizational vs individual ownership, presence
of indirect ownership). NOT a private-equity flag (CMS does not label PE here),
NOT provider-specific performance.

Run: python scripts/ingest_snf_ownership.py
"""
from __future__ import annotations
import collections, csv, io, json, statistics, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "snf_ownership"
_URL = ("https://data.cms.gov/sites/default/files/2026-05/"
        "ca006ea2-e1e9-4953-ae37-215611aa96b6/SNF_All_Owners_2026.05.01.csv")


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "150", _URL],
                         capture_output=True, check=True)
    rows = list(csv.DictReader(io.StringIO(res.stdout.decode("latin-1"))))
    fac = collections.defaultdict(lambda: {"owners": 0, "org": 0, "indirect": 0})
    for r in rows:
        eid = r.get("ENROLLMENT ID", "")
        if not eid:
            continue
        f = fac[eid]
        f["owners"] += 1
        if r.get("TYPE - OWNER", "") == "O":
            f["org"] += 1
        if "INDIRECT" in (r.get("ROLE TEXT - OWNER", "") or ""):
            f["indirect"] += 1
    n = len(fac)
    if not n:
        print("no facilities parsed", file=sys.stderr)
        return 1
    owner_counts = [f["owners"] for f in fac.values()]
    agg = {
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "extract": "SNF_All_Owners_2026.05.01",
        "facilities": n,
        "owner_rows": len(rows),
        "avg_owners_per_facility": round(sum(owner_counts) / n, 1),
        "median_owners_per_facility": int(statistics.median(owner_counts)),
        "pct_with_organizational_owner": round(100 * sum(1 for f in fac.values() if f["org"]) / n, 1),
        "pct_with_indirect_ownership": round(100 * sum(1 for f in fac.values() if f["indirect"]) / n, 1),
        "source": "CMS SNF All Owners (public); owner names/identifiers dropped at ingest",
    }
    (_OUT / "snf_ownership_summary.json").write_text(json.dumps(agg, indent=2))
    print(f"Wrote ownership aggregate: {n} facilities, median {agg['median_owners_per_facility']} "
          f"owners, {agg['pct_with_indirect_ownership']}% indirect → {_OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
