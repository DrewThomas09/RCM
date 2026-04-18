"""Fraud / Waste / Abuse Detection Panel.

Surfaces pattern-level red flags across billing, coding, referral, and
ownership data. Essential for diligence against DOJ/OIG exposure and
post-close compliance monitoring.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class BillingAnomaly:
    provider_id: str
    specialty: str
    billing_pattern: str
    anomaly_score: int
    peer_comparison_percentile: int
    dollar_exposure_k: float
    severity: str


@dataclass
class UpcodingRisk:
    cpt_code: str
    description: str
    platform_pct_high_level: float
    peer_pct_high_level: float
    delta_pp: float
    annual_volume: int
    potential_clawback_mm: float


@dataclass
class ReferralPattern:
    referring_provider: str
    referred_to: str
    referral_count_ltm: int
    ownership_overlap: bool
    stark_exception: str
    aks_risk_score: int


@dataclass
class ClaimFingerprint:
    pattern: str
    description: str
    claims_flagged: int
    dollar_impact_mm: float
    likelihood_of_payback: float
    remediation: str


@dataclass
class GeoAnomaly:
    zip_code: str
    provider_count: int
    volume_vs_pop_norm: float
    cluster_severity: str
    service_line: str


@dataclass
class ComplianceEvent:
    event: str
    date: str
    type: str
    resolution: str
    financial_impact_mm: float


@dataclass
class FraudDetectionResult:
    total_anomalies_flagged: int
    high_severity_count: int
    total_exposure_mm: float
    platform_fwa_risk_score: int
    risk_tier: str
    billing_anomalies: List[BillingAnomaly]
    upcoding: List[UpcodingRisk]
    referrals: List[ReferralPattern]
    fingerprints: List[ClaimFingerprint]
    geography: List[GeoAnomaly]
    events: List[ComplianceEvent]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 105):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_billing() -> List[BillingAnomaly]:
    return [
        BillingAnomaly("MD-018", "Cardiology", "Duplicate billing (paired CPT 93458 + 93306)", 88, 98, 285.0, "high"),
        BillingAnomaly("MD-042", "Orthopedics", "Modifier 25 overutilization (37% of E/M visits)", 76, 92, 185.0, "high"),
        BillingAnomaly("MD-007", "Dermatology", "Mohs CPT 17311 billed without pathology support", 92, 99, 425.0, "critical"),
        BillingAnomaly("MD-034", "Psychiatry", "90837 (60-min) at 78% of visits vs 35% peer median", 82, 95, 220.0, "high"),
        BillingAnomaly("MD-056", "Pain Management", "Billing 64483 epidural injections > weekly on same patient", 95, 99, 380.0, "critical"),
        BillingAnomaly("MD-021", "GI", "Colonoscopy screening CPT 45378 + diagnostic 45380 same day", 68, 85, 145.0, "medium"),
        BillingAnomaly("MD-089", "Urology", "CPT 55700 biopsy 18+ cores per session (limit 12)", 72, 90, 95.0, "medium"),
        BillingAnomaly("MD-102", "Home Health", "LUPA (low-utilization) mix abnormally high (22%)", 58, 78, 68.0, "medium"),
        BillingAnomaly("MD-119", "PT", "Billing units > 8/day per patient (CMS MUE)", 62, 82, 45.0, "medium"),
        BillingAnomaly("MD-134", "Family Med", "E/M 99214 at 72% of visits vs 48% peer", 68, 88, 115.0, "medium"),
    ]


def _build_upcoding() -> List[UpcodingRisk]:
    return [
        UpcodingRisk("99214 (Est. Office Visit L4)", "Moderate complexity", 0.62, 0.48, 0.14, 185000, 2.85),
        UpcodingRisk("99215 (Est. Office Visit L5)", "High complexity", 0.18, 0.09, 0.09, 62000, 1.45),
        UpcodingRisk("99205 (New Office Visit L5)", "High complexity - new pt", 0.22, 0.12, 0.10, 28000, 0.85),
        UpcodingRisk("90837 (Psychotherapy 60-min)", "vs 90834 (45-min)", 0.72, 0.38, 0.34, 85000, 3.25),
        UpcodingRisk("45385 (Colonoscopy w/ biopsy)", "vs 45378 (screening)", 0.45, 0.32, 0.13, 12500, 0.75),
        UpcodingRisk("DRG 470 (Joint Rep w/o MCC)", "vs 469 (with MCC)", 0.85, 0.72, 0.13, 1850, 0.95),
        UpcodingRisk("97140 (Manual Therapy)", "vs 97110 (Therex)", 0.58, 0.42, 0.16, 42000, 0.45),
        UpcodingRisk("J3301 (Triamcinolone)", "dose upcoding", 0.38, 0.25, 0.13, 28000, 0.35),
    ]


def _build_referrals() -> List[ReferralPattern]:
    return [
        ReferralPattern("Dr. Chen (PCP)", "Platform Imaging Center A", 382, True, "in-office ancillary", 72),
        ReferralPattern("Dr. Rodriguez (Ortho)", "Platform ASC B", 625, True, "group practice", 58),
        ReferralPattern("Dr. Patel (Cardiology)", "Platform Cath Lab", 485, True, "physician-owned entity", 82),
        ReferralPattern("Dr. Kim (GI)", "Platform Endoscopy Suite", 425, True, "group practice", 48),
        ReferralPattern("Dr. Thompson (PCP)", "Non-Platform Imaging X", 18, False, "n/a", 12),
        ReferralPattern("Dr. Johnson (Derm)", "Platform Dermpath Lab", 485, True, "in-office ancillary", 65),
        ReferralPattern("Dr. Lee (Oncology)", "Platform Infusion Suite", 385, True, "in-office ancillary", 58),
        ReferralPattern("Dr. Garcia (Cardio)", "Platform Sleep Lab", 245, False, "n/a", 82),
    ]


def _build_fingerprints() -> List[ClaimFingerprint]:
    return [
        ClaimFingerprint("Ghost Patient Pattern", "Same patient billed across 3+ locations same day", 142, 0.95, 0.85, "Immediate provider audit + claim reversal"),
        ClaimFingerprint("Copy-Paste Documentation", "Note text >85% identical across 5+ encounters", 285, 1.85, 0.72, "Physician documentation training"),
        ClaimFingerprint("Modifier Stacking", "Stacked modifiers (25, 59, 51) on same claim", 185, 0.62, 0.68, "Claim edit rule update"),
        ClaimFingerprint("Unbundling", "Global code billed separately from component services", 95, 0.78, 0.82, "Coding compliance review"),
        ClaimFingerprint("Medical Necessity Gaps", "Diagnosis code doesn't support procedure", 225, 1.25, 0.55, "Enhanced prior-auth workflow"),
        ClaimFingerprint("Repeat Service Abuse", "Same diagnostic procedure in shorter than clinical window", 68, 0.45, 0.78, "Utilization review protocols"),
        ClaimFingerprint("Timely Filing Pattern", "Delayed claims batched to specific month-end", 42, 0.15, 0.25, "Cycle improvements"),
    ]


def _build_geography() -> List[GeoAnomaly]:
    return [
        GeoAnomaly("85032 (Phoenix)", 12, 3.85, "severe", "Urology"),
        GeoAnomaly("33156 (Miami)", 18, 4.25, "severe", "Home Health"),
        GeoAnomaly("77379 (Houston)", 8, 2.85, "moderate", "Pain Management"),
        GeoAnomaly("32837 (Orlando)", 15, 3.15, "moderate", "DME"),
        GeoAnomaly("89147 (Las Vegas)", 10, 2.95, "moderate", "Behavioral Health"),
        GeoAnomaly("90210 (Beverly Hills)", 22, 2.45, "moderate", "Dermatology"),
    ]


def _build_events() -> List[ComplianceEvent]:
    return [
        ComplianceEvent("OIG Subpoena — Billing Audit", "2024-06-15", "civil inquiry", "closed — no action", 0.0),
        ComplianceEvent("Payer RAC Audit Finding", "2024-09-22", "administrative", "repaid + education", 0.385),
        ComplianceEvent("State Board of Medicine Complaint", "2024-11-08", "licensure", "dismissed", 0.0),
        ComplianceEvent("CMS UPIC Data Request", "2025-01-22", "administrative", "ongoing", 0.0),
        ComplianceEvent("DOJ Declination (qui tam)", "2025-03-15", "civil inquiry", "declined to intervene", 0.0),
    ]


def compute_fraud_detection() -> FraudDetectionResult:
    corpus = _load_corpus()

    billing = _build_billing()
    upcoding = _build_upcoding()
    referrals = _build_referrals()
    fingerprints = _build_fingerprints()
    geography = _build_geography()
    events = _build_events()

    # Totals
    billing_exp = sum(b.dollar_exposure_k for b in billing) / 1000
    upcode_exp = sum(u.potential_clawback_mm for u in upcoding)
    fp_exp = sum(f.dollar_impact_mm * f.likelihood_of_payback for f in fingerprints)
    event_exp = sum(e.financial_impact_mm for e in events)
    total_exposure = billing_exp + upcode_exp + fp_exp + event_exp

    total_anomalies = len(billing) + len(upcoding) + len(fingerprints) + sum(1 for r in referrals if r.aks_risk_score >= 60)
    high_sev = sum(1 for b in billing if b.severity in ("critical", "high"))
    high_sev += sum(1 for f in fingerprints if f.dollar_impact_mm >= 1.0)
    high_sev += sum(1 for g in geography if g.cluster_severity == "severe")

    # Overall risk score 0-100
    risk_score = min(100, int(total_exposure * 6 + high_sev * 4))

    if risk_score >= 70:
        tier = "elevated"
    elif risk_score >= 45:
        tier = "moderate"
    else:
        tier = "low"

    return FraudDetectionResult(
        total_anomalies_flagged=total_anomalies,
        high_severity_count=high_sev,
        total_exposure_mm=round(total_exposure, 2),
        platform_fwa_risk_score=risk_score,
        risk_tier=tier,
        billing_anomalies=billing,
        upcoding=upcoding,
        referrals=referrals,
        fingerprints=fingerprints,
        geography=geography,
        events=events,
        corpus_deal_count=len(corpus),
    )
