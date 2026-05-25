#!/usr/bin/env python3
"""Build-time ingest for the ClinicalTrials.gov trial landscape.

Queries the public, keyless ClinicalTrials.gov v2 API for headline counts
(total / recruiting / interventional / by phase) and writes a compact
committed aggregate under ``rcm_mc/data/vendor/clinical_trials/``:

  • ``clinical_trials_summary.json`` — landscape counts + extract metadata

Aggregate counts only (no PII, no per-study rows committed). Build-time
queries only; production reads the committed JSON (no runtime network).
Public domain (U.S. NLM / ClinicalTrials.gov).

Run manually to refresh: ``python scripts/ingest_clinical_trials.py``.
"""
from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

API = "https://clinicaltrials.gov/api/v2"
OUT_DIR = (Path(__file__).resolve().parents[1] / "rcm_mc" / "data"
           / "vendor" / "clinical_trials")


def _count(query: str) -> int:
    url = f"{API}/studies?{query}&countTotal=true&pageSize=0"
    res = subprocess.run(["curl", "-s", "-L", "-m", "60", url],
                         capture_output=True, check=True)
    return int(json.loads(res.stdout.decode("utf-8")).get("totalCount", 0))


def _total() -> int:
    res = subprocess.run(["curl", "-s", "-L", "-m", "60", f"{API}/stats/size"],
                         capture_output=True, check=True)
    return int(json.loads(res.stdout.decode("utf-8")).get("totalStudies", 0))


def main() -> None:
    print("querying ClinicalTrials.gov v2 ...")
    total = _total()
    recruiting = _count("filter.overallStatus=RECRUITING")
    interventional = _count("aggFilters=studyType:int")
    phases = {f"phase_{p}": _count(f"aggFilters=phase:{p}") for p in (1, 2, 3, 4)}

    summary = {
        "source": "ClinicalTrials.gov (U.S. NLM)",
        "api": "clinicaltrials.gov/api/v2",
        "extract_date": date.today().isoformat(),
        "total_studies": total,
        "recruiting": recruiting,
        "interventional": interventional,
        "phases": phases,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "clinical_trials_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  total {total:,} | recruiting {recruiting:,} | "
          f"interventional {interventional:,} | phases {phases}")
    print("  wrote clinical_trials_summary.json")


if __name__ == "__main__":
    main()
