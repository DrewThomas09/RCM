"""Medicaid Redetermination / Coverage Unwinding Tracker.

Tracks portfolio impact of Medicaid unwinding (PHE end + redetermination):
disenrollment, coverage shifts, revenue impact, self-pay bad debt.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class DealUnwinding:
    deal: str
    sector: str
    pre_phe_medicaid_pct: float
    current_medicaid_pct: float
    medicaid_patients_lost_k: float
    coverage_shift_pct: dict
    revenue_impact_m: float
    mitigation: str


@dataclass
class StateRollup:
    state: str
    disenrolled_m: float
    total_medicaid_pre_phe_m: float
    disenroll_rate_pct: float
    procedural_disenroll_pct: float
    coverage_gain_aca_pct: float
    back_to_medicaid_pct: float
    portfolio_deals: int


@dataclass
class CoverageShift:
    from_coverage: str
    to_coverage: str
    members_shifted_m: float
    revenue_per_patient_delta: int
    portfolio_impact_m: float
    retention_strategy: str


@dataclass
class OperationalMetric:
    deal: str
    self_pay_ar_days: int
    self_pay_collection_pct: float
    charity_care_growth_pct: float
    financial_assistance_apps: int
    average_settlement_pct: float
    bad_debt_growth_pct: float


@dataclass
class RetentionProgram:
    program: str
    portfolio_deals: int
    members_assisted_k: int
    re_enrolled_medicaid_pct: float
    aca_enrolled_pct: float
    self_pay_converted_pct: float
    cost_per_member: float
    revenue_preserved_m: float


@dataclass
class StateTimeline:
    state: str
    unwinding_start: str
    first_renewals: str
    projected_end: str
    total_disenrolled_k: int
    current_pace: str
    policy_posture: str


@dataclass
class MedicaidResult:
    total_deals_exposed: int
    total_medicaid_lives_pre_phe_m: float
    total_disenrolled_m: float
    total_revenue_impact_m: float
    avg_coverage_shift_back_pct: float
    active_retention_programs: int
    deals: List[DealUnwinding]
    states: List[StateRollup]
    shifts: List[CoverageShift]
    operational: List[OperationalMetric]
    programs: List[RetentionProgram]
    timelines: List[StateTimeline]
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


def _build_deals() -> List[DealUnwinding]:
    return [
        DealUnwinding("Project Cypress — GI Network", "Gastroenterology", 0.225, 0.185, 12.5,
                      {"aca": 0.42, "commercial_employer": 0.18, "self_pay": 0.28, "back_medicaid": 0.12},
                      -5.8, "in-house enrollment assistance + sliding scale"),
        DealUnwinding("Project Redwood — Behavioral", "Behavioral Health", 0.385, 0.285, 18.5,
                      {"aca": 0.35, "commercial_employer": 0.08, "self_pay": 0.42, "back_medicaid": 0.15},
                      -12.5, "charity care expansion + CCBHC enrollment"),
        DealUnwinding("Project Laurel — Derma", "Dermatology", 0.125, 0.095, 6.8,
                      {"aca": 0.38, "commercial_employer": 0.22, "self_pay": 0.32, "back_medicaid": 0.08},
                      -2.8, "sliding scale + patient assistance"),
        DealUnwinding("Project Cedar — Cardiology", "Cardiology", 0.245, 0.205, 15.2,
                      {"aca": 0.48, "commercial_employer": 0.15, "self_pay": 0.25, "back_medicaid": 0.12},
                      -6.8, "enrollment assistance + charity care"),
        DealUnwinding("Project Willow — Fertility", "Fertility / IVF", 0.065, 0.045, 2.2,
                      {"aca": 0.25, "commercial_employer": 0.32, "self_pay": 0.38, "back_medicaid": 0.05},
                      -1.8, "sliding scale + IVF financing"),
        DealUnwinding("Project Spruce — Radiology", "Radiology", 0.275, 0.225, 18.5,
                      {"aca": 0.42, "commercial_employer": 0.12, "self_pay": 0.32, "back_medicaid": 0.14},
                      -3.5, "charity care + patient assistance"),
        DealUnwinding("Project Aspen — Eye Care", "Eye Care", 0.145, 0.115, 8.5,
                      {"aca": 0.35, "commercial_employer": 0.18, "self_pay": 0.38, "back_medicaid": 0.09},
                      -2.2, "sliding scale + VSP partnership"),
        DealUnwinding("Project Maple — Urology", "Urology", 0.195, 0.165, 4.8,
                      {"aca": 0.45, "commercial_employer": 0.15, "self_pay": 0.28, "back_medicaid": 0.12},
                      -1.8, "enrollment assistance"),
        DealUnwinding("Project Sage — Home Health", "Home Health", 0.485, 0.425, 28.5,
                      {"aca": 0.25, "commercial_employer": 0.05, "self_pay": 0.45, "back_medicaid": 0.25},
                      -18.5, "back-to-Medicaid enrollment + Medicaid rate advocacy"),
        DealUnwinding("Project Linden — Behavioral", "Behavioral Health", 0.425, 0.325, 18.2,
                      {"aca": 0.32, "commercial_employer": 0.05, "self_pay": 0.45, "back_medicaid": 0.18},
                      -10.5, "CCBHC expansion + charity care"),
        DealUnwinding("Project Basil — Dental DSO", "Dental DSO", 0.185, 0.135, 14.5,
                      {"aca": 0.25, "commercial_employer": 0.18, "self_pay": 0.48, "back_medicaid": 0.09},
                      -4.5, "membership pricing + patient financing"),
        DealUnwinding("Project Magnolia — MSK Platform", "MSK / Ortho", 0.175, 0.155, 8.2,
                      {"aca": 0.48, "commercial_employer": 0.18, "self_pay": 0.25, "back_medicaid": 0.09},
                      -2.8, "enrollment assistance + charity care"),
    ]


def _build_states() -> List[StateRollup]:
    return [
        StateRollup("California", 2850.0, 14250.0, 0.200, 0.285, 0.45, 0.18, 4),
        StateRollup("Texas", 2180.0, 6250.0, 0.349, 0.485, 0.28, 0.08, 3),
        StateRollup("Florida", 1850.0, 5250.0, 0.352, 0.475, 0.32, 0.10, 3),
        StateRollup("New York", 1250.0, 7850.0, 0.159, 0.225, 0.48, 0.22, 2),
        StateRollup("Pennsylvania", 985.0, 3850.0, 0.256, 0.325, 0.42, 0.15, 2),
        StateRollup("Ohio", 825.0, 3250.0, 0.254, 0.315, 0.38, 0.16, 2),
        StateRollup("Georgia", 725.0, 2650.0, 0.274, 0.425, 0.32, 0.12, 2),
        StateRollup("Michigan", 625.0, 2750.0, 0.227, 0.285, 0.42, 0.18, 2),
        StateRollup("North Carolina", 625.0, 2850.0, 0.219, 0.295, 0.45, 0.15, 3),
        StateRollup("Illinois", 585.0, 3450.0, 0.170, 0.215, 0.48, 0.22, 2),
        StateRollup("Arizona", 485.0, 2250.0, 0.216, 0.325, 0.38, 0.14, 2),
        StateRollup("Indiana", 385.0, 1950.0, 0.197, 0.285, 0.42, 0.16, 1),
        StateRollup("Tennessee", 365.0, 1650.0, 0.221, 0.352, 0.32, 0.12, 2),
        StateRollup("Massachusetts", 325.0, 1950.0, 0.167, 0.185, 0.55, 0.25, 1),
        StateRollup("Virginia", 285.0, 1850.0, 0.154, 0.225, 0.48, 0.18, 1),
    ]


def _build_shifts() -> List[CoverageShift]:
    return [
        CoverageShift("Medicaid", "ACA Exchange (subsidized)", 4.85, 125, 32.5, "enrollment assistance + premium tax credits"),
        CoverageShift("Medicaid", "Employer Commercial", 2.85, 485, 35.5, "employer outreach + ESI verification"),
        CoverageShift("Medicaid", "Self-Pay / Uninsured", 5.25, -650, -42.5, "charity care + sliding scale + patient financing"),
        CoverageShift("Medicaid", "Back to Medicaid (re-enrolled)", 2.85, 0, 0.0, "re-enrollment outreach + state advocacy"),
        CoverageShift("Medicaid", "Medicare (age-up)", 0.85, 185, 4.2, "Medicare transition planning"),
        CoverageShift("Medicaid", "Other State Program", 0.45, -50, -1.2, "state-specific assistance programs"),
    ]


def _build_operational() -> List[OperationalMetric]:
    return [
        OperationalMetric("Project Cypress — GI Network", 68, 0.525, 0.285, 4850, 0.625, 0.185),
        OperationalMetric("Project Redwood — Behavioral", 95, 0.385, 0.425, 8250, 0.485, 0.325),
        OperationalMetric("Project Laurel — Derma", 48, 0.685, 0.185, 2850, 0.725, 0.112),
        OperationalMetric("Project Cedar — Cardiology", 72, 0.482, 0.325, 6250, 0.585, 0.218),
        OperationalMetric("Project Willow — Fertility", 42, 0.785, 0.095, 1850, 0.785, 0.082),
        OperationalMetric("Project Spruce — Radiology", 82, 0.425, 0.245, 5450, 0.525, 0.225),
        OperationalMetric("Project Aspen — Eye Care", 58, 0.625, 0.185, 3250, 0.685, 0.128),
        OperationalMetric("Project Maple — Urology", 55, 0.595, 0.198, 2850, 0.648, 0.155),
        OperationalMetric("Project Sage — Home Health", 115, 0.325, 0.485, 10850, 0.385, 0.425),
        OperationalMetric("Project Linden — Behavioral", 105, 0.352, 0.385, 6850, 0.425, 0.368),
        OperationalMetric("Project Basil — Dental DSO", 48, 0.625, 0.225, 5250, 0.625, 0.185),
        OperationalMetric("Project Magnolia — MSK Platform", 52, 0.625, 0.185, 4850, 0.685, 0.135),
    ]


def _build_programs() -> List[RetentionProgram]:
    return [
        RetentionProgram("In-House Enrollment Assistance", 12, 185, 0.35, 0.42, 0.23, 48, 18.5),
        RetentionProgram("Community Partner Navigator (CPN)", 8, 125, 0.32, 0.48, 0.20, 28, 12.5),
        RetentionProgram("Patient Assistance Program (Med Access)", 10, 85, 0.22, 0.35, 0.43, 55, 8.5),
        RetentionProgram("Sliding Scale / Financial Counseling", 12, 245, 0.15, 0.25, 0.60, 18, 15.5),
        RetentionProgram("Charity Care Expansion", 10, 165, 0.18, 0.22, 0.60, 12, 11.5),
        RetentionProgram("Employer ESI Outreach", 5, 45, 0.12, 0.28, 0.60, 32, 6.5),
        RetentionProgram("Back-to-Medicaid Re-enrollment", 8, 135, 0.82, 0.12, 0.06, 22, 22.5),
        RetentionProgram("CCBHC-Mediated Behavioral Continuity", 2, 42, 0.45, 0.38, 0.17, 45, 8.5),
    ]


def _build_timelines() -> List[StateTimeline]:
    return [
        StateTimeline("California", "2023-06-01", "2023-06-01", "2025-12-31", 3250, "moderating",
                      "pro-beneficiary; 180+ day procedural hold"),
        StateTimeline("Texas", "2023-04-01", "2023-04-01", "2024-12-31", 2485, "accelerated",
                      "procedural disenrollment high; expediting"),
        StateTimeline("Florida", "2023-04-01", "2023-04-01", "2024-12-31", 2085, "accelerated",
                      "procedural disenrollment high"),
        StateTimeline("New York", "2023-07-01", "2023-07-01", "2026-06-30", 1385, "slow",
                      "pro-beneficiary; extensions granted"),
        StateTimeline("Pennsylvania", "2023-05-01", "2023-05-01", "2025-06-30", 1085, "moderating",
                      "balanced approach"),
        StateTimeline("Ohio", "2023-05-01", "2023-05-01", "2025-03-31", 925, "moderating",
                      "balanced approach"),
        StateTimeline("Georgia", "2023-04-01", "2023-04-01", "2024-09-30", 785, "accelerated",
                      "procedural disenrollment high"),
        StateTimeline("Michigan", "2023-06-01", "2023-06-01", "2025-06-30", 685, "moderating",
                      "balanced approach"),
        StateTimeline("North Carolina", "2023-07-01", "2023-07-01", "2025-06-30", 685, "moderating",
                      "expansion state — more re-enrollment"),
        StateTimeline("Illinois", "2023-07-01", "2023-07-01", "2025-12-31", 685, "slow",
                      "pro-beneficiary; careful outreach"),
        StateTimeline("Arizona", "2023-04-01", "2023-04-01", "2024-12-31", 585, "accelerated",
                      "procedural issues early; stabilizing"),
        StateTimeline("Indiana", "2023-05-01", "2023-05-01", "2025-06-30", 465, "moderating",
                      "balanced approach"),
    ]


def compute_medicaid_unwinding() -> MedicaidResult:
    corpus = _load_corpus()
    deals = _build_deals()
    states = _build_states()
    shifts = _build_shifts()
    operational = _build_operational()
    programs = _build_programs()
    timelines = _build_timelines()

    total_pre_phe = sum(s.total_medicaid_pre_phe_m for s in states) / 1000.0
    total_disenroll = sum(s.disenrolled_m for s in states) / 1000.0
    total_rev_impact = sum(d.revenue_impact_m for d in deals)
    avg_back_to = sum(d.coverage_shift_pct.get("back_medicaid", 0) for d in deals) / len(deals) if deals else 0

    return MedicaidResult(
        total_deals_exposed=len(deals),
        total_medicaid_lives_pre_phe_m=round(total_pre_phe, 2),
        total_disenrolled_m=round(total_disenroll, 2),
        total_revenue_impact_m=round(total_rev_impact, 1),
        avg_coverage_shift_back_pct=round(avg_back_to, 4),
        active_retention_programs=len(programs),
        deals=deals,
        states=states,
        shifts=shifts,
        operational=operational,
        programs=programs,
        timelines=timelines,
        corpus_deal_count=len(corpus),
    )
