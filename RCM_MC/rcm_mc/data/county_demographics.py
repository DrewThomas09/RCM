"""County demographics (market-intel) aggregate — loader.

Reads the committed aggregate under ``rcm_mc/data/vendor/county_demographics/``
(built by ``scripts/ingest_county_demographics.py``). Source: County Health
Rankings & Roadmaps analytic file, which republishes U.S. Census Bureau
demographics (ACS / Population Estimates / SAHIE / SAIPE) keyless. No runtime
network.

Honesty: these are area-level SURVEY/estimate values (ACS-derived) for the
general population — market context, NOT this deal's patients and NOT a
provider-specific figure. Percent measures are stored as fractions (0–1).
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "county_demographics"


@functools.lru_cache(maxsize=None)
def _state() -> pd.DataFrame:
    p = _DIR / "demographics_state.csv"
    return pd.read_csv(p, dtype={"state": str}) if p.exists() else pd.DataFrame()


@functools.lru_cache(maxsize=None)
def _county() -> pd.DataFrame:
    p = _DIR / "county_demographics.csv"
    return pd.read_csv(p, dtype={"county_fips": str, "state": str}) if p.exists() else pd.DataFrame()


def demographics_summary() -> Dict[str, Any]:
    p = _DIR / "demographics_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def demographics_state(state: str) -> Dict[str, Any]:
    df = _state()
    if not len(df) or not state:
        return {}
    rows = df[df["state"] == str(state).strip().upper()]
    return rows.iloc[0].to_dict() if len(rows) else {}


def demographics_county(fips: str) -> Dict[str, Any]:
    df = _county()
    if not len(df) or not fips:
        return {}
    f = str(fips).strip().zfill(5)
    rows = df[df["county_fips"] == f]
    return rows.iloc[0].to_dict() if len(rows) else {}


def counties_for_state(state: str) -> List[Dict[str, Any]]:
    """All counties on record for a state (real ACS/CHR rows), newest-largest
    not implied — caller sorts. Empty list if the state has no rows."""
    df = _county()
    if not len(df) or not state:
        return []
    s = str(state).strip().upper()
    rows = df[df["state"] == s]
    return rows.to_dict("records") if len(rows) else []


def measure_labels() -> Dict[str, str]:
    return {
        "population": "Population",
        "pct_age_65_plus": "Age 65+",
        "median_household_income": "Median household income",
        "child_poverty_rate": "Children in poverty",
        "uninsured_rate": "Uninsured",
        "pct_white_nh": "Non-Hispanic White",
        "pct_black_nh": "Non-Hispanic Black",
        "pct_hispanic": "Hispanic",
        "pct_rural": "Rural",
    }


def top_states_by(measure: str, limit: int = 10, ascending: bool = False
                  ) -> List[Dict[str, Any]]:
    df = _state()
    if not len(df) or measure not in df.columns:
        return []
    out = df[["state", measure, "population"]].dropna(subset=[measure])
    return out.sort_values(measure, ascending=ascending).head(limit).to_dict("records")


def demographics_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "chr_county_demographics"].to_dict("records")
