"""Telehealth Economics Analyzer.

Models virtual-care economics for PE-backed telehealth platforms:
visit economics, provider productivity, payer parity, tech stack cost,
regulatory cliff exposure (PHE expiration, Ryan Haight, state compact).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class VisitTypeEcon:
    visit_type: str
    avg_reimbursement: float
    direct_cost: float
    gross_margin: float
    gross_margin_pct: float
    avg_duration_min: int
    annual_volume: int
    annual_revenue_mm: float


@dataclass
class ProviderProductivity:
    specialty: str
    providers_fte: float
    visits_per_provider_day: int
    utilization_pct: float
    avg_rev_per_provider_k: float
    attrition_rate_pct: float


@dataclass
class PayerParity:
    state: str
    parity_status: str
    medicaid_coverage: str
    medicare_extension: str
    commercial_parity: str
    sunset_risk: str


@dataclass
class TechStackCost:
    component: str
    annual_cost_mm: float
    pct_of_revenue: float
    vendor: str
    renewal_status: str


@dataclass
class RegulatoryCliff:
    policy: str
    current_status: str
    expiration_date: str
    revenue_at_risk_mm: float
    mitigation: str


@dataclass
class ComparableDTC:
    company: str
    visit_type: str
    price_per_visit: float
    subscription_monthly: float
    status: str


@dataclass
class TelehealthResult:
    total_visits_annual: int
    annual_revenue_mm: float
    blended_gross_margin_pct: float
    total_provider_fte: float
    states_operating: int
    visits: List[VisitTypeEcon]
    productivity: List[ProviderProductivity]
    parity: List[PayerParity]
    tech_stack: List[TechStackCost]
    cliffs: List[RegulatoryCliff]
    competitors: List[ComparableDTC]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 100):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_visits() -> List[VisitTypeEcon]:
    items = [
        ("Urgent Care (Acute Low)", 68.0, 22.0, 15, 180000),
        ("Primary Care Async", 48.0, 16.5, 12, 240000),
        ("Primary Care Sync", 118.0, 42.0, 18, 95000),
        ("Behavioral Health (45-min)", 165.0, 58.0, 45, 125000),
        ("Psychiatry Med Management", 95.0, 34.0, 25, 85000),
        ("Dermatology Async Photo", 58.0, 14.5, 8, 48000),
        ("Chronic Care Management", 42.0, 12.0, 20, 68000),
        ("Specialty Consult (Endo, Cardio)", 185.0, 72.0, 30, 35000),
    ]
    rows = []
    for v, rev, cost, dur, vol in items:
        gm = rev - cost
        rev_mm = rev * vol / 1000000
        rows.append(VisitTypeEcon(
            visit_type=v, avg_reimbursement=rev, direct_cost=cost,
            gross_margin=gm, gross_margin_pct=gm / rev,
            avg_duration_min=dur, annual_volume=vol,
            annual_revenue_mm=round(rev_mm, 2),
        ))
    return rows


def _build_productivity() -> List[ProviderProductivity]:
    return [
        ProviderProductivity("Primary Care", 128, 22, 0.78, 685.0, 0.18),
        ProviderProductivity("Urgent Care (PA/NP)", 185, 28, 0.82, 465.0, 0.22),
        ProviderProductivity("Psychiatry", 62, 12, 0.88, 1085.0, 0.14),
        ProviderProductivity("Behavioral Health Therapy", 142, 8, 0.85, 525.0, 0.24),
        ProviderProductivity("Dermatology Teledermatology", 38, 45, 0.72, 825.0, 0.12),
        ProviderProductivity("Specialty Consult", 24, 10, 0.68, 1285.0, 0.15),
    ]


def _build_parity() -> List[PayerParity]:
    return [
        PayerParity("California", "full parity", "permanent", "temp extension", "full", "low"),
        PayerParity("New York", "full parity", "permanent", "temp extension", "full", "low"),
        PayerParity("Texas", "service parity", "permanent", "temp extension", "limited", "medium"),
        PayerParity("Florida", "service parity", "permanent", "temp extension", "limited", "medium"),
        PayerParity("Illinois", "full parity", "permanent", "temp extension", "full", "low"),
        PayerParity("Pennsylvania", "full parity", "permanent", "temp extension", "full", "low"),
        PayerParity("Ohio", "service parity", "permanent", "temp extension", "limited", "medium"),
        PayerParity("North Carolina", "service parity", "permanent", "temp extension", "limited", "medium"),
        PayerParity("Georgia", "no parity", "permanent", "temp extension", "limited", "high"),
        PayerParity("Virginia", "full parity", "permanent", "temp extension", "full", "low"),
    ]


def _build_tech() -> List[TechStackCost]:
    return [
        TechStackCost("Video Platform (Zoom Enterprise / Twilio Live)", 2.4, 0.014, "Twilio Live", "auto-renew 2027"),
        TechStackCost("EHR/Practice Management", 4.2, 0.025, "athenahealth", "3-yr through 2028"),
        TechStackCost("Patient Portal + Scheduling", 1.8, 0.011, "Epic MyChart OEM", "annual"),
        TechStackCost("eRx + DEA EPCS", 0.9, 0.005, "Dr First", "annual"),
        TechStackCost("Billing / RCM Technology", 2.8, 0.017, "Waystar", "3-yr through 2027"),
        TechStackCost("AI Scribe / Ambient", 1.2, 0.007, "DAX Copilot", "annual pilot"),
        TechStackCost("Security / Compliance / HIPAA", 1.6, 0.010, "Drata + Vanta", "annual"),
        TechStackCost("Telephony / Call Center", 2.1, 0.013, "Five9", "3-yr through 2028"),
    ]


def _build_cliffs() -> List[RegulatoryCliff]:
    return [
        RegulatoryCliff("Medicare Telehealth Expansion (PHE-era flexibilities)",
                        "extended through 2025", "2025-12-31", 28.5,
                        "Advocate for permanent codification via TCEA / bipartisan legislation"),
        RegulatoryCliff("DEA Special Registration (Ryan Haight)",
                        "extended through 2025", "2025-12-31", 12.0,
                        "Implement in-person touchpoint model; DEA special registration application"),
        RegulatoryCliff("Home as Originating Site",
                        "PHE-era extension", "2025-12-31", 18.5,
                        "Rural site-of-service enablement; telehealth-first strategy"),
        RegulatoryCliff("Interstate Licensure Compacts (IMLC)",
                        "state-by-state", "varies", 8.2,
                        "Enroll providers in IMLC; licensure automation tooling"),
        RegulatoryCliff("Audio-Only Coverage",
                        "PHE extension", "2025-12-31", 4.5,
                        "Shift to video-first where feasible; grandfathered by some MA plans"),
        RegulatoryCliff("Behavioral Health Telehealth Parity (CMS 2023 rule)",
                        "permanent", "n/a", 0.0,
                        "No action needed"),
    ]


def _build_competitors() -> List[ComparableDTC]:
    return [
        ComparableDTC("Teladoc Health", "Primary Care + BH", 0.0, 0.0, "public, enterprise B2B2C"),
        ComparableDTC("Hims & Hers", "DTC Men's/Women's Health", 85.0, 45.0, "public, subscription-led"),
        ComparableDTC("Ro (Roman)", "DTC Telehealth + Pharmacy", 95.0, 15.0, "private, hybrid"),
        ComparableDTC("Lifestance Health", "Behavioral Health (in-net)", 0.0, 0.0, "public, payer-network"),
        ComparableDTC("Included Health (VC)", "Enterprise Concierge", 0.0, 0.0, "private, B2B"),
        ComparableDTC("Galileo Health", "Primary Care + Behavioral", 0.0, 0.0, "VC, employer-paid"),
        ComparableDTC("98point6", "Primary Care (exited DTC)", 0.0, 0.0, "pivot to enterprise"),
        ComparableDTC("MDLIVE (Evernorth acq)", "Primary Care / Urgent", 0.0, 0.0, "payer-owned"),
    ]


def compute_telehealth_econ() -> TelehealthResult:
    corpus = _load_corpus()

    visits = _build_visits()
    productivity = _build_productivity()
    parity = _build_parity()
    tech = _build_tech()
    cliffs = _build_cliffs()
    competitors = _build_competitors()

    total_visits = sum(v.annual_volume for v in visits)
    total_rev = sum(v.annual_revenue_mm for v in visits)
    total_cost = sum(v.direct_cost * v.annual_volume / 1000000 for v in visits)
    gm = (total_rev - total_cost) / total_rev if total_rev else 0
    total_fte = sum(p.providers_fte for p in productivity)

    return TelehealthResult(
        total_visits_annual=total_visits,
        annual_revenue_mm=round(total_rev, 2),
        blended_gross_margin_pct=round(gm, 4),
        total_provider_fte=round(total_fte, 1),
        states_operating=48,
        visits=visits,
        productivity=productivity,
        parity=parity,
        tech_stack=tech,
        cliffs=cliffs,
        competitors=competitors,
        corpus_deal_count=len(corpus),
    )
