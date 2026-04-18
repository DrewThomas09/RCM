"""Compliance Attestation / Security Posture Tracker.

Tracks formal attestations (SOC 2, HITRUST, HIPAA, PCI, ISO),
penetration test findings, third-party risk scores, vendor risk
reviews across portfolio companies.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class AttestationStatus:
    deal: str
    sector: str
    soc2_type: str
    soc2_expires: str
    hitrust_level: str
    hitrust_expires: str
    hipaa_assessment: str
    pci_level: str
    iso_27001: str
    overall_score: float


@dataclass
class PenTestFinding:
    deal: str
    test_date: str
    firm: str
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    remediated_pct: float
    status: str


@dataclass
class VendorRisk:
    vendor: str
    category: str
    portfolio_deals: int
    risk_score: float
    soc2_current: bool
    last_review: str
    contract_spend_m: float
    risk_tier: str


@dataclass
class IncidentHistory:
    incident_date: str
    deal: str
    incident_type: str
    severity: str
    records_affected_k: float
    downtime_hours: int
    cost_m: float
    root_cause: str
    remediation_status: str


@dataclass
class ControlFramework:
    framework: str
    version: str
    portfolio_deals: int
    avg_maturity_score: float
    avg_coverage_pct: float
    gaps_identified: int
    typical_remediation_cost_m: float


@dataclass
class AuditCalendar:
    deal: str
    auditor: str
    audit_type: str
    start_date: str
    end_date: str
    scope: str
    status: str


@dataclass
class ComplianceResult:
    total_portcos: int
    soc2_type_ii_count: int
    hitrust_certified_count: int
    avg_posture_score: float
    active_incidents: int
    high_risk_vendors: int
    audits_in_progress: int
    attestations: List[AttestationStatus]
    pentests: List[PenTestFinding]
    vendors: List[VendorRisk]
    incidents: List[IncidentHistory]
    frameworks: List[ControlFramework]
    calendar: List[AuditCalendar]
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


def _build_attestations() -> List[AttestationStatus]:
    return [
        AttestationStatus("Project Oak — RCM SaaS", "RCM / HCIT", "Type II (active)", "2026-09-30",
                          "r2 (active)", "2027-03-15", "compliant + BAA", "PCI-DSS Level 1", "ISO 27001 (active)", 9.2),
        AttestationStatus("Project Cypress — GI Network", "Gastroenterology", "Type II (active)", "2026-11-15",
                          "essentials (active)", "2026-09-30", "compliant + BAA", "not applicable", "in progress", 8.5),
        AttestationStatus("Project Magnolia — MSK Platform", "MSK / Ortho", "Type II (active)", "2026-10-31",
                          "essentials (active)", "2026-11-30", "compliant + BAA", "not applicable", "not yet", 8.0),
        AttestationStatus("Project Redwood — Behavioral", "Behavioral Health", "Type I (active)", "2026-08-15",
                          "not yet", "not yet", "compliant + BAA", "not applicable", "not yet", 7.2),
        AttestationStatus("Project Cedar — Cardiology", "Cardiology", "Type II (active)", "2026-07-31",
                          "essentials (active)", "2027-01-15", "compliant + BAA", "not applicable", "not yet", 8.2),
        AttestationStatus("Project Laurel — Derma", "Dermatology", "Type I (active)", "2026-09-30",
                          "not yet", "not yet", "compliant + BAA", "PCI-DSS Level 3", "not yet", 7.8),
        AttestationStatus("Project Willow — Fertility", "Fertility / IVF", "Type II (in audit)", "n/a (in audit)",
                          "essentials (active)", "2027-02-28", "compliant + BAA", "not applicable", "not yet", 8.0),
        AttestationStatus("Project Spruce — Radiology", "Radiology", "Type II (active)", "2026-12-15",
                          "essentials (active)", "2026-10-31", "compliant + BAA", "not applicable", "not yet", 8.5),
        AttestationStatus("Project Aspen — Eye Care", "Eye Care", "Type I (active)", "2026-08-31",
                          "not yet", "not yet", "compliant + BAA (remediation pending)", "PCI-DSS Level 3", "not yet", 6.8),
        AttestationStatus("Project Maple — Urology", "Urology", "Type I (active)", "2026-09-15",
                          "not yet", "not yet", "compliant + BAA", "not applicable", "not yet", 7.5),
        AttestationStatus("Project Ash — Infusion", "Infusion", "Type II (active)", "2026-11-30",
                          "essentials (active)", "2027-04-30", "compliant + BAA", "not applicable", "not yet", 8.8),
        AttestationStatus("Project Fir — Lab / Pathology", "Lab Services", "Type II (active)", "2026-09-15",
                          "r2 (active)", "2027-06-30", "compliant + BAA", "not applicable", "ISO 27001 (active)", 9.0),
        AttestationStatus("Project Sage — Home Health", "Home Health", "Type I (expired)", "expired 2025-12-15",
                          "not yet", "not yet", "compliant + BAA (audit pending)", "not applicable", "not yet", 6.5),
        AttestationStatus("Project Linden — Behavioral", "Behavioral Health", "Type I (active)", "2026-10-31",
                          "not yet", "not yet", "compliant + BAA", "not applicable", "not yet", 7.0),
        AttestationStatus("Project Basil — Dental DSO", "Dental DSO", "Type II (active)", "2026-08-15",
                          "essentials (active)", "2027-01-31", "compliant + BAA", "PCI-DSS Level 2", "not yet", 8.5),
        AttestationStatus("Project Thyme — Specialty Pharm", "Specialty Pharma", "Type II (active)", "2026-10-15",
                          "essentials (active)", "2027-03-30", "compliant + BAA", "PCI-DSS Level 2", "not yet", 8.8),
    ]


def _build_pentests() -> List[PenTestFinding]:
    return [
        PenTestFinding("Project Oak — RCM SaaS", "2025-11-15", "Bishop Fox", 0, 2, 8, 15, 0.95, "remediation complete"),
        PenTestFinding("Project Cypress — GI Network", "2025-12-20", "NCC Group", 0, 3, 12, 22, 0.88, "remediation active"),
        PenTestFinding("Project Magnolia — MSK Platform", "2026-01-18", "Rapid7", 1, 4, 15, 28, 0.75, "remediation active"),
        PenTestFinding("Project Redwood — Behavioral", "2026-02-10", "Praetorian", 2, 5, 18, 32, 0.55, "remediation active"),
        PenTestFinding("Project Cedar — Cardiology", "2025-11-28", "Coalfire", 0, 2, 10, 18, 0.92, "remediation complete"),
        PenTestFinding("Project Laurel — Derma", "2025-10-15", "Synopsys", 1, 3, 14, 24, 0.82, "remediation active"),
        PenTestFinding("Project Willow — Fertility", "2025-12-08", "Trail of Bits", 0, 3, 9, 15, 0.90, "remediation complete"),
        PenTestFinding("Project Spruce — Radiology", "2026-02-22", "IOActive", 0, 2, 8, 12, 0.93, "remediation active"),
        PenTestFinding("Project Aspen — Eye Care", "2025-09-30", "Mandiant", 3, 8, 22, 38, 0.35, "active remediation (critical)"),
        PenTestFinding("Project Maple — Urology", "2026-01-28", "Optiv Source Zero", 1, 4, 12, 22, 0.68, "remediation active"),
        PenTestFinding("Project Ash — Infusion", "2025-12-02", "Mandiant", 0, 2, 7, 14, 0.98, "remediation complete"),
        PenTestFinding("Project Fir — Lab / Pathology", "2026-01-12", "Bishop Fox", 0, 1, 6, 10, 1.00, "remediation complete"),
        PenTestFinding("Project Sage — Home Health", "2025-10-20", "NCC Group", 2, 6, 18, 28, 0.42, "active remediation (critical)"),
        PenTestFinding("Project Linden — Behavioral", "2026-02-15", "Synack", 1, 3, 11, 19, 0.72, "remediation active"),
        PenTestFinding("Project Basil — Dental DSO", "2025-11-08", "Trustwave", 1, 4, 13, 25, 0.78, "remediation active"),
    ]


def _build_vendors() -> List[VendorRisk]:
    return [
        VendorRisk("Epic Systems", "EHR", 8, 9.5, True, "2025-12-15", 65.0, "tier 1"),
        VendorRisk("Oracle Health (Cerner)", "EHR", 5, 9.2, True, "2025-11-20", 45.0, "tier 1"),
        VendorRisk("athenahealth", "EHR", 4, 9.0, True, "2026-01-22", 28.0, "tier 1"),
        VendorRisk("NextGen Healthcare", "EHR", 3, 8.5, True, "2026-02-10", 18.0, "tier 1"),
        VendorRisk("eClinicalWorks", "EHR", 2, 8.2, True, "2025-12-05", 12.0, "tier 1"),
        VendorRisk("Change Healthcare (UHG)", "RCM / Clearinghouse", 12, 7.5, True, "2026-02-28", 45.0, "tier 2 (post-breach)"),
        VendorRisk("Availity", "RCM / Clearinghouse", 8, 8.8, True, "2025-11-28", 22.0, "tier 1"),
        VendorRisk("Surescripts", "eRx", 10, 9.0, True, "2026-01-15", 8.5, "tier 1"),
        VendorRisk("Amazon Web Services", "Cloud Infrastructure", 16, 9.5, True, "2025-12-20", 38.0, "tier 1"),
        VendorRisk("Microsoft Azure", "Cloud Infrastructure", 8, 9.5, True, "2026-01-10", 18.0, "tier 1"),
        VendorRisk("Salesforce Health Cloud", "CRM", 12, 9.2, True, "2025-12-18", 15.0, "tier 1"),
        VendorRisk("ServiceNow", "Workflow / ITSM", 10, 9.0, True, "2026-02-15", 12.0, "tier 1"),
        VendorRisk("Zoom", "Telehealth / Comms", 14, 8.8, True, "2026-01-25", 8.0, "tier 1"),
        VendorRisk("DataRobot", "AI / ML Platform", 4, 8.2, True, "2025-12-15", 5.5, "tier 2"),
        VendorRisk("Iron Mountain", "Records / Shredding", 12, 7.8, False, "2025-09-10", 4.0, "tier 2"),
        VendorRisk("Stericycle", "Medical Waste / Secure Shred", 8, 7.5, False, "2025-10-20", 12.0, "tier 2"),
        VendorRisk("Zelis", "Payments / RCM", 6, 7.8, True, "2025-11-18", 8.5, "tier 2"),
        VendorRisk("Waystar", "RCM SaaS", 8, 8.5, True, "2026-01-30", 15.0, "tier 1"),
    ]


def _build_incidents() -> List[IncidentHistory]:
    return [
        IncidentHistory("2024-02-15", "Project Aspen — Eye Care", "Ransomware", "critical",
                        215.0, 48, 8.5, "Phishing → privilege escalation", "complete (post-breach)"),
        IncidentHistory("2025-08-22", "Project Sage — Home Health", "Data exposure", "high",
                        45.0, 12, 3.2, "Misconfigured S3 bucket", "complete"),
        IncidentHistory("2025-11-05", "Project Redwood — Behavioral", "Phishing compromise", "medium",
                        8.5, 4, 0.8, "Executive BEC attempt", "complete"),
        IncidentHistory("2025-12-08", "Project Willow — Fertility", "Insider threat", "medium",
                        12.0, 0, 0.5, "Departing MD with patient list", "complete"),
        IncidentHistory("2026-01-15", "Project Linden — Behavioral", "Ransomware (contained)", "high",
                        0.0, 8, 1.2, "Legacy system vulnerability", "complete"),
        IncidentHistory("2026-02-22", "Project Maple — Urology", "Lost laptop (encrypted)", "low",
                        2.5, 0, 0.1, "Physical device loss", "complete"),
        IncidentHistory("2026-03-18", "Project Basil — Dental DSO", "Credential stuffing", "medium",
                        5.8, 2, 0.4, "Password reuse attack", "complete"),
        IncidentHistory("2026-04-02", "Project Cypress — GI Network", "Phishing (no compromise)", "low",
                        0.0, 0, 0.05, "User reported phish", "complete"),
    ]


def _build_frameworks() -> List[ControlFramework]:
    return [
        ControlFramework("HIPAA Security Rule", "45 CFR 164.300", 16, 3.8, 0.92, 18, 0.5),
        ControlFramework("HITRUST CSF", "v11.3", 11, 4.2, 0.85, 42, 1.2),
        ControlFramework("SOC 2 Type II", "2017 TSC (r3)", 15, 4.0, 0.93, 25, 0.8),
        ControlFramework("NIST CSF 2.0", "2024", 16, 3.5, 0.80, 65, 1.5),
        ControlFramework("ISO 27001:2022", "2022", 2, 4.0, 0.88, 12, 2.2),
        ControlFramework("PCI-DSS v4.0", "4.0 (2024)", 5, 3.8, 0.82, 18, 0.6),
        ControlFramework("CIS Controls v8", "v8", 14, 3.6, 0.78, 45, 0.9),
        ControlFramework("NIST 800-53 r5 Moderate", "r5", 6, 3.2, 0.72, 48, 1.8),
    ]


def _build_calendar() -> List[AuditCalendar]:
    return [
        AuditCalendar("Project Willow — Fertility", "A-LIGN", "SOC 2 Type II (first)", "2026-01-15", "2026-05-15", "All services + BCM + DR", "in audit"),
        AuditCalendar("Project Redwood — Behavioral", "Coalfire", "SOC 2 Type II (transition)", "2026-04-01", "2026-09-30", "Platform + data center + cloud", "scheduled"),
        AuditCalendar("Project Magnolia — MSK Platform", "Schellman", "HITRUST r2 (upgrade)", "2026-05-01", "2026-10-31", "Full CSF v11.3 scope", "scheduled"),
        AuditCalendar("Project Cypress — GI Network", "Schellman", "SOC 2 Type II (renewal)", "2026-04-15", "2026-09-15", "Platform + billing + clinical", "scheduled"),
        AuditCalendar("Project Sage — Home Health", "A-LIGN", "SOC 2 Type I (urgent)", "2026-04-20", "2026-07-20", "Platform + mobile + back office", "urgent (expired)"),
        AuditCalendar("Project Aspen — Eye Care", "Coalfire", "HITRUST essentials (first)", "2026-06-01", "2026-11-30", "Patient data + clinical systems", "scheduled"),
        AuditCalendar("Project Linden — Behavioral", "Schellman", "SOC 2 Type II (transition)", "2026-05-15", "2026-10-15", "Platform + mobile + back office", "scheduled"),
        AuditCalendar("Project Maple — Urology", "A-LIGN", "SOC 2 Type II (transition)", "2026-07-01", "2026-12-31", "Platform + EHR integration", "scheduled"),
        AuditCalendar("Project Thyme — Specialty Pharm", "KirkpatrickPrice", "HITRUST r2 (upgrade)", "2026-06-15", "2026-12-15", "Full CSF v11.3 scope", "scheduled"),
        AuditCalendar("Project Ash — Infusion", "Schellman", "HITRUST r2 (upgrade)", "2026-07-15", "2027-01-15", "Full CSF scope", "scheduled"),
    ]


def compute_compliance_attestation() -> ComplianceResult:
    corpus = _load_corpus()
    attestations = _build_attestations()
    pentests = _build_pentests()
    vendors = _build_vendors()
    incidents = _build_incidents()
    frameworks = _build_frameworks()
    calendar = _build_calendar()

    soc2_ii = sum(1 for a in attestations if "Type II" in a.soc2_type and "active" in a.soc2_type)
    hitrust = sum(1 for a in attestations if "active" in a.hitrust_level)
    avg_score = sum(a.overall_score for a in attestations) / len(attestations) if attestations else 0
    active_incidents = sum(1 for i in incidents if "complete" not in i.remediation_status)
    high_risk_vendors = sum(1 for v in vendors if v.risk_tier not in ("tier 1",) or v.risk_score < 8.5)
    audits_in_progress = sum(1 for c in calendar if c.status in ("in audit", "scheduled", "urgent (expired)"))

    return ComplianceResult(
        total_portcos=len(attestations),
        soc2_type_ii_count=soc2_ii,
        hitrust_certified_count=hitrust,
        avg_posture_score=round(avg_score, 2),
        active_incidents=active_incidents,
        high_risk_vendors=high_risk_vendors,
        audits_in_progress=audits_in_progress,
        attestations=attestations,
        pentests=pentests,
        vendors=vendors,
        incidents=incidents,
        frameworks=frameworks,
        calendar=calendar,
        corpus_deal_count=len(corpus),
    )
