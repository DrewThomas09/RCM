"""Healthcare SaaS / HCIT Platform Analyzer.

Models SaaS-style healthcare technology platforms: ARR, NRR, LTV/CAC,
magic number, rule-of-40, payer/provider customer mix, TAM penetration.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CustomerSegment:
    segment: str
    customer_count: int
    acv_k: float
    annual_arr_mm: float
    nrr_pct: float
    gross_churn_pct: float
    ltv_k: float
    cac_payback_months: int


@dataclass
class ProductLine:
    product: str
    category: str
    arr_mm: float
    growth_yoy_pct: float
    gross_margin_pct: float
    users: int


@dataclass
class SaaSMetric:
    metric: str
    current: float
    benchmark_top_quartile: float
    benchmark_median: float
    unit: str
    percentile: int


@dataclass
class TAMAnalysis:
    sub_tam: str
    tam_mm: float
    serviceable_tam_mm: float
    current_penetration_pct: float
    y3_target_penetration_pct: float
    revenue_opportunity_mm: float


@dataclass
class CompetitorComp:
    company: str
    arr_mm: float
    growth_yoy_pct: float
    ev_revenue_multiple: float
    implied_ev_mm: float
    profile: str


@dataclass
class HCITResult:
    total_arr_mm: float
    arr_growth_pct: float
    total_nrr_pct: float
    total_gross_margin_pct: float
    rule_of_40_score: float
    magic_number: float
    total_customers: int
    segments: List[CustomerSegment]
    products: List[ProductLine]
    metrics: List[SaaSMetric]
    tam: List[TAMAnalysis]
    comps: List[CompetitorComp]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 98):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_segments() -> List[CustomerSegment]:
    return [
        CustomerSegment("Large Health Systems (>$1B)", 35, 425.0, 14.88, 1.12, 0.02, 2850.0, 14),
        CustomerSegment("Regional Health Systems", 85, 165.0, 14.03, 1.08, 0.04, 1180.0, 17),
        CustomerSegment("Medical Groups (200+ providers)", 245, 62.0, 15.19, 1.06, 0.06, 485.0, 19),
        CustomerSegment("ASC / Specialty Networks", 185, 32.0, 5.92, 1.04, 0.08, 285.0, 22),
        CustomerSegment("Payers (MA / Commercial)", 42, 385.0, 16.17, 1.15, 0.03, 2620.0, 15),
        CustomerSegment("PE-Backed Platforms", 68, 185.0, 12.58, 1.18, 0.05, 1485.0, 13),
        CustomerSegment("Academic Medical Centers", 22, 245.0, 5.39, 1.05, 0.02, 1820.0, 20),
    ]


def _build_products() -> List[ProductLine]:
    return [
        ProductLine("Core Analytics Platform", "Analytics", 32.5, 0.28, 0.82, 850),
        ProductLine("Population Health Module", "Clinical", 18.5, 0.42, 0.78, 420),
        ProductLine("Quality Measures Reporting", "Regulatory", 12.5, 0.22, 0.85, 620),
        ProductLine("Payer Contract Analytics", "Financial", 8.5, 0.55, 0.80, 185),
        ProductLine("Risk Adjustment / HCC Coding", "Clinical", 10.5, 0.68, 0.75, 340),
        ProductLine("Clinical Trial Matching", "Research", 4.5, 0.85, 0.82, 125),
        ProductLine("Provider Directory / Credentialing", "Admin", 6.8, 0.18, 0.88, 480),
    ]


def _build_metrics() -> List[SaaSMetric]:
    return [
        SaaSMetric("ARR Growth YoY", 0.38, 0.45, 0.25, "pct", 72),
        SaaSMetric("Net Revenue Retention", 1.12, 1.20, 1.05, "mult", 62),
        SaaSMetric("Gross Revenue Retention", 0.94, 0.96, 0.88, "mult", 68),
        SaaSMetric("Gross Margin", 0.78, 0.85, 0.72, "pct", 70),
        SaaSMetric("Rule of 40", 0.52, 0.65, 0.40, "pct", 68),
        SaaSMetric("Magic Number", 1.35, 1.50, 0.85, "mult", 72),
        SaaSMetric("CAC Payback Months", 17, 13, 21, "inv_pct", 68),
        SaaSMetric("LTV / CAC", 5.2, 6.5, 3.8, "mult", 65),
        SaaSMetric("FCF Margin", 0.14, 0.25, 0.05, "pct", 68),
        SaaSMetric("Sales Efficiency", 0.82, 1.10, 0.60, "mult", 65),
    ]


def _build_tam() -> List[TAMAnalysis]:
    return [
        TAMAnalysis("Provider Analytics Platform", 8500.0, 3200.0, 0.009, 0.045, 115.2),
        TAMAnalysis("Payer Risk Adjustment", 4200.0, 1650.0, 0.006, 0.032, 42.9),
        TAMAnalysis("Quality Reporting / Stars", 2800.0, 1050.0, 0.012, 0.055, 45.2),
        TAMAnalysis("Clinical Trial Recruitment", 1850.0, 580.0, 0.008, 0.035, 15.7),
        TAMAnalysis("Population Health Management", 5200.0, 2100.0, 0.009, 0.042, 69.3),
        TAMAnalysis("Value-Based Care Enablement", 3400.0, 1250.0, 0.010, 0.048, 47.5),
    ]


def _build_comps() -> List[CompetitorComp]:
    return [
        CompetitorComp("Veeva Systems (public)", 2850.0, 0.16, 12.5, 35625.0, "life-sci SaaS leader"),
        CompetitorComp("Doximity (public)", 510.0, 0.18, 8.2, 4182.0, "physician network monetization"),
        CompetitorComp("Definitive Healthcare (public)", 285.0, 0.08, 3.8, 1083.0, "provider data / commercial intel"),
        CompetitorComp("Health Catalyst (public)", 290.0, 0.04, 2.5, 725.0, "analytics / data warehouse"),
        CompetitorComp("HealthEdge (PE / Bain)", 425.0, 0.32, 12.0, 5100.0, "payer core system"),
        CompetitorComp("Cotiviti (PE / Veritas)", 1250.0, 0.14, 8.8, 11000.0, "payer analytics / integrity"),
        CompetitorComp("Clario (PE / Astorg/Nordic)", 725.0, 0.22, 9.5, 6888.0, "clinical trial tech"),
        CompetitorComp("Evolent (public)", 2150.0, 0.35, 3.2, 6880.0, "VBC enablement"),
        CompetitorComp("Signify Health (CVS acq)", 900.0, 0.42, 10.5, 9450.0, "in-home clinical visits"),
        CompetitorComp("Olive AI (shutdown 2023)", 0.0, -1.0, 0.0, 0.0, "cautionary tale / RIP"),
    ]


def compute_hcit_platform() -> HCITResult:
    corpus = _load_corpus()
    segments = _build_segments()
    products = _build_products()
    metrics = _build_metrics()
    tam = _build_tam()
    comps = _build_comps()

    total_arr = sum(s.annual_arr_mm for s in segments)
    total_customers = sum(s.customer_count for s in segments)

    nrr = sum(s.nrr_pct * s.annual_arr_mm for s in segments) / total_arr if total_arr else 0
    # Derive growth, gross margin, rule of 40, magic number from metrics
    growth = next((m.current for m in metrics if m.metric == "ARR Growth YoY"), 0.38)
    gm = next((m.current for m in metrics if m.metric == "Gross Margin"), 0.78)
    r40 = next((m.current for m in metrics if m.metric == "Rule of 40"), 0.52)
    mn = next((m.current for m in metrics if m.metric == "Magic Number"), 1.35)

    return HCITResult(
        total_arr_mm=round(total_arr, 2),
        arr_growth_pct=round(growth, 4),
        total_nrr_pct=round(nrr, 4),
        total_gross_margin_pct=round(gm, 4),
        rule_of_40_score=round(r40, 4),
        magic_number=round(mn, 3),
        total_customers=total_customers,
        segments=segments,
        products=products,
        metrics=metrics,
        tam=tam,
        comps=comps,
        corpus_deal_count=len(corpus),
    )
