"""PEdesk Market Intelligence — loaders over licensed SimplyAnalytics exports.

Reads the committed normalized CSVs under ``data/market_intel/`` (produced
offline by ``scripts/ingest_market_intel_exports.py`` from licensed
SimplyAnalytics tabular exports — raw exports/screenshots are NOT in the repo).
All values carry provenance + a license note. This is **market/area context**
(county/state), NOT provider-specific, and demographic/payer mix should be
combined with CMS/HCRIS/provider data before a decision. Missing stays missing.

No runtime network; loaders read committed CSV only.
"""
from __future__ import annotations

import csv
import functools
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "market_intel"

SOURCE_KIND = "LICENSED MARKET DATA DERIVED"


@functools.lru_cache(maxsize=None)
def _load(name: str) -> List[Dict[str, Any]]:
    p = _DIR / name
    if not p.exists() or not p.read_text().strip():
        return []
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _num(row: Dict[str, Any], key: str) -> Optional[float]:
    v = row.get(key, "")
    try:
        return float(v) if v not in ("", None) else None
    except (ValueError, TypeError):
        return None


def report() -> Dict[str, Any]:
    p = _DIR / "market_intel_report.json"
    return json.loads(p.read_text()) if p.exists() else {}


def load_market_variables() -> List[Dict[str, Any]]:
    return _load("market_variables.csv")


def load_market_variable(variable_id: str) -> Optional[Dict[str, Any]]:
    return next((v for v in load_market_variables()
                 if v.get("variable_id") == variable_id), None)


def load_market_values(level: str = "state") -> List[Dict[str, Any]]:
    name = "market_values_county.csv" if level == "county" else "market_values_state.csv"
    return _load(name)


def _all_values() -> List[Dict[str, Any]]:
    return load_market_values("state") + load_market_values("county")


def market_values_for_fips(fips: str) -> List[Dict[str, Any]]:
    f = str(fips).strip()
    return [r for r in _all_values() if r.get("fips") == f]


def market_values_for_state(state_fips: str) -> List[Dict[str, Any]]:
    f = str(state_fips).strip().zfill(2)
    return [r for r in _all_values()
            if r.get("fips") == f or str(r.get("fips", "")).startswith(f) and r.get("geo_level") == "county"]


def rank_markets(variable_id: str, geography: str = "state",
                 limit: int = 0, ascending: bool = False) -> List[Dict[str, Any]]:
    """Markets ranked by a variable's real value (desc by default). Only rows
    with a real value are returned (no fabricated fill)."""
    rows = [r for r in load_market_values(geography)
            if r.get("variable_id") == variable_id and _num(r, "value") is not None]
    rows.sort(key=lambda r: _num(r, "value"), reverse=not ascending)
    return rows[:limit] if limit else rows


def market_profile_for_geo(fips: str) -> Dict[str, Any]:
    """All market variables on record for one geography, with percentiles."""
    vals = market_values_for_fips(fips)
    if not vals:
        return {}
    name = vals[0].get("geo_name", "")
    level = vals[0].get("geo_level", "")
    return {
        "fips": str(fips), "geo_name": name, "geo_level": level,
        "variables": {
            r["variable_id"]: {
                "value": _num(r, "value"), "unit": r.get("unit"),
                "year": r.get("year"),
                "percentile_national": _num(r, "percentile_national"),
                "source_file": r.get("source_file"),
            } for r in vals
        },
    }


# Market-score weights — VISIBLE and documented (per spec: no fabricated
# scores). Each component is a national percentile (0-100) of a real variable;
# a component is only included if its underlying export exists.
_SCORE_COMPONENTS = {
    "demand_score": ("age_65_plus_pct", False),          # higher 65+ = more demand
    "income_score": ("median_household_income", False),  # higher income = better
    "payer_score": ("private_insurance_pct", False),     # higher commercial = better
    "uninsured_penalty": ("uninsured_pct", True),        # higher uninsured = worse (inverted)
}


def market_demand_score(fips: str) -> Dict[str, Any]:
    """Formula-driven, PARTIAL market score for a geography.

    Each available component = the national percentile of a real variable
    (0-100); the uninsured component is inverted (100 - pctile). The overall is
    the simple average of AVAILABLE components only. Components whose export is
    not yet ingested are returned under ``missing`` as EXPORT REQUIRED — never
    invented. ``overall`` is ``None`` if no component is available.
    """
    prof = market_profile_for_geo(fips)
    if not prof:
        return {}
    vars_ = prof["variables"]
    components: Dict[str, float] = {}
    missing: List[str] = []
    for score_name, (vid, invert) in _SCORE_COMPONENTS.items():
        row = vars_.get(vid)
        pct = row.get("percentile_national") if row else None
        if pct is None:
            missing.append(score_name)
            continue
        components[score_name] = round(100 - pct if invert else pct, 1)
    overall = round(sum(components.values()) / len(components), 1) if components else None
    return {
        "fips": prof["fips"], "geo_name": prof["geo_name"],
        "components": components, "overall_market_score": overall,
        "missing_export_required": missing,
        "formula": "overall = mean(available national-percentile components); "
                   "uninsured inverted; missing components excluded (not zero-filled).",
    }


def provider_supply_for_naics(naics_code: str) -> List[Dict[str, Any]]:
    """Provider-supply rows for a NAICS code (EXPORT REQUIRED until the
    SimplyAnalytics provider-count export is ingested — returns [] honestly)."""
    rows = _load("market_provider_supply.csv")
    return [r for r in rows if str(r.get("naics_code")) == str(naics_code)]


def market_intel_sources() -> List[Dict[str, str]]:
    reg = Path(__file__).resolve().parent / "vendor" / "source_registry.csv"
    if not reg.exists():
        return []
    with reg.open(newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("source_id") == "market_intel"]
