"""Cybersecurity / HIPAA Risk Scorecard.

Diligence-grade cybersecurity posture for PE healthcare platforms.
Critical post-Change Healthcare ransomware (Feb 2024) — a $22B hit to
the sector that rewrote how sponsors underwrite cyber risk.

Tracks threat exposure, control maturity, incident history, ransomware
preparedness, and HHS OCR notification posture.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ControlDomain:
    domain: str
    maturity_score: int
    industry_benchmark: int
    nist_csf_tier: str
    last_audit_date: str
    findings_count: int


@dataclass
class IncidentHistory:
    date: str
    incident_type: str
    scope: str
    records_affected: int
    hhs_reportable: bool
    remediation_cost_mm: float
    status: str


@dataclass
class RansomwarePrep:
    capability: str
    maturity: str
    rto_hours: int
    rpo_hours: int
    last_tabletop: str
    gap_description: str


@dataclass
class ThreatVector:
    vector: str
    probability_ltm: str
    financial_impact_mm: float
    industry_incidence_pct: float
    mitigation_status: str


@dataclass
class ComplianceChecklist:
    framework: str
    scope: str
    status: str
    coverage_pct: float
    last_assessment: str
    remediation_cost_mm: float


@dataclass
class VendorExposure:
    third_party: str
    access_scope: str
    bah_coverage: str
    soc2_status: str
    last_review: str
    risk_score: int


@dataclass
class CyberResult:
    overall_cyber_score: int
    risk_tier: str
    total_records_in_scope: int
    cyber_insurance_coverage_mm: float
    annual_cyber_spend_mm: float
    avg_control_maturity: float
    domains: List[ControlDomain]
    incidents: List[IncidentHistory]
    ransomware: List[RansomwarePrep]
    threats: List[ThreatVector]
    compliance: List[ComplianceChecklist]
    vendors: List[VendorExposure]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 109):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_domains() -> List[ControlDomain]:
    return [
        ControlDomain("Identity & Access Management", 72, 75, "Tier 3 (Repeatable)", "2024-11-15", 4),
        ControlDomain("Endpoint Security (EDR/XDR)", 85, 82, "Tier 4 (Adaptive)", "2024-12-08", 2),
        ControlDomain("Network Segmentation", 68, 72, "Tier 3 (Repeatable)", "2024-10-22", 6),
        ControlDomain("Vulnerability Management", 78, 78, "Tier 3 (Repeatable)", "2025-01-15", 3),
        ControlDomain("Data Protection / Encryption", 82, 80, "Tier 3 (Repeatable)", "2024-11-30", 2),
        ControlDomain("Security Operations / SIEM", 65, 72, "Tier 2 (Risk-Informed)", "2024-09-18", 8),
        ControlDomain("Incident Response", 70, 70, "Tier 3 (Repeatable)", "2024-10-01", 5),
        ControlDomain("Business Continuity / DR", 62, 68, "Tier 2 (Risk-Informed)", "2024-08-15", 7),
        ControlDomain("Third-Party Risk Management", 58, 65, "Tier 2 (Risk-Informed)", "2024-07-20", 12),
        ControlDomain("Security Awareness Training", 78, 75, "Tier 3 (Repeatable)", "2024-12-01", 3),
        ControlDomain("Governance / Risk / Compliance", 75, 72, "Tier 3 (Repeatable)", "2024-11-08", 4),
        ControlDomain("Cloud Security Posture", 72, 70, "Tier 3 (Repeatable)", "2024-10-30", 5),
    ]


def _build_incidents() -> List[IncidentHistory]:
    return [
        IncidentHistory("2024-02-21", "Phishing (credential harvesting)", "Single department",
                        485, False, 0.12, "closed — no notification"),
        IncidentHistory("2024-06-10", "Lost unencrypted device", "1 employee laptop",
                        2850, True, 0.385, "notifications complete"),
        IncidentHistory("2024-09-22", "Vendor breach (exposed portal)", "EHR vendor Y outage",
                        12500, True, 1.25, "notifications complete + OCR response"),
        IncidentHistory("2024-11-08", "Ransomware attempt (blocked by EDR)", "Zero successful encryption",
                        0, False, 0.085, "closed — no impact"),
        IncidentHistory("2025-01-22", "Insider improper access", "Single physician",
                        285, True, 0.045, "HHS notification; employee terminated"),
        IncidentHistory("2025-03-08", "Business email compromise", "Finance phishing attempt",
                        0, False, 0.22, "closed — no funds lost"),
    ]


def _build_ransomware() -> List[RansomwarePrep]:
    return [
        RansomwarePrep("Immutable Backups (WORM)", "strong", 8, 4, "2025-01-15", "well-implemented"),
        RansomwarePrep("Offline Backup Validation", "strong", 8, 4, "2025-01-15", "quarterly tests passing"),
        RansomwarePrep("Network Segmentation (EHR/Corp)", "moderate", 12, 6, "2024-10-22", "IoT/medical device VLAN incomplete"),
        RansomwarePrep("EDR on All Endpoints", "strong", 1, 0, "continuous", "100% coverage"),
        RansomwarePrep("Email Security (Phishing Defense)", "strong", 0, 0, "continuous", "Proofpoint + Abnormal"),
        RansomwarePrep("MFA on All Privileged Access", "moderate", 0, 0, "2024-12-08", "85% coverage, service accts remaining"),
        RansomwarePrep("Ransomware Tabletop Exercise", "moderate", 0, 0, "2024-10-01", "annually — increase to semi-annual"),
        RansomwarePrep("Cyber Insurance (Ransomware Cov)", "strong", 0, 0, "2025-01-01", "$50M aggregate — renewal Q1 2026"),
        RansomwarePrep("Legal / FBI Notification Playbook", "strong", 2, 0, "2024-11-15", "retainer active"),
        RansomwarePrep("Crypto Payment Preparedness", "strong", 0, 0, "n/a (no-pay policy)", "cold-wallet partner"),
    ]


def _build_threats() -> List[ThreatVector]:
    return [
        ThreatVector("Ransomware (Sector-Wide)", "high", 18.5, 0.32, "active defense"),
        ThreatVector("Third-Party Vendor Breach", "high", 12.5, 0.42, "enhanced TPRM 2025"),
        ThreatVector("Phishing / Credential Theft", "very high", 2.8, 0.68, "continuous training + email sec"),
        ThreatVector("Insider Threat (Malicious)", "medium", 4.5, 0.08, "UEBA monitoring"),
        ThreatVector("Supply Chain Attack", "medium", 8.5, 0.12, "SBOM review + vendor SOC 2"),
        ThreatVector("Medical Device Exploitation", "medium", 5.2, 0.15, "network segmentation"),
        ThreatVector("Nation-State APT", "low", 35.0, 0.02, "MDR / 24x7 SOC"),
        ThreatVector("DDoS (Operational)", "medium", 1.2, 0.18, "Cloudflare mitigation"),
    ]


def _build_compliance() -> List[ComplianceChecklist]:
    return [
        ComplianceChecklist("HIPAA Security Rule", "All PHI", "compliant", 0.92, "2024-11-15", 0.18),
        ComplianceChecklist("HIPAA Privacy Rule", "All PHI", "compliant", 0.95, "2024-11-15", 0.08),
        ComplianceChecklist("HIPAA Breach Notification", "All systems", "compliant", 1.00, "2024-11-15", 0.00),
        ComplianceChecklist("HITRUST CSF Certification", "Core platform", "r2 certified 2024", 0.88, "2024-08-30", 0.45),
        ComplianceChecklist("SOC 2 Type II", "Customer-facing platforms", "passed 2024", 1.00, "2024-10-20", 0.32),
        ComplianceChecklist("PCI-DSS (Payment)", "Payment channels", "compliant", 0.98, "2024-09-15", 0.08),
        ComplianceChecklist("ISO 27001", "Core platform", "certified 2023", 0.92, "2023-12-15", 0.28),
        ComplianceChecklist("NIST 800-66r2 (HIPAA)", "All systems", "aligned", 0.85, "2024-11-15", 0.22),
        ComplianceChecklist("HHS 405(d) HICP", "Clinical systems", "aligned", 0.78, "2024-08-30", 0.35),
        ComplianceChecklist("CMMC 2.0 (federal)", "N/A (no federal contracts)", "not applicable", 0.00, "N/A", 0.00),
    ]


def _build_vendors() -> List[VendorExposure]:
    return [
        VendorExposure("Epic EHR (hosted)", "All PHI", "BAA current", "SOC 2 Type II current", "2024-10-15", 22),
        VendorExposure("Waystar (RCM)", "Claims data", "BAA current", "SOC 2 Type II current", "2024-09-22", 28),
        VendorExposure("Microsoft Azure", "Infrastructure", "BAA current", "SOC 2 Type II current", "2024-11-08", 18),
        VendorExposure("Salesforce Health Cloud", "Patient CRM", "BAA current", "SOC 2 Type II current", "2024-08-20", 32),
        VendorExposure("Zoom Healthcare", "Telehealth video", "BAA current", "SOC 2 Type II current", "2024-10-02", 25),
        VendorExposure("Vendor X (RCM BPO offshore)", "Claims processing", "BAA current", "SOC 2 Type I only", "2024-06-18", 62),
        VendorExposure("Regional Lab Network", "Test results", "BAA current", "SOC 2 Type II current", "2024-07-30", 42),
        VendorExposure("Nuance / DAX Copilot", "Clinical documentation", "BAA current", "SOC 2 Type II current", "2024-11-15", 28),
        VendorExposure("Twilio / SMS", "Patient comms", "BAA current", "SOC 2 Type II current", "2024-10-22", 35),
        VendorExposure("Abnormal Security (email)", "Email metadata", "BAA not required", "SOC 2 Type II current", "2024-09-10", 22),
    ]


def compute_cyber_risk() -> CyberResult:
    corpus = _load_corpus()

    domains = _build_domains()
    incidents = _build_incidents()
    ransomware = _build_ransomware()
    threats = _build_threats()
    compliance = _build_compliance()
    vendors = _build_vendors()

    avg_maturity = sum(d.maturity_score for d in domains) / len(domains) if domains else 0
    overall_score = int(avg_maturity)

    if overall_score >= 80:
        tier = "strong"
    elif overall_score >= 70:
        tier = "adequate"
    elif overall_score >= 60:
        tier = "developing"
    else:
        tier = "elevated risk"

    return CyberResult(
        overall_cyber_score=overall_score,
        risk_tier=tier,
        total_records_in_scope=2850000,
        cyber_insurance_coverage_mm=50.0,
        annual_cyber_spend_mm=8.5,
        avg_control_maturity=round(avg_maturity, 1),
        domains=domains,
        incidents=incidents,
        ransomware=ransomware,
        threats=threats,
        compliance=compliance,
        vendors=vendors,
        corpus_deal_count=len(corpus),
    )
