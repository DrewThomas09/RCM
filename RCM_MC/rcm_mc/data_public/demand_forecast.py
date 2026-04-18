"""Demand Forecaster — demographic-driven patient volume projections.

Models utilization demand over 5-10 year horizon:
- US population aging curve (65+ share growth)
- Disease prevalence by age band (diabetes, arthritis, dementia, etc.)
- Medicare beneficiary growth
- Utilization per capita trend
- Payer-mix shift from demographics
- Procedure-specific volume forecasts
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Demographic projections (US national averages, rough)
# ---------------------------------------------------------------------------

_POP_GROWTH_BY_AGE = {
    "0-17":  {"cagr_5yr": 0.002, "pop_2025_mm": 73.0},
    "18-44": {"cagr_5yr": 0.008, "pop_2025_mm": 118.0},
    "45-64": {"cagr_5yr": 0.012, "pop_2025_mm": 82.0},
    "65-74": {"cagr_5yr": 0.032, "pop_2025_mm": 36.0},
    "75-84": {"cagr_5yr": 0.048, "pop_2025_mm": 18.0},
    "85+":   {"cagr_5yr": 0.045, "pop_2025_mm": 7.5},
}

# Utilization per capita (visits/year) by age band — key disease categories
_UTIL_PER_CAPITA = {
    "Primary Care":    {"0-17": 2.8, "18-44": 1.4, "45-64": 3.2, "65-74": 5.8, "75-84": 8.2, "85+": 12.5},
    "Cardiology":      {"0-17": 0.01, "18-44": 0.08, "45-64": 0.35, "65-74": 1.2, "75-84": 2.5, "85+": 3.8},
    "Orthopedics":     {"0-17": 0.15, "18-44": 0.28, "45-64": 0.45, "65-74": 0.78, "75-84": 1.2, "85+": 1.5},
    "Oncology":        {"0-17": 0.005, "18-44": 0.04, "45-64": 0.18, "65-74": 0.42, "75-84": 0.85, "85+": 1.1},
    "Ophthalmology":   {"0-17": 0.18, "18-44": 0.22, "45-64": 0.38, "65-74": 0.85, "75-84": 1.4, "85+": 1.8},
    "Dermatology":     {"0-17": 0.28, "18-44": 0.32, "45-64": 0.42, "65-74": 0.65, "75-84": 0.85, "85+": 1.0},
    "Nephrology":      {"0-17": 0.002, "18-44": 0.015, "45-64": 0.12, "65-74": 0.35, "75-84": 0.72, "85+": 0.95},
    "Behavioral Health":{"0-17": 0.35, "18-44": 0.42, "45-64": 0.28, "65-74": 0.18, "75-84": 0.15, "85+": 0.12},
    "ASC / Surgery":   {"0-17": 0.02, "18-44": 0.06, "45-64": 0.12, "65-74": 0.28, "75-84": 0.42, "85+": 0.38},
    "Home Health":     {"0-17": 0.0, "18-44": 0.008, "45-64": 0.028, "65-74": 0.08, "75-84": 0.28, "85+": 0.55},
    "Hospice":         {"0-17": 0.0, "18-44": 0.002, "45-64": 0.008, "65-74": 0.022, "75-84": 0.065, "85+": 0.15},
    "Dialysis":        {"0-17": 0.0002, "18-44": 0.002, "45-64": 0.008, "65-74": 0.018, "75-84": 0.028, "85+": 0.032},
}

# Disease prevalence by age band (for 10-yr horizon)
_DISEASE_PREVALENCE = {
    "Diabetes (T2)":      {"45-64": 0.18, "65-74": 0.27, "75-84": 0.32, "85+": 0.30},
    "Hypertension":       {"45-64": 0.42, "65-74": 0.64, "75-84": 0.72, "85+": 0.76},
    "Coronary Artery Dz": {"45-64": 0.08, "65-74": 0.18, "75-84": 0.28, "85+": 0.36},
    "COPD":               {"45-64": 0.06, "65-74": 0.12, "75-84": 0.18, "85+": 0.20},
    "Osteoarthritis":     {"45-64": 0.28, "65-74": 0.42, "75-84": 0.55, "85+": 0.62},
    "Alzheimer / Dementia":{"65-74": 0.03, "75-84": 0.12, "85+": 0.33},
    "Cancer (any)":       {"45-64": 0.045, "65-74": 0.11, "75-84": 0.17, "85+": 0.22},
    "CKD (Stage 3+)":     {"45-64": 0.08, "65-74": 0.18, "75-84": 0.28, "85+": 0.35},
    "Depression":         {"18-44": 0.08, "45-64": 0.11, "65-74": 0.10, "75-84": 0.12, "85+": 0.14},
    "Obesity (BMI 30+)":  {"18-44": 0.35, "45-64": 0.42, "65-74": 0.40, "75-84": 0.32, "85+": 0.24},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PopulationRow:
    age_band: str
    pop_2025_mm: float
    pop_2030_mm: float
    pop_2035_mm: float
    cagr_5yr: float
    share_2025: float
    share_2035: float


@dataclass
class UtilizationProjection:
    year: int
    total_pop_mm: float
    expected_visits_mm: float
    pct_vs_baseline: float
    medicare_share_pct: float


@dataclass
class DiseasePrevalence:
    disease: str
    prevalence_2025_pct: float
    prevalence_2035_pct: float
    patients_2025_mm: float
    patients_2035_mm: float
    cagr_10yr: float


@dataclass
class VolumeForecast:
    year: int
    patient_visits_k: float
    growth_vs_py: float
    medicare_share: float
    commercial_share: float


@dataclass
class MarketOpportunity:
    opportunity: str
    addressable_pop_mm: float
    current_penetration: float
    target_penetration: float
    revenue_opportunity_mm: float
    feasibility: str


@dataclass
class DemandForecastResult:
    sector: str
    baseline_market_mm: float
    ten_yr_cagr: float
    aging_tailwind_pct: float
    population: List[PopulationRow]
    utilization: List[UtilizationProjection]
    disease: List[DiseasePrevalence]
    volume_forecast: List[VolumeForecast]
    opportunities: List[MarketOpportunity]
    medicare_share_2025: float
    medicare_share_2035: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 76):
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


def _get_util(sector: str) -> Dict[str, float]:
    # Match sector to util table
    if "Primary" in sector or "Physician" in sector:
        return _UTIL_PER_CAPITA["Primary Care"]
    if "Orthop" in sector or "Spine" in sector or "MSK" in sector:
        return _UTIL_PER_CAPITA["Orthopedics"]
    if "Cardio" in sector:
        return _UTIL_PER_CAPITA["Cardiology"]
    if "Oncol" in sector:
        return _UTIL_PER_CAPITA["Oncology"]
    if "Ophthal" in sector or "Vision" in sector:
        return _UTIL_PER_CAPITA["Ophthalmology"]
    if "Derm" in sector:
        return _UTIL_PER_CAPITA["Dermatology"]
    if "Nephro" in sector or "Dialysis" in sector or "Kidney" in sector:
        return _UTIL_PER_CAPITA["Dialysis"]
    if "Behav" in sector or "Mental" in sector or "Psych" in sector:
        return _UTIL_PER_CAPITA["Behavioral Health"]
    if "ASC" in sector or "Surgery" in sector:
        return _UTIL_PER_CAPITA["ASC / Surgery"]
    if "Home Health" in sector:
        return _UTIL_PER_CAPITA["Home Health"]
    if "Hospice" in sector:
        return _UTIL_PER_CAPITA["Hospice"]
    return _UTIL_PER_CAPITA["Primary Care"]


def _build_population() -> List[PopulationRow]:
    rows = []
    total_2025 = sum(v["pop_2025_mm"] for v in _POP_GROWTH_BY_AGE.values())
    total_2035 = sum(v["pop_2025_mm"] * ((1 + v["cagr_5yr"]) ** 10) for v in _POP_GROWTH_BY_AGE.values())
    for band, data in _POP_GROWTH_BY_AGE.items():
        p25 = data["pop_2025_mm"]
        p30 = p25 * ((1 + data["cagr_5yr"]) ** 5)
        p35 = p25 * ((1 + data["cagr_5yr"]) ** 10)
        rows.append(PopulationRow(
            age_band=band,
            pop_2025_mm=round(p25, 1),
            pop_2030_mm=round(p30, 1),
            pop_2035_mm=round(p35, 1),
            cagr_5yr=round(data["cagr_5yr"], 4),
            share_2025=round(p25 / total_2025, 3),
            share_2035=round(p35 / total_2035, 3),
        ))
    return rows


def _weighted_visits(util: Dict[str, float], pop: Dict[str, float]) -> float:
    return sum(util.get(band, 0) * pop.get(band, 0) for band in util)


def _build_utilization(sector: str) -> List[UtilizationProjection]:
    util = _get_util(sector)
    rows = []
    for yr in range(2025, 2036):
        pop = {}
        for band, data in _POP_GROWTH_BY_AGE.items():
            pop[band] = data["pop_2025_mm"] * ((1 + data["cagr_5yr"]) ** (yr - 2025))
        total_pop = sum(pop.values())
        visits = _weighted_visits(util, pop)
        # Medicare share: 65+ as fraction of total visits
        medicare_visits = sum(util.get(b, 0) * pop.get(b, 0) for b in ["65-74", "75-84", "85+"])
        medicare_share = medicare_visits / visits if visits else 0
        # Baseline comparison
        if yr == 2025:
            baseline = visits
        pct_vs_baseline = visits / baseline if baseline else 1

        rows.append(UtilizationProjection(
            year=yr,
            total_pop_mm=round(total_pop, 1),
            expected_visits_mm=round(visits, 2),
            pct_vs_baseline=round(pct_vs_baseline, 4),
            medicare_share_pct=round(medicare_share, 3),
        ))
    return rows


def _build_disease() -> List[DiseasePrevalence]:
    rows = []
    # Adult pop 2025 and 2035
    adult_2025 = sum(_POP_GROWTH_BY_AGE[b]["pop_2025_mm"] for b in ["18-44", "45-64", "65-74", "75-84", "85+"])
    adult_2035 = sum(_POP_GROWTH_BY_AGE[b]["pop_2025_mm"] * ((1 + _POP_GROWTH_BY_AGE[b]["cagr_5yr"]) ** 10)
                     for b in ["18-44", "45-64", "65-74", "75-84", "85+"])

    for disease, rates in _DISEASE_PREVALENCE.items():
        # 2025 prevalent patients: pop × rate, summed
        p25 = 0
        p35 = 0
        for band, rate in rates.items():
            b25 = _POP_GROWTH_BY_AGE[band]["pop_2025_mm"]
            b35 = b25 * ((1 + _POP_GROWTH_BY_AGE[band]["cagr_5yr"]) ** 10)
            p25 += b25 * rate
            p35 += b35 * rate
        prev25 = p25 / adult_2025
        prev35 = p35 / adult_2035
        cagr = (p35 / p25) ** 0.1 - 1 if p25 else 0
        rows.append(DiseasePrevalence(
            disease=disease,
            prevalence_2025_pct=round(prev25, 3),
            prevalence_2035_pct=round(prev35, 3),
            patients_2025_mm=round(p25, 2),
            patients_2035_mm=round(p35, 2),
            cagr_10yr=round(cagr, 4),
        ))
    return rows


def _build_volume_forecast(sector: str, baseline_visits_k: float) -> List[VolumeForecast]:
    util = _build_utilization(sector)
    rows = []
    prev_visits = baseline_visits_k
    # Base year visits (2025)
    base = util[0].expected_visits_mm if util else 1
    for i, u in enumerate(util):
        # Scale to our baseline
        mult = u.expected_visits_mm / base if base else 1
        visits_k = baseline_visits_k * mult
        growth = (visits_k / prev_visits - 1) if prev_visits and i > 0 else 0
        prev_visits = visits_k
        # Commercial share = 1 - medicare - medicaid_assumed
        medicare_share = u.medicare_share_pct
        commercial_share = 1 - medicare_share - 0.12    # ~12% medicaid
        rows.append(VolumeForecast(
            year=u.year,
            patient_visits_k=round(visits_k, 1),
            growth_vs_py=round(growth, 4),
            medicare_share=round(medicare_share, 3),
            commercial_share=round(max(0, commercial_share), 3),
        ))
    return rows


def _build_opportunities(revenue_mm: float, ten_yr_cagr: float) -> List[MarketOpportunity]:
    return [
        MarketOpportunity(
            opportunity="Senior-Focused Care (65+) Growth",
            addressable_pop_mm=66.0, current_penetration=0.22, target_penetration=0.35,
            revenue_opportunity_mm=round(revenue_mm * 0.18, 2),
            feasibility="high",
        ),
        MarketOpportunity(
            opportunity="Medicare Advantage Risk Bearing",
            addressable_pop_mm=32.0, current_penetration=0.15, target_penetration=0.28,
            revenue_opportunity_mm=round(revenue_mm * 0.22, 2),
            feasibility="medium",
        ),
        MarketOpportunity(
            opportunity="Chronic Disease Management (Diabetes, CKD)",
            addressable_pop_mm=38.0, current_penetration=0.18, target_penetration=0.32,
            revenue_opportunity_mm=round(revenue_mm * 0.12, 2),
            feasibility="medium",
        ),
        MarketOpportunity(
            opportunity="Alzheimer / Dementia Care",
            addressable_pop_mm=7.5, current_penetration=0.08, target_penetration=0.22,
            revenue_opportunity_mm=round(revenue_mm * 0.08, 2),
            feasibility="medium",
        ),
        MarketOpportunity(
            opportunity="Behavioral Health (young adults)",
            addressable_pop_mm=48.0, current_penetration=0.22, target_penetration=0.40,
            revenue_opportunity_mm=round(revenue_mm * 0.15, 2),
            feasibility="high",
        ),
        MarketOpportunity(
            opportunity="Oncology Infusion (aging)",
            addressable_pop_mm=5.8, current_penetration=0.14, target_penetration=0.22,
            revenue_opportunity_mm=round(revenue_mm * 0.10, 2),
            feasibility="medium",
        ),
        MarketOpportunity(
            opportunity="Home-Based Care Expansion",
            addressable_pop_mm=28.0, current_penetration=0.08, target_penetration=0.18,
            revenue_opportunity_mm=round(revenue_mm * 0.14, 2),
            feasibility="high",
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_demand_forecast(
    sector: str = "Primary Care",
    baseline_visits_k: float = 380.0,
    revenue_mm: float = 80.0,
) -> DemandForecastResult:
    corpus = _load_corpus()

    population = _build_population()
    utilization = _build_utilization(sector)
    disease = _build_disease()
    volume = _build_volume_forecast(sector, baseline_visits_k)
    opps = _build_opportunities(revenue_mm, 0.055)

    # 10-year CAGR
    ten_cagr = (utilization[-1].expected_visits_mm / utilization[0].expected_visits_mm) ** 0.1 - 1
    aging_tailwind = utilization[-1].pct_vs_baseline - 1
    # Medicare share
    mc25 = utilization[0].medicare_share_pct
    mc35 = utilization[-1].medicare_share_pct

    # Baseline market size
    baseline_mkt = sum(p.pop_2025_mm for p in population)

    return DemandForecastResult(
        sector=sector,
        baseline_market_mm=round(baseline_mkt, 1),
        ten_yr_cagr=round(ten_cagr, 4),
        aging_tailwind_pct=round(aging_tailwind, 4),
        population=population,
        utilization=utilization,
        disease=disease,
        volume_forecast=volume,
        opportunities=opps,
        medicare_share_2025=round(mc25, 3),
        medicare_share_2035=round(mc35, 3),
        corpus_deal_count=len(corpus),
    )
