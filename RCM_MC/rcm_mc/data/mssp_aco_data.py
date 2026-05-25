"""CMS Medicare Shared Savings Program (MSSP) ACO participants — loader.

Reads the committed PII-free snapshot
(`rcm_mc/data/vendor/cms_aco/mssp_aco_participants.csv`, from
`scripts/ingest_mssp_aco.py`). Public CMS data; no runtime network calls.

Honesty: this is a national MSSP ACO **participation directory** (which provider
orgs are in which ACOs, by track/risk) — NOT financial/savings results and NOT
provider-specific performance. Missing stays empty.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "cms_aco"


@functools.lru_cache(maxsize=None)
def load_mssp_aco() -> pd.DataFrame:
    p = _DIR / "mssp_aco_participants.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str).fillna("")


def snapshot_date() -> str:
    rp = _DIR / "mssp_aco_report.json"
    if rp.exists():
        return json.loads(rp.read_text()).get("snapshot_date", "")
    return ""


def mssp_summary() -> Dict[str, Any]:
    df = load_mssp_aco()
    if not len(df):
        return {"acos": 0, "participant_orgs": 0, "snapshot_date": ""}
    by_aco = df.drop_duplicates("aco_id")
    return {
        "acos": int(df["aco_id"].nunique()),
        "participant_orgs": int(df["participant_org"].nunique()),
        "enhanced_track_acos": int((by_aco["enhanced_track"] == "1").sum()),
        "high_revenue_acos": int((by_aco["high_revenue_aco"] == "1").sum()),
        "low_revenue_acos": int((by_aco["low_revenue_aco"] == "1").sum()),
        "snapshot_date": snapshot_date(),
    }


def mssp_track_breakdown() -> List[Dict[str, Any]]:
    """ACO counts by risk track (ENHANCED vs BASIC level), deduped to ACO."""
    df = load_mssp_aco()
    if not len(df):
        return []
    by_aco = df.drop_duplicates("aco_id")
    out = []
    enh = int((by_aco["enhanced_track"] == "1").sum())
    if enh:
        out.append({"track": "ENHANCED", "acos": enh})
    basic = by_aco[by_aco["enhanced_track"] != "1"]
    for lvl, n in basic["basic_track_level"].replace("", "N/A").value_counts().items():
        out.append({"track": f"BASIC {lvl}", "acos": int(n)})
    return out


def top_acos_by_participants(limit: int = 15) -> List[Dict[str, Any]]:
    """ACOs ranked by number of distinct participant organizations."""
    df = load_mssp_aco()
    if not len(df):
        return []
    g = (df.groupby(["aco_id", "aco_name"])["participant_org"]
         .nunique().reset_index(name="participants")
         .sort_values("participants", ascending=False).head(limit))
    return [{"aco_name": r.aco_name, "service": "", "participants": int(r.participants)}
            for r in g.itertuples()]


def search_participants(query: str, limit: int = 40) -> pd.DataFrame:
    """Find ACOs/participant orgs by substring (org or ACO name)."""
    df = load_mssp_aco()
    if not len(df) or not query:
        return df.head(0) if len(df) else df
    q = query.lower()
    m = (df["participant_org"].str.lower().str.contains(q, na=False)
         | df["aco_name"].str.lower().str.contains(q, na=False))
    cols = ["participant_org", "aco_name", "service_area", "enhanced_track",
            "high_revenue_aco"]
    return df[m][cols].head(limit)


def mssp_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    rdf = pd.read_csv(reg)
    return rdf[rdf["source_id"].astype(str) == "cms_mssp_aco_py2026"].to_dict("records")
