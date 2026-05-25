"""CMS SNF Change-of-Ownership — consolidation/transaction signal (loader).

Reads the committed aggregate under ``rcm_mc/data/vendor/snf_chow/`` (from
``scripts/ingest_snf_chow.py``). Public CMS data; no runtime network.

Honesty: these are Medicare-enrolled SNF ownership CHANGES by state x year — a
real M&A / consolidation-velocity signal. NOT a PE-specific flag (buyer type
not classified), NOT every healthcare transaction, NOT provider-specific
performance.
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "snf_chow"


@functools.lru_cache(maxsize=None)
def _state_year() -> pd.DataFrame:
    p = _DIR / "snf_chow_state_year.csv"
    return pd.read_csv(p, dtype={"state": str}) if p.exists() else pd.DataFrame()


@functools.lru_cache(maxsize=None)
def _national_year() -> pd.DataFrame:
    p = _DIR / "snf_chow_national_year.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def snapshot() -> Dict[str, Any]:
    rp = _DIR / "snf_chow_report.json"
    return json.loads(rp.read_text()) if rp.exists() else {}


def chow_summary() -> Dict[str, Any]:
    snap = snapshot()
    return {"total_chows": snap.get("total_chows", 0),
            "states": snap.get("states", 0),
            "year_min": snap.get("year_min"), "year_max": snap.get("year_max")}


def chow_by_year() -> List[Dict[str, Any]]:
    df = _national_year()
    return df.to_dict("records") if len(df) else []


def chow_for_state(state: str) -> List[Dict[str, Any]]:
    df = _state_year()
    if not len(df) or not state:
        return []
    st = str(state).strip().upper()
    return df[df["state"] == st].sort_values("year").to_dict("records")


def total_chows_for_state(state: str) -> int:
    return int(sum(r["chow_count"] for r in chow_for_state(state)))


def top_chow_states(limit: int = 10) -> List[Dict[str, Any]]:
    df = _state_year()
    if not len(df):
        return []
    agg = (df.groupby("state")["chow_count"].sum()
           .sort_values(ascending=False).reset_index())
    return agg.head(limit).to_dict("records")


def chow_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_snf_chow"].to_dict("records")
