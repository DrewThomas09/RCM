"""Physician Compensation Plan Designer.

Models physician comp structures for PE healthcare platforms:
- wRVU production-based comp
- Base + bonus / eat-what-you-kill
- Quality/VBC bonus pools
- Call pay, stipends, directorships
- Partner track compensation
- Simulated comp under different plans
- Comp-to-collection ratio modeling
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Specialty benchmarks (MGMA median)
# ---------------------------------------------------------------------------

_SPECIALTY_BENCHMARKS = {
    "Primary Care":       {"median_comp_k": 275, "wrvu_median": 5200, "comp_per_wrvu": 52},
    "Family Medicine":    {"median_comp_k": 260, "wrvu_median": 5100, "comp_per_wrvu": 51},
    "Internal Medicine":  {"median_comp_k": 290, "wrvu_median": 5250, "comp_per_wrvu": 55},
    "Pediatrics":         {"median_comp_k": 245, "wrvu_median": 4800, "comp_per_wrvu": 51},
    "Cardiology":         {"median_comp_k": 575, "wrvu_median": 11200, "comp_per_wrvu": 51},
    "Gastroenterology":   {"median_comp_k": 560, "wrvu_median": 10800, "comp_per_wrvu": 52},
    "Orthopedics":        {"median_comp_k": 640, "wrvu_median": 12500, "comp_per_wrvu": 51},
    "Ophthalmology":      {"median_comp_k": 420, "wrvu_median": 9500, "comp_per_wrvu": 44},
    "Dermatology":        {"median_comp_k": 485, "wrvu_median": 8200, "comp_per_wrvu": 59},
    "Urology":            {"median_comp_k": 510, "wrvu_median": 9800, "comp_per_wrvu": 52},
    "Anesthesiology":     {"median_comp_k": 465, "wrvu_median": 9200, "comp_per_wrvu": 51},
    "Radiology":          {"median_comp_k": 510, "wrvu_median": 11500, "comp_per_wrvu": 44},
    "General Surgery":    {"median_comp_k": 465, "wrvu_median": 9000, "comp_per_wrvu": 52},
    "OB/GYN":             {"median_comp_k": 345, "wrvu_median": 7200, "comp_per_wrvu": 48},
    "Emergency Medicine": {"median_comp_k": 385, "wrvu_median": 7800, "comp_per_wrvu": 49},
    "Psychiatry":         {"median_comp_k": 295, "wrvu_median": 4800, "comp_per_wrvu": 61},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CompPlanModel:
    plan_type: str
    base_salary_pct: float       # as % of total target comp
    productivity_bonus_pct: float
    quality_bonus_pct: float
    call_pay_pct: float
    signing_bonus_pct: float
    ramp_period_months: int
    suitable_for: str
    retention_score: int


@dataclass
class ProviderComp:
    provider_id: str
    specialty: str
    wrvu_production: int
    wrvu_percentile: int
    base_salary_k: float
    productivity_pay_k: float
    quality_bonus_k: float
    call_stipend_k: float
    total_comp_k: float
    comp_per_wrvu: float
    comp_to_collection_pct: float


@dataclass
class QualityPool:
    metric: str
    weight_pct: float
    threshold: str
    max_bonus_pct_of_base: float
    current_performance: str


@dataclass
class CompSim:
    scenario: str
    top_10pct_comp_k: float
    median_comp_k: float
    bottom_10pct_comp_k: float
    total_physician_pool_mm: float
    retention_projected_pct: float
    recruitment_attractiveness: int


@dataclass
class BenchmarkRow:
    specialty: str
    median_comp_k: float
    our_median_k: float
    delta_pct: float
    market_position: str


@dataclass
class PhysCompResult:
    practice_revenue_mm: float
    total_physicians: int
    total_physician_pool_mm: float
    comp_to_collection_pct: float
    models: List[CompPlanModel]
    providers: List[ProviderComp]
    quality_pools: List[QualityPool]
    simulations: List[CompSim]
    benchmarks: List[BenchmarkRow]
    recommended_model: str
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 81):
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


def _build_models() -> List[CompPlanModel]:
    return [
        CompPlanModel(
            plan_type="100% Base Salary (W-2)",
            base_salary_pct=1.00, productivity_bonus_pct=0,
            quality_bonus_pct=0, call_pay_pct=0, signing_bonus_pct=0.05,
            ramp_period_months=6,
            suitable_for="New hires, hospitalist / shift-based roles",
            retention_score=65,
        ),
        CompPlanModel(
            plan_type="Base + wRVU Productivity (70/30)",
            base_salary_pct=0.70, productivity_bonus_pct=0.25,
            quality_bonus_pct=0.03, call_pay_pct=0.02, signing_bonus_pct=0.03,
            ramp_period_months=4,
            suitable_for="Experienced MDs with stable volume",
            retention_score=78,
        ),
        CompPlanModel(
            plan_type="Eat-What-You-Kill (Pure Production)",
            base_salary_pct=0.10, productivity_bonus_pct=0.82,
            quality_bonus_pct=0.05, call_pay_pct=0.03, signing_bonus_pct=0,
            ramp_period_months=3,
            suitable_for="Proceduralists; high-performer cultures",
            retention_score=70,
        ),
        CompPlanModel(
            plan_type="Value-Based Care / Capitation",
            base_salary_pct=0.55, productivity_bonus_pct=0.15,
            quality_bonus_pct=0.25, call_pay_pct=0.03, signing_bonus_pct=0.02,
            ramp_period_months=6,
            suitable_for="MA-risk primary care, VBC contracts",
            retention_score=72,
        ),
        CompPlanModel(
            plan_type="Partner Track (Base + Profit Share)",
            base_salary_pct=0.55, productivity_bonus_pct=0.25,
            quality_bonus_pct=0.05, call_pay_pct=0.03, signing_bonus_pct=0.12,
            ramp_period_months=12,
            suitable_for="Long-term retention, growth platforms",
            retention_score=88,
        ),
        CompPlanModel(
            plan_type="Hybrid Productivity + Quality (60/25/15)",
            base_salary_pct=0.60, productivity_bonus_pct=0.22,
            quality_bonus_pct=0.13, call_pay_pct=0.03, signing_bonus_pct=0.02,
            ramp_period_months=4,
            suitable_for="Balanced mature practices",
            retention_score=82,
        ),
    ]


def _build_providers(specialty: str, n: int, target_comp_k: float) -> List[ProviderComp]:
    import hashlib
    bench = _SPECIALTY_BENCHMARKS.get(specialty, _SPECIALTY_BENCHMARKS["Primary Care"])
    rows = []
    for i in range(n):
        h = int(hashlib.md5(f"provider{i}{specialty}".encode()).hexdigest()[:6], 16)
        pctile = 15 + (h % 80)
        wrvu_multiplier = 0.65 + pctile / 100
        wrvus = int(bench["wrvu_median"] * wrvu_multiplier)
        # Productivity comp based on wRVU
        prod = wrvus * bench["comp_per_wrvu"] / 1000
        base = target_comp_k * 0.55
        # Quality bonus: 5-15% of base
        quality = base * (0.03 + (h % 12) / 100)
        call = 8 + (h % 25)
        total = base + prod + quality + call
        cpw = total * 1000 / wrvus if wrvus else 0
        collections_k = wrvus * 135 / 1000    # $135/wRVU avg, already in $k
        cpc_pct = total / collections_k if collections_k else 0

        rows.append(ProviderComp(
            provider_id=f"MD-{i + 1:03d}",
            specialty=specialty,
            wrvu_production=wrvus,
            wrvu_percentile=pctile,
            base_salary_k=round(base, 0),
            productivity_pay_k=round(prod, 0),
            quality_bonus_k=round(quality, 0),
            call_stipend_k=round(call, 0),
            total_comp_k=round(total, 0),
            comp_per_wrvu=round(cpw, 2),
            comp_to_collection_pct=round(cpc_pct, 4),
        ))
    return rows


def _build_quality_pools() -> List[QualityPool]:
    return [
        QualityPool("HEDIS Composite Score", 0.30, "Top quartile = full bonus",
                    0.08, "Currently 62nd percentile"),
        QualityPool("Patient Satisfaction (CGCAHPS)", 0.20, "Score >85 = full",
                    0.05, "Currently 82"),
        QualityPool("Chart Closure / Documentation", 0.15, "<48hr closure = full",
                    0.04, "Currently 72hr median"),
        QualityPool("Care Gap Closure", 0.15, "<5 open gaps per 1000 = full",
                    0.05, "Currently 12 per 1000"),
        QualityPool("Follow-up Compliance", 0.10, "88%+ = full", 0.03, "Currently 78%"),
        QualityPool("Medication Adherence (PDC)", 0.05, ">80% PDC = full", 0.02, "Currently 74%"),
        QualityPool("Readmission Rate", 0.05, "<benchmark = full", 0.02, "Currently 11%"),
    ]


def _build_simulations(target_comp: float, n_physicians: int) -> List[CompSim]:
    scenarios = [
        ("Current Plan", target_comp * 1.8, target_comp, target_comp * 0.55, 0.72, 72),
        ("Increase Productivity Weight", target_comp * 1.95, target_comp * 1.02, target_comp * 0.50, 0.70, 78),
        ("Add Partner Track", target_comp * 2.2, target_comp * 1.05, target_comp * 0.55, 0.85, 88),
        ("Weight Quality Higher", target_comp * 1.7, target_comp, target_comp * 0.60, 0.75, 75),
        ("Reduce Base (EWYK)", target_comp * 2.3, target_comp * 0.95, target_comp * 0.40, 0.65, 68),
    ]
    rows = []
    for label, top, med, bot, ret, rec in scenarios:
        pool = (top + med * (n_physicians - 2) + bot) / 1000   # rough total
        rows.append(CompSim(
            scenario=label,
            top_10pct_comp_k=round(top, 0),
            median_comp_k=round(med, 0),
            bottom_10pct_comp_k=round(bot, 0),
            total_physician_pool_mm=round(pool, 2),
            retention_projected_pct=round(ret, 3),
            recruitment_attractiveness=rec,
        ))
    return rows


def _build_benchmarks(sector: str) -> List[BenchmarkRow]:
    import hashlib
    if sector in ("Primary Care", "Physician Services"):
        specs = ["Primary Care", "Internal Medicine", "Pediatrics"]
    elif sector in ("ASC", "Surgery Center"):
        specs = ["Orthopedics", "Gastroenterology", "General Surgery", "Anesthesiology", "Ophthalmology"]
    elif sector == "Cardiology":
        specs = ["Cardiology", "Internal Medicine"]
    else:
        specs = list(_SPECIALTY_BENCHMARKS.keys())[:6]

    rows = []
    for spec in specs:
        bench = _SPECIALTY_BENCHMARKS[spec]
        h = int(hashlib.md5(spec.encode()).hexdigest()[:6], 16)
        our_delta = (h % 30 - 10) / 100   # -10% to +20%
        our_comp = bench["median_comp_k"] * (1 + our_delta)
        if our_delta >= 0.08:
            position = "above market"
        elif our_delta >= -0.03:
            position = "at market"
        else:
            position = "below market"
        rows.append(BenchmarkRow(
            specialty=spec,
            median_comp_k=bench["median_comp_k"],
            our_median_k=round(our_comp, 0),
            delta_pct=round(our_delta, 4),
            market_position=position,
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_phys_comp_plan(
    sector: str = "Primary Care",
    practice_revenue_mm: float = 100.0,
    total_physicians: int = 30,
) -> PhysCompResult:
    corpus = _load_corpus()

    # Determine specialty for provider simulation
    spec_map = {
        "Primary Care": "Primary Care", "Physician Services": "Primary Care",
        "Orthopedics": "Orthopedics", "Cardiology": "Cardiology",
        "Dermatology": "Dermatology", "Gastroenterology": "Gastroenterology",
    }
    primary_specialty = spec_map.get(sector, "Primary Care")
    bench = _SPECIALTY_BENCHMARKS.get(primary_specialty, _SPECIALTY_BENCHMARKS["Primary Care"])
    target_comp = bench["median_comp_k"]

    models = _build_models()
    providers = _build_providers(primary_specialty, min(total_physicians, 15), target_comp)
    quality_pools = _build_quality_pools()
    sims = _build_simulations(target_comp, total_physicians)
    benchmarks = _build_benchmarks(sector)

    total_pool = sum(p.total_comp_k for p in providers) / 1000
    # Scale to full physician count
    total_pool = total_pool * total_physicians / max(len(providers), 1)
    cpc = sum(p.comp_to_collection_pct for p in providers) / len(providers) if providers else 0

    recommended = models[5].plan_type if len(models) > 5 else models[0].plan_type

    return PhysCompResult(
        practice_revenue_mm=round(practice_revenue_mm, 2),
        total_physicians=total_physicians,
        total_physician_pool_mm=round(total_pool, 2),
        comp_to_collection_pct=round(cpc, 4),
        models=models,
        providers=providers,
        quality_pools=quality_pools,
        simulations=sims,
        benchmarks=benchmarks,
        recommended_model=recommended,
        corpus_deal_count=len(corpus),
    )
