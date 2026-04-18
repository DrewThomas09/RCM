"""No Surprises Act / IDR Tracker.

Tracks IDR (Independent Dispute Resolution) submissions, outcomes, and
financial impact of the No Surprises Act across hospital-based,
ambulatory, and emergency services portfolio.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class IDRCase:
    case_id: str
    deal: str
    specialty: str
    payer: str
    claim_amount: float
    qpa: float
    offer_provider: float
    offer_payer: float
    idr_selected: str
    decision_days: int
    status: str
    admin_fee: float


@dataclass
class PayerPosture:
    payer: str
    cases_submitted: int
    cases_won_by_provider: int
    provider_win_rate_pct: float
    median_award_delta_pct: float
    avg_qpa_vs_claim_ratio: float
    posture: str


@dataclass
class DealExposure:
    deal: str
    sector: str
    out_of_network_revenue_m: float
    annual_idr_cases: int
    avg_case_value_m: float
    revenue_at_risk_m: float
    qpa_vs_median_charge_pct: float
    strategy: str


@dataclass
class EmergencyPortfolio:
    entity: str
    ed_visits_annual: int
    oon_rate_pct: float
    avg_charge: float
    avg_qpa: float
    avg_collected: float
    bad_debt_pct: float


@dataclass
class RegulatoryDevelopment:
    event: str
    event_date: str
    impact_description: str
    portfolio_impact_m: float
    status: str


@dataclass
class NSAResult:
    total_cases: int
    total_revenue_disputed_m: float
    total_revenue_at_risk_m: float
    provider_win_rate_pct: float
    avg_admin_fee_m: float
    active_strategies: int
    cases: List[IDRCase]
    payer_postures: List[PayerPosture]
    deals: List[DealExposure]
    emergency: List[EmergencyPortfolio]
    regulatory: List[RegulatoryDevelopment]
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


def _build_cases() -> List[IDRCase]:
    return [
        IDRCase("IDR-202408-485", "Emergency Medicine Group", "Emergency Medicine", "UnitedHealthcare",
                4850.0, 1485.0, 3250.0, 1485.0, "provider", 185, "awarded (provider)", 0.85),
        IDRCase("IDR-202409-122", "Emergency Medicine Group", "Emergency Medicine", "Anthem BCBS",
                3250.0, 945.0, 2450.0, 1150.0, "provider", 215, "awarded (provider)", 0.85),
        IDRCase("IDR-202410-285", "Anesthesia Partners", "Anesthesia", "Cigna",
                2850.0, 685.0, 2150.0, 685.0, "provider", 165, "awarded (provider)", 0.85),
        IDRCase("IDR-202411-088", "Anesthesia Partners", "Anesthesia", "Aetna",
                3450.0, 895.0, 2650.0, 1250.0, "payer", 145, "awarded (payer)", 0.85),
        IDRCase("IDR-202411-328", "Radiology Partners", "Radiology", "UnitedHealthcare",
                1850.0, 425.0, 1385.0, 725.0, "provider", 195, "awarded (provider)", 0.85),
        IDRCase("IDR-202412-185", "Radiology Partners", "Radiology", "Cigna",
                2250.0, 485.0, 1685.0, 885.0, "provider", 210, "awarded (provider)", 0.85),
        IDRCase("IDR-202501-222", "Hospitalist Group", "Hospitalist", "Centene",
                1485.0, 385.0, 1150.0, 485.0, "provider", 175, "awarded (provider)", 0.85),
        IDRCase("IDR-202502-418", "Neonatology Group", "Neonatology", "Humana",
                8850.0, 2285.0, 6450.0, 2285.0, "provider", 225, "awarded (provider)", 0.85),
        IDRCase("IDR-202503-185", "Pathology Services", "Pathology", "UnitedHealthcare",
                685.0, 145.0, 485.0, 225.0, "provider", 165, "awarded (provider)", 0.85),
        IDRCase("IDR-202503-245", "Cardiology Anesthesia", "Anesthesia", "Kaiser",
                4250.0, 1485.0, 3200.0, 1485.0, "payer", 195, "awarded (payer)", 0.85),
        IDRCase("IDR-202504-088", "Ambulance Services", "Ground Ambulance", "Anthem BCBS",
                2450.0, 585.0, 1850.0, 950.0, "provider", 185, "awarded (provider)", 0.85),
        IDRCase("IDR-202504-325", "Air Ambulance", "Air Ambulance", "Cigna",
                48500.0, 12500.0, 38500.0, 15500.0, "provider", 265, "awarded (provider)", 0.85),
        IDRCase("IDR-202504-485", "EmCare", "Emergency Medicine", "Aetna",
                3850.0, 995.0, 2885.0, 1285.0, "provider", 145, "awarded (provider)", 0.85),
        IDRCase("IDR-202505-188", "Envision", "Emergency Medicine", "Blue Shield of CA",
                2950.0, 785.0, 2285.0, 950.0, "provider", 205, "awarded (provider)", 0.85),
        IDRCase("IDR-202505-328", "Pediatrix", "Neonatology", "UnitedHealthcare",
                6750.0, 1885.0, 5285.0, 2150.0, "provider", 195, "awarded (provider)", 0.85),
        IDRCase("IDR-202506-085", "USAP", "Anesthesia", "Cigna",
                3250.0, 825.0, 2450.0, 1050.0, "in progress", 0, "pending decision", 0.85),
        IDRCase("IDR-202506-245", "RadPartners", "Radiology", "Humana",
                1550.0, 385.0, 1185.0, 625.0, "in progress", 0, "pending decision", 0.85),
        IDRCase("IDR-202507-422", "Hospitalist Group", "Hospitalist", "Anthem BCBS",
                1285.0, 325.0, 985.0, 485.0, "in progress", 0, "pending decision", 0.85),
    ]


def _build_payers() -> List[PayerPosture]:
    return [
        PayerPosture("UnitedHealthcare", 1852, 1285, 0.694, 0.485, 0.285, "aggressive QPA strategy"),
        PayerPosture("Elevance (Anthem)", 985, 712, 0.722, 0.425, 0.298, "moderate — improving"),
        PayerPosture("Cigna", 845, 625, 0.740, 0.512, 0.245, "moderate — QPA-focused"),
        PayerPosture("Aetna (CVS)", 720, 525, 0.729, 0.395, 0.318, "moderate"),
        PayerPosture("Humana", 485, 358, 0.738, 0.465, 0.275, "moderate"),
        PayerPosture("Centene", 420, 312, 0.743, 0.385, 0.325, "moderate"),
        PayerPosture("Kaiser Permanente", 185, 95, 0.514, 0.185, 0.385, "restrictive — closed network"),
        PayerPosture("Blue Shield of CA", 285, 208, 0.730, 0.445, 0.312, "moderate"),
        PayerPosture("HCSC (Blues)", 385, 282, 0.732, 0.412, 0.305, "moderate"),
        PayerPosture("Independence Blue Cross", 165, 122, 0.739, 0.398, 0.322, "moderate"),
        PayerPosture("BCBS Michigan", 145, 108, 0.745, 0.385, 0.332, "moderate"),
        PayerPosture("BCBS Tennessee", 125, 92, 0.736, 0.405, 0.315, "moderate"),
    ]


def _build_deals() -> List[DealExposure]:
    return [
        DealExposure("Project Horizon — Emergency Medicine", "Hospital-based / ED",
                     285.0, 8850, 3250.0, 185.0, 0.255, "IDR + In-Network strategy"),
        DealExposure("Project Quartz — Anesthesia", "Hospital-based / Anesthesia",
                     185.0, 6850, 2850.0, 125.0, 0.242, "IDR + contract renegotiation"),
        DealExposure("Project Spruce — Radiology", "Radiology",
                     125.0, 4250, 1850.0, 78.0, 0.232, "IDR + teleradiology network"),
        DealExposure("Project Sierra — Hospitalist", "Hospitalist",
                     85.0, 3850, 1285.0, 52.0, 0.245, "contract negotiation primary"),
        DealExposure("Project Ridge — Pathology", "Pathology",
                     68.0, 2850, 685.0, 32.0, 0.215, "minimal OON — in-network strategy"),
        DealExposure("Project Meridian — NICU", "Hospital-based / NICU",
                     125.0, 1285, 6850.0, 85.0, 0.268, "IDR primary strategy"),
        DealExposure("Air Ambulance Services", "Specialty / Ground + Air",
                     245.0, 685, 28500.0, 145.0, 0.285, "IDR + negotiated contracts"),
        DealExposure("Urgent Care Platform", "Urgent Care",
                     85.0, 2250, 385.0, 18.0, 0.195, "in-network expansion primary"),
    ]


def _build_emergency() -> List[EmergencyPortfolio]:
    return [
        EmergencyPortfolio("Horizon ED Group 1", 285000, 0.225, 2850.0, 825.0, 1485.0, 0.115),
        EmergencyPortfolio("Horizon ED Group 2", 185000, 0.245, 3050.0, 885.0, 1585.0, 0.118),
        EmergencyPortfolio("Horizon ED Group 3 (Kaiser exposure)", 125000, 0.385, 2950.0, 685.0, 985.0, 0.185),
        EmergencyPortfolio("Horizon ED Group 4", 145000, 0.212, 2750.0, 812.0, 1425.0, 0.105),
        EmergencyPortfolio("Horizon NICU Portfolio", 12500, 0.325, 6850.0, 1985.0, 3850.0, 0.145),
    ]


def _build_regulatory() -> List[RegulatoryDevelopment]:
    return [
        RegulatoryDevelopment("Texas Medical Assn v. HHS II Court Ruling", "2024-02-06",
                              "Vacated QPA methodology — CMS re-issued with broader geographic data",
                              58.5, "implemented 2024"),
        RegulatoryDevelopment("TMA III Court Ruling", "2024-07-05",
                              "Vacated 600% admin fee increase; restored $50-238 range",
                              8.5, "implemented"),
        RegulatoryDevelopment("TMA IV Court Ruling", "2024-09-25",
                              "Ruled CMS must consider all IDR factors equally (not QPA-presumptive)",
                              45.0, "implementation ongoing"),
        RegulatoryDevelopment("IDR Portal Reopening", "2023-12-15",
                              "CMS resumed IDR operations; 400K+ backlog prioritized",
                              0.0, "complete"),
        RegulatoryDevelopment("CMS IDR Administrative Fee Update", "2025-01-15",
                              "$250 per-party fixed fee + $1,000 batched minimum",
                              -2.5, "implemented"),
        RegulatoryDevelopment("Batched IDR Rulemaking", "2025-04-22",
                              "Expanded batching eligibility — same-payer/specialty/QPA service",
                              8.5, "implemented"),
        RegulatoryDevelopment("2026 Advance Notice — NSA Refinements", "2026-Q1",
                              "Proposed QPA specialty adjustments + ground ambulance rules",
                              12.5, "comment period"),
        RegulatoryDevelopment("State NSA Variations (WA, NY, CA, TX)", "ongoing",
                              "State NSA laws sometimes more favorable; federal preemption tested",
                              18.5, "state-by-state monitoring"),
    ]


def compute_nsa_tracker() -> NSAResult:
    corpus = _load_corpus()
    cases = _build_cases()
    payers = _build_payers()
    deals = _build_deals()
    emergency = _build_emergency()
    regulatory = _build_regulatory()

    total_disputed = sum(c.claim_amount for c in cases) / 1_000_000.0
    total_at_risk = sum(d.revenue_at_risk_m for d in deals)
    win_rate = sum(p.provider_win_rate_pct * p.cases_submitted for p in payers) / sum(p.cases_submitted for p in payers)
    admin_total = sum(c.admin_fee for c in cases)

    return NSAResult(
        total_cases=len(cases),
        total_revenue_disputed_m=round(total_disputed, 3),
        total_revenue_at_risk_m=round(total_at_risk, 1),
        provider_win_rate_pct=round(win_rate, 4),
        avg_admin_fee_m=round(admin_total / len(cases), 3) if cases else 0,
        active_strategies=len(deals),
        cases=cases,
        payer_postures=payers,
        deals=deals,
        emergency=emergency,
        regulatory=regulatory,
        corpus_deal_count=len(corpus),
    )
