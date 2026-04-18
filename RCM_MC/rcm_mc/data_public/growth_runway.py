"""Growth Runway Analyzer — TAM/SAM/SOM, penetration curve, share gain economics.

Quantifies organic growth potential:
- TAM (total addressable market) by sector
- SAM (serviceable addressable) = within footprint
- SOM (serviceable obtainable) = realistic share capture
- Current penetration & gap to target
- S-curve adoption / share dynamics
- Growth driver decomposition (volume × price × mix)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector TAM benchmarks ($B US healthcare)
# ---------------------------------------------------------------------------

_SECTOR_TAM = {
    "Physician Services":    {"tam_b": 420, "growth_pct": 0.035, "fragmentation_hhi": 180},
    "Primary Care":          {"tam_b": 285, "growth_pct": 0.045, "fragmentation_hhi": 220},
    "Dermatology":           {"tam_b": 22, "growth_pct": 0.065, "fragmentation_hhi": 350},
    "Ophthalmology":         {"tam_b": 38, "growth_pct": 0.042, "fragmentation_hhi": 420},
    "Orthopedics":           {"tam_b": 62, "growth_pct": 0.048, "fragmentation_hhi": 380},
    "Gastroenterology":      {"tam_b": 28, "growth_pct": 0.055, "fragmentation_hhi": 280},
    "Cardiology":            {"tam_b": 55, "growth_pct": 0.058, "fragmentation_hhi": 360},
    "Oncology":              {"tam_b": 85, "growth_pct": 0.075, "fragmentation_hhi": 320},
    "Urgent Care":           {"tam_b": 48, "growth_pct": 0.082, "fragmentation_hhi": 450},
    "ASC":                   {"tam_b": 38, "growth_pct": 0.072, "fragmentation_hhi": 520},
    "Dental":                {"tam_b": 162, "growth_pct": 0.045, "fragmentation_hhi": 180},
    "Behavioral Health":     {"tam_b": 82, "growth_pct": 0.095, "fragmentation_hhi": 220},
    "ABA Therapy":           {"tam_b": 12, "growth_pct": 0.145, "fragmentation_hhi": 280},
    "Home Health":           {"tam_b": 145, "growth_pct": 0.062, "fragmentation_hhi": 320},
    "Hospice":               {"tam_b": 24, "growth_pct": 0.058, "fragmentation_hhi": 450},
    "Dialysis":              {"tam_b": 45, "growth_pct": 0.035, "fragmentation_hhi": 3200},
    "Pharmacy":              {"tam_b": 440, "growth_pct": 0.042, "fragmentation_hhi": 1800},
    "Specialty Pharmacy":    {"tam_b": 185, "growth_pct": 0.088, "fragmentation_hhi": 1200},
    "Physical Therapy":      {"tam_b": 38, "growth_pct": 0.055, "fragmentation_hhi": 420},
    "Fertility":             {"tam_b": 8.5, "growth_pct": 0.092, "fragmentation_hhi": 380},
    "Radiology":             {"tam_b": 42, "growth_pct": 0.038, "fragmentation_hhi": 480},
    "Laboratory":            {"tam_b": 85, "growth_pct": 0.045, "fragmentation_hhi": 2200},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MarketSize:
    level: str                  # "TAM", "SAM", "SOM"
    size_mm: float
    current_capture_pct: float
    headroom_mm: float
    definition: str


@dataclass
class GrowthDriver:
    driver: str
    current_contrib_pct: float
    potential_contrib_pct: float
    implied_revenue_uplift_mm: float
    timeline_years: float
    confidence: str


@dataclass
class PenetrationYear:
    year: int
    market_share_pct: float
    revenue_mm: float
    incremental_rev_mm: float
    cumulative_capture_mm: float


@dataclass
class ComparableExpansion:
    sector: str
    median_cagr: float
    top_quartile_cagr: float
    typical_share_shift_pct: float
    tam_headroom_pct: float


@dataclass
class GrowthRunwayResult:
    sector: str
    tam_b: float
    sam_mm: float
    som_mm: float
    current_revenue_mm: float
    current_share_pct: float
    target_share_pct: float
    implied_terminal_revenue_mm: float
    market_growth_pct: float
    market_sizes: List[MarketSize]
    growth_drivers: List[GrowthDriver]
    penetration_curve: List[PenetrationYear]
    comparables: List[ComparableExpansion]
    total_addressable_upside_mm: float
    moic_lift_from_growth: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 70):
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


def _sector_tam(sector: str) -> Dict:
    return _SECTOR_TAM.get(sector, _SECTOR_TAM["Physician Services"])


def _build_market_sizes(
    tam_b: float, revenue_mm: float, footprint_pct: float, share_of_footprint: float,
) -> List[MarketSize]:
    tam_mm = tam_b * 1000
    sam_mm = tam_mm * footprint_pct
    som_mm = sam_mm * 0.18   # typically 18% obtainable share
    current_share_tam = revenue_mm / tam_mm if tam_mm else 0
    current_share_sam = revenue_mm / sam_mm if sam_mm else 0
    current_share_som = revenue_mm / som_mm if som_mm else 0

    return [
        MarketSize("TAM (Total Addressable)", round(tam_mm, 0),
                   round(current_share_tam * 100, 3),
                   round(tam_mm - revenue_mm, 0),
                   "Full US market across all demographics, geographies"),
        MarketSize("SAM (Serviceable Addressable)", round(sam_mm, 0),
                   round(current_share_sam * 100, 2),
                   round(sam_mm - revenue_mm, 0),
                   f"Within current regional footprint (~{footprint_pct * 100:.0f}% of TAM)"),
        MarketSize("SOM (Serviceable Obtainable)", round(som_mm, 0),
                   round(current_share_som * 100, 1),
                   round(som_mm - revenue_mm, 0),
                   "Realistic 5-year capture target (18% of SAM)"),
    ]


def _build_drivers(
    revenue_mm: float, market_growth: float, current_share: float, target_share: float,
) -> List[GrowthDriver]:
    rows = []

    # Market growth (organic)
    mkt_uplift = revenue_mm * market_growth * 5   # 5-year compound
    rows.append(GrowthDriver(
        driver="Market Growth (tailwind)",
        current_contrib_pct=round(market_growth, 3),
        potential_contrib_pct=round(market_growth, 3),
        implied_revenue_uplift_mm=round(mkt_uplift, 2),
        timeline_years=5.0,
        confidence="high",
    ))

    # Share expansion
    share_gain = target_share - current_share
    share_uplift = revenue_mm * (share_gain / current_share) if current_share else 0
    rows.append(GrowthDriver(
        driver="Share Gain (vs competitors)",
        current_contrib_pct=round(current_share, 4),
        potential_contrib_pct=round(target_share, 4),
        implied_revenue_uplift_mm=round(share_uplift, 2),
        timeline_years=4.0,
        confidence="medium",
    ))

    # New services / ancillary
    rows.append(GrowthDriver(
        driver="Ancillary / New Service Lines",
        current_contrib_pct=0.05,
        potential_contrib_pct=0.12,
        implied_revenue_uplift_mm=round(revenue_mm * 0.07 * 3, 2),
        timeline_years=3.0,
        confidence="medium",
    ))

    # Price / payer mix
    rows.append(GrowthDriver(
        driver="Price / Payer Mix Shift",
        current_contrib_pct=0.02,
        potential_contrib_pct=0.05,
        implied_revenue_uplift_mm=round(revenue_mm * 0.03 * 5, 2),
        timeline_years=4.0,
        confidence="high",
    ))

    # Geographic expansion
    rows.append(GrowthDriver(
        driver="Geographic Expansion (de novo)",
        current_contrib_pct=0.0,
        potential_contrib_pct=0.35,
        implied_revenue_uplift_mm=round(revenue_mm * 0.35, 2),
        timeline_years=5.0,
        confidence="medium",
    ))

    # M&A / bolt-on
    rows.append(GrowthDriver(
        driver="M&A / Bolt-on Acquisition",
        current_contrib_pct=0.0,
        potential_contrib_pct=0.80,
        implied_revenue_uplift_mm=round(revenue_mm * 0.80, 2),
        timeline_years=5.0,
        confidence="high",
    ))

    # Value-based care / risk
    rows.append(GrowthDriver(
        driver="Value-Based Care / Risk Contracts",
        current_contrib_pct=0.0,
        potential_contrib_pct=0.08,
        implied_revenue_uplift_mm=round(revenue_mm * 0.08, 2),
        timeline_years=4.0,
        confidence="low",
    ))

    return rows


def _build_penetration_curve(
    current_revenue: float, market_growth: float, current_share: float,
    target_share: float, years: int = 10,
) -> List[PenetrationYear]:
    rows = []
    # S-curve share gain (smooth transition)
    prev_rev = current_revenue
    cum_capture = 0
    for y in range(1, years + 1):
        # Share follows S-curve: slow start, fast middle, plateau
        progress = y / years
        s_curve = (3 * progress ** 2 - 2 * progress ** 3)
        share = current_share + (target_share - current_share) * s_curve
        # Market size grew
        # Assume market capture against growing TAM at market_growth rate
        share_adj = share / current_share if current_share else 1
        rev = current_revenue * ((1 + market_growth) ** y) * share_adj
        incr = rev - prev_rev
        cum_capture += incr
        prev_rev = rev

        rows.append(PenetrationYear(
            year=y,
            market_share_pct=round(share * 100, 4),
            revenue_mm=round(rev, 2),
            incremental_rev_mm=round(incr, 2),
            cumulative_capture_mm=round(cum_capture, 2),
        ))
    return rows


def _build_comparables(sector: str) -> List[ComparableExpansion]:
    # Typical healthcare PE expansion stories
    return [
        ComparableExpansion("US Dermatology Partners", 0.155, 0.225, 0.085, 0.86),
        ComparableExpansion("MedExpress (Urgent Care)", 0.182, 0.285, 0.065, 0.79),
        ComparableExpansion("Epiphany Dermatology", 0.118, 0.185, 0.042, 0.92),
        ComparableExpansion("One Medical (Primary Care)", 0.145, 0.225, 0.038, 0.88),
        ComparableExpansion("BayMark (Addiction Treatment)", 0.168, 0.245, 0.095, 0.78),
        ComparableExpansion("Vivo Capital Healthcare", 0.128, 0.195, 0.055, 0.82),
        ComparableExpansion("Community-Based Platforms", 0.082, 0.145, 0.032, 0.88),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_growth_runway(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    footprint_pct: float = 0.02,        # share of TAM in geographic footprint
    target_share_of_footprint: float = 0.035,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> GrowthRunwayResult:
    corpus = _load_corpus()

    sector_data = _sector_tam(sector)
    tam_b = sector_data["tam_b"]
    market_growth = sector_data["growth_pct"]

    sam_mm = tam_b * 1000 * footprint_pct
    som_mm = sam_mm * 0.18
    current_share_sam = revenue_mm / sam_mm if sam_mm else 0
    target_share_sam = target_share_of_footprint

    sizes = _build_market_sizes(tam_b, revenue_mm, footprint_pct, current_share_sam)
    drivers = _build_drivers(revenue_mm, market_growth, current_share_sam, target_share_sam)
    penetration = _build_penetration_curve(revenue_mm, market_growth, current_share_sam, target_share_sam, 10)
    comps = _build_comparables(sector)

    terminal_rev = penetration[-1].revenue_mm if penetration else revenue_mm
    total_upside = terminal_rev - revenue_mm
    # MOIC lift estimate: uplift × margin × exit mult / equity
    equity_assumed = revenue_mm * ebitda_margin * 11 * 0.45    # placeholder
    ebitda_uplift = total_upside * ebitda_margin
    ev_uplift = ebitda_uplift * exit_multiple
    moic_lift = ev_uplift / equity_assumed if equity_assumed else 0

    return GrowthRunwayResult(
        sector=sector,
        tam_b=round(tam_b, 1),
        sam_mm=round(sam_mm, 0),
        som_mm=round(som_mm, 0),
        current_revenue_mm=round(revenue_mm, 1),
        current_share_pct=round(current_share_sam * 100, 3),
        target_share_pct=round(target_share_sam * 100, 2),
        implied_terminal_revenue_mm=round(terminal_rev, 1),
        market_growth_pct=round(market_growth, 4),
        market_sizes=sizes,
        growth_drivers=drivers,
        penetration_curve=penetration,
        comparables=comps,
        total_addressable_upside_mm=round(total_upside, 1),
        moic_lift_from_growth=round(moic_lift, 2),
        corpus_deal_count=len(corpus),
    )
