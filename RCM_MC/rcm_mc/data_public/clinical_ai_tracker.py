"""Clinical AI / ML Deployment Tracker.

Tracks AI and ML systems deployed in clinical workflows across
portfolio: vendors, FDA status, use cases, adoption metrics, ROI.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class AISystem:
    deal: str
    vendor: str
    product: str
    use_case: str
    fda_status: str
    clinical_domain: str
    deployment_date: str
    sites_deployed: int
    monthly_cases_k: int
    annual_license_m: float


@dataclass
class OutcomeMetric:
    system: str
    deal: str
    accuracy_pct: float
    sensitivity_pct: float
    specificity_pct: float
    time_saved_min_per_case: float
    revenue_impact_m: float
    clinician_satisfaction: float


@dataclass
class AdoptionMetric:
    deal: str
    total_clinicians: int
    trained_clinicians: int
    active_users: int
    daily_usage_pct: float
    override_rate_pct: float
    complaint_count: int


@dataclass
class FDASubmission:
    vendor: str
    product: str
    submission_type: str
    k_number: str
    cleared_date: str
    intended_use: str
    predicate: str


@dataclass
class VendorEvaluation:
    vendor: str
    product: str
    evaluation_stage: str
    deals_piloting: int
    expected_close: str
    competitor_products: str
    risk_assessment: str


@dataclass
class AIGovernance:
    deal: str
    aiace_framework: bool
    algorithmic_audit_freq: str
    bias_monitoring: bool
    clinical_oversight_committee: bool
    patient_disclosure: bool
    hipaa_baa: bool
    compliance_score: float


@dataclass
class AIResult:
    total_systems: int
    total_deals_with_ai: int
    total_annual_spend_m: float
    total_cases_monthly_k: int
    avg_adoption_pct: float
    avg_accuracy_pct: float
    systems: List[AISystem]
    outcomes: List[OutcomeMetric]
    adoption: List[AdoptionMetric]
    fda: List[FDASubmission]
    evaluations: List[VendorEvaluation]
    governance: List[AIGovernance]
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


def _build_systems() -> List[AISystem]:
    return [
        AISystem("Project Spruce — Radiology", "Aidoc", "CADaas (intracranial hemorrhage)",
                 "stroke triage", "FDA 510(k) cleared", "Radiology", "2024-08-15", 45, 85, 1.8),
        AISystem("Project Spruce — Radiology", "Viz.ai", "Viz ANEURYSM",
                 "aneurysm detection", "FDA 510(k) cleared", "Radiology", "2024-10-22", 45, 65, 1.5),
        AISystem("Project Spruce — Radiology", "Aidoc", "CADaas (PE)",
                 "pulmonary embolism detection", "FDA 510(k) cleared", "Radiology", "2025-03-10", 38, 48, 1.2),
        AISystem("Project Cedar — Cardiology", "Ultromics", "EchoGo Heart Failure",
                 "CHF detection on echo", "FDA 510(k) cleared", "Cardiology", "2025-06-18", 28, 32, 0.95),
        AISystem("Project Cedar — Cardiology", "Cleerly", "Cleerly ISCHEMIA",
                 "CCTA analysis + plaque characterization", "FDA 510(k) cleared", "Cardiology", "2025-04-12", 22, 25, 1.4),
        AISystem("Project Cypress — GI Network", "Medtronic", "GI Genius",
                 "polyp detection on colonoscopy", "FDA 510(k) cleared", "Gastroenterology", "2024-05-18", 65, 185, 2.2),
        AISystem("Project Magnolia — MSK Platform", "Radiobotics", "RBknee",
                 "osteoarthritis severity scoring", "FDA De Novo", "MSK", "2025-01-15", 48, 55, 0.85),
        AISystem("Project Oak — RCM SaaS", "Enter (internal)", "Denials prediction ML",
                 "claim denials prevention", "N/A (operational)", "RCM", "2024-02-22", 28, 245, 0.45),
        AISystem("Project Oak — RCM SaaS", "Notable Health", "Clinical Autopilot",
                 "ambient scribe", "N/A (workflow)", "Ambient", "2024-11-10", 12, 185, 1.8),
        AISystem("Project Oak — RCM SaaS", "Abridge", "Abridge Scribe",
                 "ambient scribe", "N/A (workflow)", "Ambient", "2025-02-15", 8, 125, 1.5),
        AISystem("Project Cypress — GI Network", "Nuance / DAX Copilot", "DAX Copilot",
                 "ambient scribe", "N/A (workflow)", "Ambient", "2024-09-05", 32, 145, 2.2),
        AISystem("Project Magnolia — MSK Platform", "Abridge", "Abridge Scribe",
                 "ambient scribe", "N/A (workflow)", "Ambient", "2025-03-25", 22, 115, 1.3),
        AISystem("Project Fir — Lab / Pathology", "Paige.AI", "Paige Prostate",
                 "prostate cancer detection", "FDA De Novo", "Pathology", "2025-02-18", 15, 18, 1.2),
        AISystem("Project Fir — Lab / Pathology", "Ibex Medical", "Galen Prostate",
                 "digital pathology workflow", "CE-marked (EU)", "Pathology", "2024-12-08", 12, 15, 0.85),
        AISystem("Project Redwood — Behavioral", "Ellipsis Health", "Voice biomarkers",
                 "depression screening from voice", "FDA clearance pending", "Behavioral Health", "2025-05-22", 8, 12, 0.65),
        AISystem("Project Sage — Home Health", "CloudMedX", "Readmission prediction",
                 "hospital readmission risk", "N/A (operational)", "Care Coord", "2024-10-18", 28, 82, 0.75),
        AISystem("Project Cedar — Cardiology", "Heartflow", "FFRct",
                 "fractional flow reserve from CTA", "FDA 510(k) cleared", "Cardiology", "2024-04-28", 18, 22, 1.0),
    ]


def _build_outcomes() -> List[OutcomeMetric]:
    return [
        OutcomeMetric("Aidoc CADaas (ICH)", "Project Spruce — Radiology", 0.94, 0.95, 0.92, 18.5, 8.5, 4.6),
        OutcomeMetric("Viz.ai Aneurysm", "Project Spruce — Radiology", 0.91, 0.88, 0.93, 12.2, 3.8, 4.5),
        OutcomeMetric("Aidoc CADaas (PE)", "Project Spruce — Radiology", 0.93, 0.91, 0.94, 15.5, 4.2, 4.6),
        OutcomeMetric("Ultromics EchoGo", "Project Cedar — Cardiology", 0.88, 0.86, 0.89, 8.5, 5.2, 4.4),
        OutcomeMetric("Cleerly ISCHEMIA", "Project Cedar — Cardiology", 0.92, 0.90, 0.93, 22.5, 8.5, 4.5),
        OutcomeMetric("Medtronic GI Genius", "Project Cypress — GI Network", 0.95, 0.93, 0.96, 4.5, 18.5, 4.7),
        OutcomeMetric("Radiobotics RBknee", "Project Magnolia — MSK Platform", 0.89, 0.87, 0.90, 6.5, 4.2, 4.3),
        OutcomeMetric("Enter ML Denials", "Project Oak — RCM SaaS", 0.86, 0.82, 0.88, 0.0, 28.5, 4.5),
        OutcomeMetric("Notable Autopilot", "Project Oak — RCM SaaS", 0.91, 0.89, 0.92, 12.5, 38.5, 4.7),
        OutcomeMetric("Abridge Scribe (Oak)", "Project Oak — RCM SaaS", 0.92, 0.90, 0.93, 14.2, 25.5, 4.7),
        OutcomeMetric("Nuance DAX Copilot", "Project Cypress — GI Network", 0.91, 0.88, 0.92, 12.5, 32.0, 4.6),
        OutcomeMetric("Abridge Scribe (Magnolia)", "Project Magnolia — MSK Platform", 0.92, 0.90, 0.93, 13.5, 22.5, 4.7),
        OutcomeMetric("Paige Prostate", "Project Fir — Lab / Pathology", 0.93, 0.91, 0.94, 18.5, 4.2, 4.6),
        OutcomeMetric("Ibex Galen Prostate", "Project Fir — Lab / Pathology", 0.90, 0.88, 0.91, 15.2, 3.2, 4.4),
        OutcomeMetric("Ellipsis Voice Biomarkers", "Project Redwood — Behavioral", 0.82, 0.80, 0.84, 5.5, 2.5, 4.1),
        OutcomeMetric("CloudMedX Readmission", "Project Sage — Home Health", 0.85, 0.82, 0.87, 0.0, 8.5, 4.3),
        OutcomeMetric("Heartflow FFRct", "Project Cedar — Cardiology", 0.94, 0.92, 0.95, 4.5, 5.8, 4.5),
    ]


def _build_adoption() -> List[AdoptionMetric]:
    return [
        AdoptionMetric("Project Spruce — Radiology", 285, 285, 265, 0.92, 0.085, 2),
        AdoptionMetric("Project Cedar — Cardiology", 185, 178, 152, 0.82, 0.115, 3),
        AdoptionMetric("Project Cypress — GI Network", 220, 215, 205, 0.94, 0.052, 1),
        AdoptionMetric("Project Magnolia — MSK Platform", 325, 295, 252, 0.78, 0.105, 2),
        AdoptionMetric("Project Fir — Lab / Pathology", 85, 82, 72, 0.84, 0.095, 1),
        AdoptionMetric("Project Oak — RCM SaaS", 125, 118, 115, 0.92, 0.068, 0),
        AdoptionMetric("Project Redwood — Behavioral", 165, 145, 85, 0.52, 0.185, 5),
        AdoptionMetric("Project Sage — Home Health", 285, 265, 225, 0.78, 0.135, 2),
    ]


def _build_fda() -> List[FDASubmission]:
    return [
        FDASubmission("Aidoc Medical", "CADaas (ICH)", "510(k)", "K182177", "2018-08-29",
                      "non-contrast CT — ICH detection", "Not applicable (de novo 2018)"),
        FDASubmission("Viz.ai", "Viz ANEURYSM", "510(k)", "K220085", "2022-04-18",
                      "CTA head — unruptured intracranial aneurysm detection", "K192935"),
        FDASubmission("Aidoc Medical", "CADaas (PE)", "510(k)", "K192895", "2019-08-01",
                      "CT pulmonary angiography — PE detection", "K183182 (not Aidoc)"),
        FDASubmission("Ultromics Ltd", "EchoGo Heart Failure", "510(k)", "K230014", "2023-04-28",
                      "echo-derived quantitative measurements", "K200378 (Bay Labs)"),
        FDASubmission("Cleerly Inc", "Cleerly ISCHEMIA", "510(k)", "K213498", "2022-06-17",
                      "CCTA-derived ischemia analysis", "K200389 (HeartFlow)"),
        FDASubmission("Medtronic", "GI Genius", "De Novo", "DEN200055", "2021-04-09",
                      "colonoscopy — polyp detection assist", "n/a (first of class)"),
        FDASubmission("Radiobotics ApS", "RBknee", "De Novo", "DEN230044", "2024-03-15",
                      "knee radiograph — osteoarthritis severity", "n/a (first of class)"),
        FDASubmission("Paige.AI Inc", "Paige Prostate", "De Novo", "DEN200080", "2021-09-22",
                      "digital pathology — prostate cancer detection assist", "n/a (first of class)"),
        FDASubmission("Heartflow Inc", "FFRct Analysis", "510(k)", "K133803", "2014-11-21",
                      "CCTA-derived fractional flow reserve", "n/a"),
        FDASubmission("Ellipsis Health", "Voice Depression Detection", "510(k) pending", "pending", "expected 2026-Q3",
                      "voice-based depression screening", "pending evaluation"),
    ]


def _build_evaluations() -> List[VendorEvaluation]:
    return [
        VendorEvaluation("Navina", "Navina Copilot", "pilot", 3, "2026-Q3", "Abridge, Nuance DAX",
                         "medium — early MA integration"),
        VendorEvaluation("RapidAI", "Rapid LVO / ICH", "evaluation", 2, "2026-Q2", "Aidoc, Viz.ai",
                         "low — established vendor space"),
        VendorEvaluation("MaxQ.AI", "Accipio ICH", "evaluation", 1, "2026-Q2", "Aidoc, Viz.ai",
                         "low — single use case"),
        VendorEvaluation("Qure.ai", "qXR + qCT", "pilot", 2, "2026-Q3", "Aidoc, Viz.ai",
                         "medium — international vendor"),
        VendorEvaluation("Ambience Healthcare", "AutoScribe+", "pilot", 4, "2026-Q3", "Abridge, DAX, Notable",
                         "medium — newer entrant"),
        VendorEvaluation("Suki AI", "Suki Assistant", "evaluation", 2, "2026-Q2", "Abridge, DAX",
                         "medium — CEO relationships exist"),
        VendorEvaluation("Tempus Labs", "Tempus xT (genomic)", "pilot", 3, "2026-Q4", "Foundation Medicine, Guardant",
                         "high — genomic data implications"),
        VendorEvaluation("PathAI", "PathPresenter + ML", "pilot", 2, "2026-Q3", "Paige, Ibex",
                         "medium — pathology workflow fit"),
        VendorEvaluation("Rad AI", "Rad AI Continuum", "evaluation", 2, "2026-Q4", "none direct",
                         "medium — workflow efficiency"),
    ]


def _build_governance() -> List[AIGovernance]:
    return [
        AIGovernance("Project Spruce — Radiology", True, "quarterly", True, True, True, True, 9.5),
        AIGovernance("Project Cedar — Cardiology", True, "quarterly", True, True, True, True, 9.0),
        AIGovernance("Project Cypress — GI Network", True, "semi-annual", True, True, True, True, 8.8),
        AIGovernance("Project Magnolia — MSK Platform", True, "semi-annual", True, True, True, True, 8.5),
        AIGovernance("Project Fir — Lab / Pathology", True, "quarterly", True, True, True, True, 9.2),
        AIGovernance("Project Oak — RCM SaaS", True, "continuous (MLOps)", True, True, False, True, 9.0),
        AIGovernance("Project Redwood — Behavioral", True, "quarterly", True, True, True, True, 8.5),
        AIGovernance("Project Sage — Home Health", True, "quarterly", True, True, True, True, 8.8),
    ]


def compute_clinical_ai_tracker() -> AIResult:
    corpus = _load_corpus()
    systems = _build_systems()
    outcomes = _build_outcomes()
    adoption = _build_adoption()
    fda = _build_fda()
    evaluations = _build_evaluations()
    governance = _build_governance()

    deals = {s.deal for s in systems}
    total_spend = sum(s.annual_license_m for s in systems)
    total_cases = sum(s.monthly_cases_k for s in systems)
    avg_adoption = sum(a.daily_usage_pct for a in adoption) / len(adoption) if adoption else 0
    avg_acc = sum(o.accuracy_pct for o in outcomes) / len(outcomes) if outcomes else 0

    return AIResult(
        total_systems=len(systems),
        total_deals_with_ai=len(deals),
        total_annual_spend_m=round(total_spend, 1),
        total_cases_monthly_k=total_cases,
        avg_adoption_pct=round(avg_adoption, 4),
        avg_accuracy_pct=round(avg_acc, 4),
        systems=systems,
        outcomes=outcomes,
        adoption=adoption,
        fda=fda,
        evaluations=evaluations,
        governance=governance,
        corpus_deal_count=len(corpus),
    )
