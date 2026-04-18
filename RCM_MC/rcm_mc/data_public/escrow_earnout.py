"""Escrow & Earnout Tracker.

Tracks contingent consideration (escrows, earnouts, indemnification holdbacks,
PPA true-ups, milestone payments) across portfolio deals. Surfaces accrual
liabilities, probability-weighted payouts, claim history, and release schedule.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class EscrowPosition:
    deal: str
    sector: str
    vintage: int
    escrow_type: str
    escrow_size_m: float
    held_pct: float
    release_date: str
    months_to_release: int
    claims_filed: int
    claims_paid_m: float
    expected_release_m: float
    status: str


@dataclass
class EarnoutPosition:
    deal: str
    sector: str
    metric: str
    target: str
    achievement_pct: float
    max_payout_m: float
    accrued_m: float
    expected_m: float
    measurement_end: str
    months_remaining: int
    probability: float


@dataclass
class MilestonePayment:
    deal: str
    milestone: str
    trigger: str
    payment_m: float
    target_date: str
    current_status: str
    probability: float


@dataclass
class SectorRollup:
    sector: str
    deals: int
    escrow_held_m: float
    earnout_max_m: float
    earnout_accrued_m: float
    avg_claim_ratio: float
    expected_release_m: float


@dataclass
class ClaimHistory:
    deal: str
    claim_date: str
    claim_type: str
    claim_amount_m: float
    recovery_m: float
    status: str
    notes: str


@dataclass
class CoverageAnalysis:
    coverage_type: str
    portfolio_deals: int
    median_pct_of_purchase: float
    median_hold_months: int
    claim_rate: float
    avg_recovery_ratio: float


@dataclass
class EscrowResult:
    total_deals: int
    total_escrow_held_m: float
    total_earnout_max_m: float
    total_earnout_accrued_m: float
    total_milestones_m: float
    active_claims: int
    expected_12mo_release_m: float
    escrows: List[EscrowPosition]
    earnouts: List[EarnoutPosition]
    milestones: List[MilestonePayment]
    sectors: List[SectorRollup]
    claims: List[ClaimHistory]
    coverage: List[CoverageAnalysis]
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


def _build_escrows() -> List[EscrowPosition]:
    return [
        EscrowPosition("Project Magnolia — MSK Platform", "MSK / Ortho", 2024, "Indemnity", 28.5, 1.00, "2026-11-15", 7, 0, 0.0, 27.8, "active"),
        EscrowPosition("Project Cypress — GI Network", "Gastroenterology", 2024, "Indemnity", 22.0, 1.00, "2026-09-30", 5, 1, 1.2, 20.5, "active"),
        EscrowPosition("Project Redwood — Behavioral Health", "Behavioral Health", 2023, "Indemnity", 35.0, 0.85, "2026-06-15", 2, 3, 5.3, 24.5, "active"),
        EscrowPosition("Project Laurel — Dermatology", "Dermatology", 2023, "Tax", 18.0, 1.00, "2027-03-15", 11, 0, 0.0, 18.0, "active"),
        EscrowPosition("Project Iris — Dental DSO", "Dental DSO", 2022, "Indemnity", 42.0, 0.25, "2026-04-30", 0, 2, 31.5, 10.5, "final release"),
        EscrowPosition("Project Willow — Fertility", "Fertility / IVF", 2024, "Indemnity", 25.5, 1.00, "2027-01-31", 9, 0, 0.0, 25.2, "active"),
        EscrowPosition("Project Cedar — Cardiology", "Cardiology", 2023, "Indemnity", 32.0, 0.75, "2026-08-15", 4, 4, 8.0, 22.5, "active"),
        EscrowPosition("Project Birch — Home Health", "Home Health", 2022, "R&W Retention", 15.0, 0.00, "2025-06-30", -10, 1, 14.5, 0.0, "released"),
        EscrowPosition("Project Spruce — Radiology", "Radiology", 2024, "Indemnity", 30.0, 1.00, "2026-12-31", 8, 0, 0.0, 29.8, "active"),
        EscrowPosition("Project Maple — Urology", "Urology", 2023, "Tax", 12.0, 1.00, "2026-10-31", 6, 0, 0.0, 12.0, "active"),
        EscrowPosition("Project Oak — RCM SaaS", "RCM", 2023, "Indemnity", 20.0, 0.50, "2026-05-15", 1, 2, 9.5, 10.0, "active"),
        EscrowPosition("Project Aspen — Eye Care", "Eye Care", 2024, "Indemnity", 18.5, 1.00, "2027-02-28", 10, 0, 0.0, 18.3, "active"),
        EscrowPosition("Project Pine — Physical Therapy", "MSK / Ortho", 2022, "Indemnity", 16.0, 0.15, "2026-04-28", 0, 3, 13.2, 2.5, "final release"),
        EscrowPosition("Project Fir — Lab / Pathology", "Lab Services", 2023, "Purchase Price", 45.0, 1.00, "2026-07-15", 3, 1, 2.5, 42.0, "active"),
        EscrowPosition("Project Ash — Infusion", "Infusion", 2024, "Indemnity", 38.0, 1.00, "2027-04-15", 12, 0, 0.0, 37.5, "active"),
    ]


def _build_earnouts() -> List[EarnoutPosition]:
    return [
        EarnoutPosition("Project Magnolia — MSK Platform", "MSK / Ortho", "LTM EBITDA 2026", "$72M", 0.88, 25.0, 19.0, 21.0, "2026-12-31", 8, 0.82),
        EarnoutPosition("Project Cypress — GI Network", "Gastroenterology", "LTM revenue 2026", "$480M", 0.92, 15.0, 11.5, 13.5, "2026-12-31", 8, 0.88),
        EarnoutPosition("Project Redwood — Behavioral Health", "Behavioral Health", "LTM EBITDA 2026", "$58M", 0.75, 30.0, 15.5, 18.5, "2026-12-31", 8, 0.70),
        EarnoutPosition("Project Laurel — Dermatology", "Dermatology", "De novo count 2026", "12 clinics", 0.83, 8.0, 5.8, 6.5, "2026-12-31", 8, 0.80),
        EarnoutPosition("Project Willow — Fertility", "Fertility / IVF", "Cycle volume 2027", "18K cycles", 0.65, 35.0, 12.5, 18.0, "2027-06-30", 14, 0.62),
        EarnoutPosition("Project Cedar — Cardiology", "Cardiology", "LTM EBITDA 2026", "$48M", 0.94, 20.0, 16.0, 18.5, "2026-12-31", 8, 0.90),
        EarnoutPosition("Project Spruce — Radiology", "Radiology", "Volume growth (% YoY)", "15%", 0.72, 12.0, 7.0, 8.5, "2026-12-31", 8, 0.68),
        EarnoutPosition("Project Maple — Urology", "Urology", "Same-store growth 2026", "7%", 0.86, 10.0, 7.5, 8.5, "2026-12-31", 8, 0.82),
        EarnoutPosition("Project Aspen — Eye Care", "Eye Care", "LTM EBITDA 2027", "$65M", 0.55, 28.0, 12.0, 15.5, "2027-03-31", 11, 0.58),
        EarnoutPosition("Project Fir — Lab / Pathology", "Lab Services", "LTM revenue 2026", "$420M", 0.91, 18.0, 13.5, 16.0, "2026-12-31", 8, 0.86),
        EarnoutPosition("Project Ash — Infusion", "Infusion", "Site count 2027", "95 sites", 0.48, 40.0, 14.0, 22.0, "2027-06-30", 14, 0.50),
        EarnoutPosition("Project Oak — RCM SaaS", "RCM", "ARR growth 2026", "$85M ARR", 0.78, 22.0, 13.5, 16.0, "2026-12-31", 8, 0.75),
    ]


def _build_milestones() -> List[MilestonePayment]:
    return [
        MilestonePayment("Project Laurel — Dermatology", "Add-on 3 complete", "Close 3 bolt-ons", 5.0, "2026-09-30", "on track", 0.85),
        MilestonePayment("Project Willow — Fertility", "New market entry", "2 new MSAs launched", 7.5, "2026-12-31", "on track", 0.75),
        MilestonePayment("Project Cedar — Cardiology", "EHR migration", "Epic live at 100% locations", 4.0, "2026-10-31", "at risk", 0.55),
        MilestonePayment("Project Spruce — Radiology", "AI detection deployment", "Aidoc live at 50% hospitals", 6.0, "2026-11-30", "on track", 0.78),
        MilestonePayment("Project Aspen — Eye Care", "Add-on 2 complete", "2 regional acquisitions", 10.0, "2027-03-31", "on track", 0.80),
        MilestonePayment("Project Fir — Lab / Pathology", "Direct contracting win", "2 regional Blues contracts", 8.0, "2026-12-31", "at risk", 0.50),
        MilestonePayment("Project Ash — Infusion", "FDA approval milestone", "2 new infusion drugs approved", 12.0, "2027-06-30", "pending", 0.65),
        MilestonePayment("Project Cypress — GI Network", "De novo expansion", "4 ASC openings", 6.5, "2026-09-30", "on track", 0.88),
    ]


def _build_sectors(escrows: List[EscrowPosition], earnouts: List[EarnoutPosition]) -> List[SectorRollup]:
    sectors: dict = {}
    for e in escrows:
        s = sectors.setdefault(e.sector, {"deals": set(), "held": 0.0, "max_earnout": 0.0, "accrued_earnout": 0.0, "claims": 0.0, "sz": 0.0, "exp_rel": 0.0})
        s["deals"].add(e.deal)
        s["held"] += e.escrow_size_m * e.held_pct
        s["claims"] += e.claims_paid_m
        s["sz"] += e.escrow_size_m
        s["exp_rel"] += e.expected_release_m
    for eo in earnouts:
        s = sectors.setdefault(eo.sector, {"deals": set(), "held": 0.0, "max_earnout": 0.0, "accrued_earnout": 0.0, "claims": 0.0, "sz": 0.0, "exp_rel": 0.0})
        s["deals"].add(eo.deal)
        s["max_earnout"] += eo.max_payout_m
        s["accrued_earnout"] += eo.accrued_m
    rows = []
    for sector, d in sectors.items():
        cr = d["claims"] / d["sz"] if d["sz"] > 0 else 0.0
        rows.append(SectorRollup(
            sector=sector, deals=len(d["deals"]),
            escrow_held_m=round(d["held"], 1),
            earnout_max_m=round(d["max_earnout"], 1),
            earnout_accrued_m=round(d["accrued_earnout"], 1),
            avg_claim_ratio=round(cr, 4),
            expected_release_m=round(d["exp_rel"], 1),
        ))
    return sorted(rows, key=lambda x: x.escrow_held_m + x.earnout_max_m, reverse=True)


def _build_claims() -> List[ClaimHistory]:
    return [
        ClaimHistory("Project Redwood — Behavioral Health", "2025-08-12", "Tax exposure", 2.3, 2.1, "resolved", "state Medicaid audit adjustment"),
        ClaimHistory("Project Redwood — Behavioral Health", "2025-11-05", "Wage & hour", 1.8, 1.5, "resolved", "DOL settlement"),
        ClaimHistory("Project Redwood — Behavioral Health", "2026-02-18", "R&W insurance claim", 1.2, 0.0, "open", "alleged clinical compliance breach"),
        ClaimHistory("Project Cypress — GI Network", "2026-01-22", "Environmental", 1.2, 1.0, "resolved", "Phase I finding — asbestos abatement"),
        ClaimHistory("Project Iris — Dental DSO", "2024-11-15", "IP infringement", 18.5, 15.0, "resolved", "patent claim settlement"),
        ClaimHistory("Project Iris — Dental DSO", "2025-03-08", "Employee classification", 13.0, 10.0, "resolved", "1099 vs W-2 settlement"),
        ClaimHistory("Project Cedar — Cardiology", "2025-06-15", "RAC audit", 3.2, 2.5, "resolved", "Medicare overpayment recovery"),
        ClaimHistory("Project Cedar — Cardiology", "2025-09-28", "Stark Law", 2.8, 2.2, "resolved", "physician compensation restructure"),
        ClaimHistory("Project Cedar — Cardiology", "2026-01-10", "Breach of rep", 2.0, 0.0, "open", "undisclosed litigation"),
        ClaimHistory("Project Cedar — Cardiology", "2026-03-05", "Working capital true-up", 1.0, 0.8, "settling", "net working capital adjustment"),
        ClaimHistory("Project Birch — Home Health", "2024-08-20", "Medicare audit", 8.5, 7.0, "resolved", "home health F2F documentation"),
        ClaimHistory("Project Birch — Home Health", "2025-02-15", "Fraud / FCA", 6.5, 5.0, "resolved", "referral pattern inquiry"),
        ClaimHistory("Project Oak — RCM SaaS", "2025-12-03", "Data breach", 5.5, 4.5, "resolved", "HIPAA incident remediation"),
        ClaimHistory("Project Oak — RCM SaaS", "2026-02-28", "Contract breach", 5.0, 0.0, "settling", "SLA liquidated damages"),
        ClaimHistory("Project Pine — Physical Therapy", "2024-12-10", "Environmental", 4.5, 3.5, "resolved", "Phase II remediation"),
        ClaimHistory("Project Pine — Physical Therapy", "2025-05-18", "Warranty breach", 5.2, 4.2, "resolved", "EHR compatibility issue"),
        ClaimHistory("Project Pine — Physical Therapy", "2025-08-22", "Tax gross-up", 3.5, 3.5, "resolved", "state income tax exposure"),
        ClaimHistory("Project Fir — Lab / Pathology", "2026-01-18", "Working capital true-up", 2.5, 2.5, "resolved", "inventory true-up"),
    ]


def _build_coverage() -> List[CoverageAnalysis]:
    return [
        CoverageAnalysis("General Indemnity", 15, 0.085, 18, 0.240, 0.80),
        CoverageAnalysis("Tax Indemnity", 12, 0.040, 30, 0.080, 0.90),
        CoverageAnalysis("R&W Insurance Retention", 10, 0.025, 12, 0.120, 0.85),
        CoverageAnalysis("Working Capital True-Up", 15, 0.012, 6, 0.950, 0.90),
        CoverageAnalysis("Environmental Indemnity", 8, 0.020, 36, 0.130, 0.82),
        CoverageAnalysis("Purchase Price Holdback", 5, 0.150, 9, 0.180, 0.92),
    ]


def compute_escrow_earnout() -> EscrowResult:
    corpus = _load_corpus()
    escrows = _build_escrows()
    earnouts = _build_earnouts()
    milestones = _build_milestones()
    sectors = _build_sectors(escrows, earnouts)
    claims = _build_claims()
    coverage = _build_coverage()

    deal_set = {e.deal for e in escrows} | {eo.deal for eo in earnouts} | {m.deal for m in milestones}
    total_escrow_held = sum(e.escrow_size_m * e.held_pct for e in escrows)
    total_earnout_max = sum(eo.max_payout_m for eo in earnouts)
    total_earnout_accrued = sum(eo.accrued_m for eo in earnouts)
    total_milestones = sum(m.payment_m * m.probability for m in milestones)
    active_claims = sum(1 for c in claims if c.status in ("open", "settling"))
    expected_12mo = sum(e.expected_release_m for e in escrows if e.months_to_release <= 12 and e.months_to_release >= 0)

    return EscrowResult(
        total_deals=len(deal_set),
        total_escrow_held_m=round(total_escrow_held, 1),
        total_earnout_max_m=round(total_earnout_max, 1),
        total_earnout_accrued_m=round(total_earnout_accrued, 1),
        total_milestones_m=round(total_milestones, 1),
        active_claims=active_claims,
        expected_12mo_release_m=round(expected_12mo, 1),
        escrows=escrows,
        earnouts=earnouts,
        milestones=milestones,
        sectors=sectors,
        claims=claims,
        coverage=coverage,
        corpus_deal_count=len(corpus),
    )
