"""Physician Productivity Analyzer — wRVU benchmarks, provider utilization, comp ratios.

Healthcare PE deals live or die on physician productivity. Models:
- wRVU production per provider (specialty benchmarks: MGMA, AMGA, Sullivan Cotter)
- Compensation-to-collection ratio
- Panel size / visits per provider per day
- Benchmarking vs. corpus median
- Physician-driven FTE capacity planning
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# MGMA / AMGA productivity benchmarks (annual wRVUs per FTE)
# ---------------------------------------------------------------------------

_WRVU_BENCHMARKS = {
    "Family Medicine":    {"p25": 4200, "median": 4850, "p75": 5700, "comp_per_wrvu": 48},
    "Internal Medicine":  {"p25": 4100, "median": 4700, "p75": 5500, "comp_per_wrvu": 49},
    "Pediatrics":         {"p25": 4300, "median": 5100, "p75": 6000, "comp_per_wrvu": 46},
    "Cardiology":         {"p25": 7500, "median": 9200, "p75":11000, "comp_per_wrvu": 63},
    "Gastroenterology":   {"p25": 7800, "median": 9500, "p75":11500, "comp_per_wrvu": 71},
    "Orthopedics":        {"p25": 8000, "median":10000, "p75":12500, "comp_per_wrvu": 82},
    "Ophthalmology":      {"p25": 7200, "median": 8800, "p75":10500, "comp_per_wrvu": 68},
    "Dermatology":        {"p25": 6500, "median": 7800, "p75": 9500, "comp_per_wrvu": 72},
    "Anesthesiology":     {"p25": 7200, "median": 8500, "p75":10000, "comp_per_wrvu": 75},
    "Radiology":          {"p25": 8500, "median":10500, "p75":13000, "comp_per_wrvu": 58},
    "Emergency Medicine": {"p25": 6500, "median": 7500, "p75": 8800, "comp_per_wrvu": 52},
    "OB/GYN":             {"p25": 5800, "median": 6800, "p75": 8200, "comp_per_wrvu": 65},
    "General Surgery":    {"p25": 7000, "median": 8500, "p75":10200, "comp_per_wrvu": 78},
    "Urology":            {"p25": 7200, "median": 8800, "p75":10500, "comp_per_wrvu": 72},
    "Neurology":          {"p25": 5200, "median": 6200, "p75": 7500, "comp_per_wrvu": 58},
    "Psychiatry":         {"p25": 3800, "median": 4600, "p75": 5500, "comp_per_wrvu": 55},
    "Pulmonology":        {"p25": 5500, "median": 6800, "p75": 8200, "comp_per_wrvu": 62},
    "Endocrinology":      {"p25": 4200, "median": 5100, "p75": 6200, "comp_per_wrvu": 58},
    "Rheumatology":       {"p25": 4800, "median": 5800, "p75": 7000, "comp_per_wrvu": 58},
    "Nephrology":         {"p25": 5500, "median": 6800, "p75": 8200, "comp_per_wrvu": 62},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProviderStats:
    specialty: str
    fte_count: float
    annual_wrvu_per_fte: float
    percentile: str               # "P25", "P50", "P75", "Below", "Above"
    total_annual_wrvu: float
    total_comp_mm: float
    comp_per_wrvu: float
    collections_mm: float
    comp_to_collection_pct: float


@dataclass
class SpecialtyBenchmark:
    specialty: str
    p25_wrvu: float
    median_wrvu: float
    p75_wrvu: float
    actual_wrvu: float
    percentile: float             # 0-100 where actual sits
    delta_from_median: float      # actual - median
    comp_per_wrvu: float


@dataclass
class UtilizationMetric:
    metric: str
    value: float
    unit: str
    benchmark: float
    status: str                   # "strong", "benchmark", "below"


@dataclass
class CapacityScenario:
    scenario: str
    productivity_pct_of_p75: float
    implied_wrvu_lift_pct: float
    implied_revenue_lift_mm: float
    implied_ebitda_lift_mm: float
    implied_ev_uplift_mm: float


@dataclass
class PhysicianProductivityResult:
    providers: List[ProviderStats]
    benchmarks: List[SpecialtyBenchmark]
    utilization: List[UtilizationMetric]
    capacity_scenarios: List[CapacityScenario]
    total_fte: float
    total_wrvu: float
    total_provider_comp_mm: float
    total_collections_mm: float
    blended_comp_to_coll_pct: float
    productivity_score: float      # 0-100
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 61):
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


def _percentile(p25: float, med: float, p75: float, actual: float) -> float:
    """Estimate where actual sits within benchmark band (0-100 percentile)."""
    if actual <= p25:
        return max(0, (actual / p25) * 25)
    elif actual <= med:
        return 25 + ((actual - p25) / (med - p25)) * 25
    elif actual <= p75:
        return 50 + ((actual - med) / (p75 - med)) * 25
    else:
        # Above p75: extrapolate up to 100
        return min(100, 75 + ((actual - p75) / p75) * 25)


def _bucket(percentile: float) -> str:
    if percentile >= 75: return "P75+"
    if percentile >= 50: return "P50"
    if percentile >= 25: return "P25"
    return "Below P25"


def _build_providers(
    specialties: List[Dict],
) -> List[ProviderStats]:
    rows = []
    for s in specialties:
        spec = s["specialty"]
        bench = _WRVU_BENCHMARKS.get(spec, {"p25": 5000, "median": 6000, "p75": 7500, "comp_per_wrvu": 55})
        fte = s["fte"]
        wrvu_per_fte = s.get("wrvu_per_fte", bench["median"])
        pct = _percentile(bench["p25"], bench["median"], bench["p75"], wrvu_per_fte)
        total_wrvu = fte * wrvu_per_fte
        comp_per = bench["comp_per_wrvu"]
        total_comp = total_wrvu * comp_per / 1_000_000   # $ / 1M = MM
        # Collections at ~$120/wRVU average in healthcare services
        collections = total_wrvu * 125 / 1_000_000
        comp_to_coll = total_comp / collections if collections else 0

        rows.append(ProviderStats(
            specialty=spec,
            fte_count=round(fte, 1),
            annual_wrvu_per_fte=round(wrvu_per_fte, 0),
            percentile=_bucket(pct),
            total_annual_wrvu=round(total_wrvu, 0),
            total_comp_mm=round(total_comp, 2),
            comp_per_wrvu=round(comp_per, 2),
            collections_mm=round(collections, 2),
            comp_to_collection_pct=round(comp_to_coll, 4),
        ))
    return rows


def _build_benchmarks(specialties: List[Dict]) -> List[SpecialtyBenchmark]:
    rows = []
    for s in specialties:
        spec = s["specialty"]
        bench = _WRVU_BENCHMARKS.get(spec, {"p25": 5000, "median": 6000, "p75": 7500, "comp_per_wrvu": 55})
        actual = s.get("wrvu_per_fte", bench["median"])
        pct = _percentile(bench["p25"], bench["median"], bench["p75"], actual)
        rows.append(SpecialtyBenchmark(
            specialty=spec,
            p25_wrvu=bench["p25"],
            median_wrvu=bench["median"],
            p75_wrvu=bench["p75"],
            actual_wrvu=round(actual, 0),
            percentile=round(pct, 1),
            delta_from_median=round(actual - bench["median"], 0),
            comp_per_wrvu=bench["comp_per_wrvu"],
        ))
    return rows


def _build_utilization(providers: List[ProviderStats]) -> List[UtilizationMetric]:
    total_fte = sum(p.fte_count for p in providers)
    total_wrvu = sum(p.total_annual_wrvu for p in providers)
    blended_wrvu_per_fte = total_wrvu / total_fte if total_fte else 0
    avg_comp_pct = sum(p.comp_to_collection_pct for p in providers) / len(providers) if providers else 0

    # Derived: panel size, visits/day
    # Assume 2500 visits / year per PCP FTE (median), 3.5 wRVU / visit average
    visits_per_fte = blended_wrvu_per_fte / 3.2
    visits_per_day = visits_per_fte / 220    # working days/year
    panel_size = visits_per_fte * 0.55

    return [
        UtilizationMetric(
            metric="Blended wRVU / FTE",
            value=round(blended_wrvu_per_fte, 0),
            unit="wRVUs/yr",
            benchmark=6500,
            status="strong" if blended_wrvu_per_fte > 7500 else ("benchmark" if blended_wrvu_per_fte > 5500 else "below"),
        ),
        UtilizationMetric(
            metric="Visits / FTE (annual)",
            value=round(visits_per_fte, 0),
            unit="visits/yr",
            benchmark=2400,
            status="strong" if visits_per_fte > 2600 else ("benchmark" if visits_per_fte > 1800 else "below"),
        ),
        UtilizationMetric(
            metric="Visits / Provider / Day",
            value=round(visits_per_day, 1),
            unit="visits/day",
            benchmark=11,
            status="strong" if visits_per_day > 13 else ("benchmark" if visits_per_day > 9 else "below"),
        ),
        UtilizationMetric(
            metric="Active Panel Size",
            value=round(panel_size, 0),
            unit="patients",
            benchmark=1500,
            status="strong" if panel_size > 1800 else ("benchmark" if panel_size > 1200 else "below"),
        ),
        UtilizationMetric(
            metric="Comp / Collection %",
            value=round(avg_comp_pct * 100, 1),
            unit="%",
            benchmark=48.0,
            status="strong" if avg_comp_pct < 0.42 else ("benchmark" if avg_comp_pct < 0.52 else "below"),
        ),
    ]


def _build_capacity(
    providers: List[ProviderStats],
    benchmarks: List[SpecialtyBenchmark],
    current_revenue_mm: float,
    ebitda_margin: float,
    exit_multiple: float,
) -> List[CapacityScenario]:
    rows = []
    total_current_wrvu = sum(p.total_annual_wrvu for p in providers)

    for label, pct_of_p75 in [("Reach P50", 0.8), ("Reach P75", 1.0), ("P75 + Hire", 1.1)]:
        # Implied wRVU at target
        target_wrvu = sum(b.p75_wrvu * pct_of_p75 for b in benchmarks for _ in range(int(providers[i].fte_count if i < len(providers) else 1) if False else 0))
        # Simpler: scale each provider by pct_of_p75 relative to their benchmark p75
        new_wrvu = 0.0
        for p, b in zip(providers, benchmarks):
            target = b.p75_wrvu * pct_of_p75
            new_wrvu += p.fte_count * target
        lift_pct = (new_wrvu / total_current_wrvu - 1) if total_current_wrvu else 0
        rev_lift = current_revenue_mm * lift_pct
        ebitda_lift = rev_lift * (ebitda_margin + 0.03)    # higher fall-through on incremental revenue
        ev_uplift = ebitda_lift * exit_multiple

        rows.append(CapacityScenario(
            scenario=label,
            productivity_pct_of_p75=round(pct_of_p75, 2),
            implied_wrvu_lift_pct=round(lift_pct, 3),
            implied_revenue_lift_mm=round(rev_lift, 2),
            implied_ebitda_lift_mm=round(ebitda_lift, 2),
            implied_ev_uplift_mm=round(ev_uplift, 1),
        ))
    return rows


def _productivity_score(providers: List[ProviderStats], benchmarks: List[SpecialtyBenchmark]) -> float:
    if not benchmarks:
        return 50.0
    avg_pct = sum(b.percentile for b in benchmarks) / len(benchmarks)
    return round(avg_pct, 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_physician_productivity(
    specialties: Optional[List[Dict]] = None,
    revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> PhysicianProductivityResult:
    corpus = _load_corpus()

    if specialties is None:
        specialties = [
            {"specialty": "Family Medicine", "fte": 18, "wrvu_per_fte": 5100},
            {"specialty": "Internal Medicine", "fte": 12, "wrvu_per_fte": 4850},
            {"specialty": "Cardiology", "fte": 4, "wrvu_per_fte": 9800},
            {"specialty": "Orthopedics", "fte": 3, "wrvu_per_fte": 10800},
            {"specialty": "Pediatrics", "fte": 6, "wrvu_per_fte": 5300},
            {"specialty": "OB/GYN", "fte": 4, "wrvu_per_fte": 7100},
        ]

    providers = _build_providers(specialties)
    benchmarks = _build_benchmarks(specialties)
    utilization = _build_utilization(providers)
    capacity = _build_capacity(providers, benchmarks, revenue_mm, ebitda_margin, exit_multiple)

    total_fte = sum(p.fte_count for p in providers)
    total_wrvu = sum(p.total_annual_wrvu for p in providers)
    total_comp = sum(p.total_comp_mm for p in providers)
    total_coll = sum(p.collections_mm for p in providers)
    blended_ratio = total_comp / total_coll if total_coll else 0
    score = _productivity_score(providers, benchmarks)

    return PhysicianProductivityResult(
        providers=providers,
        benchmarks=benchmarks,
        utilization=utilization,
        capacity_scenarios=capacity,
        total_fte=round(total_fte, 1),
        total_wrvu=round(total_wrvu, 0),
        total_provider_comp_mm=round(total_comp, 2),
        total_collections_mm=round(total_coll, 2),
        blended_comp_to_coll_pct=round(blended_ratio, 4),
        productivity_score=score,
        corpus_deal_count=len(corpus),
    )
