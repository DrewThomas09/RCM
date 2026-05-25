"""OIG LEIE excluded-provider aggregate — loader.

Reads the committed PII-free aggregate under ``rcm_mc/data/vendor/oig_leie/``
(built by ``scripts/ingest_oig_leie.py``). Public OIG data; no runtime network.

Honesty: counts of OIG-excluded individuals/entities (Medicare/Medicaid
fraud-&-abuse / sanction signal) by state, exclusion type, year, specialty.
Names/NPI/DOB/address are dropped at ingest. NOT this deal's providers and
NOT a prediction — it is the realized exclusion record.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_DIR = Path(__file__).resolve().parent / "vendor" / "oig_leie"


def leie_summary() -> Dict[str, Any]:
    p = _DIR / "oig_leie_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def top_states(limit: int = 8) -> List[Dict[str, Any]]:
    return (leie_summary().get("by_state") or [])[:limit]


def by_exclusion_type(limit: int = 8) -> List[Dict[str, Any]]:
    return (leie_summary().get("by_exclusion_type") or [])[:limit]


def by_year_recent() -> List[Dict[str, Any]]:
    return leie_summary().get("by_year_recent") or []


def leie_sources() -> List[Dict[str, str]]:
    import pandas as pd
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "oig_leie"].to_dict("records")
