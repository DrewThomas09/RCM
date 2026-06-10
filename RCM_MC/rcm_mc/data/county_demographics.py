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


def _norm_county(name: str) -> str:
    """Normalize a county label for name-matching: uppercase, drop the
    County/Parish/Borough suffix and internal spaces so the geocode file's
    'DE KALB' / 'HOUSTON' collide with the ACS file's 'DeKalb County' /
    'Houston County'. Bridges the common label gaps WITHOUT fuzzy matching
    (which could mis-join a target to the wrong county)."""
    n = (name or "").upper()
    for suf in (" COUNTY", " PARISH", " BOROUGH", " CENSUS AREA",
                " CITY AND BOROUGH", " MUNICIPALITY"):
        if n.endswith(suf):
            n = n[: -len(suf)]
    return n.replace(" ", "").strip()


@functools.lru_cache(maxsize=1)
def _county_by_name() -> Dict[tuple, Dict[str, Any]]:
    """(state, normalized county-name) → county row, for joins that only have
    a county NAME (e.g. the hospital geocode file) rather than a FIPS code."""
    df = _county()
    out: Dict[tuple, Dict[str, Any]] = {}
    if not len(df) or "county_name" not in df.columns:
        return out
    for rec in df.to_dict("records"):
        st = str(rec.get("state") or "").upper().strip()
        cn = rec.get("county_name") or ""
        if st and cn:
            out[(st, _norm_county(cn))] = rec
    return out


def demographics_for_ccn(ccn: str) -> Dict[str, Any]:
    """Resolve a hospital CCN → its vendored geocode county → county
    demographics, by EXACT normalized name match within state. Empty dict
    when the CCN isn't geocoded or its county doesn't match the ACS file
    exactly — never a guessed/nearest county (a wrong county's demographics
    would mislead diligence)."""
    from .hospital_coords import load_hospital_coords
    c = load_hospital_coords().get(str(ccn))
    if c is None or not c.county or not c.state:
        return {}
    return _county_by_name().get(
        (c.state.upper().strip(), _norm_county(c.county)), {})

