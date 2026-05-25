"""openFDA drug-shortage dataset — loader + summaries.

Reads the committed build-time snapshot
(`rcm_mc/data/vendor/drug_data/fda_drug_shortages.csv`, produced by
`scripts/ingest_fda_drug_shortages.py`). openFDA is public domain (CC0). No
runtime network calls — the snapshot is read from disk.

Honesty: this is product/drug-level shortage data, NOT provider-specific; a
shortage does not by itself imply impact on a given target. Missing fields stay
empty; counts report the snapshot's coverage.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "drug_data"


@functools.lru_cache(maxsize=None)
def load_drug_shortages() -> pd.DataFrame:
    p = _DIR / "fda_drug_shortages.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str).fillna("")


def snapshot_date() -> str:
    rp = _DIR / "fda_drug_shortages_report.json"
    if rp.exists():
        return json.loads(rp.read_text()).get("snapshot_date", "")
    return ""


def drug_shortage_summary() -> Dict[str, Any]:
    df = load_drug_shortages()
    if not len(df):
        return {"total": 0, "current": 0, "categories": 0, "snapshot_date": ""}
    status = df["status"].astype(str).str.lower()
    return {
        "total": len(df),
        "current": int((status == "current").sum()),
        "resolved": int((status == "resolved").sum()),
        "categories": int(df["therapeutic_category"].nunique()),
        "snapshot_date": snapshot_date(),
    }


def shortages_by_category(current_only: bool = True, limit: int = 15
                          ) -> List[Dict[str, Any]]:
    """Therapeutic categories ranked by number of shortages."""
    df = load_drug_shortages()
    if not len(df):
        return []
    if current_only:
        df = df[df["status"].astype(str).str.lower() == "current"]
    counts = (df["therapeutic_category"].replace("", "Uncategorized")
              .value_counts().head(limit))
    return [{"category": k, "n": int(v)} for k, v in counts.items()]


def current_shortages(category: str = "", search: str = "", limit: int = 50
                      ) -> pd.DataFrame:
    """Current shortages, optionally filtered by therapeutic category or a
    generic-name/company search."""
    df = load_drug_shortages()
    if not len(df):
        return df
    df = df[df["status"].astype(str).str.lower() == "current"]
    if category:
        df = df[df["therapeutic_category"].astype(str).str.contains(
            category, case=False, na=False)]
    if search:
        s = search.lower()
        df = df[df["generic_name"].astype(str).str.lower().str.contains(s)
                | df["company_name"].astype(str).str.lower().str.contains(s)]
    cols = ["generic_name", "company_name", "therapeutic_category",
            "dosage_form", "availability", "initial_posting_date", "update_date"]
    return df[cols].head(limit)


def drug_shortage_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    rdf = pd.read_csv(reg)
    return rdf[rdf["source_id"].astype(str) == "openfda_drug_shortages"].to_dict("records")
