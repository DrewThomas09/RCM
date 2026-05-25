"""CMS Open Payments (staged) — industry-payments aggregates (loader).

Reads the committed PII-free aggregate under
``rcm_mc/data/vendor/open_payments/`` (from ``scripts/ingest_open_payments.py``,
the small CMS summary file). Public CMS data; no runtime network.

Honesty: industry (manufacturer/GPO) payments to physicians/teaching hospitals —
a real financial-relationship SCALE signal. NOT provider-specific here (entity
side only), NOT a wrongdoing flag (disclosure is lawful/routine). Detail
(recipient/specialty/nature labels) is a documented full-ingest follow-up.
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "open_payments"


@functools.lru_cache(maxsize=None)
def _top_entities() -> pd.DataFrame:
    p = _DIR / "open_payments_top_entities.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def open_payments_summary() -> Dict[str, Any]:
    rp = _DIR / "open_payments_report.json"
    snap = json.loads(rp.read_text()) if rp.exists() else {}
    return {
        "program_year": snap.get("program_year"),
        "total_payments_usd": snap.get("total_payments_usd", 0),
        "total_transactions": snap.get("total_transactions", 0),
        "reporting_entities": snap.get("reporting_entities", 0),
    }


def top_reporting_entities(limit: int = 10) -> List[Dict[str, Any]]:
    df = _top_entities()
    if not len(df):
        return []
    return df.head(limit).to_dict("records")


def open_payments_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_open_payments_2023"].to_dict("records")
