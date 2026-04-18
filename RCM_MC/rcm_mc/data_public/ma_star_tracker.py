"""Medicare Advantage / Star Ratings Tracker.

Tracks MA plan star ratings (2-year lookback), rebates, benchmark
rates, risk adjustment, revenue yield — economics that determine
profitability of MA-focused platforms in the portfolio.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class MAPlan:
    plan: str
    parent: str
    states: str
    enrollment_k: float
    star_rating_2025: float
    star_rating_2026: float
    rebate_pct: float
    benchmark_pct: float
    mbr_pct: float
    mlr_pct: float
    quality_bonus_pct: float


@dataclass
class PortfolioExposureMA:
    deal: str
    sector: str
    primary_ma_partners: str
    at_risk_lives_k: float
    annual_capitation_m: float
    shared_savings_m: float
    quality_incentive_m: float
    total_ma_revenue_m: float


@dataclass
class StarsMetric:
    measure: str
    category: str
    weight: str
    industry_median: float
    top_quartile: float
    portfolio_measure: float
    trajectory: str


@dataclass
class RateBenchmark:
    region: str
    ma_benchmark_pmpm: float
    ffs_spend_pmpm: float
    ab_revenue_pmpm: float
    d_revenue_pmpm: float
    bid_vs_benchmark_pct: float


@dataclass
class RADVExposure:
    plan: str
    parent: str
    members_audited_k: float
    alleged_recovery_m: float
    status: str
    likely_exposure_m: float


@dataclass
class PolicyUpdate:
    update: str
    effective_date: str
    impact: str
    industry_dollar_b: float
    portfolio_impact_m: float


@dataclass
class MAResult:
    total_plans: int
    total_enrollment_m: float
    avg_star_rating: float
    pct_4star_plus: float
    total_portfolio_ma_revenue_m: float
    total_radv_exposure_m: float
    plans: List[MAPlan]
    exposures: List[PortfolioExposureMA]
    stars: List[StarsMetric]
    benchmarks: List[RateBenchmark]
    radv: List[RADVExposure]
    updates: List[PolicyUpdate]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_plans() -> List[MAPlan]:
    return [
        MAPlan("UnitedHealthcare MA / Optum", "UnitedHealth Group", "52 states", 9850.0, 4.5, 4.5,
               0.685, 1.085, 1.155, 0.845, 0.050),
        MAPlan("Humana MA", "Humana", "48 states", 5720.0, 4.0, 3.5,
               0.625, 1.060, 1.135, 0.865, 0.030),
        MAPlan("Aetna MA / CVS Health", "CVS Health", "46 states", 3450.0, 4.0, 4.0,
               0.615, 1.045, 1.125, 0.880, 0.050),
        MAPlan("BCBS MA (Anthem)", "Elevance Health", "22 states", 2180.0, 3.5, 4.0,
               0.555, 1.020, 1.095, 0.890, 0.045),
        MAPlan("Cigna MA (PartD)", "Cigna / The Cigna Group", "44 states", 560.0, 3.5, 3.5,
               0.525, 1.000, 1.080, 0.905, 0.000),
        MAPlan("Kaiser Permanente MA", "Kaiser Permanente", "8 states", 1890.0, 4.5, 5.0,
               0.725, 1.095, 1.175, 0.835, 0.050),
        MAPlan("Centene MA", "Centene Corp", "35 states", 1680.0, 3.0, 3.0,
               0.485, 0.985, 1.045, 0.925, 0.000),
        MAPlan("Molina MA", "Molina Healthcare", "18 states", 245.0, 3.0, 3.5,
               0.495, 0.990, 1.055, 0.915, 0.000),
        MAPlan("Alignment Healthcare", "Alignment Health", "4 states", 185.0, 4.0, 3.5,
               0.685, 1.085, 1.155, 0.820, 0.030),
        MAPlan("Clover Health", "Clover Health", "9 states", 95.0, 3.0, 3.5,
               0.515, 1.000, 1.070, 0.905, 0.000),
        MAPlan("Bright Health (remaining)", "Bright Health (wind-down)", "2 states", 5.0, 0.0, 0.0,
               0.0, 0.0, 0.0, 1.02, 0.000),
        MAPlan("Devoted Health", "Devoted Health", "14 states", 285.0, 4.5, 4.5,
               0.735, 1.085, 1.165, 0.825, 0.050),
        MAPlan("SCAN Health Plan", "SCAN Health", "5 states", 355.0, 4.0, 4.0,
               0.685, 1.055, 1.135, 0.855, 0.050),
        MAPlan("WellCare (Centene)", "Centene Corp", "35 states", 1550.0, 3.0, 3.0,
               0.475, 0.980, 1.040, 0.925, 0.000),
        MAPlan("Independence Blue Cross MA", "Independence Health Group", "PA/NJ", 285.0, 4.0, 4.0,
               0.625, 1.045, 1.125, 0.870, 0.050),
    ]


def _build_exposures() -> List[PortfolioExposureMA]:
    return [
        PortfolioExposureMA("Project Oak — RCM SaaS", "RCM / HCIT",
                            "All MA plans (platform)", 0.0, 0.0, 0.0, 0.0, 65.0),
        PortfolioExposureMA("Project Magnolia — MSK Platform", "MSK / Ortho",
                            "UHC, Humana, Aetna, BCBS", 145.0, 52.0, 8.5, 2.5, 63.0),
        PortfolioExposureMA("Project Cypress — GI Network", "Gastroenterology",
                            "UHC, Humana, Kaiser", 168.0, 68.0, 6.2, 1.8, 76.0),
        PortfolioExposureMA("Project Redwood — Behavioral", "Behavioral Health",
                            "UHC, Humana, Aetna", 118.0, 35.0, 4.5, 1.5, 41.0),
        PortfolioExposureMA("Project Cedar — Cardiology", "Cardiology",
                            "UHC, Humana, Aetna, BCBS", 195.0, 85.0, 8.2, 2.2, 95.4),
        PortfolioExposureMA("Project Sage — Home Health", "Home Health",
                            "UHC, Humana, Kaiser, Aetna", 128.0, 52.0, 12.5, 3.5, 68.0),
        PortfolioExposureMA("Project Linden — Behavioral", "Behavioral Health",
                            "UHC, Humana, Aetna, Alignment, SCAN", 88.0, 32.0, 3.8, 1.2, 37.0),
        PortfolioExposureMA("Project Spruce — Radiology", "Radiology",
                            "UHC, Humana, Aetna", 110.0, 22.0, 2.2, 0.8, 25.0),
        PortfolioExposureMA("Project Ash — Infusion", "Infusion",
                            "UHC, Humana, Aetna", 48.0, 18.0, 2.8, 1.0, 21.8),
        PortfolioExposureMA("Project Fir — Lab / Pathology", "Lab Services",
                            "UHC, Humana, Aetna, Kaiser, Cigna", 205.0, 42.0, 5.2, 1.5, 48.7),
        PortfolioExposureMA("Project Aspen — Eye Care", "Eye Care",
                            "UHC, Humana, BCBS", 85.0, 15.0, 1.2, 0.5, 16.7),
        PortfolioExposureMA("Project Maple — Urology", "Urology",
                            "UHC, Humana, Aetna", 78.0, 24.0, 2.8, 0.8, 27.6),
    ]


def _build_stars() -> List[StarsMetric]:
    return [
        StarsMetric("HEDIS / HOS / CAHPS Overall", "Clinical", "5x", 3.9, 4.5, 4.1, "stable"),
        StarsMetric("Breast Cancer Screening", "Part C", "1x", 0.72, 0.82, 0.74, "improving"),
        StarsMetric("Colorectal Cancer Screening", "Part C", "1x", 0.78, 0.86, 0.79, "improving"),
        StarsMetric("Osteoporosis Mgmt in Women (Frac)", "Part C", "1x", 0.41, 0.58, 0.45, "improving"),
        StarsMetric("Medication Adherence - Diabetes", "Part D", "3x", 0.85, 0.92, 0.87, "stable"),
        StarsMetric("Medication Adherence - RAS Antag", "Part D", "3x", 0.86, 0.93, 0.88, "stable"),
        StarsMetric("Medication Adherence - Statins", "Part D", "3x", 0.84, 0.91, 0.86, "stable"),
        StarsMetric("Diabetes Care - Blood Sugar", "Part C", "3x", 0.77, 0.89, 0.80, "improving"),
        StarsMetric("Controlling Blood Pressure", "Part C", "3x", 0.72, 0.84, 0.75, "improving"),
        StarsMetric("Rating of Health Care Quality", "CAHPS", "1.5x", 0.84, 0.90, 0.85, "stable"),
        StarsMetric("Getting Care Quickly", "CAHPS", "1.5x", 0.76, 0.83, 0.78, "stable"),
        StarsMetric("Care Coordination", "CAHPS", "1.5x", 0.82, 0.88, 0.83, "stable"),
        StarsMetric("Customer Service", "CAHPS", "1.5x", 0.85, 0.91, 0.86, "stable"),
        StarsMetric("Complaints about the Plan", "Complaints", "1.5x", 0.15, 0.08, 0.16, "watching"),
        StarsMetric("Health Equity Index (NEW)", "Clinical", "0.4x", 0.0, 0.0, 0.0, "launching 2027"),
    ]


def _build_benchmarks() -> List[RateBenchmark]:
    return [
        RateBenchmark("Manhattan (NYC)", 1420, 1285, 1198, 145, 0.883),
        RateBenchmark("Miami-Dade", 1385, 1265, 1152, 138, 0.845),
        RateBenchmark("Los Angeles County", 1325, 1180, 1115, 132, 0.862),
        RateBenchmark("Dallas-Fort Worth", 1158, 1042, 982, 118, 0.878),
        RateBenchmark("Chicago", 1125, 1018, 958, 115, 0.891),
        RateBenchmark("Atlanta", 985, 895, 845, 112, 0.900),
        RateBenchmark("Phoenix", 1048, 945, 895, 118, 0.906),
        RateBenchmark("Houston", 1095, 985, 935, 115, 0.895),
        RateBenchmark("Tampa", 1145, 1025, 968, 124, 0.894),
        RateBenchmark("Portland OR", 985, 895, 845, 115, 0.902),
        RateBenchmark("Denver", 935, 848, 795, 108, 0.898),
        RateBenchmark("Rural / High-Cost", 925, 865, 788, 105, 0.912),
    ]


def _build_radv() -> List[RADVExposure]:
    return [
        RADVExposure("UnitedHealthcare MA", "UnitedHealth Group", 485.0, 2850.0, "DOJ litigation", 1850.0),
        RADVExposure("Humana MA", "Humana", 320.0, 1680.0, "CMS extrapolation — challenged", 1125.0),
        RADVExposure("Elevance (Anthem) MA", "Elevance Health", 145.0, 985.0, "CMS audit — in review", 425.0),
        RADVExposure("Aetna MA", "CVS Health", 215.0, 1285.0, "DOJ investigation", 725.0),
        RADVExposure("Cigna MA", "The Cigna Group", 68.0, 485.0, "DOJ investigation", 285.0),
        RADVExposure("Centene Health MA", "Centene Corp", 85.0, 325.0, "CMS audit closed", 125.0),
        RADVExposure("Kaiser Permanente MA", "Kaiser Permanente", 125.0, 285.0, "DOJ investigation", 115.0),
        RADVExposure("Alignment Healthcare", "Alignment Health", 42.0, 145.0, "CMS audit — ongoing", 55.0),
    ]


def _build_updates() -> List[PolicyUpdate]:
    return [
        PolicyUpdate("2027 MA Advance Notice", "2026-02-01", "Benchmark growth +3.7%; MLR floor formula update", 850.0, 32.0),
        PolicyUpdate("RADV extrapolation rule takes effect", "2026-04-01", "Contract-level extrapolation retroactive 2018-2024", 7850.0, 185.0),
        PolicyUpdate("Health Equity Index launches", "2027-01-01", "New 0.4x weighted measure in Stars formula", 3200.0, 45.0),
        PolicyUpdate("Inflation Reduction Act Part D Redesign PY2", "2026-01-01", "Manufacturer discount restructure", 2800.0, 15.0),
        PolicyUpdate("Star Rating cut-point adjustment", "2026-10-01", "Tukey outlier removal — gentle trimming", 450.0, -8.0),
        PolicyUpdate("Risk Adjustment V28 Phase 3", "2026-01-01", "100% implementation of V28 model", 4500.0, 58.0),
        PolicyUpdate("2026 Marketing Rule", "2026-01-01", "Third-party marketing oversight tightened", 120.0, 0.5),
        PolicyUpdate("SDoH encounter data requirements", "2026-01-01", "Z-code submission required", 85.0, 2.5),
    ]


def compute_ma_star_tracker() -> MAResult:
    corpus = _load_corpus()
    plans = _build_plans()
    exposures = _build_exposures()
    stars = _build_stars()
    benchmarks = _build_benchmarks()
    radv = _build_radv()
    updates = _build_updates()

    total_enroll = sum(p.enrollment_k for p in plans)
    active = [p for p in plans if p.star_rating_2026 > 0]
    avg_star = sum(p.star_rating_2026 * p.enrollment_k for p in active) / sum(p.enrollment_k for p in active) if active else 0
    four_plus = sum(p.enrollment_k for p in active if p.star_rating_2026 >= 4.0)
    four_plus_pct = four_plus / sum(p.enrollment_k for p in active) if active else 0
    port_rev = sum(e.total_ma_revenue_m for e in exposures)
    radv_total = sum(r.likely_exposure_m for r in radv)

    return MAResult(
        total_plans=len(plans),
        total_enrollment_m=round(total_enroll / 1000, 2),
        avg_star_rating=round(avg_star, 2),
        pct_4star_plus=round(four_plus_pct, 4),
        total_portfolio_ma_revenue_m=round(port_rev, 1),
        total_radv_exposure_m=round(radv_total, 1),
        plans=plans,
        exposures=exposures,
        stars=stars,
        benchmarks=benchmarks,
        radv=radv,
        updates=updates,
        corpus_deal_count=len(corpus),
    )
