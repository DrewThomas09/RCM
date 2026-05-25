"""CDC PLACES health-equity / SDOH aggregate (loader).

Reads the committed aggregate under ``rcm_mc/data/vendor/cdc_places/``
(built by ``scripts/ingest_cdc_places.py``). Public CDC data; no runtime
network.

Honesty: these are model-based, FULL-POPULATION county estimates (BRFSS +
ACS) rolled up to population-weighted state and national prevalence — a real
social-determinants / health-equity benchmark. NOT this deal's patient
population, NOT a payer-mix figure, and not a clinical outcome for any
specific provider.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "cdc_places"


@functools.lru_cache(maxsize=None)
def _state() -> pd.DataFrame:
    p = _DIR / "places_equity_state.csv"
    return pd.read_csv(p, dtype={"state": str}) if p.exists() else pd.DataFrame()


def places_equity_summary() -> Dict[str, Any]:
    p = _DIR / "places_equity_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def places_equity_state(state: str) -> Dict[str, Any]:
    df = _state()
    if not len(df) or not state:
        return {}
    st = str(state).strip().upper()
    rows = df[df["state"] == st]
    return rows.iloc[0].to_dict() if len(rows) else {}


def measure_labels() -> Dict[str, str]:
    """Human label per equity measure key (for column headers)."""
    return {
        "uninsured_18_64": "Uninsured 18–64",
        "fair_poor_health": "Fair/poor health",
        "poor_mental_health": "Frequent mental distress",
        "poor_physical_health": "Poor physical health",
        "routine_checkup": "Routine checkup",
        "food_insecurity": "Food insecurity",
        "snap_participation": "SNAP participation",
        "utility_shutoff_threat": "Utility-shutoff threat",
        "lack_transportation": "Lack of transportation",
        "lack_emotional_support": "Lack emotional support",
        "depression": "Depression",
        "diabetes": "Diabetes",
        "obesity": "Obesity",
    }


def top_states_by(measure: str, limit: int = 10, ascending: bool = False
                  ) -> List[Dict[str, Any]]:
    """States ranked by a measure's prevalence (default: highest first =
    highest equity burden)."""
    df = _state()
    if not len(df) or measure not in df.columns:
        return []
    out = df[["state", measure, "population"]].dropna(subset=[measure])
    out = out.sort_values(measure, ascending=ascending).head(limit)
    return out.to_dict("records")


def places_equity_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cdc_places_equity"].to_dict("records")
