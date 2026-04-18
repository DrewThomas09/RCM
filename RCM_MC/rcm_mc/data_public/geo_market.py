"""Geographic Market Analyzer — CBSA-level white-space and market-entry scoring.

Scores markets (Core-Based Statistical Areas) by:
- Demographics: population, 65+ share, income
- Competitive density (HHI)
- Physicians per 1K population
- Payer mix favorability
- Reimbursement index
- Market growth
- White-space attractiveness (composite 0-100)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Representative CBSA data (synthetic but realistic)
# ---------------------------------------------------------------------------

_CBSAS = [
    {"cbsa": "New York-Newark-Jersey City, NY-NJ-PA", "pop_k": 19500, "pct_65plus": 16.2,
     "median_income_k": 89, "pcp_per_1k": 2.8, "hhi": 1650, "comm_pct": 0.58,
     "mcr_index": 1.12, "growth_5yr": 0.028},
    {"cbsa": "Los Angeles-Long Beach-Anaheim, CA", "pop_k": 13200, "pct_65plus": 14.8,
     "median_income_k": 82, "pcp_per_1k": 2.5, "hhi": 1420, "comm_pct": 0.55,
     "mcr_index": 1.08, "growth_5yr": 0.018},
    {"cbsa": "Chicago-Naperville-Elgin, IL-IN-WI", "pop_k": 9500, "pct_65plus": 15.5,
     "median_income_k": 76, "pcp_per_1k": 2.4, "hhi": 1580, "comm_pct": 0.54,
     "mcr_index": 0.98, "growth_5yr": 0.008},
    {"cbsa": "Dallas-Fort Worth-Arlington, TX", "pop_k": 7700, "pct_65plus": 12.5,
     "median_income_k": 78, "pcp_per_1k": 1.9, "hhi": 1250, "comm_pct": 0.63,
     "mcr_index": 0.92, "growth_5yr": 0.098},
    {"cbsa": "Houston-The Woodlands-Sugar Land, TX", "pop_k": 7200, "pct_65plus": 12.8,
     "median_income_k": 74, "pcp_per_1k": 2.0, "hhi": 1380, "comm_pct": 0.61,
     "mcr_index": 0.90, "growth_5yr": 0.082},
    {"cbsa": "Washington-Arlington-Alexandria, DC-VA-MD", "pop_k": 6400, "pct_65plus": 13.5,
     "median_income_k": 112, "pcp_per_1k": 3.1, "hhi": 1520, "comm_pct": 0.62,
     "mcr_index": 1.18, "growth_5yr": 0.034},
    {"cbsa": "Miami-Fort Lauderdale-Pompano Beach, FL", "pop_k": 6200, "pct_65plus": 19.2,
     "median_income_k": 68, "pcp_per_1k": 2.6, "hhi": 1340, "comm_pct": 0.48,
     "mcr_index": 0.94, "growth_5yr": 0.055},
    {"cbsa": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD", "pop_k": 6100, "pct_65plus": 17.0,
     "median_income_k": 78, "pcp_per_1k": 2.9, "hhi": 1680, "comm_pct": 0.56,
     "mcr_index": 1.05, "growth_5yr": 0.012},
    {"cbsa": "Atlanta-Sandy Springs-Alpharetta, GA", "pop_k": 6100, "pct_65plus": 13.2,
     "median_income_k": 72, "pcp_per_1k": 2.1, "hhi": 1290, "comm_pct": 0.58,
     "mcr_index": 0.88, "growth_5yr": 0.072},
    {"cbsa": "Phoenix-Mesa-Chandler, AZ", "pop_k": 5000, "pct_65plus": 17.8,
     "median_income_k": 70, "pcp_per_1k": 2.0, "hhi": 1150, "comm_pct": 0.50,
     "mcr_index": 0.85, "growth_5yr": 0.108},
    {"cbsa": "Boston-Cambridge-Newton, MA-NH", "pop_k": 4900, "pct_65plus": 16.8,
     "median_income_k": 96, "pcp_per_1k": 3.4, "hhi": 1850, "comm_pct": 0.64,
     "mcr_index": 1.15, "growth_5yr": 0.022},
    {"cbsa": "San Francisco-Oakland-Berkeley, CA", "pop_k": 4700, "pct_65plus": 15.5,
     "median_income_k": 125, "pcp_per_1k": 3.0, "hhi": 1420, "comm_pct": 0.62,
     "mcr_index": 1.22, "growth_5yr": 0.015},
    {"cbsa": "Riverside-San Bernardino-Ontario, CA", "pop_k": 4600, "pct_65plus": 14.5,
     "median_income_k": 69, "pcp_per_1k": 1.7, "hhi": 1180, "comm_pct": 0.52,
     "mcr_index": 0.86, "growth_5yr": 0.042},
    {"cbsa": "Detroit-Warren-Dearborn, MI", "pop_k": 4400, "pct_65plus": 17.5,
     "median_income_k": 63, "pcp_per_1k": 2.5, "hhi": 1620, "comm_pct": 0.52,
     "mcr_index": 0.88, "growth_5yr": -0.002},
    {"cbsa": "Seattle-Tacoma-Bellevue, WA", "pop_k": 4000, "pct_65plus": 14.2,
     "median_income_k": 94, "pcp_per_1k": 2.8, "hhi": 1540, "comm_pct": 0.60,
     "mcr_index": 1.10, "growth_5yr": 0.058},
    {"cbsa": "Minneapolis-St. Paul-Bloomington, MN-WI", "pop_k": 3700, "pct_65plus": 15.2,
     "median_income_k": 85, "pcp_per_1k": 2.7, "hhi": 2100, "comm_pct": 0.65,
     "mcr_index": 1.04, "growth_5yr": 0.022},
    {"cbsa": "Tampa-St. Petersburg-Clearwater, FL", "pop_k": 3300, "pct_65plus": 20.5,
     "median_income_k": 62, "pcp_per_1k": 2.5, "hhi": 1240, "comm_pct": 0.44,
     "mcr_index": 0.92, "growth_5yr": 0.082},
    {"cbsa": "San Diego-Chula Vista-Carlsbad, CA", "pop_k": 3300, "pct_65plus": 15.0,
     "median_income_k": 88, "pcp_per_1k": 2.8, "hhi": 1480, "comm_pct": 0.58,
     "mcr_index": 1.05, "growth_5yr": 0.038},
    {"cbsa": "Denver-Aurora-Lakewood, CO", "pop_k": 3000, "pct_65plus": 13.5,
     "median_income_k": 86, "pcp_per_1k": 2.6, "hhi": 1320, "comm_pct": 0.61,
     "mcr_index": 1.00, "growth_5yr": 0.062},
    {"cbsa": "Charlotte-Concord-Gastonia, NC-SC", "pop_k": 2800, "pct_65plus": 14.2,
     "median_income_k": 68, "pcp_per_1k": 2.0, "hhi": 1340, "comm_pct": 0.58,
     "mcr_index": 0.90, "growth_5yr": 0.088},
    {"cbsa": "Portland-Vancouver-Hillsboro, OR-WA", "pop_k": 2500, "pct_65plus": 15.4,
     "median_income_k": 80, "pcp_per_1k": 2.8, "hhi": 1720, "comm_pct": 0.58,
     "mcr_index": 0.96, "growth_5yr": 0.048},
    {"cbsa": "Nashville-Davidson-Murfreesboro, TN", "pop_k": 2100, "pct_65plus": 14.0,
     "median_income_k": 70, "pcp_per_1k": 2.3, "hhi": 1290, "comm_pct": 0.56,
     "mcr_index": 0.88, "growth_5yr": 0.092},
    {"cbsa": "Las Vegas-Henderson-Paradise, NV", "pop_k": 2400, "pct_65plus": 15.0,
     "median_income_k": 65, "pcp_per_1k": 1.7, "hhi": 1080, "comm_pct": 0.48,
     "mcr_index": 0.85, "growth_5yr": 0.070},
    {"cbsa": "Austin-Round Rock-Georgetown, TX", "pop_k": 2400, "pct_65plus": 11.8,
     "median_income_k": 84, "pcp_per_1k": 2.2, "hhi": 1140, "comm_pct": 0.62,
     "mcr_index": 0.92, "growth_5yr": 0.155},
    {"cbsa": "Raleigh-Cary, NC", "pop_k": 1500, "pct_65plus": 13.0,
     "median_income_k": 82, "pcp_per_1k": 2.5, "hhi": 1420, "comm_pct": 0.60,
     "mcr_index": 0.94, "growth_5yr": 0.112},
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MarketRow:
    cbsa: str
    population_k: float
    pct_65plus: float
    median_income_k: float
    pcp_per_1k: float
    hhi: int
    comm_pct: float
    medicare_index: float
    growth_5yr_pct: float
    white_space_score: float
    tier: str                         # "Priority", "Watch", "Secondary", "Avoid"


@dataclass
class MarketComponent:
    dimension: str
    value: float
    normalized_score: float           # 0-100
    weight: float
    contribution: float


@dataclass
class EntryScenario:
    cbsa: str
    entry_strategy: str               # "De novo", "Acquisition", "JV"
    year1_revenue_mm: float
    year3_revenue_mm: float
    year5_revenue_mm: float
    capex_mm: float
    payback_years: float
    expected_moic: float


@dataclass
class CompetitiveTier:
    tier: str
    cbsa_count: int
    avg_population_k: float
    avg_hhi: int
    avg_growth: float
    recommended_action: str


@dataclass
class GeoMarketResult:
    sector: str
    markets: List[MarketRow]
    components: List[MarketComponent]
    entry_scenarios: List[EntryScenario]
    tiers: List[CompetitiveTier]
    priority_markets: int
    watch_markets: int
    secondary_markets: int
    avoid_markets: int
    total_addressable_pop_mm: float
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


def _normalize(val: float, low: float, high: float) -> float:
    if high <= low:
        return 50
    return max(0, min(100, (val - low) / (high - low) * 100))


def _score_market(m: Dict, sector: str) -> (float, str):
    """Composite white-space score 0-100."""
    # Growth (higher = better)
    growth_score = _normalize(m["growth_5yr"], -0.02, 0.15)
    # Density HHI (lower = better for white-space)
    hhi_score = _normalize(3000 - m["hhi"], 0, 2500)
    # Reimbursement (higher = better)
    mcr_score = _normalize(m["mcr_index"], 0.80, 1.25)
    # Commercial mix (higher = better for most sectors)
    comm_score = _normalize(m["comm_pct"], 0.40, 0.70)
    # Demographic fit (depends on sector)
    if sector in ("Senior Primary Care", "Dialysis", "Home Health", "Hospice", "Oncology"):
        demo_score = _normalize(m["pct_65plus"], 10, 22)
    else:
        demo_score = _normalize(100 - m["pct_65plus"], 78, 95)    # younger markets for most sectors

    # Income (higher = better for commercial-heavy sectors)
    income_score = _normalize(m["median_income_k"], 60, 120)

    # PCP density: for white-space, lower is better
    pcp_score = _normalize(4 - m["pcp_per_1k"], 0, 3)

    composite = (
        growth_score * 0.22 +
        hhi_score * 0.14 +
        mcr_score * 0.12 +
        comm_score * 0.12 +
        demo_score * 0.14 +
        income_score * 0.12 +
        pcp_score * 0.14
    )

    if composite >= 68:
        tier = "Priority"
    elif composite >= 55:
        tier = "Watch"
    elif composite >= 40:
        tier = "Secondary"
    else:
        tier = "Avoid"

    return round(composite, 1), tier


def _build_markets(sector: str) -> List[MarketRow]:
    rows = []
    for m in _CBSAS:
        score, tier = _score_market(m, sector)
        rows.append(MarketRow(
            cbsa=m["cbsa"],
            population_k=m["pop_k"],
            pct_65plus=m["pct_65plus"],
            median_income_k=m["median_income_k"],
            pcp_per_1k=m["pcp_per_1k"],
            hhi=m["hhi"],
            comm_pct=m["comm_pct"],
            medicare_index=m["mcr_index"],
            growth_5yr_pct=m["growth_5yr"],
            white_space_score=score,
            tier=tier,
        ))
    return sorted(rows, key=lambda r: -r.white_space_score)


def _build_components() -> List[MarketComponent]:
    return [
        MarketComponent("Market Growth (5yr CAGR)", 0.058, 68, 0.22, round(68 * 0.22, 1)),
        MarketComponent("Competitive Density (HHI)", 1420, 56, 0.14, round(56 * 0.14, 1)),
        MarketComponent("Reimbursement Index", 1.02, 65, 0.12, round(65 * 0.12, 1)),
        MarketComponent("Commercial Payer Mix", 0.58, 60, 0.12, round(60 * 0.12, 1)),
        MarketComponent("Demographic Fit", 0.145, 55, 0.14, round(55 * 0.14, 1)),
        MarketComponent("Median Household Income", 81, 57, 0.12, round(57 * 0.12, 1)),
        MarketComponent("PCP Density (inverse)", 2.4, 52, 0.14, round(52 * 0.14, 1)),
    ]


def _build_entry_scenarios(markets: List[MarketRow]) -> List[EntryScenario]:
    scenarios = []
    top = [m for m in markets if m.tier in ("Priority", "Watch")][:5]
    for m in top:
        # Three strategies per top market
        pop_factor = m.population_k / 5000      # normalize to reference 5M population
        # De novo
        scenarios.append(EntryScenario(
            cbsa=m.cbsa,
            entry_strategy="De novo (4 sites over 3 yrs)",
            year1_revenue_mm=round(pop_factor * 3.5, 2),
            year3_revenue_mm=round(pop_factor * 14.0, 2),
            year5_revenue_mm=round(pop_factor * 24.5, 2),
            capex_mm=round(pop_factor * 3.6, 2),
            payback_years=round(3.2, 1),
            expected_moic=round(2.3 + (m.white_space_score - 55) / 30, 2),
        ))
        # Acquisition
        scenarios.append(EntryScenario(
            cbsa=m.cbsa,
            entry_strategy="Acquisition (platform)",
            year1_revenue_mm=round(pop_factor * 22.0, 2),
            year3_revenue_mm=round(pop_factor * 32.0, 2),
            year5_revenue_mm=round(pop_factor * 48.0, 2),
            capex_mm=round(pop_factor * 95.0, 2),
            payback_years=round(4.8, 1),
            expected_moic=round(2.6 + (m.white_space_score - 55) / 28, 2),
        ))
    return scenarios[:10]    # cap for display


def _build_tiers(markets: List[MarketRow]) -> List[CompetitiveTier]:
    tier_map: Dict[str, List[MarketRow]] = {}
    for m in markets:
        tier_map.setdefault(m.tier, []).append(m)

    actions = {
        "Priority": "Active pursuit — lead with best-of-channel team",
        "Watch": "Monitor quarterly; platform acq may unlock",
        "Secondary": "Opportunistic only; high bar for capital",
        "Avoid": "Do not pursue de novo; fix-it bolt-on only",
    }

    rows = []
    for tier in ["Priority", "Watch", "Secondary", "Avoid"]:
        ms = tier_map.get(tier, [])
        if not ms:
            continue
        rows.append(CompetitiveTier(
            tier=tier,
            cbsa_count=len(ms),
            avg_population_k=round(sum(m.population_k for m in ms) / len(ms), 0),
            avg_hhi=int(sum(m.hhi for m in ms) / len(ms)),
            avg_growth=round(sum(m.growth_5yr_pct for m in ms) / len(ms), 4),
            recommended_action=actions[tier],
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_geo_market(
    sector: str = "Physician Services",
) -> GeoMarketResult:
    corpus = _load_corpus()

    markets = _build_markets(sector)
    components = _build_components()
    scenarios = _build_entry_scenarios(markets)
    tiers = _build_tiers(markets)

    priority = sum(1 for m in markets if m.tier == "Priority")
    watch = sum(1 for m in markets if m.tier == "Watch")
    secondary = sum(1 for m in markets if m.tier == "Secondary")
    avoid = sum(1 for m in markets if m.tier == "Avoid")

    total_pop = sum(m.population_k for m in markets if m.tier in ("Priority", "Watch")) / 1000

    return GeoMarketResult(
        sector=sector,
        markets=markets,
        components=components,
        entry_scenarios=scenarios,
        tiers=tiers,
        priority_markets=priority,
        watch_markets=watch,
        secondary_markets=secondary,
        avoid_markets=avoid,
        total_addressable_pop_mm=round(total_pop, 1),
        corpus_deal_count=len(corpus),
    )
