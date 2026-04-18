"""Litigation Watchlist Tracker.

Tracks open litigation, regulatory actions, and class-action exposure
across portfolio companies — materiality, accruals, insurance coverage,
and SPA indemnity availability.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class LitigationMatter:
    matter_id: str
    deal: str
    sector: str
    case_name: str
    court: str
    jurisdiction: str
    matter_type: str
    alleged_amount_m: float
    accrued_m: float
    insurance_coverage_m: float
    spa_indemnity_coverage_m: float
    est_exposure_m: float
    filing_date: str
    stage: str
    counsel: str


@dataclass
class MatterTypeRollup:
    matter_type: str
    open_matters: int
    alleged_amount_m: float
    est_exposure_m: float
    avg_time_open_months: float
    win_rate_pct: float


@dataclass
class RegulatoryAction:
    agency: str
    deal: str
    action_type: str
    status: str
    alleged_violation: str
    estimated_fine_m: float
    resolution_pathway: str
    timeline: str


@dataclass
class ClassAction:
    case_name: str
    deal: str
    sector: str
    plaintiff_class: str
    filing_date: str
    class_size: int
    alleged_damages_m: float
    certification_status: str
    settlement_estimate_m: float


@dataclass
class InsuranceLayer:
    layer: str
    primary_carrier: str
    limit_m: float
    attachment_m: float
    premium_annual_m: float
    loss_activity_m: float


@dataclass
class SettlementHistory:
    year: int
    matters_closed: int
    alleged_total_m: float
    paid_total_m: float
    paid_to_alleged_ratio: float
    avg_resolution_days: int


@dataclass
class LitResult:
    total_matters: int
    total_alleged_m: float
    total_accrued_m: float
    total_exposure_m: float
    insurance_coverage_m: float
    active_regulatory_actions: int
    active_class_actions: int
    matters: List[LitigationMatter]
    types: List[MatterTypeRollup]
    regulatory: List[RegulatoryAction]
    class_actions: List[ClassAction]
    insurance: List[InsuranceLayer]
    history: List[SettlementHistory]
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


def _build_matters() -> List[LitigationMatter]:
    return [
        LitigationMatter("LIT-001", "Project Redwood — Behavioral", "Behavioral Health",
                         "Doe v. Redwood Behavioral Health", "D.Mass.", "Federal",
                         "Medical malpractice", 4.5, 1.2, 15.0, 0.0, 1.5, "2025-08-12", "discovery", "Ropes & Gray"),
        LitigationMatter("LIT-002", "Project Redwood — Behavioral", "Behavioral Health",
                         "State of Mass. v. Redwood", "Mass. Superior", "State", "Consumer protection / AG inquiry",
                         8.2, 0.5, 5.0, 10.0, 2.5, "2025-11-03", "pleadings", "Goodwin Procter"),
        LitigationMatter("LIT-003", "Project Cypress — GI Network", "Gastroenterology",
                         "Smith v. Cypress GI", "D.N.J.", "Federal", "Medical malpractice",
                         2.5, 0.7, 10.0, 0.0, 0.8, "2025-09-18", "early discovery", "Morgan Lewis"),
        LitigationMatter("LIT-004", "Project Cedar — Cardiology", "Cardiology",
                         "Garcia v. Cedar Cardiology", "D.Ariz.", "Federal", "Wrongful death",
                         8.5, 2.0, 25.0, 0.0, 2.8, "2025-06-22", "discovery", "Latham & Watkins"),
        LitigationMatter("LIT-005", "Project Cedar — Cardiology", "Cardiology",
                         "SEC v. Cedar Cardiology LLC", "D.Ariz.", "Federal", "Securities fraud (pre-close)",
                         12.5, 4.0, 0.0, 15.0, 0.0, "2024-12-10", "settlement discussion", "Wachtell Lipton"),
        LitigationMatter("LIT-006", "Project Oak — RCM SaaS", "RCM / HCIT",
                         "HealthCo v. Oak RCM", "N.D.Cal.", "Federal", "Breach of contract / SLA",
                         6.5, 3.0, 0.0, 0.0, 3.5, "2025-12-05", "pleadings", "Sidley Austin"),
        LitigationMatter("LIT-007", "Project Magnolia — MSK", "MSK / Ortho",
                         "Thompson v. Magnolia MSK", "D.Ill.", "Federal", "Medical malpractice",
                         3.2, 0.9, 20.0, 0.0, 1.0, "2025-07-28", "discovery", "Kirkland & Ellis"),
        LitigationMatter("LIT-008", "Project Sage — Home Health", "Home Health",
                         "OIG (HHS) v. Sage Home Health", "Admin", "Federal", "Medicare billing / FCA",
                         28.5, 8.0, 0.0, 25.0, 8.0, "2025-04-15", "discovery", "Hogan Lovells"),
        LitigationMatter("LIT-009", "Project Willow — Fertility", "Fertility / IVF",
                         "Johnson v. Willow Fertility", "D.Tex.", "Federal", "Tort (storage / embryo)",
                         12.5, 3.5, 35.0, 0.0, 4.5, "2025-10-11", "discovery", "Vinson & Elkins"),
        LitigationMatter("LIT-010", "Project Laurel — Derma", "Dermatology",
                         "Williams v. Laurel Dermatology", "D.N.C.", "Federal", "Consumer protection",
                         2.8, 0.8, 5.0, 0.0, 1.0, "2025-11-20", "early discovery", "Alston & Bird"),
        LitigationMatter("LIT-011", "Project Basil — Dental DSO", "Dental DSO",
                         "DOJ v. Basil Dental", "D.Ind.", "Federal", "Healthcare fraud",
                         18.5, 6.0, 0.0, 20.0, 6.0, "2025-02-28", "discovery", "Jones Day"),
        LitigationMatter("LIT-012", "Project Ash — Infusion", "Infusion",
                         "Federal Trade Commission v. Ash", "Admin", "Federal", "Anti-trust / competition",
                         35.0, 8.5, 0.0, 25.0, 6.5, "2025-03-22", "consent order discussion", "Cravath Swaine"),
        LitigationMatter("LIT-013", "Project Fir — Lab / Pathology", "Lab Services",
                         "Quest v. Fir Lab", "D.Del.", "Federal", "Patent infringement",
                         45.0, 8.0, 0.0, 0.0, 12.0, "2025-05-14", "claim construction", "Fish & Richardson"),
        LitigationMatter("LIT-014", "Project Thyme — Specialty Pharm", "Specialty Pharma",
                         "State of Calif. v. Thyme", "Cal.Sup.", "State", "340B compliance",
                         15.5, 4.0, 0.0, 10.0, 3.5, "2025-09-05", "discovery", "Gibson Dunn"),
        LitigationMatter("LIT-015", "Project Aspen — Eye Care", "Eye Care",
                         "Doe v. Aspen Eye Care", "D.Minn.", "Federal", "Data breach / HIPAA",
                         8.5, 2.5, 10.0, 0.0, 3.0, "2025-10-22", "discovery", "Cooley"),
        LitigationMatter("LIT-016", "Project Linden — Behavioral", "Behavioral Health",
                         "Doe v. Linden Behavioral", "D.Ohio", "Federal", "Tort (patient care)",
                         5.8, 1.5, 15.0, 0.0, 1.8, "2025-12-18", "pleadings", "Vorys Sater"),
        LitigationMatter("LIT-017", "Project Maple — Urology", "Urology",
                         "Garcia v. Maple Urology", "D.N.C.", "Federal", "Medical malpractice",
                         2.0, 0.5, 10.0, 0.0, 0.8, "2025-08-28", "discovery", "Kilpatrick Townsend"),
        LitigationMatter("LIT-018", "Project Spruce — Radiology", "Radiology",
                         "Thompson v. Spruce Radiology", "D.Colo.", "Federal", "Negligent radiology",
                         3.5, 1.2, 12.0, 0.0, 1.2, "2025-11-02", "discovery", "Brownstein Hyatt"),
    ]


def _build_types(matters: List[LitigationMatter]) -> List[MatterTypeRollup]:
    buckets: dict = {}
    for m in matters:
        b = buckets.setdefault(m.matter_type, {"count": 0, "alleged": 0.0, "exposure": 0.0})
        b["count"] += 1
        b["alleged"] += m.alleged_amount_m
        b["exposure"] += m.est_exposure_m
    rows = []
    for mt, d in buckets.items():
        rows.append(MatterTypeRollup(
            matter_type=mt, open_matters=d["count"],
            alleged_amount_m=round(d["alleged"], 1),
            est_exposure_m=round(d["exposure"], 1),
            avg_time_open_months=round(12.0, 1),
            win_rate_pct=0.72,
        ))
    return sorted(rows, key=lambda x: x.est_exposure_m, reverse=True)


def _build_regulatory() -> List[RegulatoryAction]:
    return [
        RegulatoryAction("OIG (HHS)", "Project Sage — Home Health", "False Claims Act",
                         "active discovery", "Medicare overbilling (2023-2024)", 12.5, "settlement + CIA", "Q3 2026 est"),
        RegulatoryAction("DOJ", "Project Basil — Dental DSO", "FCA healthcare fraud",
                         "active discovery", "upcoding + Stark Law", 8.5, "settlement", "Q4 2026 est"),
        RegulatoryAction("FTC", "Project Ash — Infusion", "Section 7 Clayton Act",
                         "consent order", "post-acquisition divestiture", 6.0, "divestiture", "Q2 2026"),
        RegulatoryAction("SEC", "Project Cedar — Cardiology", "10b-5 + Section 17(a)",
                         "settlement discussion", "pre-acquisition disclosures", 4.0, "NPA + penalty", "Q3 2026"),
        RegulatoryAction("State AG (California)", "Project Thyme — Specialty Pharm", "340B compliance audit",
                         "active investigation", "340B diversion allegations", 3.5, "consent decree", "Q2 2026"),
        RegulatoryAction("DOL (Wage & Hour)", "Project Redwood — Behavioral", "FLSA misclassification",
                         "active audit", "per-diem worker classification", 1.8, "settlement + back pay", "Q2 2026"),
        RegulatoryAction("CMS", "Project Cypress — GI Network", "RAC audit",
                         "appeal", "ASC billing errors (2022-2023)", 2.2, "payback + CAP", "Q3 2026"),
        RegulatoryAction("State Medicaid Fraud Unit (NY)", "Project Maple — Urology", "Medicaid billing",
                         "active investigation", "coding practices", 1.5, "settlement", "Q4 2026"),
        RegulatoryAction("OCR (HIPAA)", "Project Aspen — Eye Care", "HIPAA security incident",
                         "CAP in progress", "Feb 2024 breach remediation", 2.5, "CAP + remediation", "Q3 2026"),
        RegulatoryAction("Medical Board (TX)", "Project Willow — Fertility", "physician conduct",
                         "investigation", "MD credentialing lapse", 0.5, "consent + oversight", "Q2 2026"),
    ]


def _build_class_actions() -> List[ClassAction]:
    return [
        ClassAction("In re Cedar Cardiology Securities Litigation", "Project Cedar — Cardiology", "Cardiology",
                    "Shareholders (pre-acquisition)", "2025-07-15", 4200, 85.0, "certified", 12.0),
        ClassAction("Medicare Beneficiaries v. Sage Home Health", "Project Sage — Home Health", "Home Health",
                    "Medicare beneficiaries", "2025-10-22", 28500, 45.0, "certification pending", 8.5),
        ClassAction("Employees v. Redwood Behavioral Health", "Project Redwood — Behavioral", "Behavioral Health",
                    "Current + former employees (wage/hour)", "2025-09-18", 1850, 18.5, "certification pending", 4.5),
        ClassAction("Patients v. Aspen Eye Care (HIPAA breach)", "Project Aspen — Eye Care", "Eye Care",
                    "Patients affected by Feb 2024 breach", "2024-06-22", 215000, 25.0, "certified, settlement", 8.0),
        ClassAction("Patients v. Willow Fertility (storage)", "Project Willow — Fertility", "Fertility / IVF",
                    "Fertility patients (2019-2023)", "2025-11-15", 485, 35.0, "certification pending", 12.5),
        ClassAction("Consumers v. Basil Dental DSO", "Project Basil — Dental DSO", "Dental DSO",
                    "Consumers (pricing/disclosure)", "2025-06-10", 95000, 18.5, "certification denied (appeal)", 3.5),
    ]


def _build_insurance() -> List[InsuranceLayer]:
    return [
        InsuranceLayer("Primary", "AIG / Lexington", 25.0, 0.0, 3.2, 4.5),
        InsuranceLayer("First Excess", "Liberty Mutual / Tokio Marine", 50.0, 25.0, 2.5, 0.8),
        InsuranceLayer("Second Excess", "Swiss Re / Munich Re", 75.0, 75.0, 1.8, 0.0),
        InsuranceLayer("Third Excess", "Allianz / Zurich", 100.0, 150.0, 1.2, 0.0),
        InsuranceLayer("Cyber Standalone", "Beazley / Travelers", 50.0, 0.0, 4.5, 8.5),
        InsuranceLayer("D&O Primary", "AIG / Chubb", 25.0, 0.0, 1.8, 2.2),
        InsuranceLayer("Medical Malpractice (Captive)", "Redlands Insurance Co. (Captive)", 35.0, 0.0, 2.8, 5.2),
        InsuranceLayer("Reps & Warranty", "Beazley / AIG R&W", 25.0, 5.0, 0.5, 1.8),
    ]


def _build_history() -> List[SettlementHistory]:
    return [
        SettlementHistory(2022, 15, 58.5, 12.2, 0.21, 385),
        SettlementHistory(2023, 22, 85.8, 18.5, 0.22, 365),
        SettlementHistory(2024, 28, 115.5, 28.2, 0.24, 345),
        SettlementHistory(2025, 31, 145.8, 32.5, 0.22, 325),
        SettlementHistory(2026, 8, 42.5, 9.8, 0.23, 310),
    ]


def compute_litigation_tracker() -> LitResult:
    corpus = _load_corpus()
    matters = _build_matters()
    types = _build_types(matters)
    regulatory = _build_regulatory()
    class_actions = _build_class_actions()
    insurance = _build_insurance()
    history = _build_history()

    total_alleged = sum(m.alleged_amount_m for m in matters)
    total_accrued = sum(m.accrued_m for m in matters)
    total_exposure = sum(m.est_exposure_m for m in matters)
    insurance_cov = sum(m.insurance_coverage_m for m in matters)

    return LitResult(
        total_matters=len(matters),
        total_alleged_m=round(total_alleged, 1),
        total_accrued_m=round(total_accrued, 1),
        total_exposure_m=round(total_exposure, 1),
        insurance_coverage_m=round(insurance_cov, 1),
        active_regulatory_actions=len(regulatory),
        active_class_actions=len(class_actions),
        matters=matters,
        types=types,
        regulatory=regulatory,
        class_actions=class_actions,
        insurance=insurance,
        history=history,
        corpus_deal_count=len(corpus),
    )
