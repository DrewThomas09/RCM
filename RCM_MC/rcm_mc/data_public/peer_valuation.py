"""Peer Valuation Analyzer — public trading comps + precedent transactions.

Standard bank/IB valuation framework:
- Trading comps (public healthcare companies by sector)
- Precedent transactions (from corpus; PE-backed sector deals)
- Football-field valuation range
- Implied EV/EBITDA, EV/Rev, P/E distributions
- Size premium / discount analysis
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Public comp universe (synthetic but realistic)
# ---------------------------------------------------------------------------

_TRADING_COMPS_BY_SECTOR = {
    "Physician Services": [
        ("HCA Healthcare (proxy)", 98_000, 12.5, 2.1, 21.5, 1.08, 0.15, "Large-cap"),
        ("Tenet Healthcare", 14_500, 9.8, 1.4, 16.5, 0.95, 0.08, "Mid-cap"),
        ("Universal Health Services", 12_800, 9.5, 1.5, 15.8, 1.02, 0.10, "Mid-cap"),
        ("Community Health Systems", 4_200, 8.2, 0.9, 10.2, 0.85, 0.05, "Small-cap"),
        ("US Physical Therapy", 1_800, 14.5, 2.5, 28.5, 1.20, 0.18, "Small-cap"),
    ],
    "Healthcare IT": [
        ("Veeva Systems", 32_000, 32.0, 15.2, 78.0, 1.45, 0.22, "Large-cap"),
        ("Cerner (proxy)", 28_500, 17.5, 4.8, 38.0, 1.28, 0.14, "Large-cap"),
        ("Evolent Health", 3_200, 20.5, 2.8, 45.0, 1.22, 0.10, "Mid-cap"),
        ("HealthEquity", 7_400, 22.0, 7.5, 52.0, 1.32, 0.18, "Mid-cap"),
        ("Phreesia", 1_900, 45.0, 4.2, 95.0, 1.18, 0.28, "Small-cap"),
    ],
    "Dialysis": [
        ("DaVita", 12_500, 8.5, 1.4, 14.2, 0.92, 0.08, "Large-cap"),
        ("Fresenius (proxy)", 18_000, 8.0, 1.1, 13.5, 0.88, 0.06, "Large-cap"),
        ("US Renal Care (proxy)", 4_500, 9.5, 1.6, 18.0, 0.95, 0.10, "Mid-cap"),
    ],
    "Home Health": [
        ("Amedisys", 4_800, 14.5, 2.2, 28.0, 1.08, 0.14, "Mid-cap"),
        ("Encompass Health (HH div)", 6_200, 11.5, 1.8, 22.0, 1.05, 0.12, "Mid-cap"),
        ("BrightSpring Health", 3_600, 10.2, 1.4, 18.5, 0.98, 0.08, "Mid-cap"),
        ("Enhabit", 1_200, 9.8, 1.2, 16.0, 0.92, 0.05, "Small-cap"),
    ],
    "Hospice": [
        ("Addus HomeCare", 1_700, 15.5, 2.4, 32.0, 1.10, 0.15, "Small-cap"),
        ("VITAS Healthcare (proxy)", 2_800, 12.8, 2.1, 26.0, 1.05, 0.12, "Small-cap"),
    ],
    "Pharmacy": [
        ("CVS Health", 78_000, 9.5, 0.6, 14.5, 0.78, 0.08, "Large-cap"),
        ("Walgreens Boots Alliance", 22_000, 8.2, 0.4, 11.5, 0.72, 0.05, "Large-cap"),
        ("BioPharma Specialty (proxy)", 8_500, 14.5, 1.8, 25.0, 1.05, 0.14, "Mid-cap"),
    ],
    "Behavioral Health": [
        ("Acadia Healthcare", 8_500, 11.5, 2.8, 22.0, 1.05, 0.12, "Mid-cap"),
        ("Universal Health Services (BH)", 12_800, 9.8, 1.6, 16.0, 1.02, 0.10, "Mid-cap"),
    ],
    "Diagnostic Imaging": [
        ("RadNet", 2_200, 12.8, 1.6, 28.0, 1.05, 0.12, "Small-cap"),
        ("Akumin", 950, 10.5, 1.1, 18.0, 0.92, 0.05, "Small-cap"),
    ],
    "Medical Devices": [
        ("Medtronic", 128_000, 16.5, 4.8, 28.0, 1.25, 0.20, "Large-cap"),
        ("Boston Scientific", 78_000, 18.5, 5.8, 35.0, 1.30, 0.22, "Large-cap"),
        ("Stryker", 105_000, 17.8, 5.2, 32.0, 1.28, 0.21, "Large-cap"),
        ("Baxter International", 22_000, 11.5, 2.4, 22.0, 1.05, 0.12, "Mid-cap"),
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TradingComp:
    company: str
    market_cap_mm: float
    ev_ebitda: float
    ev_revenue: float
    pe_ratio: float
    relative_valuation: float     # proxy for quality premium
    ebitda_margin: float
    size_category: str


@dataclass
class PrecedentTransaction:
    target_company: str
    acquirer: str
    year: int
    ev_mm: float
    ev_ebitda: float
    sector: str
    status: str


@dataclass
class ValuationRange:
    methodology: str
    low_ev_mm: float
    median_ev_mm: float
    high_ev_mm: float
    low_multiple: float
    median_multiple: float
    high_multiple: float
    basis: str


@dataclass
class SizePremium:
    size_bucket: str
    median_mult: float
    n_transactions: int
    premium_to_small: float


@dataclass
class PeerValuationResult:
    sector: str
    target_ebitda_mm: float
    target_revenue_mm: float
    trading_comps: List[TradingComp]
    precedent_transactions: List[PrecedentTransaction]
    valuation_ranges: List[ValuationRange]
    size_premiums: List[SizePremium]
    implied_ev_low_mm: float
    implied_ev_median_mm: float
    implied_ev_high_mm: float
    current_implied_mult: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 67):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _percentile(lst: List[float], p: float) -> float:
    if not lst:
        return 0
    s = sorted(lst)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _get_trading_comps(sector: str) -> List[TradingComp]:
    # Try exact match, then partial
    comps_raw = _TRADING_COMPS_BY_SECTOR.get(sector)
    if not comps_raw:
        # Try partial
        for key in _TRADING_COMPS_BY_SECTOR:
            if sector.lower() in key.lower() or key.lower() in sector.lower():
                comps_raw = _TRADING_COMPS_BY_SECTOR[key]
                break
    if not comps_raw:
        comps_raw = _TRADING_COMPS_BY_SECTOR["Physician Services"]

    return [TradingComp(
        company=c, market_cap_mm=mc, ev_ebitda=eb, ev_revenue=evr, pe_ratio=pe,
        relative_valuation=rv, ebitda_margin=em, size_category=sc,
    ) for c, mc, eb, evr, pe, rv, em, sc in comps_raw]


def _get_precedent_transactions(sector: str, corpus: List[dict]) -> List[PrecedentTransaction]:
    """Filter corpus for sector-matching deals."""
    matches = [
        d for d in corpus
        if d.get("sector") and (
            sector.lower() == d.get("sector", "").lower()
            or sector.lower() in d.get("sector", "").lower()
        )
        and d.get("ev_mm") and d.get("ev_ebitda")
    ]
    # Sort by year desc, take recent
    matches.sort(key=lambda d: -(d.get("year") or 0))
    rows = []
    for d in matches[:20]:
        rows.append(PrecedentTransaction(
            target_company=d.get("company_name", "—"),
            acquirer=d.get("buyer", "—"),
            year=d.get("year", 2020),
            ev_mm=round(d.get("ev_mm", 0), 1),
            ev_ebitda=round(d.get("ev_ebitda", 0), 2),
            sector=d.get("sector", sector),
            status=d.get("status", "—"),
        ))
    return rows


def _build_valuation_ranges(
    trading_comps: List[TradingComp], precedents: List[PrecedentTransaction],
    target_ebitda: float, target_revenue: float,
) -> List[ValuationRange]:
    rows = []

    # Trading comps: EV/EBITDA
    tc_ev_ebitda = [c.ev_ebitda for c in trading_comps]
    if tc_ev_ebitda:
        p25 = _percentile(tc_ev_ebitda, 25)
        p50 = _percentile(tc_ev_ebitda, 50)
        p75 = _percentile(tc_ev_ebitda, 75)
        rows.append(ValuationRange(
            methodology="Trading Comps — EV/EBITDA",
            low_ev_mm=round(target_ebitda * p25, 1),
            median_ev_mm=round(target_ebitda * p50, 1),
            high_ev_mm=round(target_ebitda * p75, 1),
            low_multiple=round(p25, 2),
            median_multiple=round(p50, 2),
            high_multiple=round(p75, 2),
            basis=f"Public comps P25/P50/P75 × {target_ebitda:.1f}M EBITDA",
        ))

    # Trading comps: EV/Revenue
    tc_ev_rev = [c.ev_revenue for c in trading_comps]
    if tc_ev_rev and target_revenue:
        p25 = _percentile(tc_ev_rev, 25)
        p50 = _percentile(tc_ev_rev, 50)
        p75 = _percentile(tc_ev_rev, 75)
        rows.append(ValuationRange(
            methodology="Trading Comps — EV/Revenue",
            low_ev_mm=round(target_revenue * p25, 1),
            median_ev_mm=round(target_revenue * p50, 1),
            high_ev_mm=round(target_revenue * p75, 1),
            low_multiple=round(p25, 2),
            median_multiple=round(p50, 2),
            high_multiple=round(p75, 2),
            basis=f"Public comps P25/P50/P75 × {target_revenue:.1f}M Revenue",
        ))

    # Precedent transactions
    pt_mults = [p.ev_ebitda for p in precedents]
    if pt_mults:
        p25 = _percentile(pt_mults, 25)
        p50 = _percentile(pt_mults, 50)
        p75 = _percentile(pt_mults, 75)
        rows.append(ValuationRange(
            methodology="Precedent Transactions",
            low_ev_mm=round(target_ebitda * p25, 1),
            median_ev_mm=round(target_ebitda * p50, 1),
            high_ev_mm=round(target_ebitda * p75, 1),
            low_multiple=round(p25, 2),
            median_multiple=round(p50, 2),
            high_multiple=round(p75, 2),
            basis=f"{len(precedents)} PE transactions × {target_ebitda:.1f}M EBITDA",
        ))

    # Apply PE control premium (typical 15-25% over public comps)
    if tc_ev_ebitda:
        p50 = _percentile(tc_ev_ebitda, 50)
        premium_low = p50 * 1.10
        premium_mid = p50 * 1.20
        premium_high = p50 * 1.30
        rows.append(ValuationRange(
            methodology="Comps + Control Premium",
            low_ev_mm=round(target_ebitda * premium_low, 1),
            median_ev_mm=round(target_ebitda * premium_mid, 1),
            high_ev_mm=round(target_ebitda * premium_high, 1),
            low_multiple=round(premium_low, 2),
            median_multiple=round(premium_mid, 2),
            high_multiple=round(premium_high, 2),
            basis="Median trading comp + 10/20/30% control premium",
        ))

    return rows


def _build_size_premiums(precedents: List[PrecedentTransaction]) -> List[SizePremium]:
    buckets = {
        "<$100M":    (0, 100),
        "$100-250M": (100, 250),
        "$250-500M": (250, 500),
        "$500M-1B":  (500, 1000),
        ">$1B":      (1000, 99999),
    }
    rows = []
    small_med = None
    for label, (low, high) in buckets.items():
        ms = [p.ev_ebitda for p in precedents if low <= p.ev_mm < high]
        if not ms:
            continue
        med = _percentile(ms, 50)
        if label == "<$100M":
            small_med = med
        premium = (med / small_med - 1) if small_med else 0
        rows.append(SizePremium(
            size_bucket=label,
            median_mult=round(med, 2),
            n_transactions=len(ms),
            premium_to_small=round(premium, 3),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_peer_valuation(
    sector: str = "Physician Services",
    target_ebitda_mm: float = 25.0,
    target_revenue_mm: float = 140.0,
) -> PeerValuationResult:
    corpus = _load_corpus()

    trading_comps = _get_trading_comps(sector)
    precedents = _get_precedent_transactions(sector, corpus)
    ranges = _build_valuation_ranges(trading_comps, precedents, target_ebitda_mm, target_revenue_mm)
    size_prems = _build_size_premiums(precedents)

    # Implied range: take min/max across all methodologies
    if ranges:
        implied_low = min(r.low_ev_mm for r in ranges)
        implied_mid = sum(r.median_ev_mm for r in ranges) / len(ranges)
        implied_high = max(r.high_ev_mm for r in ranges)
    else:
        implied_low = implied_mid = implied_high = 0

    current_mult = implied_mid / target_ebitda_mm if target_ebitda_mm else 0

    return PeerValuationResult(
        sector=sector,
        target_ebitda_mm=round(target_ebitda_mm, 2),
        target_revenue_mm=round(target_revenue_mm, 2),
        trading_comps=trading_comps,
        precedent_transactions=precedents,
        valuation_ranges=ranges,
        size_premiums=size_prems,
        implied_ev_low_mm=round(implied_low, 1),
        implied_ev_median_mm=round(implied_mid, 1),
        implied_ev_high_mm=round(implied_high, 1),
        current_implied_mult=round(current_mult, 2),
        corpus_deal_count=len(corpus),
    )
