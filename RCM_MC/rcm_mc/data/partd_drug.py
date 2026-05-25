"""CMS Medicare Part D Spending by Drug aggregate — loader.

Reads the committed aggregate under ``rcm_mc/data/vendor/partd_drug/`` (built
by ``scripts/ingest_partd_drug_spending.py``). Public CMS data; no runtime
network.

Honesty: real Medicare Part D retail drug spend + per-dosage-unit price and
its 2019-2023 CAGR — a real drug-cost / price-inflation signal. NOT 340B
ceiling prices, NOT this deal's formulary, and Part-D-retail (not 340B
acquisition) economics.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "partd_drug"


def partd_drug_summary() -> Dict[str, Any]:
    p = _DIR / "partd_drug_summary.json"
    return json.loads(p.read_text()) if p.exists() else {}


@functools.lru_cache(maxsize=None)
def _top_spend() -> pd.DataFrame:
    p = _DIR / "partd_drug_top_spend.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@functools.lru_cache(maxsize=None)
def _top_inflation() -> pd.DataFrame:
    p = _DIR / "partd_drug_top_inflation.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def top_drugs_by_spend(limit: int = 10) -> List[Dict[str, Any]]:
    df = _top_spend()
    return df.head(limit).to_dict("records") if len(df) else []


def top_drugs_by_price_inflation(limit: int = 10) -> List[Dict[str, Any]]:
    df = _top_inflation()
    return df.head(limit).to_dict("records") if len(df) else []


def partd_drug_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    return df[df["source_id"].astype(str) == "cms_partd_drug_spending"].to_dict("records")
