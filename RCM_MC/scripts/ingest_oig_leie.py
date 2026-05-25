#!/usr/bin/env python3
"""Build-time ingest for the OIG LEIE (List of Excluded Individuals/Entities).

Downloads the public OIG exclusions file and writes a compact, **PII-free**
committed aggregate under ``rcm_mc/data/vendor/oig_leie/``:

  • ``oig_leie_summary.json`` — total + by-state + by-exclusion-type +
                                by-year + top-specialty counts

CRITICAL: the raw LEIE file contains PII (names, NPI, DOB, address). Those
columns are DROPPED at ingest — only aggregate counts are committed. The
excluded-provider population is a real Medicare/Medicaid fraud-&-abuse signal.
Build-time download only; production reads the committed JSON (no runtime net).

Run manually to refresh: ``python scripts/ingest_oig_leie.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"
OUT_DIR = Path(__file__).resolve().parents[1] / "rcm_mc" / "data" / "vendor" / "oig_leie"

# OIG exclusion authority code → readable reason (common codes).
EXCL_LABELS = {
    "1128a1": "Program-related crime conviction",
    "1128a2": "Patient abuse/neglect conviction",
    "1128a3": "Health-care fraud felony",
    "1128a4": "Felony controlled-substance conviction",
    "1128b1": "Misdemeanor health-care fraud",
    "1128b4": "License revocation/suspension",
    "1128b5": "Federal/state program exclusion",
    "1128b6": "Excessive claims / poor-quality care",
    "1128b7": "Fraud, kickbacks, prohibited activities",
    "1128b8": "Entity controlled by a sanctioned party",
}


def _download() -> pd.DataFrame:
    print("downloading OIG LEIE exclusions ...")
    res = subprocess.run(["curl", "-s", "-L", "-m", "180", URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), encoding="latin-1", dtype=str, low_memory=False)
    print(f"  {len(df):,} exclusion rows, {len(df.columns)} cols")
    # PII columns dropped immediately — never aggregated, never committed.
    return df


def _topn(counter: Counter, n: int) -> list:
    return [{"key": k, "count": int(v)} for k, v in counter.most_common(n)]


def main() -> None:
    df = _download()
    state = df.get("STATE", pd.Series(dtype=str)).fillna("").str.strip().str.upper()
    excltype = df.get("EXCLTYPE", pd.Series(dtype=str)).fillna("").str.strip().str.lower()
    spec = df.get("SPECIALTY", pd.Series(dtype=str)).fillna("").str.strip()
    excldate = df.get("EXCLDATE", pd.Series(dtype=str)).fillna("").str.strip()

    years = excldate.str[:4]
    year_counts = Counter(y for y in years if y.isdigit() and "1980" <= y <= "2030")
    by_year = [{"year": int(y), "count": int(c)}
               for y, c in sorted(year_counts.items()) if int(y) >= date.today().year - 9]

    by_state = [{"state": s, "count": int(c)}
                for s, c in Counter(s for s in state if len(s) == 2).most_common()]
    by_type = []
    for code, c in Counter(t for t in excltype if t).most_common(10):
        by_type.append({"code": code, "label": EXCL_LABELS.get(code, code.upper()),
                        "count": int(c)})
    top_spec = _topn(Counter(s for s in spec if s and s.upper() != "UNKNOWN"), 10)

    summary = {
        "source": "HHS OIG — List of Excluded Individuals/Entities (LEIE)",
        "url": URL,
        "extract_date": date.today().isoformat(),
        "total_exclusions": int(len(df)),
        "states": int(sum(1 for s in set(state) if len(s) == 2)),
        "by_state": by_state,
        "by_exclusion_type": by_type,
        "by_year_recent": by_year,
        "top_specialties": top_spec,
        "pii_note": "Names, NPI, DOB, address DROPPED at ingest — counts only.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "oig_leie_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  total {summary['total_exclusions']:,} across {summary['states']} states; "
          f"top type {by_type[0]['label'] if by_type else '—'}")
    print("  wrote oig_leie_summary.json (PII-free)")


if __name__ == "__main__":
    main()
