"""CMS clinician MIPS performance — PII-free score distribution (PY2023).

Reads the committed aggregates under ``rcm_mc/data/vendor/mips/`` (produced by
``scripts/ingest_mips_performance.py`` from CMS's per-clinician
``ec_score_file.csv``, with all NPIs/names dropped at ingest). Public CMS data;
no runtime network.

Honesty: this is the real published MIPS final-score DISTRIBUTION across
clinicians — a physician-quality market benchmark, NOT a deal-specific score
and NOT a payment figure. Missing scores were excluded at ingest (never 0).
"""
from __future__ import annotations
import functools
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "mips"


@functools.lru_cache(maxsize=None)
def _load(name: str) -> pd.DataFrame:
    p = _DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def snapshot() -> Dict[str, Any]:
    rp = _DIR / "mips_report.json"
    return json.loads(rp.read_text()) if rp.exists() else {}


def mips_score_summary(scope: str = "All clinicians") -> Dict[str, Any]:
    """Distribution stats (n, mean, median, p10/p25/p75/p90) for a scope.

    ``scope`` is ``"All clinicians"`` or ``"source: <individual|group|apm|...>"``.
    Returns ``{}`` if the scope/data is absent.
    """
    df = _load("mips_score_summary.csv")
    if not len(df):
        return {}
    m = df[df["scope"].astype(str) == scope]
    if not len(m):
        return {}
    row = m.iloc[0].to_dict()
    row["performance_year"] = snapshot().get("performance_year", "")
    return row


def mips_scopes() -> List[str]:
    df = _load("mips_score_summary.csv")
    return df["scope"].astype(str).tolist() if len(df) else []


def mips_score_bands() -> List[Dict[str, Any]]:
    """Score-band histogram (0-20 … 75-100) with count + pct of clinicians."""
    df = _load("mips_score_bands.csv")
    return df.to_dict("records") if len(df) else []


def mips_category_scores() -> List[Dict[str, Any]]:
    """Per-category sub-score distribution (Quality / PI / IA / Cost)."""
    df = _load("mips_category_scores.csv")
    return df.to_dict("records") if len(df) else []


def mips_sources() -> List[Dict[str, str]]:
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    r = pd.read_csv(reg)
    return r[r["source_id"].astype(str) == "cms_mips_py2023"].to_dict("records")
