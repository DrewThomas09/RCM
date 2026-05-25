"""CMS Medicare FFS provider-supply counts by state x provider type (loader).

Reads the committed PII-free aggregate under
``rcm_mc/data/vendor/provider_supply/`` (from
``scripts/ingest_provider_supply.py``). Public CMS data; no runtime network.

Honesty: this is Medicare-enrolled provider SUPPLY (density) by geography — a
real market/access signal. It is NOT every provider (FFS Medicare-enrolled
only, excludes Medicare Advantage-only / non-Medicare), NOT a quality measure,
and NOT provider-specific. Use it for relative supply density / demand-supply
framing, combined with demand (age 65+) and CMS/HCRIS data.
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "provider_supply"

# provider-type substrings that approximate primary-care physician supply
# (the NAICS 621111 / "primary care doctors" concept from the market maps).
_PRIMARY_CARE = ("FAMILY PRACTICE", "INTERNAL MEDICINE", "GENERAL PRACTICE",
                 "PEDIATRIC", "GERIATRIC")


@functools.lru_cache(maxsize=None)
def _state_type() -> pd.DataFrame:
    p = _DIR / "provider_supply_state_type.csv"
    return pd.read_csv(p, dtype={"state": str}) if p.exists() else pd.DataFrame()


@functools.lru_cache(maxsize=None)
def _national_type() -> pd.DataFrame:
    p = _DIR / "provider_supply_national_type.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def snapshot() -> Dict[str, Any]:
    rp = _DIR / "provider_supply_report.json"
    return json.loads(rp.read_text()) if rp.exists() else {}


def supply_national_by_type(limit: int = 0) -> List[Dict[str, Any]]:
    df = _national_type()
    if not len(df):
        return []
    return (df.head(limit) if limit else df).to_dict("records")


def supply_for_state(state: str) -> List[Dict[str, Any]]:
    df = _state_type()
    if not len(df) or not state:
        return []
    st = str(state).strip().upper()
    return df[df["state"] == st].sort_values("enrolled_count", ascending=False).to_dict("records")


def total_supply_for_state(state: str) -> int:
    return int(sum(r["enrolled_count"] for r in supply_for_state(state)))


def primary_care_supply_for_state(state: str) -> int:
    """Approximate primary-care physician supply (family/internal/general/
    pediatric/geriatric practitioner enrollments) for a state — the
    NAICS-621111-style supply signal. Approximation, not an exact NAICS count."""
    rows = supply_for_state(state)
    return int(sum(r["enrolled_count"] for r in rows
                   if any(k in str(r["provider_type"]).upper() for k in _PRIMARY_CARE)))


def supply_summary() -> Dict[str, Any]:
    snap = snapshot()
    return {
        "states": snap.get("states", 0),
        "provider_types": snap.get("provider_types", 0),
        "total_enrollments": snap.get("total_enrollments", 0),
        "extract": snap.get("extract", ""),
    }


def provider_supply_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_ffs_provider_enrollment"].to_dict("records")
