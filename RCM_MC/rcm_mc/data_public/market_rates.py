"""Market-Rates / Base-Rate Engine.

Computes percentile cuts (P25/P50/P75/P90) of key valuation metrics across
the corpus, filterable by sector, size, region, vintage. This is the
foundational base-rate API for any deal comp.

Metrics:
- EV/EBITDA multiple
- EV/Revenue multiple
- Entry EBITDA margin
- Hold years
- Realized MOIC
- Realized IRR
- Commercial payer share
"""
from __future__ import annotations

import importlib
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PercentileRow:
    metric: str
    n: int
    p25: float
    p50: float
    p75: float
    p90: float
    mean: float
    min: float
    max: float


@dataclass
class SectorRollup:
    sector: str
    deal_count: int
    median_ev_mm: float
    median_ev_ebitda: float
    median_ev_revenue: float
    median_ebitda_margin: float
    median_moic: float
    median_irr: float


@dataclass
class SizeBucketRollup:
    bucket: str
    deal_count: int
    median_ev_ebitda: float
    median_ebitda_margin: float
    median_moic: float
    median_hold_years: float


@dataclass
class VintageRollup:
    year: int
    deal_count: int
    median_ev_ebitda: float
    median_ebitda_margin: float
    median_moic: float


@dataclass
class CommPctRollup:
    comm_bucket: str
    deal_count: int
    median_ev_ebitda: float
    median_ebitda_margin: float
    median_moic: float


@dataclass
class MarketRatesResult:
    filter_sector: str
    filter_size_bucket: str
    filter_region: str
    total_matching: int
    percentile_rows: List[PercentileRow]
    sector_rollups: List[SectorRollup]
    size_rollups: List[SizeBucketRollup]
    vintage_rollups: List[VintageRollup]
    comm_rollups: List[CommPctRollup]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(d: dict) -> dict:
    return {
        "sector": d.get("sector") or d.get("deal_type") or "",
        "region": d.get("region") or "",
        "year": d.get("year") or 0,
        "ev_mm": d.get("ev_mm") or 0,
        "ev_ebitda": d.get("ev_ebitda") or 0,
        "ebitda_mm": d.get("ebitda_mm") or d.get("ebitda_at_entry_mm") or 0,
        "ebitda_margin": d.get("ebitda_margin") or 0,
        "revenue_mm": d.get("revenue_mm") or 0,
        "hold_years": d.get("hold_years") or 0,
        "moic": d.get("moic") or d.get("realized_moic") or 0,
        "irr": d.get("irr") or d.get("realized_irr") or 0,
        "comm_pct": d.get("comm_pct") or (d.get("payer_mix", {}).get("commercial") if isinstance(d.get("payer_mix"), dict) else 0) or 0,
    }


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 89):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return [_normalize(d) for d in deals]


def _pct(vs: List[float], p: float) -> float:
    if not vs: return 0
    vs = sorted(vs)
    n = len(vs)
    if n == 1: return vs[0]
    k = (n - 1) * p
    lo = int(k)
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return vs[lo] * (1 - frac) + vs[hi] * frac


def _size_bucket(ev_mm: float) -> str:
    if ev_mm < 100: return "< $100M (small)"
    if ev_mm < 250: return "$100-250M (mid)"
    if ev_mm < 500: return "$250-500M (upper-mid)"
    if ev_mm < 1000: return "$500M-1B (large)"
    return "$1B+ (mega)"


def _build_percentile_rows(deals: List[dict]) -> List[PercentileRow]:
    metrics = [
        ("EV ($M)", "ev_mm"),
        ("EV/EBITDA (x)", "ev_ebitda"),
        ("EBITDA Margin", "ebitda_margin"),
        ("Revenue ($M)", "revenue_mm"),
        ("Hold Years", "hold_years"),
        ("MOIC (x)", "moic"),
        ("IRR", "irr"),
        ("Commercial Payer Share", "comm_pct"),
    ]
    rows = []
    for label, key in metrics:
        vals = [d.get(key) for d in deals if d.get(key) and d.get(key) > 0]
        if not vals: continue
        rows.append(PercentileRow(
            metric=label,
            n=len(vals),
            p25=round(_pct(vals, 0.25), 4),
            p50=round(_pct(vals, 0.50), 4),
            p75=round(_pct(vals, 0.75), 4),
            p90=round(_pct(vals, 0.90), 4),
            mean=round(sum(vals) / len(vals), 4),
            min=round(min(vals), 4),
            max=round(max(vals), 4),
        ))
    return rows


def _build_sector_rollups(deals: List[dict], min_deals: int = 5) -> List[SectorRollup]:
    bucket: Dict[str, List[dict]] = {}
    for d in deals:
        s = d.get("sector")
        if s:
            bucket.setdefault(s, []).append(d)
    rows = []
    for sector, ds in bucket.items():
        if len(ds) < min_deals:
            continue
        ev_m = [d.get("ev_mm") for d in ds if d.get("ev_mm")]
        eve = [d.get("ev_ebitda") for d in ds if d.get("ev_ebitda")]
        ev_r = [d.get("ev_mm") / d.get("revenue_mm")
                for d in ds if d.get("ev_mm") and d.get("revenue_mm")]
        em = [d.get("ebitda_margin") for d in ds if d.get("ebitda_margin")]
        moic = [d.get("moic") for d in ds if d.get("moic")]
        irr = [d.get("irr") for d in ds if d.get("irr")]
        rows.append(SectorRollup(
            sector=sector,
            deal_count=len(ds),
            median_ev_mm=round(statistics.median(ev_m) if ev_m else 0, 2),
            median_ev_ebitda=round(statistics.median(eve) if eve else 0, 2),
            median_ev_revenue=round(statistics.median(ev_r) if ev_r else 0, 2),
            median_ebitda_margin=round(statistics.median(em) if em else 0, 4),
            median_moic=round(statistics.median(moic) if moic else 0, 3),
            median_irr=round(statistics.median(irr) if irr else 0, 4),
        ))
    return sorted(rows, key=lambda r: r.deal_count, reverse=True)


