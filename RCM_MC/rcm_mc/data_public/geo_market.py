"""ILLUSTRATIVE — Geographic Market Analyzer over a curated synthetic CBSA panel.

Do not quote these outputs in IC documents: the CBSA metrics below are
curated to be realistic but are NOT sourced Census/CMS values — the
deliverable is the scoring methodology. For real metro/county
demographics use :mod:`rcm_mc.data.cbsa_demographics` and
:mod:`rcm_mc.data.county_demographics`.

Scores markets (Core-Based Statistical Areas) by:
- Demographics: population, 65+ share, income
- Competitive density (HHI)
- Physicians per 1K population
- Payer mix favorability
- Reimbursement index
- Market growth
- White-space attractiveness (composite 0-100)

The component panel is derived from the same ``_score_market`` pass
that scores the markets (panel-average normalized score × the actual
weight, summing to the panel-average composite). An earlier version
returned seven hardcoded rows that claimed to decompose the composite
while being disconnected from it — fake even by illustrative standards.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


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
    entry_strategy: str               # "De novo" | "Acquisition (platform)"
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
    # Machine-readable honesty flag: the CBSA panel is curated synthetic
    # data, so any consumer beyond the labelled UI page (exports,
    # assistant context, future APIs) inherits the caveat instead of
    # unlabelled numbers.
    is_illustrative: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    """Delegate to the canonical registry-driven loader.

    Five sibling market models each hand-rolled an ``importlib`` loop
    over divergent ``range()``s, so the same corpus read as five
    different "Corpus Deals" counts depending on the page and silently
    drifted stale as seed files were added. The registry enumerates
    every seed group, so all five now agree and track new seeds.
    """
    from rcm_mc.data_public.corpus_loader import load_corpus_deals
    return load_corpus_deals("all")


def _normalize(val: float, low: float, high: float) -> float:
    if high <= low:
        return 50
    return max(0, min(100, (val - low) / (high - low) * 100))


# (dimension label, weight, raw-metric key) — single source of truth for
# both the market scores and the component decomposition panel, so the
# two can never diverge again.
_SCORE_DIMENSIONS: List[Tuple[str, float, str]] = [
    ("Market Growth (5yr CAGR)", 0.22, "growth_5yr"),
    ("Competitive Density (HHI)", 0.14, "hhi"),
    ("Reimbursement Index", 0.12, "mcr_index"),
    ("Commercial Payer Mix", 0.12, "comm_pct"),
    ("Demographic Fit", 0.14, "pct_65plus"),
    ("Median Household Income", 0.12, "median_income_k"),
    ("PCP Density (inverse)", 0.14, "pcp_per_1k"),
]

# Sectors whose demographic fit favors 65+ share instead of younger mix.
_SENIOR_SECTORS = (
    "Senior Primary Care", "Dialysis", "Home Health", "Hospice", "Oncology",
)


def _dimension_scores(m: Dict, sector: str) -> Dict[str, float]:
    """Per-dimension normalized scores (0-100) for one market.

    Split out of ``_score_market`` so the component panel decomposes
    the same numbers the composite is built from.
    """
    if sector in _SENIOR_SECTORS:
        demo_score = _normalize(m["pct_65plus"], 10, 22)
    else:
        demo_score = _normalize(100 - m["pct_65plus"], 78, 95)  # younger markets
    return {
        # Growth (higher = better)
        "Market Growth (5yr CAGR)": _normalize(m["growth_5yr"], -0.02, 0.15),
        # Density HHI (lower = better for white-space)
        "Competitive Density (HHI)": _normalize(3000 - m["hhi"], 0, 2500),
        # Reimbursement (higher = better)
        "Reimbursement Index": _normalize(m["mcr_index"], 0.80, 1.25),
        # Commercial mix (higher = better for most sectors)
        "Commercial Payer Mix": _normalize(m["comm_pct"], 0.40, 0.70),
        # Demographic fit (depends on sector)
        "Demographic Fit": demo_score,
        # Income (higher = better for commercial-heavy sectors)
        "Median Household Income": _normalize(m["median_income_k"], 60, 120),
        # PCP density: for white-space, lower is better
        "PCP Density (inverse)": _normalize(4 - m["pcp_per_1k"], 0, 3),
    }


def _score_market(m: Dict, sector: str) -> Tuple[float, str]:
    """Composite white-space score 0-100."""
    scores = _dimension_scores(m, sector)
    composite = sum(
        scores[label] * weight for label, weight, _ in _SCORE_DIMENSIONS
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


def _build_components(sector: str) -> List[MarketComponent]:
    """Decompose the composite from the real scoring pass.

    Each row is the panel-average raw metric, the panel-average
    normalized score for that dimension, the actual weight, and the
    resulting contribution — so contributions sum (± rounding) to the
    panel-average white-space composite the markets table shows.
    """
    n = len(_CBSAS)
    if n == 0:
        return []
    per_market = [_dimension_scores(m, sector) for m in _CBSAS]
    rows = []
    for label, weight, metric_key in _SCORE_DIMENSIONS:
        avg_value = sum(m[metric_key] for m in _CBSAS) / n
        avg_score = sum(scores[label] for scores in per_market) / n
        rows.append(MarketComponent(
            dimension=label,
            value=round(avg_value, 3),
            normalized_score=round(avg_score, 1),
            weight=weight,
            contribution=round(avg_score * weight, 1),
        ))
    return rows


# Contribution / EBITDA margin assumptions used to derive payback from
# each scenario's own capital and revenue ramp (illustrative but
# internally consistent — an earlier version showed constant 3.2/4.8yr
# paybacks disconnected from the scenario economics):
#   De novo   — 20% site-level contribution margin on ramped revenue.
#   Acquisition — 22% platform EBITDA margin; payback on the purchase
#   price in EBITDA-years therefore reads as the entry EV/EBITDA
#   multiple, which is the honest way to state it.
_DE_NOVO_CONTRIBUTION_MARGIN = 0.20
_ACQUISITION_EBITDA_MARGIN = 0.22


def _payback_years(capex_mm: float, year3_revenue_mm: float,
                   margin: float) -> float:
    """Capital ÷ steady-state annual contribution (year-3 run rate)."""
    annual = year3_revenue_mm * margin
    if annual <= 0:
        return 0.0
    return round(capex_mm / annual, 1)


def _build_entry_scenarios(markets: List[MarketRow]) -> List[EntryScenario]:
    scenarios = []
    top = [m for m in markets if m.tier in ("Priority", "Watch")][:5]
    for m in top:
        # Two strategies per top market
        pop_factor = m.population_k / 5000      # normalize to reference 5M population
        # De novo
        dn_capex = round(pop_factor * 3.6, 2)
        dn_y3 = round(pop_factor * 14.0, 2)
        scenarios.append(EntryScenario(
            cbsa=m.cbsa,
            entry_strategy="De novo (4 sites over 3 yrs)",
            year1_revenue_mm=round(pop_factor * 3.5, 2),
            year3_revenue_mm=dn_y3,
            year5_revenue_mm=round(pop_factor * 24.5, 2),
            capex_mm=dn_capex,
            payback_years=_payback_years(
                dn_capex, dn_y3, _DE_NOVO_CONTRIBUTION_MARGIN),
            expected_moic=round(2.3 + (m.white_space_score - 55) / 30, 2),
        ))
        # Acquisition
        acq_capex = round(pop_factor * 95.0, 2)
        acq_y3 = round(pop_factor * 32.0, 2)
        scenarios.append(EntryScenario(
            cbsa=m.cbsa,
            entry_strategy="Acquisition (platform)",
            year1_revenue_mm=round(pop_factor * 22.0, 2),
            year3_revenue_mm=acq_y3,
            year5_revenue_mm=round(pop_factor * 48.0, 2),
            capex_mm=acq_capex,
            payback_years=_payback_years(
                acq_capex, acq_y3, _ACQUISITION_EBITDA_MARGIN),
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
    components = _build_components(sector)
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
