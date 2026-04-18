"""340B Pharmacy Program Tracker.

Tracks 340B-eligible entities, contract pharmacy arrangements, savings,
compliance, and regulatory exposure across portfolio.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class Entity340B:
    deal: str
    entity_name: str
    entity_type: str
    eligibility_basis: str
    enrolled_date: str
    ce_id: str
    annual_340b_spend_m: float
    annual_savings_m: float
    compliance_score: float


@dataclass
class ContractPharmacy:
    covered_entity: str
    pharmacy_chain: str
    arrangement_type: str
    dispense_volume_k: int
    admin_fee_pct: float
    share_to_ce_pct: float
    annual_savings_m: float
    status: str


@dataclass
class ManufacturerRestriction:
    manufacturer: str
    effective_date: str
    scope: str
    affected_deals: int
    annual_exposure_m: float
    litigation_status: str
    workaround: str


@dataclass
class AuditHistory:
    covered_entity: str
    audit_type: str
    audit_date: str
    auditor: str
    findings: int
    repayment_m: float
    status: str


@dataclass
class SavingsBreakdown:
    drug_category: str
    utilizers: int
    gross_wac_m: float
    net_cost_m: float
    savings_m: float
    savings_pct: float
    rebate_capture_m: float


@dataclass
class RegulatoryUpdate:
    topic: str
    effective_date: str
    description: str
    portfolio_impact_m: float
    action_required: str


@dataclass
class Tracker340BResult:
    total_entities: int
    total_annual_spend_m: float
    total_annual_savings_m: float
    effective_savings_rate: float
    total_contract_pharmacies: int
    avg_compliance_score: float
    restricted_manufacturers: int
    entities: List[Entity340B]
    pharmacies: List[ContractPharmacy]
    restrictions: List[ManufacturerRestriction]
    audits: List[AuditHistory]
    breakdown: List[SavingsBreakdown]
    updates: List[RegulatoryUpdate]
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


def _build_entities() -> List[Entity340B]:
    return [
        Entity340B("Project Thyme — Specialty Pharm", "Oncology Specialty Pharm LLC", "SCH", "Sole Community Hospital affiliate",
                   "2014-03-15", "SCH370052", 85.2, 28.5, 9.2),
        Entity340B("Project Thyme — Specialty Pharm", "Infusion Specialty Services", "DSH", "Disproportionate Share Hospital",
                   "2016-08-22", "DSH370055", 45.8, 14.8, 9.0),
        Entity340B("Project Ash — Infusion", "Regional Infusion Network", "CAH", "Critical Access Hospital partnership",
                   "2017-05-18", "CAH140102", 68.5, 22.5, 8.8),
        Entity340B("Project Ash — Infusion", "Oncology Infusion Center", "CA", "Cancer Hospital",
                   "2015-11-02", "CAH330088", 95.2, 32.0, 9.0),
        Entity340B("Project Sage — Home Health", "Home Infusion Network LLC", "FQHC", "Federally Qualified Health Center",
                   "2018-04-10", "FQHC220015", 28.5, 9.2, 8.5),
        Entity340B("Project Redwood — Behavioral", "Behavioral Health FQHC", "FQHC", "Federally Qualified Health Center",
                   "2015-09-18", "FQHC280042", 18.2, 6.5, 8.8),
        Entity340B("Project Laurel — Derma", "Specialty Dermatology Clinic", "Ryan White", "Ryan White HIV/AIDS Program",
                   "2019-06-15", "RYW220028", 8.5, 3.2, 8.2),
        Entity340B("Project Sage — Home Health", "Community Health Alliance", "FQHC-LA", "Look-Alike FQHC",
                   "2020-02-28", "LAL180022", 15.8, 5.5, 8.5),
        Entity340B("Project Cypress — GI Network", "Charity GI Clinic", "FQHC-LA", "Look-Alike FQHC",
                   "2019-11-05", "LAL340055", 12.5, 4.0, 8.8),
        Entity340B("Project Willow — Fertility", "Community IVF Access", "FQHC-LA", "Look-Alike FQHC",
                   "2021-03-22", "LAL480018", 8.2, 2.8, 8.5),
        Entity340B("Project Basil — Dental DSO", "Dental FQHC Partner", "FQHC", "FQHC dental services",
                   "2016-07-18", "FQHC180042", 22.5, 7.5, 8.0),
        Entity340B("Project Redwood — Behavioral", "Community Behavioral Services", "FQHC", "Dual MH/SUD FQHC",
                   "2020-09-10", "FQHC120055", 12.8, 4.5, 8.7),
        Entity340B("Project Magnolia — MSK Platform", "Sports Medicine Clinic", "FQHC-LA", "Community access program",
                   "2022-01-15", "LAL520028", 5.8, 2.0, 8.2),
    ]


def _build_pharmacies() -> List[ContractPharmacy]:
    return [
        ContractPharmacy("Oncology Specialty Pharm LLC", "Walgreens", "ECE (cancer)", 125, 0.085, 0.85, 8.5, "active"),
        ContractPharmacy("Oncology Specialty Pharm LLC", "CVS Health", "ECE (cancer)", 95, 0.075, 0.82, 6.2, "active"),
        ContractPharmacy("Oncology Specialty Pharm LLC", "Specialty Pharm (in-house)", "CE-owned", 285, 0.0, 1.00, 22.5, "active"),
        ContractPharmacy("Infusion Specialty Services", "Accredo (Cigna)", "ECE (specialty)", 85, 0.080, 0.85, 5.5, "active"),
        ContractPharmacy("Regional Infusion Network", "Specialty Pharm (in-house)", "CE-owned", 145, 0.0, 1.00, 12.8, "active"),
        ContractPharmacy("Regional Infusion Network", "Optum (UHG)", "ECE (specialty)", 68, 0.075, 0.80, 4.2, "active"),
        ContractPharmacy("Oncology Infusion Center", "Specialty Pharm (in-house)", "CE-owned", 195, 0.0, 1.00, 18.5, "active"),
        ContractPharmacy("Oncology Infusion Center", "Express Scripts", "ECE (specialty)", 85, 0.080, 0.82, 5.8, "active"),
        ContractPharmacy("Home Infusion Network LLC", "Walgreens", "retail", 45, 0.095, 0.75, 2.8, "active"),
        ContractPharmacy("Behavioral Health FQHC", "Walgreens", "retail", 28, 0.100, 0.75, 1.5, "active"),
        ContractPharmacy("Behavioral Health FQHC", "CVS Health", "retail", 22, 0.095, 0.75, 1.1, "active"),
        ContractPharmacy("Specialty Dermatology Clinic", "Specialty Pharm (in-house)", "CE-owned", 35, 0.0, 1.00, 2.2, "active"),
        ContractPharmacy("Community Health Alliance", "Walgreens", "retail", 42, 0.100, 0.75, 2.5, "active"),
        ContractPharmacy("Community Health Alliance", "Walmart Pharmacy", "retail", 28, 0.090, 0.75, 1.6, "active"),
        ContractPharmacy("Charity GI Clinic", "Walgreens", "retail", 22, 0.095, 0.75, 1.3, "active"),
        ContractPharmacy("Community IVF Access", "CVS Health", "retail", 15, 0.100, 0.75, 0.8, "active"),
        ContractPharmacy("Dental FQHC Partner", "Local independent pharmacies (3)", "retail", 35, 0.125, 0.72, 1.8, "active"),
        ContractPharmacy("Community Behavioral Services", "Walgreens", "retail", 25, 0.100, 0.75, 1.4, "active"),
    ]


def _build_restrictions() -> List[ManufacturerRestriction]:
    return [
        ManufacturerRestriction("AstraZeneca", "2020-07-01", "Contract pharmacy restrictions (insulin + oncology)",
                                4, 8.5, "HRSA enforcement stayed; lawsuit pending", "CE-pharmacy + mail order expansion"),
        ManufacturerRestriction("Eli Lilly", "2020-09-01", "Limit to single contract pharmacy", 3, 6.2,
                                "litigation ongoing", "CE-pharmacy consolidation"),
        ManufacturerRestriction("Sanofi", "2020-10-01", "Contract pharmacy conditions", 3, 5.8,
                                "litigation ongoing", "CE-pharmacy + grandfathered"),
        ManufacturerRestriction("Novartis", "2020-07-01", "340B claim data required", 4, 7.2,
                                "HRSA enforcement on hold", "claim data submission"),
        ManufacturerRestriction("Merck", "2021-09-15", "Contract pharmacy restrictions (immuno-oncology)",
                                4, 11.2, "litigation ongoing", "CE-pharmacy + payment process"),
        ManufacturerRestriction("Bristol Myers Squibb", "2021-09-15", "Contract pharmacy restrictions (immuno-oncology)",
                                4, 12.5, "litigation ongoing", "CE-pharmacy + payment process"),
        ManufacturerRestriction("Boehringer Ingelheim", "2020-10-01", "Contract pharmacy claim data",
                                2, 2.8, "HRSA enforcement on hold", "claim data submission"),
        ManufacturerRestriction("Johnson & Johnson (Janssen)", "2021-01-01", "Contract pharmacy restrictions",
                                3, 4.5, "litigation ongoing", "CE-pharmacy + grandfathered"),
        ManufacturerRestriction("Pfizer", "2022-04-01", "Contract pharmacy claim data + repayment",
                                3, 3.8, "3rd Circuit ruling against HRSA", "CE-pharmacy"),
        ManufacturerRestriction("Takeda", "2023-01-01", "Contract pharmacy conditions",
                                2, 2.2, "litigation ongoing", "CE-pharmacy"),
    ]


def _build_audits() -> List[AuditHistory]:
    return [
        AuditHistory("Oncology Specialty Pharm LLC", "HRSA OPA Audit", "2025-09-15", "HRSA Office of Pharmacy Affairs",
                     2, 1.2, "repaid + CAP complete"),
        AuditHistory("Infusion Specialty Services", "HRSA OPA Audit", "2024-08-22", "HRSA OPA",
                     3, 2.5, "repaid + CAP complete"),
        AuditHistory("Regional Infusion Network", "Manufacturer Audit (Gilead)", "2025-04-10", "Gilead / Third-party",
                     1, 0.8, "resolved"),
        AuditHistory("Oncology Infusion Center", "HRSA OPA Audit", "2025-11-05", "HRSA OPA",
                     4, 3.5, "repayment in progress"),
        AuditHistory("Home Infusion Network LLC", "HRSA Self-Audit", "2026-02-15", "Internal / Annual Program Audit",
                     2, 0.5, "finalized"),
        AuditHistory("Behavioral Health FQHC", "HRSA OPA Audit", "2024-12-20", "HRSA OPA",
                     1, 0.3, "repaid"),
        AuditHistory("Specialty Dermatology Clinic", "HRSA Self-Audit", "2025-10-10", "Internal",
                     0, 0.0, "clean"),
        AuditHistory("Community Health Alliance", "HRSA OPA Audit", "2025-07-25", "HRSA OPA",
                     3, 1.8, "repaid + CAP complete"),
        AuditHistory("Charity GI Clinic", "HRSA OPA Audit", "2025-11-12", "HRSA OPA",
                     1, 0.4, "repayment in progress"),
        AuditHistory("Dental FQHC Partner", "HRSA OPA Audit", "2025-08-30", "HRSA OPA",
                     2, 0.6, "repaid"),
        AuditHistory("Community Behavioral Services", "State Medicaid Audit", "2026-01-15", "State Medicaid Fraud Unit",
                     1, 0.4, "finalized"),
    ]


def _build_breakdown() -> List[SavingsBreakdown]:
    return [
        SavingsBreakdown("Oncology / Chemotherapy", 12500, 148.5, 98.2, 50.3, 0.339, 5.2),
        SavingsBreakdown("Specialty (IVIG, Hemophilia)", 8500, 85.2, 57.5, 27.7, 0.325, 3.8),
        SavingsBreakdown("Biologics (rheumatology)", 15200, 52.8, 38.5, 14.3, 0.271, 2.5),
        SavingsBreakdown("Infusion (autoimmune)", 6800, 48.5, 32.0, 16.5, 0.340, 2.2),
        SavingsBreakdown("HIV Antivirals (Ryan White)", 3200, 12.8, 8.5, 4.3, 0.336, 0.8),
        SavingsBreakdown("Insulin / Diabetes Supplies", 28000, 18.5, 14.2, 4.3, 0.232, 2.8),
        SavingsBreakdown("Mental Health / Psych Meds", 15500, 15.2, 11.8, 3.4, 0.224, 1.5),
        SavingsBreakdown("Retail Generic (standard)", 185000, 28.5, 22.5, 6.0, 0.211, 1.8),
        SavingsBreakdown("Vaccines", 45000, 12.5, 9.5, 3.0, 0.240, 1.2),
        SavingsBreakdown("Women's Health / Contraception", 12500, 8.5, 5.8, 2.7, 0.318, 0.6),
        SavingsBreakdown("Respiratory (COPD/Asthma)", 22500, 18.5, 13.5, 5.0, 0.270, 1.5),
        SavingsBreakdown("Cardiology", 32500, 14.8, 10.8, 4.0, 0.270, 1.3),
    ]


def _build_updates() -> List[RegulatoryUpdate]:
    return [
        RegulatoryUpdate("HRSA 340B Modernization (discussion draft)", "2026-Q3",
                         "Formal regulatory framework for contract pharmacies + reporting",
                         5.5, "policy monitoring + contingency planning"),
        RegulatoryUpdate("Novartis/BMS/Merck 3rd Circuit Ruling", "2025-05-15",
                         "Manufacturer conditions allowed; significant CE impact",
                         -8.5, "CE-pharmacy expansion to offset"),
        RegulatoryUpdate("State 340B Non-Discrimination Laws (LA, MS, WV)", "2026-01-01",
                         "State laws preventing PBM/Mfr restrictions on 340B",
                         2.5, "state-by-state enforcement monitoring"),
        RegulatoryUpdate("Federal 340B Non-Discrimination Act (pending)", "2026-Q4 / 2027-Q1",
                         "Federal law preventing PBM anti-340B contracting",
                         4.5, "advocacy + policy tracking"),
        RegulatoryUpdate("CMS Medicare 340B Drug Payment (reinstated)", "2024-01-01",
                         "Medicare Part B pays 340B hospitals ASP+6% (was ASP-22.5%)",
                         3.8, "complete; 2024 remedy payments received"),
        RegulatoryUpdate("HRSA Patient Definition (proposed)", "2026-Q3",
                         "Narrower patient definition could reduce 340B-eligible encounters",
                         -3.2, "comment letter preparation"),
        RegulatoryUpdate("Medicaid Duplicate Discount Prohibition", "2026-Q3",
                         "HRSA Medicaid 'carve-out' policy clarification",
                         -1.5, "Medicaid pharmacy billing review"),
        RegulatoryUpdate("340B Program Integrity Act (proposed)", "2027-Q1",
                         "Mandatory public reporting of 340B savings",
                         -0.5, "transparency reporting infrastructure"),
    ]


def compute_tracker_340b() -> Tracker340BResult:
    corpus = _load_corpus()
    entities = _build_entities()
    pharmacies = _build_pharmacies()
    restrictions = _build_restrictions()
    audits = _build_audits()
    breakdown = _build_breakdown()
    updates = _build_updates()

    total_spend = sum(e.annual_340b_spend_m for e in entities)
    total_savings = sum(e.annual_savings_m for e in entities)
    eff_rate = total_savings / total_spend if total_spend > 0 else 0
    avg_comp = sum(e.compliance_score for e in entities) / len(entities) if entities else 0

    return Tracker340BResult(
        total_entities=len(entities),
        total_annual_spend_m=round(total_spend, 1),
        total_annual_savings_m=round(total_savings, 1),
        effective_savings_rate=round(eff_rate, 4),
        total_contract_pharmacies=len(pharmacies),
        avg_compliance_score=round(avg_comp, 2),
        restricted_manufacturers=len(restrictions),
        entities=entities,
        pharmacies=pharmacies,
        restrictions=restrictions,
        audits=audits,
        breakdown=breakdown,
        updates=updates,
        corpus_deal_count=len(corpus),
    )
