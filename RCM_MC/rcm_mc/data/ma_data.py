"""CMS Medicare Advantage Geographic Variation — state MA profile (loader).

Reads the committed state-level snapshot under ``rcm_mc/data/vendor/ma_geo/``
(from ``scripts/ingest_ma_geo_variation.py``). Public CMS data; no runtime
network. CMS-suppressed small cells were dropped to NaN at ingest (never 0).

Honesty: this is MA market/population context by state — MA enrollment plus the
demographic drivers of risk adjustment (dual-eligible %, age) and headline
utilization. It is NOT a plan-level Star Rating, NOT a risk SCORE, and NOT
provider-specific. Use it to frame MA exposure and risk-adjustment population
mix, not to assert a target's coding intensity.
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "ma_geo"


@functools.lru_cache(maxsize=None)
def load_ma_geo_state() -> pd.DataFrame:
    p = _DIR / "ma_geo_state.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def ma_snapshot() -> Dict[str, Any]:
    rp = _DIR / "ma_geo_report.json"
    return json.loads(rp.read_text()) if rp.exists() else {}


def ma_summary() -> Dict[str, Any]:
    df = load_ma_geo_state()
    if not len(df):
        return {"states": 0, "total_ma_enrollment": 0, "data_year": ""}
    snap = ma_snapshot()
    return {
        "states": int(df["state"].nunique()),
        "total_ma_enrollment": int(df["ma_enrollment"].dropna().sum()),
        "data_year": snap.get("data_year", ""),
        "median_dual_pct": round(float(df["dual_eligible_pct"].median()), 4),
        "median_avg_age": round(float(df["avg_age"].median()), 1),
    }


def ma_state(state: str) -> Dict[str, Any]:
    df = load_ma_geo_state()
    if not len(df) or not state:
        return {}
    m = df[df["state"].astype(str).str.upper() == str(state).upper()]
    return m.iloc[0].to_dict() if len(m) else {}


def top_ma_states(limit: int = 10) -> List[Dict[str, Any]]:
    df = load_ma_geo_state()
    if not len(df):
        return []
    return df.head(limit).to_dict("records")


def top_dual_states(limit: int = 10) -> List[Dict[str, Any]]:
    """States with the highest dual-eligible share — the population mix that
    drives MA risk-adjustment. Requires a non-null dual % (suppressed dropped)."""
    df = load_ma_geo_state()
    if not len(df):
        return []
    d = df.dropna(subset=["dual_eligible_pct"]).sort_values(
        "dual_eligible_pct", ascending=False)
    return d.head(limit)[["state", "dual_eligible_pct", "ma_enrollment",
                          "avg_age"]].to_dict("records")


def ma_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_ma_geo_ry2025"].to_dict("records")
