"""ESG / Impact Reporting Tracker.

Tracks ESG performance across portfolio companies: clinical access,
patient outcomes, workforce DEI, emissions, board diversity, compliance
with PRI / ILPA / SASB frameworks.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ESGScorecard:
    deal: str
    sector: str
    environmental_score: float
    social_score: float
    governance_score: float
    composite_score: float
    prior_year_score: float
    year_over_year_change: float
    sasb_materiality_met: bool


@dataclass
class PatientAccessMetric:
    deal: str
    medicaid_pct: float
    uninsured_charity_care_m: float
    sliding_scale_patients_k: float
    avg_wait_days: float
    no_show_rate_pct: float
    language_support_count: int


@dataclass
class ClinicalOutcome:
    deal: str
    sector: str
    hedis_composite: float
    cms_stars_equivalent: float
    readmission_rate_pct: float
    patient_satisfaction: float
    clinical_guideline_adherence_pct: float
    sentinel_events: int


@dataclass
class WorkforceDEI:
    deal: str
    total_employees: int
    female_pct: float
    poc_pct: float
    female_leadership_pct: float
    poc_leadership_pct: float
    turnover_rate_pct: float
    engagement_score: float
    living_wage_compliant: bool


@dataclass
class EmissionsMetric:
    deal: str
    scope_1_mtco2e: float
    scope_2_mtco2e: float
    scope_3_mtco2e: float
    intensity_per_patient: float
    renewable_electricity_pct: float
    sbti_commitment: str
    reduction_vs_baseline_pct: float


@dataclass
class GovernanceMetric:
    deal: str
    independent_directors_pct: float
    board_diversity_pct: float
    ethics_hotline: bool
    annual_csr_report: bool
    dsh_assessment: bool
    whistleblower_claims_resolved: int
    compliance_training_pct: float


@dataclass
class FrameworkCompliance:
    framework: str
    version: str
    portfolio_deals: int
    compliant_deals: int
    avg_maturity: float
    next_reporting: str


@dataclass
class ESGResult:
    total_portcos: int
    avg_composite_score: float
    total_charity_care_m: float
    total_medicaid_patients_k: float
    total_scope_12_mtco2e: float
    prior_year_delta: float
    frameworks_tracked: int
    scorecards: List[ESGScorecard]
    access: List[PatientAccessMetric]
    outcomes: List[ClinicalOutcome]
    dei: List[WorkforceDEI]
    emissions: List[EmissionsMetric]
    governance: List[GovernanceMetric]
    frameworks: List[FrameworkCompliance]
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


def _build_scorecards() -> List[ESGScorecard]:
    return [
        ESGScorecard("Project Cypress — GI Network", "Gastroenterology", 7.2, 8.5, 8.8, 8.3, 7.8, 0.5, True),
        ESGScorecard("Project Magnolia — MSK Platform", "MSK / Ortho", 7.5, 8.2, 8.5, 8.1, 7.5, 0.6, True),
        ESGScorecard("Project Redwood — Behavioral", "Behavioral Health", 7.0, 9.0, 7.8, 8.0, 7.5, 0.5, True),
        ESGScorecard("Project Laurel — Derma", "Dermatology", 7.8, 7.5, 8.2, 7.8, 7.3, 0.5, True),
        ESGScorecard("Project Cedar — Cardiology", "Cardiology", 7.5, 8.8, 8.6, 8.3, 7.8, 0.5, True),
        ESGScorecard("Project Willow — Fertility", "Fertility / IVF", 7.2, 8.5, 8.0, 7.9, 7.2, 0.7, True),
        ESGScorecard("Project Spruce — Radiology", "Radiology", 7.0, 7.8, 8.2, 7.7, 7.2, 0.5, True),
        ESGScorecard("Project Aspen — Eye Care", "Eye Care", 7.8, 7.8, 7.5, 7.7, 7.0, 0.7, True),
        ESGScorecard("Project Maple — Urology", "Urology", 7.2, 7.5, 8.0, 7.6, 7.0, 0.6, True),
        ESGScorecard("Project Ash — Infusion", "Infusion", 7.5, 8.8, 8.5, 8.3, 7.8, 0.5, True),
        ESGScorecard("Project Fir — Lab / Pathology", "Lab Services", 7.8, 8.0, 8.5, 8.1, 7.5, 0.6, True),
        ESGScorecard("Project Sage — Home Health", "Home Health", 6.8, 8.8, 7.5, 7.7, 7.2, 0.5, True),
        ESGScorecard("Project Linden — Behavioral", "Behavioral Health", 7.0, 8.5, 7.8, 7.8, 7.2, 0.6, True),
        ESGScorecard("Project Oak — RCM SaaS", "RCM / HCIT", 8.5, 7.5, 9.2, 8.4, 8.0, 0.4, True),
        ESGScorecard("Project Basil — Dental DSO", "Dental DSO", 7.5, 7.8, 8.0, 7.8, 7.3, 0.5, True),
        ESGScorecard("Project Thyme — Specialty Pharm", "Specialty Pharma", 7.2, 8.2, 8.5, 8.0, 7.5, 0.5, True),
    ]


def _build_access() -> List[PatientAccessMetric]:
    return [
        PatientAccessMetric("Project Cypress — GI Network", 0.185, 12.5, 28.5, 8.5, 0.075, 8),
        PatientAccessMetric("Project Magnolia — MSK Platform", 0.155, 8.2, 22.0, 12.5, 0.082, 7),
        PatientAccessMetric("Project Redwood — Behavioral", 0.285, 18.5, 38.5, 14.2, 0.125, 12),
        PatientAccessMetric("Project Laurel — Derma", 0.095, 3.5, 12.5, 10.2, 0.068, 5),
        PatientAccessMetric("Project Cedar — Cardiology", 0.205, 15.2, 32.0, 7.2, 0.078, 9),
        PatientAccessMetric("Project Willow — Fertility", 0.045, 2.5, 5.8, 22.5, 0.112, 6),
        PatientAccessMetric("Project Spruce — Radiology", 0.225, 8.5, 25.5, 5.8, 0.062, 8),
        PatientAccessMetric("Project Aspen — Eye Care", 0.115, 5.2, 18.5, 9.5, 0.098, 7),
        PatientAccessMetric("Project Maple — Urology", 0.165, 7.2, 18.5, 11.2, 0.085, 6),
        PatientAccessMetric("Project Ash — Infusion", 0.095, 3.2, 8.5, 6.5, 0.042, 6),
        PatientAccessMetric("Project Fir — Lab / Pathology", 0.185, 6.5, 22.0, 4.5, 0.035, 8),
        PatientAccessMetric("Project Sage — Home Health", 0.425, 12.5, 45.5, 0.0, 0.085, 9),
        PatientAccessMetric("Project Linden — Behavioral", 0.385, 15.5, 32.0, 16.5, 0.115, 11),
        PatientAccessMetric("Project Basil — Dental DSO", 0.145, 6.2, 28.5, 8.5, 0.092, 7),
        PatientAccessMetric("Project Thyme — Specialty Pharm", 0.085, 4.5, 12.0, 3.2, 0.038, 7),
    ]


def _build_outcomes() -> List[ClinicalOutcome]:
    return [
        ClinicalOutcome("Project Cypress — GI Network", "Gastroenterology", 0.86, 4.3, 0.045, 4.6, 0.92, 0),
        ClinicalOutcome("Project Magnolia — MSK Platform", "MSK / Ortho", 0.84, 4.2, 0.058, 4.5, 0.89, 0),
        ClinicalOutcome("Project Redwood — Behavioral", "Behavioral Health", 0.82, 4.1, 0.095, 4.2, 0.86, 0),
        ClinicalOutcome("Project Laurel — Derma", "Dermatology", 0.88, 4.4, 0.032, 4.7, 0.91, 0),
        ClinicalOutcome("Project Cedar — Cardiology", "Cardiology", 0.87, 4.3, 0.085, 4.5, 0.93, 0),
        ClinicalOutcome("Project Willow — Fertility", "Fertility / IVF", 0.82, 4.0, 0.028, 4.6, 0.90, 0),
        ClinicalOutcome("Project Spruce — Radiology", "Radiology", 0.86, 4.3, 0.022, 4.4, 0.94, 0),
        ClinicalOutcome("Project Aspen — Eye Care", "Eye Care", 0.85, 4.2, 0.032, 4.5, 0.91, 0),
        ClinicalOutcome("Project Maple — Urology", "Urology", 0.84, 4.2, 0.048, 4.5, 0.90, 0),
        ClinicalOutcome("Project Ash — Infusion", "Infusion", 0.88, 4.4, 0.038, 4.7, 0.95, 0),
        ClinicalOutcome("Project Fir — Lab / Pathology", "Lab Services", 0.90, 4.5, 0.018, 4.7, 0.96, 0),
        ClinicalOutcome("Project Sage — Home Health", "Home Health", 0.83, 4.1, 0.085, 4.4, 0.88, 1),
        ClinicalOutcome("Project Linden — Behavioral", "Behavioral Health", 0.81, 4.0, 0.108, 4.1, 0.85, 1),
    ]


def _build_dei() -> List[WorkforceDEI]:
    return [
        WorkforceDEI("Project Cypress — GI Network", 2850, 0.68, 0.45, 0.52, 0.38, 0.128, 7.8, True),
        WorkforceDEI("Project Magnolia — MSK Platform", 2150, 0.62, 0.42, 0.48, 0.35, 0.135, 7.5, True),
        WorkforceDEI("Project Redwood — Behavioral", 1850, 0.82, 0.52, 0.65, 0.48, 0.185, 7.2, True),
        WorkforceDEI("Project Laurel — Derma", 1150, 0.85, 0.38, 0.72, 0.32, 0.095, 8.2, True),
        WorkforceDEI("Project Cedar — Cardiology", 1650, 0.65, 0.48, 0.42, 0.38, 0.105, 7.8, True),
        WorkforceDEI("Project Willow — Fertility", 850, 0.88, 0.42, 0.75, 0.38, 0.115, 8.0, True),
        WorkforceDEI("Project Spruce — Radiology", 1450, 0.58, 0.44, 0.38, 0.38, 0.095, 7.6, True),
        WorkforceDEI("Project Aspen — Eye Care", 1250, 0.72, 0.38, 0.55, 0.32, 0.118, 7.4, True),
        WorkforceDEI("Project Maple — Urology", 750, 0.55, 0.42, 0.32, 0.35, 0.122, 7.2, True),
        WorkforceDEI("Project Ash — Infusion", 1850, 0.78, 0.48, 0.58, 0.42, 0.095, 8.0, True),
        WorkforceDEI("Project Fir — Lab / Pathology", 2450, 0.68, 0.52, 0.52, 0.45, 0.088, 7.8, True),
        WorkforceDEI("Project Sage — Home Health", 3850, 0.92, 0.68, 0.75, 0.55, 0.285, 6.8, True),
        WorkforceDEI("Project Linden — Behavioral", 1650, 0.82, 0.58, 0.62, 0.48, 0.225, 7.0, True),
        WorkforceDEI("Project Oak — RCM SaaS", 850, 0.52, 0.48, 0.42, 0.42, 0.068, 8.5, True),
    ]


def _build_emissions() -> List[EmissionsMetric]:
    return [
        EmissionsMetric("Project Cypress — GI Network", 1250.0, 2850.0, 14500.0, 0.125, 0.42, "SBTi validated 2025", -0.18),
        EmissionsMetric("Project Magnolia — MSK Platform", 850.0, 2100.0, 11200.0, 0.098, 0.35, "SBTi committed", -0.12),
        EmissionsMetric("Project Redwood — Behavioral", 950.0, 2450.0, 12800.0, 0.088, 0.28, "committed to commit", -0.05),
        EmissionsMetric("Project Laurel — Derma", 325.0, 880.0, 4800.0, 0.045, 0.48, "SBTi committed", -0.08),
        EmissionsMetric("Project Cedar — Cardiology", 1150.0, 2650.0, 13500.0, 0.115, 0.32, "committed to commit", -0.10),
        EmissionsMetric("Project Willow — Fertility", 180.0, 450.0, 2800.0, 0.055, 0.58, "SBTi committed", -0.15),
        EmissionsMetric("Project Spruce — Radiology", 2850.0, 7200.0, 18500.0, 0.335, 0.40, "SBTi committed", -0.22),
        EmissionsMetric("Project Aspen — Eye Care", 385.0, 950.0, 5200.0, 0.068, 0.35, "not committed", -0.04),
        EmissionsMetric("Project Maple — Urology", 215.0, 520.0, 2900.0, 0.068, 0.25, "not committed", -0.02),
        EmissionsMetric("Project Ash — Infusion", 485.0, 1250.0, 6800.0, 0.055, 0.48, "SBTi committed", -0.12),
        EmissionsMetric("Project Fir — Lab / Pathology", 1850.0, 4500.0, 15800.0, 0.245, 0.42, "SBTi validated 2025", -0.20),
        EmissionsMetric("Project Sage — Home Health", 485.0, 1180.0, 3200.0, 0.022, 0.25, "not committed", -0.03),
    ]


def _build_governance() -> List[GovernanceMetric]:
    return [
        GovernanceMetric("Project Cypress — GI Network", 0.43, 0.43, True, True, True, 8, 1.00),
        GovernanceMetric("Project Magnolia — MSK Platform", 0.43, 0.43, True, True, True, 5, 0.98),
        GovernanceMetric("Project Redwood — Behavioral", 0.38, 0.50, True, True, True, 12, 0.95),
        GovernanceMetric("Project Laurel — Derma", 0.43, 0.43, True, True, False, 4, 0.97),
        GovernanceMetric("Project Cedar — Cardiology", 0.43, 0.29, True, True, True, 6, 1.00),
        GovernanceMetric("Project Willow — Fertility", 0.43, 0.57, True, True, True, 3, 1.00),
        GovernanceMetric("Project Spruce — Radiology", 0.38, 0.25, True, False, True, 4, 0.95),
        GovernanceMetric("Project Aspen — Eye Care", 0.43, 0.29, True, False, False, 3, 0.92),
        GovernanceMetric("Project Maple — Urology", 0.38, 0.25, True, False, False, 2, 0.90),
        GovernanceMetric("Project Ash — Infusion", 0.50, 0.43, True, True, True, 5, 0.98),
        GovernanceMetric("Project Fir — Lab / Pathology", 0.43, 0.43, True, True, True, 6, 1.00),
        GovernanceMetric("Project Sage — Home Health", 0.43, 0.43, True, True, True, 9, 0.98),
        GovernanceMetric("Project Linden — Behavioral", 0.43, 0.43, True, True, False, 7, 0.95),
        GovernanceMetric("Project Oak — RCM SaaS", 0.43, 0.43, True, True, True, 2, 1.00),
    ]


def _build_frameworks() -> List[FrameworkCompliance]:
    return [
        FrameworkCompliance("ILPA Template (Principles 3.0)", "3.0", 16, 16, 0.95, "Q2 2026"),
        FrameworkCompliance("PRI Annual Reporting", "2025", 16, 14, 0.88, "2026-03-31 (complete)"),
        FrameworkCompliance("SASB Healthcare Standards", "2024", 16, 15, 0.92, "2026-Q2"),
        FrameworkCompliance("CSRD (EU)", "2024", 3, 2, 0.65, "2026-Q3"),
        FrameworkCompliance("SEC Climate Rule (pending)", "2024 proposed", 16, 8, 0.48, "rulemaking delay"),
        FrameworkCompliance("TCFD Climate Risk", "2021", 16, 14, 0.85, "2026-Q3"),
        FrameworkCompliance("SBTi Corporate Net-Zero", "1.0", 16, 10, 0.62, "ongoing"),
        FrameworkCompliance("CDP Climate / Water", "2025", 16, 13, 0.80, "2026-07-31"),
    ]


def compute_esg_impact() -> ESGResult:
    corpus = _load_corpus()
    scorecards = _build_scorecards()
    access = _build_access()
    outcomes = _build_outcomes()
    dei = _build_dei()
    emissions = _build_emissions()
    governance = _build_governance()
    frameworks = _build_frameworks()

    avg_score = sum(s.composite_score for s in scorecards) / len(scorecards) if scorecards else 0
    total_charity = sum(a.uninsured_charity_care_m for a in access)
    total_medicaid = sum(a.medicaid_pct * 1.0 for a in access)
    avg_medicaid = total_medicaid / len(access) if access else 0
    total_scope12 = sum(e.scope_1_mtco2e + e.scope_2_mtco2e for e in emissions)
    avg_delta = sum(s.year_over_year_change for s in scorecards) / len(scorecards) if scorecards else 0

    return ESGResult(
        total_portcos=len(scorecards),
        avg_composite_score=round(avg_score, 2),
        total_charity_care_m=round(total_charity, 1),
        total_medicaid_patients_k=round(avg_medicaid * 100, 1),
        total_scope_12_mtco2e=round(total_scope12, 1),
        prior_year_delta=round(avg_delta, 2),
        frameworks_tracked=len(frameworks),
        scorecards=scorecards,
        access=access,
        outcomes=outcomes,
        dei=dei,
        emissions=emissions,
        governance=governance,
        frameworks=frameworks,
        corpus_deal_count=len(corpus),
    )
