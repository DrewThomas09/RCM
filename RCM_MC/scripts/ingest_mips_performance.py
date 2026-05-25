#!/usr/bin/env python3
"""Snapshot CMS clinician MIPS performance → PII-free score distribution.

Source: CMS Provider Data Catalog — "PY 2023 Clinician Public Reporting:
Overall MIPS Performance" (``ec_score_file.csv``), public. BUILD-TIME: fetch the
full per-clinician file (~41 MB, ~1.1M rows with NPIs/names), drop ALL
identifying columns, and aggregate to a tiny score distribution. Runtime reads
only the committed aggregate (no live API, no PII). Missing scores stay out of
the sample (never counted as 0).

This is the physician-quality benchmark used by the physician/quality diligence
pages — the real published MIPS final-score distribution, far more relevant to
physician-services deals than the nursing-home Care Compare ratings.

Run: python scripts/ingest_mips_performance.py
"""
from __future__ import annotations
import io, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "mips"
_URL = ("https://data.cms.gov/provider-data/sites/default/files/resources/"
        "6b9e57db797c95853b034b329b1212b2_1763510763/ec_score_file.csv")

_BANDS = [(0, 20), (20, 40), (40, 60), (60, 75), (75, 100.0001)]


def _dist(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if not len(s):
        return {}
    return {
        "n": int(len(s)),
        "mean": round(float(s.mean()), 1),
        "median": round(float(s.median()), 1),
        "p10": round(float(s.quantile(0.10)), 1),
        "p25": round(float(s.quantile(0.25)), 1),
        "p75": round(float(s.quantile(0.75)), 1),
        "p90": round(float(s.quantile(0.90)), 1),
    }


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "180", _URL],
                         capture_output=True, text=True, check=True)
    df = pd.read_csv(io.StringIO(res.stdout), dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    score_col = "final_MIPS_score"
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")

    # Summary rows: overall + per reporting source (individual/group/...).
    summary_rows = []
    overall = _dist(df[score_col])
    if overall:
        summary_rows.append({"scope": "All clinicians", **overall})
    for src, g in df.groupby(df["source"].fillna("unknown")):
        d = _dist(g[score_col])
        if d:
            summary_rows.append({"scope": f"source: {src}", **d})
    summary = pd.DataFrame(summary_rows)
    summary["source_id"] = "cms_mips_py2023"
    summary.to_csv(_OUT / "mips_score_summary.csv", index=False)

    # Score-band histogram (overall).
    scores = pd.to_numeric(df[score_col], errors="coerce").dropna()
    n = len(scores)
    band_rows = []
    for lo, hi in _BANDS:
        cnt = int(((scores >= lo) & (scores < hi)).sum())
        band_rows.append({"band": f"{int(lo)}-{int(hi if hi <= 100 else 100)}",
                          "count": cnt, "pct": round(100 * cnt / n, 1) if n else 0.0})
    pd.DataFrame(band_rows).to_csv(_OUT / "mips_score_bands.csv", index=False)

    # Category sub-score means (quality / PI / IA / cost), where present.
    cat_rows = []
    for col, label in (("Quality_category_score", "Quality"),
                       ("PI_category_score", "Promoting Interoperability"),
                       ("IA_category_score", "Improvement Activities"),
                       ("Cost_category_score", "Cost")):
        if col in df.columns:
            d = _dist(df[col])
            if d:
                cat_rows.append({"category": label, **d})
    pd.DataFrame(cat_rows).to_csv(_OUT / "mips_category_scores.csv", index=False)

    (_OUT / "mips_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "performance_year": "2023",
        "raw_rows": int(len(df)),
        "scored_clinicians": int(n),
        "source": "CMS Provider Data Catalog — PY2023 Clinician Overall MIPS "
                  "Performance (public); PII dropped at ingest",
    }, indent=2))
    print(f"Wrote MIPS aggregates ({n:,} scored of {len(df):,} rows) → {_OUT}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
