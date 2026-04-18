"""Regulatory Risk Tracker — HIPAA, Stark, Anti-Kickback, OIG, CMS reg risk.

Healthcare PE deals carry heavy regulatory risk. Models:
- Sector-specific regulatory risk score (1-10)
- Known historical enforcement patterns (OIG settlements, CIA, DOJ)
- Upcoming rule changes (CMS Physician Fee Schedule, HH CoP, 340B)
- Materiality score: which risks could impair >5% of EV
- Diligence flag list with severity
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector regulatory risk priors
# ---------------------------------------------------------------------------

_SECTOR_RISK_PROFILE = {
    "Home Health":        {"risk_score": 9, "primary_risks": ["OIG audit", "HH CoP", "Face-to-face rule"]},
    "Hospice":            {"risk_score": 9, "primary_risks": ["Revocation rates", "OIG LCDs", "CoP rule"]},
    "DME":                {"risk_score": 9, "primary_risks": ["Competitive bidding", "Prior auth", "Fraud"]},
    "Pharmacy":           {"risk_score": 7, "primary_risks": ["340B", "PBM contracts", "Diversion"]},
    "Specialty Pharmacy": {"risk_score": 7, "primary_risks": ["340B", "PBM", "Split-billing"]},
    "Skilled Nursing":    {"risk_score": 9, "primary_risks": ["PDPM", "Staffing", "IJ deficiencies"]},
    "Behavioral Health":  {"risk_score": 8, "primary_risks": ["Licensing", "Parity Act", "Coding"]},
    "Addiction Treatment":{"risk_score": 9, "primary_risks": ["Eliza's Law", "Patient brokering", "Licensing"]},
    "ABA Therapy":        {"risk_score": 7, "primary_risks": ["Coverage", "Credentialing", "Coding audits"]},
    "ASC":                {"risk_score": 6, "primary_risks": ["ASC payment rule", "Anti-kickback", "Joint venture Stark"]},
    "Surgery Center":     {"risk_score": 6, "primary_risks": ["ASC payment rule", "Anti-kickback"]},
    "Physician Services": {"risk_score": 6, "primary_risks": ["Stark II", "PFS", "Managed care contracts"]},
    "Dermatology":        {"risk_score": 5, "primary_risks": ["Modifier usage", "Path coding", "Stark"]},
    "Ophthalmology":      {"risk_score": 6, "primary_risks": ["Cataract billing", "Stark JV", "Modifier 25"]},
    "Gastroenterology":   {"risk_score": 6, "primary_risks": ["Screening vs diagnostic", "Pathology", "Anesthesia billing"]},
    "Orthopedics":        {"risk_score": 6, "primary_risks": ["Physician-owned distributorships", "Implants"]},
    "Laboratory":         {"risk_score": 8, "primary_risks": ["EKRA", "Markup regs", "PAMA"]},
    "Diagnostics":        {"risk_score": 8, "primary_risks": ["EKRA", "Medical necessity"]},
    "Hospital":           {"risk_score": 7, "primary_risks": ["EMTALA", "340B", "Provider-based rules"]},
    "Urgent Care":        {"risk_score": 5, "primary_risks": ["Scope of practice", "Observation"]},
    "Clinical Trials":    {"risk_score": 6, "primary_risks": ["FDA 483s", "GCP", "Subject safety"]},
    "Healthcare IT":      {"risk_score": 4, "primary_risks": ["ONC certification", "Info blocking", "HIPAA"]},
    "EHR/EMR":            {"risk_score": 5, "primary_risks": ["ONC rule", "Cures Act", "Anti-trust"]},
    "Telehealth":         {"risk_score": 7, "primary_risks": ["PHE expiration", "State licensure", "Corp practice"]},
}


# ---------------------------------------------------------------------------
# Active regulatory events (CY2025-2026)
# ---------------------------------------------------------------------------

_ACTIVE_REGS = [
    {
        "name": "2026 Physician Fee Schedule",
        "agency": "CMS",
        "impact_areas": ["Physician Services", "Cardiology", "Gastroenterology",
                         "Dermatology", "Ophthalmology", "Primary Care"],
        "direction": "mixed",
        "revenue_impact_pct": -0.012,
        "effective_date": "2026-01-01",
        "status": "final",
    },
    {
        "name": "340B Neutrality Policy Reset",
        "agency": "HRSA",
        "impact_areas": ["Pharmacy", "Specialty Pharmacy", "Hospital"],
        "direction": "negative",
        "revenue_impact_pct": -0.035,
        "effective_date": "2025-10-01",
        "status": "active",
    },
    {
        "name": "HH CoP Rewrite (Face-to-Face)",
        "agency": "CMS",
        "impact_areas": ["Home Health"],
        "direction": "negative",
        "revenue_impact_pct": -0.045,
        "effective_date": "2025-07-01",
        "status": "final",
    },
    {
        "name": "PHE Telehealth Flexibilities Sunset",
        "agency": "CMS",
        "impact_areas": ["Telehealth", "Behavioral Health"],
        "direction": "negative",
        "revenue_impact_pct": -0.08,
        "effective_date": "2025-12-31",
        "status": "active",
    },
    {
        "name": "Medicare Advantage Risk Adjustment V28",
        "agency": "CMS",
        "impact_areas": ["Primary Care", "Medicare Advantage"],
        "direction": "negative",
        "revenue_impact_pct": -0.018,
        "effective_date": "2026-01-01",
        "status": "phase-in",
    },
    {
        "name": "ASC Payment Rule Update",
        "agency": "CMS",
        "impact_areas": ["ASC", "Surgery Center"],
        "direction": "positive",
        "revenue_impact_pct": 0.028,
        "effective_date": "2026-01-01",
        "status": "final",
    },
    {
        "name": "PDPM NTA Phase-2",
        "agency": "CMS",
        "impact_areas": ["Skilled Nursing"],
        "direction": "negative",
        "revenue_impact_pct": -0.024,
        "effective_date": "2025-10-01",
        "status": "active",
    },
    {
        "name": "OIG Work Plan — Specialty Drug Markups",
        "agency": "OIG",
        "impact_areas": ["Specialty Pharmacy", "Oncology Pharmacy"],
        "direction": "negative",
        "revenue_impact_pct": -0.022,
        "effective_date": "2025-01-01",
        "status": "enforcement",
    },
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RiskFactor:
    factor: str
    severity: str                 # "high", "medium", "low"
    description: str
    mitigations: str


@dataclass
class RegulatoryEvent:
    name: str
    agency: str
    effective_date: str
    status: str
    direction: str                # "positive", "negative", "mixed"
    revenue_impact_pct: float
    applies_to_deal: bool
    notes: str


@dataclass
class MaterialityRow:
    impact_name: str
    revenue_impact_pct: float
    ebitda_impact_mm: float
    ev_impact_mm: float
    materiality_tier: str         # "material", "non-material"


@dataclass
class ComplianceGap:
    area: str
    requirement: str
    current_status: str           # "compliant", "gap", "unknown"
    remediation_cost_mm: float
    days_to_close: int


@dataclass
class RegulatoryRiskResult:
    sector: str
    risk_score: int               # 1-10
    risk_label: str               # "Low", "Medium", "High", "Critical"
    risk_factors: List[RiskFactor]
    active_events: List[RegulatoryEvent]
    materiality_schedule: List[MaterialityRow]
    compliance_gaps: List[ComplianceGap]
    total_revenue_drag_pct: float
    total_ev_risk_mm: float
    total_remediation_cost_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 61):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _label_for_score(score: int) -> str:
    if score >= 9: return "Critical"
    if score >= 7: return "High"
    if score >= 5: return "Medium"
    return "Low"


def _sector_profile(sector: str) -> Dict:
    return _SECTOR_RISK_PROFILE.get(sector, {"risk_score": 5, "primary_risks": ["General"]})


def _risk_factors_for(sector: str) -> List[RiskFactor]:
    """Canonical risk catalog filtered by sector relevance."""
    catalog = [
        ("Stark Law II Physician Self-Referral",
         "high" if sector in ("Physician Services", "Ophthalmology", "Orthopedics", "Gastroenterology", "Cardiology") else "medium",
         "Physician financial relationships with DHS entities. Technical violations trigger per-claim penalties.",
         "Run Stark mapping; validate rental/comp FMV; document exceptions"),
        ("Anti-Kickback Statute (AKS) / EKRA",
         "high" if sector in ("Laboratory", "Diagnostics", "Addiction Treatment", "DME", "Home Health") else "medium",
         "Remuneration intended to induce referrals. EKRA expanded to labs/recovery in 2018.",
         "Compensation model audit; documented safe harbors; referral source analysis"),
        ("HIPAA Privacy & Security Rule",
         "medium",
         "PHI breaches → OCR investigations + state AG actions. Avg breach cost $10.9M.",
         "SRA; encryption; BAAs; breach response playbook"),
        ("OIG Exclusion / CIA",
         "high" if sector in ("Home Health", "DME", "Hospice", "Skilled Nursing") else "low",
         "OIG program exclusion = termination of Medicare/Medicaid reimbursement.",
         "Monthly OIG LEIE/SAM checks; cost-report integrity; whistleblower process"),
        ("FCA / Qui Tam Relator Risk",
         "high" if sector in ("Home Health", "Hospice", "DME", "Laboratory") else "medium",
         "Whistleblower lawsuits for false claims. Treble damages + $25K/claim penalties.",
         "Hotline; audit; compliance committee; exit interview review"),
        ("340B Program Compliance (if applicable)",
         "high" if sector in ("Pharmacy", "Specialty Pharmacy", "Hospital") else "low",
         "Split-billing, duplicate discount, child-site eligibility. HRSA audits ongoing.",
         "TPA; virtual inventory; audit-ready policies"),
        ("State Corporate Practice of Medicine",
         "high" if sector in ("Dermatology", "Ophthalmology", "Physician Services", "ABA Therapy", "Behavioral Health") else "low",
         "MSO / friendly PC structure under attack in CA, NY, TX, NJ.",
         "Legal opinion per state; clinical governance separation"),
        ("Licensing & Accreditation",
         "high" if sector in ("Skilled Nursing", "Hospital", "Home Health", "Hospice", "Behavioral Health") else "medium",
         "State licensure, Joint Commission, CARF, CoPs. Survey deficiencies → IJ status.",
         "Mock surveys; track-A follow-up; survey-preparedness training"),
        ("Managed Care Contract Renewal Risk",
         "medium",
         "Commercial payer contract termination/repricing on 60-90 day notice.",
         "Contract matrix; renewal cadence; rate benchmarking"),
        ("CMS Rate Reimbursement Cuts",
         "high" if sector in ("Home Health", "Skilled Nursing", "Hospice", "Physician Services") else "medium",
         "Annual PFS/HH/SNF/ASC rule updates. Historically -1% to -4% each cycle.",
         "Budget-neutrality models; contract re-negotiation; volume offsets"),
    ]
    return [RiskFactor(factor=f, severity=sev, description=desc, mitigations=mit)
            for f, sev, desc, mit in catalog]


def _active_events_for(sector: str) -> List[RegulatoryEvent]:
    rows = []
    for ev in _ACTIVE_REGS:
        applies = sector in ev["impact_areas"] or any(sector.lower() in a.lower() for a in ev["impact_areas"])
        rows.append(RegulatoryEvent(
            name=ev["name"],
            agency=ev["agency"],
            effective_date=ev["effective_date"],
            status=ev["status"],
            direction=ev["direction"],
            revenue_impact_pct=ev["revenue_impact_pct"] if applies else 0.0,
            applies_to_deal=applies,
            notes="—",
        ))
    return rows


def _materiality_schedule(
    events: List[RegulatoryEvent],
    revenue_mm: float,
    ebitda_margin: float,
    exit_multiple: float,
) -> List[MaterialityRow]:
    rows = []
    for e in events:
        if not e.applies_to_deal:
            continue
        ebitda_impact = revenue_mm * e.revenue_impact_pct * (ebitda_margin + 0.02)
        ev_impact = ebitda_impact * exit_multiple
        material = abs(ev_impact) / (revenue_mm * exit_multiple * ebitda_margin) > 0.05 if (revenue_mm * exit_multiple * ebitda_margin) else False
        rows.append(MaterialityRow(
            impact_name=e.name,
            revenue_impact_pct=round(e.revenue_impact_pct, 4),
            ebitda_impact_mm=round(ebitda_impact, 2),
            ev_impact_mm=round(ev_impact, 2),
            materiality_tier="material" if material else "non-material",
        ))
    return rows


def _compliance_gaps(sector: str, ev_mm: float) -> List[ComplianceGap]:
    gaps = [
        ("HIPAA Security Risk Assessment", "Annual SRA required; last performed >18mo",
         "gap", 0.25, 90),
        ("OIG Compliance Program", "7-element effective program documented",
         "compliant", 0.0, 0),
        ("Stark Exception Documentation", "Written agreements for all physician relationships",
         "gap", 0.45, 120),
        ("State Licensure Current", "All facility/provider licenses valid",
         "compliant", 0.0, 0),
        ("Payer Contract Inventory", "Master contract schedule with renewal dates",
         "gap", 0.12, 60),
        ("Data Privacy / BAA Audit", "All vendors covered by current BAAs",
         "gap", 0.18, 45),
    ]
    if sector in ("Home Health", "Hospice", "Skilled Nursing"):
        gaps.append((
            "CoP Compliance / Survey Readiness",
            "Last CMS survey & follow-up on all deficiencies",
            "unknown", 0.65, 150,
        ))
    if sector in ("Pharmacy", "Specialty Pharmacy", "Hospital"):
        gaps.append((
            "340B Program Audit",
            "TPA reconciliation + virtual inventory audit",
            "gap", 0.55, 180,
        ))
    return [ComplianceGap(
        area=area, requirement=req, current_status=st,
        remediation_cost_mm=round(cost, 2), days_to_close=days,
    ) for area, req, st, cost, days in gaps]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_regulatory_risk(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
    ev_mm: float = 250.0,
) -> RegulatoryRiskResult:
    corpus = _load_corpus()
    profile = _sector_profile(sector)
    score = profile["risk_score"]
    label = _label_for_score(score)

    risk_factors = _risk_factors_for(sector)
    events = _active_events_for(sector)
    materiality = _materiality_schedule(events, revenue_mm, ebitda_margin, exit_multiple)
    gaps = _compliance_gaps(sector, ev_mm)

    # Total drag: sum of negative events that apply
    total_drag = sum(e.revenue_impact_pct for e in events if e.applies_to_deal and e.revenue_impact_pct < 0)
    total_ev_risk = sum(abs(m.ev_impact_mm) for m in materiality if m.materiality_tier == "material")
    total_remediation = sum(g.remediation_cost_mm for g in gaps if g.current_status in ("gap", "unknown"))

    return RegulatoryRiskResult(
        sector=sector,
        risk_score=score,
        risk_label=label,
        risk_factors=risk_factors,
        active_events=events,
        materiality_schedule=materiality,
        compliance_gaps=gaps,
        total_revenue_drag_pct=round(total_drag, 4),
        total_ev_risk_mm=round(total_ev_risk, 2),
        total_remediation_cost_mm=round(total_remediation, 2),
        corpus_deal_count=len(corpus),
    )
