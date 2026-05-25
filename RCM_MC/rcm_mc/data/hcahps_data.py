"""CMS HCAHPS patient-experience aggregate (loader).

Reads the committed aggregate under ``rcm_mc/data/vendor/hcahps/`` (built
by ``scripts/ingest_hcahps.py``). Public CMS Care Compare data; no runtime
network.

Honesty: these are the official CMS HCAHPS patient-survey top-box
percentages at the STATE level — a real, published patient-experience
benchmark. NOT this deal's facilities, NOT a payer-mix figure. National
figures are the simple mean across states (not patient-volume weighted).
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "hcahps"


@functools.lru_cache(maxsize=None)
def _state() -> pd.DataFrame:
    p = _DIR / "hcahps_state.csv"
    return pd.read_csv(p, dtype={"state": str}) if p.exists() else pd.DataFrame()


def hcahps_summary() -> Dict[str, Any]:
    p = _DIR / "hcahps_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


def hcahps_state(state: str) -> Dict[str, Any]:
    df = _state()
    if not len(df) or not state:
        return {}
    st = str(state).strip().upper()
    rows = df[df["state"] == st]
    return rows.iloc[0].to_dict() if len(rows) else {}


def measure_labels() -> Dict[str, str]:
    return {
        "overall_rating_9_10": "Overall rating 9–10",
        "would_definitely_recommend": "Would definitely recommend",
        "nurse_comm_always": "Nurses always communicated well",
        "doctor_comm_always": "Doctors always communicated well",
        "staff_explained_meds_always": "Staff always explained meds",
        "given_discharge_info": "Given discharge info",
        "room_always_clean": "Room always clean",
        "always_quiet_night": "Always quiet at night",
    }


def top_states_by(measure: str, limit: int = 10, ascending: bool = False
                  ) -> List[Dict[str, Any]]:
    """States ranked by an HCAHPS top-box measure (default: highest first)."""
    df = _state()
    if not len(df) or measure not in df.columns:
        return []
    out = df[["state", measure]].dropna(subset=[measure])
    out = out.sort_values(measure, ascending=ascending).head(limit)
    return out.to_dict("records")


def hcahps_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_hcahps_state"].to_dict("records")
