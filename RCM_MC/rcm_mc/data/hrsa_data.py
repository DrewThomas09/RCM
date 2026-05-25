"""HRSA Health Professional Shortage Area (HPSA) — Primary Care, state index.

Reads the committed state-aggregated snapshot
(`rcm_mc/data/vendor/hrsa/hrsa_hpsa_pc_by_state.csv`, from
`scripts/ingest_hrsa_hpsa.py`). Public HRSA data; no runtime network.

Honesty: this is MARKET/access context (state-level primary-care shortage),
NOT provider-specific and NOT a productivity/comp measure. Missing stays NaN.
"""
from __future__ import annotations
import functools, json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "hrsa"


@functools.lru_cache(maxsize=None)
def load_hpsa_by_state() -> pd.DataFrame:
    p = _DIR / "hrsa_hpsa_pc_by_state.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def snapshot_date() -> str:
    rp = _DIR / "hrsa_hpsa_report.json"
    return json.loads(rp.read_text()).get("snapshot_date", "") if rp.exists() else ""


def hpsa_summary() -> Dict[str, Any]:
    df = load_hpsa_by_state()
    if not len(df):
        return {"states": 0, "total_designated": 0, "snapshot_date": ""}
    return {
        "states": int(len(df)),
        "total_designated": int(df["designated_pc_hpsas"].sum()),
        "national_median_score": float(df["median_hpsa_score"].median()),
        "snapshot_date": snapshot_date(),
    }


def hpsa_state(state: str) -> Dict[str, Any]:
    df = load_hpsa_by_state()
    if not len(df) or not state:
        return {}
    m = df[df["state"].astype(str).str.upper() == str(state).upper()]
    return m.iloc[0].to_dict() if len(m) else {}


def top_shortage_states(limit: int = 12) -> List[Dict[str, Any]]:
    df = load_hpsa_by_state()
    if not len(df):
        return []
    return df.head(limit).to_dict("records")


def hpsa_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    r = pd.read_csv(reg)
    return r[r["source_id"].astype(str) == "hrsa_hpsa_pc"].to_dict("records")
