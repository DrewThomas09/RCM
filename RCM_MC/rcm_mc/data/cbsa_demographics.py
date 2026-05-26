"""CBSA (metro/micro) demographics — derived loader.

Joins the committed OMB CBSA<->county crosswalk
(``vendor/cbsa_crosswalk/``, built by ``scripts/ingest_cbsa_crosswalk.py``)
to the committed county demographics (County Health Rankings / Census ACS) and
rolls counties up to Core-Based Statistical Areas. NO runtime network.

Honesty:
  • Population is a real SUM of member-county ACS populations.
  • Age-65+, uninsured and rural shares are real POPULATION-WEIGHTED MEANS of
    the member-county ACS values.
  • Median household income is a population-weighted mean of county medians — a
    reasonable ESTIMATE, not a true CBSA median (which needs microdata). It is
    labelled as an estimate wherever surfaced.
Counties with no demographic row are simply excluded from that CBSA's roll-up;
nothing is fabricated to fill gaps.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "cbsa_crosswalk"

# (county-demographics column, weighted? ) — population is summed; the rest are
# population-weighted means.
_WEIGHTED_COLS = ["pct_age_65_plus", "median_household_income",
                  "uninsured_rate", "child_poverty_rate", "pct_rural"]


@functools.lru_cache(maxsize=None)
def _crosswalk() -> pd.DataFrame:
    p = _DIR / "cbsa_county_crosswalk.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype={"county_fips": str, "cbsa_code": str})


@functools.lru_cache(maxsize=None)
def _joined() -> pd.DataFrame:
    """County demographics joined to their CBSA. county_fips is normalised to a
    5-digit string on both sides (the demographics file drops the leading 0)."""
    xw = _crosswalk()
    if not len(xw):
        return pd.DataFrame()
    from rcm_mc.data import county_demographics as _cd
    cd = _cd._county()
    if not len(cd):
        return pd.DataFrame()
    cd = cd.copy()
    cd["county_fips"] = cd["county_fips"].astype(str).str.zfill(5)
    xw = xw.copy()
    xw["county_fips"] = xw["county_fips"].astype(str).str.zfill(5)
    return cd.merge(xw, on="county_fips", how="inner")


@functools.lru_cache(maxsize=None)
def _aggregated() -> pd.DataFrame:
    """One row per CBSA with summed population + population-weighted means."""
    df = _joined()
    if not len(df):
        return pd.DataFrame()
    df = df.copy()
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    rows: List[Dict[str, Any]] = []
    for (code, title, area), g in df.groupby(["cbsa_code", "cbsa_title", "area_type"]):
        pop = g["population"].fillna(0).sum()
        rec: Dict[str, Any] = {
            "cbsa_code": code, "cbsa_title": title, "area_type": area,
            "population": float(pop), "county_count": int(len(g)),
        }
        for col in _WEIGHTED_COLS:
            vals = pd.to_numeric(g[col], errors="coerce")
            w = g["population"].where(vals.notna())
            den = w.fillna(0).sum()
            rec[col] = float((vals.fillna(0) * w.fillna(0)).sum() / den) if den else None
        rows.append(rec)
    out = pd.DataFrame(rows)
    return out.sort_values("population", ascending=False).reset_index(drop=True)


def cbsa_list(area_type: str = "", limit: int = 0) -> List[Dict[str, Any]]:
    """All CBSAs (optionally filtered to 'Metropolitan'/'Micropolitan'),
    largest population first. Real derived aggregates."""
    df = _aggregated()
    if not len(df):
        return []
    if area_type:
        df = df[df["area_type"] == area_type]
    if limit:
        df = df.head(limit)
    return df.to_dict("records")


def cbsa_demographics(cbsa_code: str) -> Dict[str, Any]:
    """One CBSA's real derived demographics, or {} if unknown."""
    df = _aggregated()
    if not len(df) or not cbsa_code:
        return {}
    rows = df[df["cbsa_code"] == str(cbsa_code).strip()]
    return rows.iloc[0].to_dict() if len(rows) else {}


def cbsa_summary() -> Dict[str, Any]:
    """National roll-up + provenance for the CBSA demographics layer."""
    df = _aggregated()
    if not len(df):
        return {}
    import json
    meta_p = _DIR / "cbsa_crosswalk_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    return {
        "cbsas": int(len(df)),
        "metros": int((df["area_type"] == "Metropolitan").sum()),
        "micros": int((df["area_type"] == "Micropolitan").sum()),
        "covered_population": float(df["population"].sum()),
        "vintage": meta.get("vintage", ""),
        "source": meta.get("source", ""),
    }


def cbsa_sources() -> List[Dict[str, str]]:
    return [{
        "source_id": "cbsa_crosswalk",
        "name": "OMB CBSA delineation (Census, July 2023) × County Health Rankings/ACS demographics",
        "url": "https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html",
    }]
