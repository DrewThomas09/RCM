"""Health Equity / SDOH Scorecard.

Models CMS Health Equity Index (HEI) components for MA plans and VBC
providers. Critical because HEI replaced the Reward Factor in 2027+ Stars
calculations, making equity performance directly tied to bonus payments.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class HEIComponent:
    measure: str
    domain: str
    lis_dual_performance: float
    non_lis_performance: float
    gap_pct: float
    weight_in_hei: float
    points_available: int


@dataclass
class SDOHScreening:
    domain: str
    screened_pct: float
    positive_screen_pct: float
    referral_closed_loop_pct: float
    intervention_cost_pmpy: float
    roi_score: int


@dataclass
class EquityInvestment:
    initiative: str
    category: str
    annual_cost_mm: float
    lives_impacted: int
    measurable_outcome: str
    hei_points_delta: float
    star_bonus_impact_mm: float


@dataclass
class DemographicSegment:
    segment: str
    population_000: int
    avg_raf: float
    preventive_utilization_pct: float
    ed_utilization_per_1000: int
    hedis_composite: float
    disparity_flag: bool


@dataclass
class HEIResult:
    total_attributed_lives: int
    lis_dual_pct: float
    overall_hei_score: float
    hei_points_current: float
    hei_bonus_potential_mm: float
    hei_components: List[HEIComponent]
    sdoh: List[SDOHScreening]
    investments: List[EquityInvestment]
    demographics: List[DemographicSegment]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 102):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_hei_components() -> List[HEIComponent]:
    return [
        HEIComponent("Breast Cancer Screening", "Preventive", 0.68, 0.78, 0.10, 0.12, 10),
        HEIComponent("Colorectal Cancer Screening", "Preventive", 0.62, 0.72, 0.10, 0.12, 10),
        HEIComponent("Controlling Blood Pressure", "Chronic", 0.58, 0.71, 0.13, 0.15, 12),
        HEIComponent("Diabetes Care - HbA1c Poor Control", "Chronic", 0.32, 0.22, -0.10, 0.15, 12),
        HEIComponent("Eye Exam for Diabetics", "Chronic", 0.65, 0.75, 0.10, 0.10, 10),
        HEIComponent("Transitions of Care - Discharge Review", "Care Coordination", 0.52, 0.72, 0.20, 0.08, 8),
        HEIComponent("Follow-Up After ED Visit (BH)", "Behavioral", 0.42, 0.55, 0.13, 0.08, 8),
        HEIComponent("Osteoporosis Mgmt (Women 67-85)", "Preventive", 0.28, 0.45, 0.17, 0.05, 5),
        HEIComponent("Flu Vaccine (65+)", "Preventive", 0.72, 0.80, 0.08, 0.08, 8),
        HEIComponent("Plan All-Cause Readmission", "Utilization", 0.22, 0.14, -0.08, 0.07, 7),
    ]


def _build_sdoh() -> List[SDOHScreening]:
    return [
        SDOHScreening("Food Insecurity", 0.52, 0.28, 0.42, 185.0, 72),
        SDOHScreening("Housing Instability", 0.45, 0.18, 0.35, 385.0, 68),
        SDOHScreening("Transportation", 0.62, 0.22, 0.68, 125.0, 78),
        SDOHScreening("Utility Needs", 0.38, 0.14, 0.45, 85.0, 62),
        SDOHScreening("Interpersonal Safety", 0.48, 0.08, 0.52, 225.0, 65),
        SDOHScreening("Social Isolation", 0.42, 0.25, 0.38, 95.0, 60),
        SDOHScreening("Financial Strain", 0.55, 0.32, 0.28, 145.0, 58),
        SDOHScreening("Health Literacy", 0.72, 0.38, 0.55, 55.0, 72),
    ]


def _build_investments() -> List[EquityInvestment]:
    return [
        EquityInvestment("Transportation Partnership (Lyft/Uber Health)", "Access", 1.8, 42000, "12% ED reduction for non-drivers", 0.22, 2.85),
        EquityInvestment("Community Health Worker Program", "Access", 3.2, 28500, "18pp HEDIS uplift in target ZIPs", 0.38, 4.25),
        EquityInvestment("Food Pantry / Produce Rx", "Nutrition", 2.1, 15800, "1.2-point HbA1c reduction", 0.28, 3.15),
        EquityInvestment("Medicare-Medicaid Dual Care Coordinator", "Coordination", 4.5, 18500, "22% readmit reduction for duals", 0.42, 5.20),
        EquityInvestment("Language Line / Translator Services", "Access", 1.2, 125000, "30% LEP closed-gap uplift", 0.18, 2.15),
        EquityInvestment("Mobile Clinic (Rural/Urban Gap)", "Access", 2.8, 8500, "42% new-PCP visits", 0.32, 3.45),
        EquityInvestment("Behavioral Integration at FQHC", "Behavioral", 3.5, 22000, "55% improvement in follow-up rate", 0.48, 5.85),
        EquityInvestment("Rx Assistance / $0 Copay Program", "Pharmacy", 2.4, 85000, "18% adherence lift", 0.25, 2.95),
    ]


def _build_demographics() -> List[DemographicSegment]:
    return [
        DemographicSegment("LIS / Dual Eligibles", 28.5, 1.62, 0.58, 482, 0.68, True),
        DemographicSegment("Non-LIS Medicare", 62.5, 1.08, 0.72, 285, 0.81, False),
        DemographicSegment("Hispanic / Latino", 18.2, 1.14, 0.62, 395, 0.72, True),
        DemographicSegment("Black / African American", 14.5, 1.28, 0.55, 465, 0.69, True),
        DemographicSegment("Asian / Pacific Islander", 8.8, 0.95, 0.78, 225, 0.85, False),
        DemographicSegment("Rural Residents", 22.5, 1.22, 0.54, 412, 0.71, True),
        DemographicSegment("English Limited Proficiency (LEP)", 12.8, 1.18, 0.48, 445, 0.65, True),
        DemographicSegment("Disabled Under-65 Medicare", 8.5, 1.85, 0.52, 625, 0.62, True),
    ]


def compute_health_equity() -> HEIResult:
    corpus = _load_corpus()

    components = _build_hei_components()
    sdoh = _build_sdoh()
    investments = _build_investments()
    demographics = _build_demographics()

    total_lives = sum(d.population_000 * 1000 for d in demographics)
    lis_pct = next((d.population_000 * 1000 / total_lives for d in demographics if d.segment == "LIS / Dual Eligibles"), 0)

    # HEI score: higher is better, 0-1 scale
    total_weight = sum(c.weight_in_hei for c in components)
    hei_score = sum(c.weight_in_hei * (1 - abs(c.gap_pct)) for c in components) / total_weight if total_weight else 0

    # HEI points current - max 100
    hei_points = hei_score * 100
    # Bonus potential: each 0.5 Star uplift ~$50M per 100k lives
    bonus_potential = sum(i.star_bonus_impact_mm for i in investments)

    return HEIResult(
        total_attributed_lives=total_lives,
        lis_dual_pct=round(lis_pct, 4),
        overall_hei_score=round(hei_score, 3),
        hei_points_current=round(hei_points, 1),
        hei_bonus_potential_mm=round(bonus_potential, 2),
        hei_components=components,
        sdoh=sdoh,
        investments=investments,
        demographics=demographics,
        corpus_deal_count=len(corpus),
    )
