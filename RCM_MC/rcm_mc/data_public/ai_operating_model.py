"""AI / ML Operating Model for Healthcare Platforms.

Tracks AI adoption, ROI, model risk, and governance across a PE-backed
healthcare platform. Diligence-grade view: which AI initiatives are
proving out, which are marketing theater, what's the regulatory exposure.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class AIInitiative:
    use_case: str
    category: str
    deployment_stage: str
    annual_spend_mm: float
    annual_savings_mm: float
    annual_revenue_lift_mm: float
    net_roi_pct: float
    adoption_pct: float
    pilot_to_prod_months: int


@dataclass
class VendorLandscape:
    vendor: str
    category: str
    annual_contract_mm: float
    integration_depth: str
    clinical_accuracy_pct: float
    user_nps: int
    retention_tier: str


@dataclass
class ModelGovernance:
    model: str
    use_case: str
    fda_class: str
    bias_audit_status: str
    drift_monitoring: str
    last_validation_date: str
    risk_tier: str


@dataclass
class AIROIBucket:
    bucket: str
    spend_mm: float
    savings_mm: float
    roi_multiple: float
    payback_months: int
    strategic_value: str


@dataclass
class RegulatoryExposure:
    regulation: str
    applicability: str
    current_compliance: str
    gap_description: str
    remediation_cost_mm: float
    deadline: str


@dataclass
class AIResult:
    total_annual_ai_spend_mm: float
    total_annual_savings_mm: float
    total_revenue_lift_mm: float
    blended_roi_pct: float
    initiatives_in_prod: int
    governance_risk_tier: str
    initiatives: List[AIInitiative]
    vendors: List[VendorLandscape]
    governance: List[ModelGovernance]
    roi_buckets: List[AIROIBucket]
    regulation: List[RegulatoryExposure]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 108):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_initiatives() -> List[AIInitiative]:
    items = [
        ("Ambient AI Scribe (DAX Copilot / Abridge)", "Clinical Productivity", "production", 4.8, 15.5, 8.5, 4.0, 0.72, 6),
        ("RCM Claim Scrubbing (AI Denial Prediction)", "Revenue Cycle", "production", 2.2, 12.5, 4.2, 6.59, 0.88, 4),
        ("Prior Auth Automation (Machine Learning)", "Revenue Cycle", "production", 1.8, 6.8, 2.5, 4.17, 0.62, 8),
        ("Predictive Readmission Risk (MA)", "Clinical", "production", 1.5, 8.5, 0.0, 4.67, 0.82, 9),
        ("Radiology AI Triage (Aidoc / Viz.ai)", "Clinical Diagnostic", "production", 2.5, 4.5, 2.8, 1.92, 0.55, 12),
        ("Dermatology Image Classification", "Clinical Diagnostic", "pilot", 0.65, 0.35, 0.48, 0.28, 0.18, 10),
        ("LLM-Based Patient Navigation (Enroll)", "Front-Office", "pilot", 1.2, 2.2, 1.8, 2.33, 0.45, 8),
        ("Revenue Intelligence / Contract Analytics", "Managed Care", "production", 1.8, 4.8, 3.5, 3.61, 0.68, 7),
        ("Physician Scheduling Optimization", "Operations", "production", 0.85, 3.5, 0.0, 3.12, 0.78, 5),
        ("Clinical Documentation Improvement (CDI) AI", "Revenue Cycle", "production", 1.4, 7.2, 2.8, 6.14, 0.85, 6),
        ("Prior Auth Letter Generation (LLM)", "Admin", "pilot", 0.45, 1.85, 0.0, 3.11, 0.38, 6),
        ("Chatbot Patient Intake", "Patient Experience", "production", 0.95, 2.8, 1.5, 3.53, 0.72, 4),
        ("Ambient Medication Reconciliation", "Clinical", "pilot", 0.55, 0.85, 0.0, 0.55, 0.22, 8),
        ("Prior Auth Medical Necessity Review", "Clinical Review", "pilot", 0.75, 2.2, 0.8, 3.00, 0.32, 9),
        ("Fraud / Waste / Abuse Detection", "Compliance", "production", 1.8, 5.5, 2.2, 3.28, 0.75, 8),
    ]
    rows = []
    for uc, cat, stage, spend, savings, rev, roi, adopt, p2p in items:
        rows.append(AIInitiative(
            use_case=uc, category=cat, deployment_stage=stage,
            annual_spend_mm=spend, annual_savings_mm=savings, annual_revenue_lift_mm=rev,
            net_roi_pct=roi, adoption_pct=adopt, pilot_to_prod_months=p2p,
        ))
    return rows


def _build_vendors() -> List[VendorLandscape]:
    return [
        VendorLandscape("Nuance / Microsoft DAX Copilot", "Ambient Scribe", 2.85, "deep EHR-integrated", 0.96, 78, "platinum"),
        VendorLandscape("Abridge", "Ambient Scribe", 1.95, "EHR-integrated", 0.95, 82, "gold"),
        VendorLandscape("Aidoc", "Radiology AI Triage", 1.45, "PACS-integrated", 0.93, 72, "gold"),
        VendorLandscape("Viz.ai", "Stroke AI Triage", 0.85, "PACS-integrated", 0.94, 75, "gold"),
        VendorLandscape("Waystar AI", "Denial Management AI", 1.25, "RCM-integrated", 0.88, 68, "gold"),
        VendorLandscape("Olive AI (Deprecated 2023)", "RPA / Workflow", 0.0, "replaced", 0.0, 0, "divested"),
        VendorLandscape("Infinitus", "Prior Auth Voice AI", 1.65, "standalone", 0.85, 65, "silver"),
        VendorLandscape("Notable Health", "Patient Intake AI", 1.15, "EHR-integrated", 0.88, 72, "gold"),
        VendorLandscape("Epic Azure OpenAI Integration", "LLM Platform", 0.45, "native EHR", 0.92, 85, "platinum"),
        VendorLandscape("Glass Health", "Clinical Decision Support", 0.35, "pilot API", 0.82, 68, "silver"),
        VendorLandscape("Suki AI", "Ambient Scribe (Boutique)", 0.85, "EHR-integrated", 0.91, 74, "silver"),
        VendorLandscape("Rad AI", "Radiology Summaries", 0.72, "PACS-integrated", 0.89, 70, "silver"),
    ]


def _build_governance() -> List[ModelGovernance]:
    return [
        ModelGovernance("DAX Copilot Ambient Scribe", "Clinical Documentation", "Class II SaMD", "passed Q4 2024", "continuous monitoring", "2024-12-15", "low"),
        ModelGovernance("Denial Prediction Ensemble", "RCM", "N/A - Administrative", "passed Q3 2024", "monthly drift checks", "2024-09-22", "low"),
        ModelGovernance("Predictive Readmission Model", "Clinical Decision", "Class II SaMD pending", "passed Q2 2024", "quarterly drift checks", "2024-06-30", "medium"),
        ModelGovernance("Aidoc Acute Head CT AI", "Diagnostic", "Class II (FDA cleared)", "passed 2024", "continuous (FDA post-market)", "2024-10-15", "low"),
        ModelGovernance("Viz.ai LVO Detection", "Diagnostic", "Class II (FDA cleared)", "passed 2024", "continuous (FDA post-market)", "2024-11-08", "low"),
        ModelGovernance("Dermatology Image Model (Pilot)", "Clinical Decision", "Class II SaMD pending", "in progress", "not yet", "pending", "high"),
        ModelGovernance("LLM Patient Navigation (Pilot)", "Admin", "N/A", "internal review only", "not yet", "pending", "medium"),
        ModelGovernance("CDI AI Recommendation", "RCM", "N/A - Administrative", "passed Q3 2024", "monthly drift checks", "2024-09-10", "low"),
        ModelGovernance("Prior Auth Letter Gen LLM", "Admin", "N/A", "in progress", "not yet", "pending", "medium"),
        ModelGovernance("FWA Detection Model", "Compliance", "N/A - Administrative", "passed Q1 2025", "monthly drift checks", "2025-01-28", "low"),
    ]


def _build_roi_buckets() -> List[AIROIBucket]:
    return [
        AIROIBucket("Revenue Cycle Automation", 7.2, 27.5, 3.82, 14, "high"),
        AIROIBucket("Clinical Productivity / Documentation", 6.65, 24.25, 3.65, 15, "high"),
        AIROIBucket("Radiology / Diagnostic", 3.15, 6.55, 2.08, 21, "medium"),
        AIROIBucket("Front-Office / Patient Experience", 3.2, 8.3, 2.59, 16, "medium"),
        AIROIBucket("Operations / Scheduling", 2.35, 9.2, 3.91, 12, "medium"),
        AIROIBucket("Compliance / FWA", 1.8, 5.5, 3.06, 14, "medium"),
    ]


def _build_regulation() -> List[RegulatoryExposure]:
    return [
        RegulatoryExposure("FDA SaMD Clearance (Class II)", "All diagnostic AI used in clinical decisions",
                           "2 FDA-cleared, 2 pending", "Dermatology image model awaiting clearance", 0.85, "2026-06-30"),
        RegulatoryExposure("HIPAA Privacy (AI Training Data)", "Any AI trained on PHI",
                           "compliant", "ongoing audits", 0.15, "continuous"),
        RegulatoryExposure("HHS Office for Civil Rights (AI Bias)", "Clinical decision support",
                           "passed 2024", "model cards published Q1 2025", 0.28, "2025-12-31"),
        RegulatoryExposure("California AB 3030 (AI Disclosure)", "Patient-facing AI",
                           "implementing Q2 2026", "disclosure language + opt-out", 0.32, "2026-07-01"),
        RegulatoryExposure("Colorado SB 21-169 (Algorithmic Discrimination)", "Insurance/eligibility AI",
                           "not applicable (provider only)", "N/A", 0.0, "N/A"),
        RegulatoryExposure("EU AI Act (for EU-source care)", "N/A currently",
                           "N/A", "future expansion consideration", 0.0, "N/A"),
        RegulatoryExposure("ONC HTI-1 Rule (Transparency)", "Certified EHR with Predictive DSI",
                           "compliant via Epic", "standard", 0.05, "continuous"),
        RegulatoryExposure("State-Level AI Laws (8+ states pending 2025)", "Multi-state deployment",
                           "monitoring", "need centralized AI policy", 0.25, "2026"),
    ]


def compute_ai_operating_model() -> AIResult:
    corpus = _load_corpus()

    initiatives = _build_initiatives()
    vendors = _build_vendors()
    governance = _build_governance()
    roi_buckets = _build_roi_buckets()
    regulation = _build_regulation()

    total_spend = sum(i.annual_spend_mm for i in initiatives)
    total_savings = sum(i.annual_savings_mm for i in initiatives)
    total_rev = sum(i.annual_revenue_lift_mm for i in initiatives)
    total_value = total_savings + total_rev
    blended_roi = (total_value - total_spend) / total_spend if total_spend else 0

    in_prod = sum(1 for i in initiatives if i.deployment_stage == "production")

    high_risk_models = sum(1 for m in governance if m.risk_tier == "high")
    medium_risk = sum(1 for m in governance if m.risk_tier == "medium")
    if high_risk_models > 0:
        gov_tier = "elevated"
    elif medium_risk >= 2:
        gov_tier = "moderate"
    else:
        gov_tier = "well-governed"

    return AIResult(
        total_annual_ai_spend_mm=round(total_spend, 2),
        total_annual_savings_mm=round(total_savings, 2),
        total_revenue_lift_mm=round(total_rev, 2),
        blended_roi_pct=round(blended_roi, 3),
        initiatives_in_prod=in_prod,
        governance_risk_tier=gov_tier,
        initiatives=initiatives,
        vendors=vendors,
        governance=governance,
        roi_buckets=roi_buckets,
        regulation=regulation,
        corpus_deal_count=len(corpus),
    )
