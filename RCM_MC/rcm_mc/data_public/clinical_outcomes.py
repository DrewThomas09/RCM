"""Clinical Outcomes Tracker — MA Stars, readmission, complications, VBC economics.

Monetizes quality outcomes for PE healthcare deals:
- CMS Star Rating trajectory (MA bonus thresholds)
- 30 / 90-day readmission rates vs benchmark
- Surgical / procedural complication rates
- Mortality-adjusted outcomes (SMR)
- Outcome-based payer contract uplift
- Quality bonus capture vs plan
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Outcome benchmarks by sector
# ---------------------------------------------------------------------------

_SECTOR_OUTCOMES = {
    "Primary Care":       {"readmission_30d": 0.098, "complication_rate": 0.032, "smr": 0.94,
                           "star_current": 3.8, "ma_attributed_lives": 12500},
    "Physician Services": {"readmission_30d": 0.105, "complication_rate": 0.045, "smr": 0.96,
                           "star_current": 3.6, "ma_attributed_lives": 8000},
    "Hospital":           {"readmission_30d": 0.155, "complication_rate": 0.085, "smr": 1.02,
                           "star_current": 3.2, "ma_attributed_lives": 22000},
    "Home Health":        {"readmission_30d": 0.145, "complication_rate": 0.0, "smr": 0.98,
                           "star_current": 3.9, "ma_attributed_lives": 4500},
    "Hospice":            {"readmission_30d": 0.05, "complication_rate": 0.0, "smr": 1.08,
                           "star_current": 4.1, "ma_attributed_lives": 2200},
    "Skilled Nursing":    {"readmission_30d": 0.205, "complication_rate": 0.12, "smr": 1.12,
                           "star_current": 3.1, "ma_attributed_lives": 3500},
    "ASC":                {"readmission_30d": 0.025, "complication_rate": 0.018, "smr": 0.85,
                           "star_current": 0, "ma_attributed_lives": 0},
    "Orthopedics":        {"readmission_30d": 0.035, "complication_rate": 0.028, "smr": 0.88,
                           "star_current": 0, "ma_attributed_lives": 2500},
    "Cardiology":         {"readmission_30d": 0.115, "complication_rate": 0.055, "smr": 0.92,
                           "star_current": 0, "ma_attributed_lives": 4000},
    "Oncology":           {"readmission_30d": 0.145, "complication_rate": 0.085, "smr": 1.00,
                           "star_current": 0, "ma_attributed_lives": 3200},
    "Dialysis":           {"readmission_30d": 0.28, "complication_rate": 0.14, "smr": 1.05,
                           "star_current": 3.7, "ma_attributed_lives": 1800},
    "Behavioral Health":  {"readmission_30d": 0.185, "complication_rate": 0.0, "smr": 0.95,
                           "star_current": 3.4, "ma_attributed_lives": 6500},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OutcomeMetric:
    metric: str
    current_value: float
    unit: str
    benchmark: float
    target: float
    percentile: float
    trend: str
    quality_bonus_trigger: bool


@dataclass
class StarProgression:
    year: int
    star_rating: float
    ma_bonus_eligible: bool
    bonus_bps: int
    pmpm_bonus: float
    annual_bonus_mm: float


@dataclass
class ComplicationBreakdown:
    complication: str
    current_rate: float
    benchmark_rate: float
    avg_cost_per_event: float
    annual_events: int
    annual_cost_mm: float


@dataclass
class VBCContract:
    payer: str
    contract_type: str              # "Upside-only", "Two-sided", "Full risk"
    covered_lives: int
    upside_quality_pool_mm: float
    downside_risk_mm: float
    current_performance: str
    expected_payout_mm: float


@dataclass
class QualityROI:
    initiative: str
    one_time_cost_mm: float
    annual_benefit_mm: float
    payback_months: int
    ev_impact_mm: float


@dataclass
class ClinicalOutcomesResult:
    sector: str
    composite_quality_score: float
    ma_star_rating: float
    star_bonus_opportunity_mm: float
    readmission_vs_benchmark_bp: int
    metrics: List[OutcomeMetric]
    star_progression: List[StarProgression]
    complications: List[ComplicationBreakdown]
    vbc_contracts: List[VBCContract]
    quality_roi: List[QualityROI]
    total_annual_quality_bonus_mm: float
    total_ev_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 72):
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


def _get_profile(sector: str) -> Dict:
    return _SECTOR_OUTCOMES.get(sector, _SECTOR_OUTCOMES["Physician Services"])


def _build_metrics(sector: str, profile: Dict) -> List[OutcomeMetric]:
    rows = []
    # Readmission
    if profile["readmission_30d"] > 0:
        rows.append(OutcomeMetric(
            metric="30-Day Readmission Rate",
            current_value=profile["readmission_30d"] * 100,
            unit="%",
            benchmark=profile["readmission_30d"] * 100,
            target=profile["readmission_30d"] * 100 * 0.85,
            percentile=55,
            trend="improving",
            quality_bonus_trigger=True,
        ))
    # Complications
    if profile["complication_rate"] > 0:
        rows.append(OutcomeMetric(
            metric="Surgical Complication Rate",
            current_value=profile["complication_rate"] * 100,
            unit="%",
            benchmark=profile["complication_rate"] * 100,
            target=profile["complication_rate"] * 100 * 0.80,
            percentile=50,
            trend="stable",
            quality_bonus_trigger=True,
        ))
    # SMR
    rows.append(OutcomeMetric(
        metric="Standardized Mortality Ratio",
        current_value=profile["smr"],
        unit="SMR",
        benchmark=1.00,
        target=0.92,
        percentile=60 if profile["smr"] < 1 else 40,
        trend="improving",
        quality_bonus_trigger=True,
    ))
    # Star rating
    if profile["star_current"] > 0:
        rows.append(OutcomeMetric(
            metric="CMS Star Rating",
            current_value=profile["star_current"],
            unit="stars",
            benchmark=3.5,
            target=4.5,
            percentile=62,
            trend="improving",
            quality_bonus_trigger=True,
        ))
    # Patient Experience (HCAHPS)
    rows.append(OutcomeMetric(
        metric="Patient Experience (HCAHPS)",
        current_value=82,
        unit="pct",
        benchmark=78,
        target=90,
        percentile=68,
        trend="improving",
        quality_bonus_trigger=True,
    ))
    # ED visits per 1K MA members
    if profile["ma_attributed_lives"] > 0:
        rows.append(OutcomeMetric(
            metric="ED Visits / 1K MA Members",
            current_value=215,
            unit="per 1K",
            benchmark=235,
            target=180,
            percentile=58,
            trend="improving",
            quality_bonus_trigger=True,
        ))
    # Advanced Care Planning
    rows.append(OutcomeMetric(
        metric="Advance Care Planning Rate",
        current_value=68,
        unit="%",
        benchmark=60,
        target=85,
        percentile=62,
        trend="improving",
        quality_bonus_trigger=False,
    ))
    return rows


def _build_star_progression(profile: Dict) -> List[StarProgression]:
    if profile["star_current"] <= 0:
        return []
    rows = []
    ma_lives = profile["ma_attributed_lives"]
    # Year 0 = current
    current_stars = profile["star_current"]
    projected = [current_stars, current_stars + 0.1, current_stars + 0.3, current_stars + 0.4, min(5.0, current_stars + 0.5)]
    for i, stars in enumerate(projected):
        eligible = stars >= 4.0
        bps = 500 if stars >= 5.0 else (500 if stars >= 4.5 else (500 if stars >= 4.0 else 0))
        pmpm = bps / 10000 * 12 * 90   # bps × 12 mo × $90 pmpm
        annual = pmpm * ma_lives / 1_000_000
        rows.append(StarProgression(
            year=i,
            star_rating=round(stars, 2),
            ma_bonus_eligible=eligible,
            bonus_bps=bps,
            pmpm_bonus=round(pmpm, 2) if eligible else 0,
            annual_bonus_mm=round(annual, 2) if eligible else 0,
        ))
    return rows


def _build_complications(profile: Dict, revenue_mm: float) -> List[ComplicationBreakdown]:
    if profile["complication_rate"] <= 0:
        return []
    # Synthesize complications
    total_procedures = int(revenue_mm * 1_000_000 / 8500)    # $8500 avg procedure
    complications_def = [
        ("Surgical Site Infection", profile["complication_rate"] * 0.35, 32000),
        ("Post-op Readmission", profile["complication_rate"] * 0.28, 18000),
        ("Deep Vein Thrombosis", profile["complication_rate"] * 0.15, 25000),
        ("Pneumonia", profile["complication_rate"] * 0.10, 28000),
        ("Urinary Retention", profile["complication_rate"] * 0.06, 8000),
        ("Bleeding / Transfusion", profile["complication_rate"] * 0.06, 18000),
    ]
    rows = []
    for comp, rate, cost in complications_def:
        events = int(total_procedures * rate)
        annual_cost = events * cost / 1_000_000
        rows.append(ComplicationBreakdown(
            complication=comp,
            current_rate=round(rate, 4),
            benchmark_rate=round(rate * 0.80, 4),
            avg_cost_per_event=round(cost, 0),
            annual_events=events,
            annual_cost_mm=round(annual_cost, 2),
        ))
    return rows


def _build_vbc(profile: Dict, revenue_mm: float) -> List[VBCContract]:
    ma_lives = profile["ma_attributed_lives"]
    rows = [
        VBCContract(
            payer="UnitedHealthcare MA",
            contract_type="Two-sided",
            covered_lives=int(ma_lives * 0.32),
            upside_quality_pool_mm=round(revenue_mm * 0.018, 2),
            downside_risk_mm=round(revenue_mm * 0.012, 2),
            current_performance="On track (+$1.8M YTD)",
            expected_payout_mm=round(revenue_mm * 0.012, 2),
        ),
        VBCContract(
            payer="Humana MA",
            contract_type="Upside-only",
            covered_lives=int(ma_lives * 0.24),
            upside_quality_pool_mm=round(revenue_mm * 0.012, 2),
            downside_risk_mm=0,
            current_performance="On track (+$800K YTD)",
            expected_payout_mm=round(revenue_mm * 0.008, 2),
        ),
        VBCContract(
            payer="Aetna MA",
            contract_type="Two-sided",
            covered_lives=int(ma_lives * 0.18),
            upside_quality_pool_mm=round(revenue_mm * 0.010, 2),
            downside_risk_mm=round(revenue_mm * 0.006, 2),
            current_performance="At risk (lagging)",
            expected_payout_mm=round(revenue_mm * 0.003, 2),
        ),
        VBCContract(
            payer="Medicare MSSP (ACO)",
            contract_type="Upside-only",
            covered_lives=int(ma_lives * 0.16),
            upside_quality_pool_mm=round(revenue_mm * 0.008, 2),
            downside_risk_mm=0,
            current_performance="Likely (+$600K)",
            expected_payout_mm=round(revenue_mm * 0.005, 2),
        ),
        VBCContract(
            payer="BCBS Commercial P4P",
            contract_type="Upside-only",
            covered_lives=int(ma_lives * 0.10),
            upside_quality_pool_mm=round(revenue_mm * 0.005, 2),
            downside_risk_mm=0,
            current_performance="On track",
            expected_payout_mm=round(revenue_mm * 0.004, 2),
        ),
    ]
    return rows


def _build_quality_roi(revenue_mm: float, exit_multiple: float) -> List[QualityROI]:
    items = [
        ("Readmission Reduction Program", 0.35, 0.85, 5, 0.85 * exit_multiple),
        ("Patient Satisfaction / HCAHPS Prog.", 0.18, 0.42, 5, 0.42 * exit_multiple),
        ("Star Rating 4→4.5 Initiative", 1.2, 2.8, 5, 2.8 * exit_multiple),
        ("Clinical Documentation Improvement", 0.22, 0.55, 5, 0.55 * exit_multiple),
        ("ACO Infrastructure Build", 0.85, 1.4, 7, 1.4 * exit_multiple),
        ("Care Gap Closure Team", 0.28, 0.65, 5, 0.65 * exit_multiple),
    ]
    rows = []
    for init, cost, benefit, months, ev in items:
        rows.append(QualityROI(
            initiative=init,
            one_time_cost_mm=round(cost, 2),
            annual_benefit_mm=round(benefit, 2),
            payback_months=months,
            ev_impact_mm=round(ev, 1),
        ))
    return rows


def _composite_score(metrics: List[OutcomeMetric]) -> float:
    if not metrics:
        return 50
    return round(sum(m.percentile for m in metrics) / len(metrics), 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_clinical_outcomes(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> ClinicalOutcomesResult:
    corpus = _load_corpus()
    profile = _get_profile(sector)

    metrics = _build_metrics(sector, profile)
    stars = _build_star_progression(profile)
    comps = _build_complications(profile, revenue_mm)
    vbc = _build_vbc(profile, revenue_mm)
    roi = _build_quality_roi(revenue_mm, exit_multiple)

    composite = _composite_score(metrics)

    total_annual = sum(v.expected_payout_mm for v in vbc)
    total_star = stars[-1].annual_bonus_mm if stars else 0
    total_readmission_savings = sum(c.annual_cost_mm for c in comps) * 0.25    # 25% of complications are avoidable
    total_quality_bonus = total_annual + total_star

    total_ev = (total_quality_bonus + total_readmission_savings) * exit_multiple
    readmission_bp = int((profile["readmission_30d"] - profile["readmission_30d"] * 0.85) * 10000)

    return ClinicalOutcomesResult(
        sector=sector,
        composite_quality_score=composite,
        ma_star_rating=profile["star_current"],
        star_bonus_opportunity_mm=round(total_star, 2),
        readmission_vs_benchmark_bp=readmission_bp,
        metrics=metrics,
        star_progression=stars,
        complications=comps,
        vbc_contracts=vbc,
        quality_roi=roi,
        total_annual_quality_bonus_mm=round(total_quality_bonus, 2),
        total_ev_impact_mm=round(total_ev, 1),
        corpus_deal_count=len(corpus),
    )