def _build_size_rollups(deals: List[dict]) -> List[SizeBucketRollup]:
    buckets: Dict[str, List[dict]] = {
        "< $100M (small)": [],
        "$100-250M (mid)": [],
        "$250-500M (upper-mid)": [],
        "$500M-1B (large)": [],
        "$1B+ (mega)": [],
    }
    for d in deals:
        if d.get("ev_mm"):
            buckets[_size_bucket(d["ev_mm"])].append(d)
    rows = []
    for label, ds in buckets.items():
        if not ds:
            continue
        eve = [d.get("ev_ebitda") for d in ds if d.get("ev_ebitda")]
        em = [d.get("ebitda_margin") for d in ds if d.get("ebitda_margin")]
        moic = [d.get("moic") for d in ds if d.get("moic")]
        hy = [d.get("hold_years") for d in ds if d.get("hold_years")]
        rows.append(SizeBucketRollup(
            bucket=label,
            deal_count=len(ds),
            median_ev_ebitda=round(statistics.median(eve) if eve else 0, 2),
            median_ebitda_margin=round(statistics.median(em) if em else 0, 4),
            median_moic=round(statistics.median(moic) if moic else 0, 3),
            median_hold_years=round(statistics.median(hy) if hy else 0, 1),
        ))
    return rows


def _build_vintage_rollups(deals: List[dict]) -> List[VintageRollup]:
    bucket: Dict[int, List[dict]] = {}
    for d in deals:
        y = d.get("year") or 0
        if y:
            bucket.setdefault(y, []).append(d)
    rows = []
    for year in sorted(bucket.keys()):
        ds = bucket[year]
        if len(ds) < 5:
            continue
        eve = [d.get("ev_ebitda") for d in ds if d.get("ev_ebitda")]
        em = [d.get("ebitda_margin") for d in ds if d.get("ebitda_margin")]
        moic = [d.get("moic") for d in ds if d.get("moic")]
        rows.append(VintageRollup(
            year=year,
            deal_count=len(ds),
            median_ev_ebitda=round(statistics.median(eve) if eve else 0, 2),
            median_ebitda_margin=round(statistics.median(em) if em else 0, 4),
            median_moic=round(statistics.median(moic) if moic else 0, 3),
        ))
    return rows


def _build_comm_rollups(deals: List[dict]) -> List[CommPctRollup]:
    buckets: Dict[str, List[dict]] = {
        "Commercial-Light (<30%)": [],
        "Balanced (30-50%)": [],
        "Commercial-Heavy (>50%)": [],
    }
    for d in deals:
        cp = d.get("comm_pct") or 0
        if cp == 0:
            continue
        if cp < 0.30: buckets["Commercial-Light (<30%)"].append(d)
        elif cp < 0.50: buckets["Balanced (30-50%)"].append(d)
        else: buckets["Commercial-Heavy (>50%)"].append(d)
    rows = []
    for label, ds in buckets.items():
        if not ds:
            continue
        eve = [d.get("ev_ebitda") for d in ds if d.get("ev_ebitda")]
        em = [d.get("ebitda_margin") for d in ds if d.get("ebitda_margin")]
        moic = [d.get("moic") for d in ds if d.get("moic")]
        rows.append(CommPctRollup(
            comm_bucket=label,
            deal_count=len(ds),
            median_ev_ebitda=round(statistics.median(eve) if eve else 0, 2),
            median_ebitda_margin=round(statistics.median(em) if em else 0, 4),
            median_moic=round(statistics.median(moic) if moic else 0, 3),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_market_rates(
    sector: str = "",
    size_bucket: str = "",
    region: str = "",
) -> MarketRatesResult:
    corpus = _load_corpus()

    filtered = corpus
    if sector:
        filtered = [d for d in filtered if sector.lower() in str(d.get("sector") or "").lower()]
    if size_bucket:
        filtered = [d for d in filtered if _size_bucket(d.get("ev_mm") or 0) == size_bucket]
    if region:
        filtered = [d for d in filtered if str(d.get("region") or "").lower() == region.lower()]

    pct_rows = _build_percentile_rows(filtered)
    sector_rollups = _build_sector_rollups(filtered, min_deals=3 if (sector or size_bucket or region) else 5)
    size_rollups = _build_size_rollups(filtered)
    vintage_rollups = _build_vintage_rollups(filtered)
    comm_rollups = _build_comm_rollups(filtered)

    return MarketRatesResult(
        filter_sector=sector,
        filter_size_bucket=size_bucket,
        filter_region=region,
        total_matching=len(filtered),
        percentile_rows=pct_rows,
        sector_rollups=sector_rollups,
        size_rollups=size_rollups,
        vintage_rollups=vintage_rollups,
        comm_rollups=comm_rollups,
        corpus_deal_count=len(corpus),
    )
