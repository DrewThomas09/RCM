"""Base-rate API: P25/P50/P75 benchmarks from the public deals corpus.

Segments deals by hospital size (small / medium / large / unknown),
dominant payer mix, deal type, and geographic region when available,
then computes percentile statistics over realized_moic and realized_irr.

Why percentiles rather than means?
    Hospital deal returns are fat-tailed.  A handful of home-run outcomes
    (Acadia, HCA re-IPO) skew the mean upward significantly; the median
    is a more honest calibration anchor for a new deal underwriting.

Size buckets (by enterprise value — beds data rarely disclosed publicly):
    small   EV < $500M
    medium  EV $500M – $3B
    large   EV > $3B

Dominant payer: the payer category with the highest share in payer_mix.

Public API:
    Benchmarks dataclass            – result container
    get_benchmarks(corpus_db_path)  – all deals (no filter)
    get_benchmarks_by_size(...)     – filter by size bucket
    get_benchmarks_by_payer(...)    – filter by dominant payer
    get_benchmarks_by_buyer(...)    – filter by buyer substring
    full_summary(corpus_db_path)    – combined dict of all segment benchmarks
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..portfolio.store import PortfolioStore


# ---------------------------------------------------------------------------
# Size bucket thresholds (EV in $M)
# ---------------------------------------------------------------------------
_SMALL_MAX  = 500.0
_MEDIUM_MAX = 3_000.0


@dataclass
class Benchmarks:
    """P25/P50/P75 statistics for a filtered deal set."""

    n_deals: int = 0
    n_with_moic: int = 0
    n_with_irr: int = 0

    moic_p25: Optional[float] = None
    moic_p50: Optional[float] = None
    moic_p75: Optional[float] = None
    moic_mean: Optional[float] = None

    irr_p25: Optional[float] = None
    irr_p50: Optional[float] = None
    irr_p75: Optional[float] = None
    irr_mean: Optional[float] = None

    ev_p50: Optional[float] = None
    hold_p50: Optional[float] = None

    filters: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "n_deals": self.n_deals,
            "n_with_moic": self.n_with_moic,
            "n_with_irr": self.n_with_irr,
            "moic": {
                "p25": self.moic_p25,
                "p50": self.moic_p50,
                "p75": self.moic_p75,
                "mean": self.moic_mean,
            },
            "irr": {
                "p25": self.irr_p25,
                "p50": self.irr_p50,
                "p75": self.irr_p75,
                "mean": self.irr_mean,
            },
            "ev_p50": self.ev_p50,
            "hold_p50": self.hold_p50,
            "filters": self.filters,
        }


def _percentile(values: List[float], pct: float) -> Optional[float]:
    """Compute the p-th percentile (0–100) using linear interpolation."""
    if not values:
        return None
    n = len(values)
    if n == 1:
        return values[0]
    sorted_v = sorted(values)
    # fractional index
    idx = (pct / 100.0) * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_v[-1]
    frac = idx - lo
    return sorted_v[lo] + frac * (sorted_v[hi] - sorted_v[lo])


def _safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _dominant_payer(payer_mix_json: Optional[str]) -> Optional[str]:
    """Return the payer category with the highest share."""
    if not payer_mix_json:
        return None
    try:
        pm = json.loads(payer_mix_json)
        if not pm:
            return None
        return max(pm, key=lambda k: pm[k])
    except (json.JSONDecodeError, TypeError):
        return None


def _size_bucket(ev_mm: Optional[float]) -> str:
    if ev_mm is None:
        return "unknown"
    if ev_mm < _SMALL_MAX:
        return "small"
    if ev_mm < _MEDIUM_MAX:
        return "medium"
    return "large"


def _compute_benchmarks(rows: List[Any], filters: Dict[str, Any]) -> Benchmarks:
    moic_vals = [r["realized_moic"] for r in rows if r["realized_moic"] is not None]
    irr_vals  = [r["realized_irr"]  for r in rows if r["realized_irr"]  is not None]
    ev_vals   = [r["ev_mm"]         for r in rows if r["ev_mm"]          is not None]
    hold_vals = [r["hold_years"]    for r in rows if r["hold_years"]     is not None]

    return Benchmarks(
        n_deals     = len(rows),
        n_with_moic = len(moic_vals),
        n_with_irr  = len(irr_vals),
        moic_p25    = _percentile(moic_vals, 25),
        moic_p50    = _percentile(moic_vals, 50),
        moic_p75    = _percentile(moic_vals, 75),
        moic_mean   = _safe_mean(moic_vals),
        irr_p25     = _percentile(irr_vals, 25),
        irr_p50     = _percentile(irr_vals, 50),
        irr_p75     = _percentile(irr_vals, 75),
        irr_mean    = _safe_mean(irr_vals),
        ev_p50      = _percentile(ev_vals, 50),
        hold_p50    = _percentile(hold_vals, 50),
        filters     = filters,
    )


def _query_all(db_path: str) -> List[Any]:
    # Route through PortfolioStore (campaign target 4E, data_public
    # sweep): inherits busy_timeout=5000, foreign_keys=ON, and
    # row_factory=Row — exactly what the prior _connect() helper
    # set up by hand.
    with PortfolioStore(db_path).connect() as con:
        return con.execute("SELECT * FROM public_deals").fetchall()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_benchmarks(corpus_db_path: str) -> Benchmarks:
    """Percentile benchmarks across all deals with realized outcomes."""
    rows = _query_all(corpus_db_path)
    return _compute_benchmarks(rows, {})


def get_benchmarks_by_size(
    corpus_db_path: str,
    size_bucket: str,
) -> Benchmarks:
    """Benchmarks for deals in a specific EV size bucket.

    size_bucket: 'small' (EV < $500M), 'medium' ($500M-$3B), 'large' (> $3B).
    """
    all_rows = _query_all(corpus_db_path)
    filtered = [r for r in all_rows if _size_bucket(r["ev_mm"]) == size_bucket]
    return _compute_benchmarks(filtered, {"size_bucket": size_bucket})


def get_benchmarks_by_payer(
    corpus_db_path: str,
    dominant_payer: str,
) -> Benchmarks:
    """Benchmarks for deals where the dominant payer matches the given category.

    dominant_payer: 'medicare', 'medicaid', 'commercial', 'self_pay'.
    """
    all_rows = _query_all(corpus_db_path)
    filtered = [
        r for r in all_rows
        if _dominant_payer(r["payer_mix"]) == dominant_payer
    ]
    return _compute_benchmarks(filtered, {"dominant_payer": dominant_payer})


def get_benchmarks_by_buyer(
    corpus_db_path: str,
    buyer_substr: str,
) -> Benchmarks:
    """Benchmarks for deals where buyer contains buyer_substr (case-insensitive)."""
    all_rows = _query_all(corpus_db_path)
    s = buyer_substr.lower()
    filtered = [
        r for r in all_rows
        if r["buyer"] and s in r["buyer"].lower()
    ]
    return _compute_benchmarks(filtered, {"buyer_contains": buyer_substr})


def get_benchmarks_by_year_range(
    corpus_db_path: str,
    year_min: int,
    year_max: int,
) -> Benchmarks:
    all_rows = _query_all(corpus_db_path)
    filtered = [
        r for r in all_rows
        if r["year"] is not None and year_min <= r["year"] <= year_max
    ]
    return _compute_benchmarks(filtered, {"year_min": year_min, "year_max": year_max})


def full_summary(corpus_db_path: str) -> Dict[str, Any]:
    """Return a nested dict of benchmarks across all key segmentations."""
    return {
        "overall": get_benchmarks(corpus_db_path).as_dict(),
        "by_size": {
            bucket: get_benchmarks_by_size(corpus_db_path, bucket).as_dict()
            for bucket in ("small", "medium", "large", "unknown")
        },
        "by_dominant_payer": {
            payer: get_benchmarks_by_payer(corpus_db_path, payer).as_dict()
            for payer in ("medicare", "medicaid", "commercial", "self_pay")
        },
        "by_era": {
            "pre_aca": get_benchmarks_by_year_range(corpus_db_path, 2000, 2013).as_dict(),
            "aca_era": get_benchmarks_by_year_range(corpus_db_path, 2014, 2018).as_dict(),
            "post_covid": get_benchmarks_by_year_range(corpus_db_path, 2019, 2030).as_dict(),
        },
    }
