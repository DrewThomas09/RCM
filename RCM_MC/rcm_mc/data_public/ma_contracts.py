"""Medicare Advantage Contract Analyzer.

Models MA plan economics for PE healthcare platforms with MA-risk exposure:
provider groups bearing MA risk, MSOs managing MA lives, delegated-risk
IPAs, and capitated primary care.

Key analytics:
- Benchmark / bid positioning (CMS benchmark vs bid vs rebate)
- RAF score delta to market
- Star ratings and quality bonus (>=4.0 unlocks 5% bonus)
- Medical Loss Ratio (MLR) — 85% floor in many states
- V28 (risk-adjustment model) transition phase-in — 2024 -> 2026
- Supplemental benefits load
- MLR by plan segment
- Year-over-year reimbursement pressure
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Plan-level benchmarks (derived from public CMS bid/rebate data)
# ---------------------------------------------------------------------------

_PLAN_TYPE_BENCH = {
    "HMO":       {"mlr_target": 0.85, "admin_pct": 0.08, "raf_base": 1.02},
    "PPO":       {"mlr_target": 0.85, "admin_pct": 0.09, "raf_base": 1.04},
    "D-SNP":     {"mlr_target": 0.88, "admin_pct": 0.11, "raf_base": 1.58},
    "C-SNP":     {"mlr_target": 0.88, "admin_pct": 0.12, "raf_base": 1.82},
    "I-SNP":     {"mlr_target": 0.90, "admin_pct": 0.13, "raf_base": 2.35},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MAPlan:
    plan_name: str
    plan_type: str
    enrollment: int
    raf_score: float
    benchmark_pmpm: float
    bid_pmpm: float
    rebate_pmpm: float
    star_rating: float
    quality_bonus_pct: float
    mlr_pct: float
    margin_pmpm: float
    annual_revenue_mm: float
    annual_margin_mm: float


@dataclass
class RAFAnalysis:
    hcc_category: str
    prevalence_pct: float
    avg_raf_contribution: float
    current_capture_pct: float
    target_capture_pct: float
    incremental_revenue_mm: float


@dataclass
class StarRating:
    measure_domain: str
    current_score: float
    target_score: float
    weight: float
    bonus_revenue_mm: float
    priority: str


@dataclass
class V28Impact:
    plan_segment: str
    v24_raf: float
    v28_raf: float
    raf_delta: float
    revenue_impact_mm: float
    transition_year: int


@dataclass
class MLRWaterfall:
    component: str
    pmpm_cost: float
    pct_of_premium: float
    ytd_actual: float
    target: float
    variance: float


@dataclass
class SupplementalBenefit:
    benefit: str
    utilization_pct: float
    cost_pmpm: float
    enrollment_impact: str
    roi_score: float


@dataclass
class MAContractResult:
    total_enrollment: int
    blended_benchmark_pmpm: float
    blended_bid_pmpm: float
    weighted_star_rating: float
    blended_mlr: float
    annual_revenue_mm: float
    annual_margin_mm: float
    margin_pct: float
    plans: List[MAPlan]
    raf: List[RAFAnalysis]
    stars: List[StarRating]
    v28: List[V28Impact]
    mlr_components: List[MLRWaterfall]
    supplemental: List[SupplementalBenefit]
    v28_net_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 83):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_plans(total_lives: int, regional_bench: float) -> List[MAPlan]:
    import hashlib
    # Realistic plan mix for a mid-size MA-risk provider group
    mix = [
        ("Platform HMO Gold", "HMO", 0.42, 4.0, 1.06, 0.845),
        ("Platform PPO Silver", "PPO", 0.23, 3.5, 1.08, 0.855),
        ("Platform DSNP", "D-SNP", 0.18, 4.5, 1.62, 0.868),
        ("Platform CSNP Diabetic", "C-SNP", 0.08, 4.0, 1.78, 0.882),
        ("Platform ISNP LTC", "I-SNP", 0.05, 4.5, 2.28, 0.895),
        ("Platform HMO Basic", "HMO", 0.04, 3.0, 0.98, 0.862),
    ]
    rows = []
    for name, plan_type, share, star, raf_adj, mlr in mix:
        bench = _PLAN_TYPE_BENCH[plan_type]
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        enrollment = max(100, int(total_lives * share))
        raf = round(bench["raf_base"] * raf_adj * (0.98 + (h % 5) / 100), 3)
        benchmark = regional_bench * raf
        bid = benchmark * (0.92 + (h % 6) / 100)   # bid below bench
        rebate = (benchmark - bid) * 0.65   # rebate is % of savings
        bonus_pct = 0.05 if star >= 4.0 else (0.035 if star >= 3.5 else 0)
        # Revenue = (bid + rebate) * 12 * enrollment
        rev_pmpm = bid + rebate * (1 + bonus_pct)
        annual_rev = rev_pmpm * 12 * enrollment / 1000000
        margin_pmpm = rev_pmpm * (1 - mlr - bench["admin_pct"])
        annual_margin = margin_pmpm * 12 * enrollment / 1000000
        rows.append(MAPlan(
            plan_name=name, plan_type=plan_type, enrollment=enrollment,
            raf_score=raf,
            benchmark_pmpm=round(benchmark, 2),
            bid_pmpm=round(bid, 2),
            rebate_pmpm=round(rebate, 2),
            star_rating=star,
            quality_bonus_pct=round(bonus_pct, 3),
            mlr_pct=round(mlr, 3),
            margin_pmpm=round(margin_pmpm, 2),
            annual_revenue_mm=round(annual_rev, 2),
            annual_margin_mm=round(annual_margin, 2),
        ))
    return rows


def _build_raf() -> List[RAFAnalysis]:
    import hashlib
    items = [
        ("Diabetes (HCC 17-19)", 0.32, 0.318),
        ("CHF / Heart Failure (HCC 85)", 0.14, 0.368),
        ("COPD / Asthma (HCC 111-112)", 0.18, 0.335),
        ("Chronic Kidney Disease 4-5 (HCC 136-138)", 0.08, 0.428),
        ("Major Depression (HCC 58-59)", 0.22, 0.309),
        ("Vascular Disease (HCC 108)", 0.16, 0.288),
        ("Morbid Obesity (HCC 22)", 0.12, 0.250),
        ("Dementia / Alzheimer's (HCC 51-52)", 0.09, 0.395),
        ("Cancer - Active (HCC 8-14)", 0.07, 0.625),
        ("Protein-Calorie Malnutrition (HCC 21)", 0.04, 0.455),
    ]
    rows = []
    for name, prev, raf in items:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        current = 0.55 + (h % 30) / 100   # current capture 55-85%
        target = min(0.95, current + 0.12)
        # Incremental revenue = prevalence * delta_capture * raf * avg_pmpm * lives
        incr = prev * (target - current) * raf * 1100 * 12 * 8500 / 1000000
        rows.append(RAFAnalysis(
            hcc_category=name,
            prevalence_pct=round(prev, 3),
            avg_raf_contribution=round(raf, 3),
            current_capture_pct=round(current, 3),
            target_capture_pct=round(target, 3),
            incremental_revenue_mm=round(incr, 2),
        ))
    return rows


def _build_stars() -> List[StarRating]:
    import hashlib
    measures = [
        ("HEDIS Clinical Measures", 4.0, 4.5, 0.40),
        ("CAHPS Patient Experience", 3.5, 4.0, 0.25),
        ("HOS Health Outcomes", 4.0, 4.5, 0.15),
        ("Complaints & Disenrollment", 3.0, 4.0, 0.10),
        ("Part D Drug Safety", 4.0, 4.5, 0.05),
        ("Appeals / Timely Decisions", 3.5, 4.0, 0.05),
    ]
    rows = []
    for name, curr, tgt, weight in measures:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        # 0.5 rating uplift * weight * bonus * revenue
        uplift_value = (tgt - curr) * weight * 0.05 * 420 * 12 * 8500 / 1000000
        if tgt - curr >= 1.0:
            pri = "critical"
        elif tgt - curr >= 0.5:
            pri = "high"
        else:
            pri = "standard"
        rows.append(StarRating(
            measure_domain=name,
            current_score=curr,
            target_score=tgt,
            weight=round(weight, 3),
            bonus_revenue_mm=round(uplift_value, 2),
            priority=pri,
        ))
    return rows


def _build_v28(plans: List[MAPlan]) -> List[V28Impact]:
    # V28 ramps: 2024 33%, 2025 67%, 2026 100% blend
    rows = []
    for p in plans:
        # V28 reduces RAF ~3-6% depending on chronic mix
        if p.plan_type in ("D-SNP", "C-SNP", "I-SNP"):
            raf_cut = 0.055
        elif p.plan_type == "PPO":
            raf_cut = 0.042
        else:
            raf_cut = 0.038
        v24 = p.raf_score
        v28 = round(v24 * (1 - raf_cut), 3)
        delta = round(v28 - v24, 3)
        # Revenue impact: delta * benchmark * enrollment * 12 / raf(to normalize)
        rev_impact = delta * p.benchmark_pmpm / p.raf_score * 12 * p.enrollment / 1000000
        rows.append(V28Impact(
            plan_segment=p.plan_name,
            v24_raf=v24,
            v28_raf=v28,
            raf_delta=delta,
            revenue_impact_mm=round(rev_impact, 2),
            transition_year=2026,
        ))
    return rows


def _build_mlr_waterfall() -> List[MLRWaterfall]:
    items = [
        ("Inpatient Facility", 165, 0.165, 0.168, 0.160, 0.008),
        ("Outpatient Facility", 128, 0.128, 0.130, 0.125, 0.005),
        ("Professional / MD", 185, 0.185, 0.189, 0.180, 0.009),
        ("Pharmacy (Part D)", 148, 0.148, 0.152, 0.145, 0.007),
        ("Skilled Nursing", 62, 0.062, 0.058, 0.060, -0.002),
        ("Home Health / DME", 42, 0.042, 0.044, 0.040, 0.004),
        ("Administrative", 85, 0.085, 0.082, 0.090, -0.008),
        ("Supplemental Benefits", 48, 0.048, 0.051, 0.045, 0.006),
    ]
    rows = []
    for comp, pmpm, pct, ytd, tgt, var in items:
        rows.append(MLRWaterfall(
            component=comp, pmpm_cost=pmpm,
            pct_of_premium=round(pct, 4),
            ytd_actual=round(ytd, 4),
            target=round(tgt, 4),
            variance=round(var, 4),
        ))
    return rows


def _build_supplemental() -> List[SupplementalBenefit]:
    return [
        SupplementalBenefit("Dental Preventive", 0.62, 18.5, "high — D-SNP driver", 4.2),
        SupplementalBenefit("Vision Exam + Eyewear", 0.38, 9.2, "medium", 3.8),
        SupplementalBenefit("OTC Card ($100/qtr)", 0.78, 28.0, "very high", 4.7),
        SupplementalBenefit("Flex Card Grocery", 0.55, 42.5, "high — SNP only", 3.9),
        SupplementalBenefit("Hearing Aids", 0.22, 12.8, "medium", 3.2),
        SupplementalBenefit("Transportation (non-emer)", 0.18, 8.5, "low", 2.4),
        SupplementalBenefit("SilverSneakers Fitness", 0.35, 4.2, "medium", 3.6),
        SupplementalBenefit("In-Home Support", 0.08, 35.0, "high — I-SNP", 3.8),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_ma_contracts(
    total_lives: int = 85000,
    regional_benchmark_pmpm: float = 1050.0,
) -> MAContractResult:
    corpus = _load_corpus()

    plans = _build_plans(total_lives, regional_benchmark_pmpm)
    raf = _build_raf()
    stars = _build_stars()
    v28 = _build_v28(plans)
    mlr_components = _build_mlr_waterfall()
    supplemental = _build_supplemental()

    total_enrollment = sum(p.enrollment for p in plans)
    total_rev = sum(p.annual_revenue_mm for p in plans)
    total_margin = sum(p.annual_margin_mm for p in plans)
    weighted_bench = (
        sum(p.benchmark_pmpm * p.enrollment for p in plans) / total_enrollment
    ) if total_enrollment else 0
    weighted_bid = (
        sum(p.bid_pmpm * p.enrollment for p in plans) / total_enrollment
    ) if total_enrollment else 0
    weighted_star = (
        sum(p.star_rating * p.enrollment for p in plans) / total_enrollment
    ) if total_enrollment else 0
    blended_mlr = (
        sum(p.mlr_pct * p.enrollment for p in plans) / total_enrollment
    ) if total_enrollment else 0

    v28_net = sum(v.revenue_impact_mm for v in v28)

    return MAContractResult(
        total_enrollment=total_enrollment,
        blended_benchmark_pmpm=round(weighted_bench, 2),
        blended_bid_pmpm=round(weighted_bid, 2),
        weighted_star_rating=round(weighted_star, 3),
        blended_mlr=round(blended_mlr, 4),
        annual_revenue_mm=round(total_rev, 2),
        annual_margin_mm=round(total_margin, 2),
        margin_pct=round(total_margin / total_rev, 4) if total_rev else 0,
        plans=plans,
        raf=raf,
        stars=stars,
        v28=v28,
        mlr_components=mlr_components,
        supplemental=supplemental,
        v28_net_impact_mm=round(v28_net, 2),
        corpus_deal_count=len(corpus),
    )
