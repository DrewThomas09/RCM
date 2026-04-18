"""Workforce Turnover / Retention Tracker.

Tracks clinical + support workforce turnover, retention programs,
engagement, contract labor exposure across portfolio.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class TurnoverByRole:
    role: str
    total_headcount: int
    annual_turnover_pct: float
    industry_benchmark_pct: float
    replacement_cost_k: float
    replacement_time_days: int
    critical: bool


@dataclass
class DealTurnover:
    deal: str
    sector: str
    total_headcount: int
    overall_turnover_pct: float
    clinical_turnover_pct: float
    support_turnover_pct: float
    contract_labor_pct: float
    engagement_score: float
    retention_spend_m: float


@dataclass
class RetentionProgram:
    program: str
    portfolio_deals: int
    employees_covered: int
    annual_cost_m: float
    turnover_impact_pp: float
    rationale: str


@dataclass
class ContractLaborMetric:
    deal: str
    agency_spend_m: float
    agency_pct_of_labor: float
    premium_vs_staff_pct: float
    peak_quarters: str
    transition_to_staff_k: int
    savings_opportunity_m: float


@dataclass
class EngagementSurvey:
    deal: str
    response_rate_pct: float
    engagement_score: float
    ennp_score: float
    burnout_rate_pct: float
    would_recommend_pct: float
    top_3_concerns: str


@dataclass
class BenefitsBenchmark:
    benefit: str
    p25: str
    median: str
    p75: str
    portfolio_median: str
    adoption_rate_pct: float


@dataclass
class WorkforceResult:
    total_headcount: int
    weighted_turnover_pct: float
    avg_engagement_score: float
    total_contract_labor_spend_m: float
    total_retention_spend_m: float
    critical_roles: int
    roles: List[TurnoverByRole]
    deals: List[DealTurnover]
    programs: List[RetentionProgram]
    contract_labor: List[ContractLaborMetric]
    surveys: List[EngagementSurvey]
    benefits: List[BenefitsBenchmark]
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


def _build_roles() -> List[TurnoverByRole]:
    return [
        TurnoverByRole("RN — Bedside / Clinical", 8500, 0.225, 0.250, 88.5, 95, True),
        TurnoverByRole("RN — OR / Specialty", 1850, 0.165, 0.185, 125.0, 115, True),
        TurnoverByRole("RN — ICU / Critical Care", 485, 0.195, 0.215, 135.0, 125, True),
        TurnoverByRole("RN — Infusion / Oncology", 385, 0.125, 0.145, 85.0, 95, True),
        TurnoverByRole("LPN / LVN", 2250, 0.285, 0.315, 55.0, 65, False),
        TurnoverByRole("Medical Assistant", 4850, 0.345, 0.385, 32.0, 45, False),
        TurnoverByRole("Scope Technician", 485, 0.185, 0.215, 48.0, 60, True),
        TurnoverByRole("Cath Lab RN/Tech", 285, 0.165, 0.195, 115.0, 105, True),
        TurnoverByRole("Echo Technologist", 225, 0.175, 0.205, 85.0, 95, True),
        TurnoverByRole("Radiology Tech", 1850, 0.195, 0.225, 72.0, 85, True),
        TurnoverByRole("CT / MRI Tech", 685, 0.155, 0.185, 95.0, 105, True),
        TurnoverByRole("Physician Assistant (PA)", 625, 0.145, 0.165, 125.0, 120, False),
        TurnoverByRole("Nurse Practitioner (NP)", 1285, 0.155, 0.175, 115.0, 115, False),
        TurnoverByRole("Behavioral Tech / MHP", 985, 0.325, 0.365, 42.0, 55, True),
        TurnoverByRole("Therapist (PT / OT / SLP)", 1250, 0.185, 0.215, 72.0, 90, False),
        TurnoverByRole("Pharmacy Tech / Clinical Pharm", 485, 0.195, 0.225, 85.0, 95, False),
        TurnoverByRole("Anesthesia Tech", 185, 0.145, 0.165, 68.0, 85, False),
        TurnoverByRole("Surgical Tech / OR Scrub", 785, 0.205, 0.235, 62.0, 80, True),
        TurnoverByRole("Phlebotomist", 1250, 0.385, 0.425, 28.0, 35, False),
        TurnoverByRole("Housekeeping / EVS", 1850, 0.485, 0.525, 25.0, 30, False),
        TurnoverByRole("Food Service", 985, 0.425, 0.465, 25.0, 30, False),
        TurnoverByRole("Front Desk / Scheduling", 2450, 0.285, 0.325, 28.0, 40, False),
        TurnoverByRole("Billing / Coding Specialist", 985, 0.195, 0.235, 48.0, 60, False),
        TurnoverByRole("IT / Systems Support", 385, 0.125, 0.155, 95.0, 110, False),
        TurnoverByRole("Case Manager / Care Coord", 685, 0.155, 0.185, 68.0, 80, False),
    ]


def _build_deals() -> List[DealTurnover]:
    return [
        DealTurnover("Project Cypress — GI Network", "Gastroenterology", 2850, 0.185, 0.165, 0.225, 0.052, 7.8, 2.8),
        DealTurnover("Project Magnolia — MSK Platform", "MSK / Ortho", 2150, 0.195, 0.175, 0.245, 0.068, 7.5, 2.2),
        DealTurnover("Project Redwood — Behavioral", "Behavioral Health", 1850, 0.285, 0.315, 0.235, 0.125, 7.2, 3.5),
        DealTurnover("Project Laurel — Derma", "Dermatology", 1150, 0.145, 0.125, 0.185, 0.028, 8.2, 1.2),
        DealTurnover("Project Cedar — Cardiology", "Cardiology", 1650, 0.165, 0.145, 0.205, 0.055, 7.8, 2.5),
        DealTurnover("Project Willow — Fertility", "Fertility / IVF", 850, 0.135, 0.115, 0.175, 0.038, 8.0, 1.5),
        DealTurnover("Project Spruce — Radiology", "Radiology", 1450, 0.185, 0.175, 0.205, 0.042, 7.6, 2.2),
        DealTurnover("Project Aspen — Eye Care", "Eye Care", 1250, 0.175, 0.155, 0.215, 0.048, 7.4, 1.8),
        DealTurnover("Project Maple — Urology", "Urology", 750, 0.185, 0.165, 0.225, 0.045, 7.2, 1.2),
        DealTurnover("Project Ash — Infusion", "Infusion", 1850, 0.145, 0.125, 0.185, 0.038, 8.0, 2.8),
        DealTurnover("Project Fir — Lab / Pathology", "Lab Services", 2450, 0.175, 0.155, 0.215, 0.045, 7.8, 2.5),
        DealTurnover("Project Sage — Home Health", "Home Health", 3850, 0.385, 0.425, 0.315, 0.165, 6.8, 5.8),
        DealTurnover("Project Linden — Behavioral", "Behavioral Health", 1650, 0.325, 0.365, 0.255, 0.125, 7.0, 3.2),
        DealTurnover("Project Oak — RCM SaaS", "RCM / HCIT", 850, 0.125, 0.095, 0.145, 0.012, 8.5, 1.5),
        DealTurnover("Project Basil — Dental DSO", "Dental DSO", 1850, 0.225, 0.215, 0.245, 0.052, 7.5, 2.2),
        DealTurnover("Project Thyme — Specialty Pharm", "Specialty Pharma", 1250, 0.155, 0.135, 0.195, 0.035, 8.0, 1.8),
    ]


def _build_programs() -> List[RetentionProgram]:
    return [
        RetentionProgram("Sign-On Bonus (RN / specialty)", 16, 1850, 18.5, -3.5, "offset to fill critical vacancies"),
        RetentionProgram("Loan Repayment (tenure-based)", 14, 2450, 12.5, -4.2, "CRNAs, specialty RNs, therapists"),
        RetentionProgram("Career Ladder / Clinical Ladder", 16, 8500, 8.5, -2.8, "structured advancement + salary steps"),
        RetentionProgram("Tuition Reimbursement", 14, 6250, 12.5, -2.5, "nursing school + advanced degrees"),
        RetentionProgram("Childcare / Dependent Care", 6, 2850, 4.5, -2.2, "on-site or subsidized childcare"),
        RetentionProgram("Clinical Housing Stipend", 4, 485, 2.8, -3.8, "high-COL markets — NYC, SF, BOS"),
        RetentionProgram("Mental Health / Burnout Prevention", 16, 12500, 5.5, -3.2, "EAP + therapy + psychological safety programs"),
        RetentionProgram("Flexible Scheduling / Remote", 14, 15500, 0.0, -4.5, "self-scheduling + hybrid for eligible roles"),
        RetentionProgram("Premium Pay (differential)", 16, 5250, 28.5, -1.8, "shift diff, weekend, holiday, float pool"),
        RetentionProgram("Retention Bonus (longevity)", 14, 10250, 18.5, -2.5, "3/5/7-year vesting bonuses"),
        RetentionProgram("Staff Recognition / Peer Awards", 16, 28500, 1.2, -1.5, "Cleveland Clinic-model peer recognition"),
        RetentionProgram("Leadership Development (high-potential)", 12, 1850, 3.2, -2.5, "ICU/ED/OR leadership track"),
    ]


def _build_contract_labor() -> List[ContractLaborMetric]:
    return [
        ContractLaborMetric("Project Cypress — GI Network", 8.5, 0.052, 0.85, "Q3, Q4", 125, 4.2),
        ContractLaborMetric("Project Magnolia — MSK Platform", 11.2, 0.068, 0.95, "Q2, Q3", 155, 5.8),
        ContractLaborMetric("Project Redwood — Behavioral", 22.5, 0.125, 1.05, "Q3, Q4", 225, 11.5),
        ContractLaborMetric("Project Laurel — Derma", 3.2, 0.028, 0.55, "Q3", 45, 1.5),
        ContractLaborMetric("Project Cedar — Cardiology", 9.8, 0.055, 0.88, "Q3, Q4", 115, 4.8),
        ContractLaborMetric("Project Spruce — Radiology", 7.8, 0.042, 0.75, "Q3, Q4", 95, 3.5),
        ContractLaborMetric("Project Aspen — Eye Care", 6.2, 0.048, 0.78, "Q3", 85, 3.2),
        ContractLaborMetric("Project Sage — Home Health", 48.5, 0.165, 1.25, "Q3, Q4", 485, 28.5),
        ContractLaborMetric("Project Linden — Behavioral", 22.5, 0.125, 1.15, "Q3, Q4", 195, 11.8),
        ContractLaborMetric("Project Basil — Dental DSO", 8.2, 0.052, 0.65, "Q4", 125, 3.5),
        ContractLaborMetric("Project Fir — Lab / Pathology", 11.5, 0.045, 0.72, "Q3, Q4", 135, 4.8),
        ContractLaborMetric("Project Ash — Infusion", 8.2, 0.038, 0.75, "Q3", 105, 3.8),
    ]


def _build_surveys() -> List[EngagementSurvey]:
    return [
        EngagementSurvey("Project Cypress — GI Network", 0.78, 7.8, 42, 0.185, 0.78, "staffing ratios, EHR burden, comp"),
        EngagementSurvey("Project Magnolia — MSK Platform", 0.82, 7.5, 35, 0.225, 0.74, "surgical volume, scheduling, comp"),
        EngagementSurvey("Project Redwood — Behavioral", 0.68, 7.2, 28, 0.285, 0.72, "safety, caseload, documentation burden"),
        EngagementSurvey("Project Laurel — Derma", 0.85, 8.2, 52, 0.115, 0.88, "growth opportunities, clinical autonomy"),
        EngagementSurvey("Project Cedar — Cardiology", 0.82, 7.8, 42, 0.155, 0.82, "call schedule, cath lab efficiency, comp"),
        EngagementSurvey("Project Willow — Fertility", 0.88, 8.0, 55, 0.108, 0.85, "patient outcomes, lab automation"),
        EngagementSurvey("Project Spruce — Radiology", 0.72, 7.6, 38, 0.165, 0.78, "reading volume, AI integration, comp"),
        EngagementSurvey("Project Aspen — Eye Care", 0.78, 7.4, 32, 0.195, 0.74, "ASC operations, optical integration"),
        EngagementSurvey("Project Maple — Urology", 0.72, 7.2, 25, 0.215, 0.72, "call coverage, OR block time"),
        EngagementSurvey("Project Ash — Infusion", 0.82, 8.0, 48, 0.135, 0.85, "patient complexity, pharmacy workflow"),
        EngagementSurvey("Project Fir — Lab / Pathology", 0.85, 7.8, 45, 0.125, 0.82, "automation, digital pathology, volume"),
        EngagementSurvey("Project Sage — Home Health", 0.55, 6.8, 15, 0.385, 0.58, "windshield time, Medicaid margins, documentation"),
        EngagementSurvey("Project Linden — Behavioral", 0.62, 7.0, 22, 0.325, 0.68, "safety, caseload, reimbursement"),
        EngagementSurvey("Project Oak — RCM SaaS", 0.92, 8.5, 62, 0.085, 0.90, "product velocity, comp equity, WFH"),
    ]


def _build_benefits() -> List[BenefitsBenchmark]:
    return [
        BenefitsBenchmark("Health Insurance Contribution", "60% employer", "70% employer", "82% employer", "72% employer", 0.98),
        BenefitsBenchmark("401(k) Match", "3%", "4% (100% up to 4%)", "6% (100% up to 6%)", "4% (100% up to 4%)", 0.85),
        BenefitsBenchmark("PTO Accrual (Year 1)", "15 days", "20 days", "25 days", "22 days", 1.00),
        BenefitsBenchmark("Parental Leave (Primary)", "6 weeks", "10 weeks", "16 weeks", "12 weeks", 0.88),
        BenefitsBenchmark("Parental Leave (Secondary)", "2 weeks", "4 weeks", "10 weeks", "6 weeks", 0.82),
        BenefitsBenchmark("Tuition Reimbursement (Annual)", "$3,500", "$5,250", "$10,000", "$5,250", 0.65),
        BenefitsBenchmark("Student Loan Repayment", "$0", "$3,600/yr", "$10,000/yr", "$3,600/yr", 0.38),
        BenefitsBenchmark("Mental Health Benefit", "6 visits/yr", "12 visits + EAP", "Unlimited + EAP", "12 visits + EAP", 0.92),
        BenefitsBenchmark("Childcare Benefit", "None", "$1,500/yr", "$5,000/yr on-site", "$2,500/yr", 0.28),
        BenefitsBenchmark("Commuter Benefit", "None", "$100/mo", "$300/mo", "$150/mo", 0.45),
        BenefitsBenchmark("Wellness Stipend", "None", "$500/yr", "$1,500/yr", "$500/yr", 0.55),
        BenefitsBenchmark("Short-Term Disability", "60% / 13 wk", "70% / 26 wk", "100% / 26 wk", "70% / 26 wk", 0.95),
    ]


def compute_workforce_retention() -> WorkforceResult:
    corpus = _load_corpus()
    roles = _build_roles()
    deals = _build_deals()
    programs = _build_programs()
    contract_labor = _build_contract_labor()
    surveys = _build_surveys()
    benefits = _build_benefits()

    total_hc = sum(d.total_headcount for d in deals)
    wtd_turnover = sum(d.overall_turnover_pct * d.total_headcount for d in deals) / total_hc if total_hc > 0 else 0
    avg_eng = sum(d.engagement_score for d in deals) / len(deals) if deals else 0
    total_cl = sum(c.agency_spend_m for c in contract_labor)
    total_ret = sum(d.retention_spend_m for d in deals)
    critical = sum(1 for r in roles if r.critical)

    return WorkforceResult(
        total_headcount=total_hc,
        weighted_turnover_pct=round(wtd_turnover, 4),
        avg_engagement_score=round(avg_eng, 2),
        total_contract_labor_spend_m=round(total_cl, 1),
        total_retention_spend_m=round(total_ret, 1),
        critical_roles=critical,
        roles=roles,
        deals=deals,
        programs=programs,
        contract_labor=contract_labor,
        surveys=surveys,
        benefits=benefits,
        corpus_deal_count=len(corpus),
    )
