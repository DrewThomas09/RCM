"""Insurance / Malpractice / D&O Tracker.

Models insurance economics for healthcare PE deals:
- Malpractice (professional liability) by specialty
- Tail coverage obligations at acquisition
- D&O insurance for board / officers
- General liability, cyber, workers comp
- Self-insured retention (SIR) and captive analysis
- Claim frequency and severity benchmarks
- Market hardening / soft cycle tracking
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Malpractice premium by specialty (per-provider annual)
# ---------------------------------------------------------------------------

_MALPRACTICE_BY_SPECIALTY = {
    "Primary Care":      {"base_premium_k": 12, "claim_freq_per_100": 1.8, "severity_k": 220},
    "Family Medicine":   {"base_premium_k": 11, "claim_freq_per_100": 1.7, "severity_k": 210},
    "Internal Medicine": {"base_premium_k": 14, "claim_freq_per_100": 2.2, "severity_k": 260},
    "Pediatrics":        {"base_premium_k": 9, "claim_freq_per_100": 1.5, "severity_k": 320},   # higher severity
    "Dermatology":       {"base_premium_k": 14, "claim_freq_per_100": 2.5, "severity_k": 180},
    "Ophthalmology":     {"base_premium_k": 22, "claim_freq_per_100": 3.2, "severity_k": 240},
    "Orthopedics":       {"base_premium_k": 58, "claim_freq_per_100": 5.8, "severity_k": 420},
    "Cardiology":        {"base_premium_k": 28, "claim_freq_per_100": 3.8, "severity_k": 480},
    "Gastroenterology":  {"base_premium_k": 45, "claim_freq_per_100": 5.2, "severity_k": 380},
    "General Surgery":   {"base_premium_k": 68, "claim_freq_per_100": 6.5, "severity_k": 520},
    "Neurosurgery":      {"base_premium_k": 165, "claim_freq_per_100": 8.5, "severity_k": 1200},
    "OB/GYN":            {"base_premium_k": 85, "claim_freq_per_100": 7.2, "severity_k": 680},
    "Anesthesiology":    {"base_premium_k": 42, "claim_freq_per_100": 4.5, "severity_k": 420},
    "Emergency Medicine":{"base_premium_k": 52, "claim_freq_per_100": 6.2, "severity_k": 380},
    "Radiology":         {"base_premium_k": 32, "claim_freq_per_100": 3.8, "severity_k": 340},
    "Psychiatry":        {"base_premium_k": 18, "claim_freq_per_100": 2.8, "severity_k": 200},
    "Urology":           {"base_premium_k": 35, "claim_freq_per_100": 4.2, "severity_k": 360},
    "ENT":               {"base_premium_k": 28, "claim_freq_per_100": 3.5, "severity_k": 290},
    "Oncology":          {"base_premium_k": 38, "claim_freq_per_100": 3.8, "severity_k": 480},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InsuranceCoverage:
    coverage_type: str
    annual_premium_mm: float
    pct_of_revenue: float
    limits_mm: float            # per-occurrence / per-claim
    retention_mm: float         # self-insured retention
    carrier: str
    renewal_date: str
    market_trend: str           # "hardening", "stable", "softening"


@dataclass
class SpecialtyPremium:
    specialty: str
    headcount: int
    premium_per_provider_k: float
    total_annual_k: float
    claim_frequency: float
    avg_severity_k: float
    loss_ratio: float


@dataclass
class ClaimReserve:
    claim_id: str
    specialty: str
    accident_year: int
    reserve_mm: float
    case_mm: float
    status: str                 # "open", "closed", "settled", "litigation"
    projected_resolution: str


@dataclass
class TailCoverage:
    structure: str
    upfront_cost_mm: float
    coverage_period_yrs: int
    ongoing_risk_mm: float
    recommended: bool


@dataclass
class CaptiveAnalysis:
    structure: str
    annual_retained_loss_mm: float
    tax_benefit_mm: float
    admin_cost_mm: float
    net_benefit_mm: float
    viable: bool


@dataclass
class InsuranceResult:
    total_annual_insurance_mm: float
    insurance_pct_of_revenue: float
    total_coverage_limits_mm: float
    risk_adjusted_reserve_mm: float
    coverages: List[InsuranceCoverage]
    specialty_premiums: List[SpecialtyPremium]
    open_claims: List[ClaimReserve]
    tail_coverage: List[TailCoverage]
    captive: List[CaptiveAnalysis]
    total_deal_insurance_cost_mm: float
    market_hardening_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 79):
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


def _build_specialty_premiums(sector: str, total_providers: int) -> List[SpecialtyPremium]:
    # Sector to specialty mix
    if sector in ("Primary Care", "Physician Services"):
        mix = [
            ("Primary Care", 0.35), ("Family Medicine", 0.20), ("Internal Medicine", 0.15),
            ("Pediatrics", 0.10), ("OB/GYN", 0.06), ("Cardiology", 0.05),
            ("Dermatology", 0.04), ("Orthopedics", 0.03), ("Emergency Medicine", 0.02),
        ]
    elif sector in ("ASC", "Surgery Center"):
        mix = [
            ("Orthopedics", 0.30), ("General Surgery", 0.20), ("Gastroenterology", 0.15),
            ("Ophthalmology", 0.10), ("Anesthesiology", 0.15), ("Urology", 0.06), ("ENT", 0.04),
        ]
    elif sector == "Oncology":
        mix = [("Oncology", 0.85), ("Radiology", 0.10), ("Internal Medicine", 0.05)]
    else:
        mix = [("Primary Care", 0.50), ("Orthopedics", 0.20), ("Cardiology", 0.15),
               ("Internal Medicine", 0.10), ("Radiology", 0.05)]

    rows = []
    for specialty, pct in mix:
        bench = _MALPRACTICE_BY_SPECIALTY.get(specialty, {"base_premium_k": 20, "claim_freq_per_100": 3, "severity_k": 300})
        hc = int(total_providers * pct)
        if hc == 0:
            continue
        total_k = bench["base_premium_k"] * hc
        # Loss ratio: (claim freq × severity) / premium
        incurred = hc * bench["claim_freq_per_100"] / 100 * bench["severity_k"]
        loss_ratio = incurred / total_k if total_k else 0
        rows.append(SpecialtyPremium(
            specialty=specialty,
            headcount=hc,
            premium_per_provider_k=round(bench["base_premium_k"], 1),
            total_annual_k=round(total_k, 0),
            claim_frequency=round(bench["claim_freq_per_100"], 2),
            avg_severity_k=round(bench["severity_k"], 0),
            loss_ratio=round(loss_ratio, 3),
        ))
    return rows


def _build_coverages(revenue_mm: float, malpractice_total_mm: float) -> List[InsuranceCoverage]:
    return [
        InsuranceCoverage(
            coverage_type="Professional Liability (Malpractice)",
            annual_premium_mm=round(malpractice_total_mm, 2),
            pct_of_revenue=round(malpractice_total_mm / revenue_mm if revenue_mm else 0, 4),
            limits_mm=25,
            retention_mm=0.5,
            carrier="ProAssurance / Coverys / MedPro",
            renewal_date="2026-01-01",
            market_trend="hardening",
        ),
        InsuranceCoverage(
            coverage_type="D&O Insurance",
            annual_premium_mm=round(revenue_mm * 0.0015, 2),
            pct_of_revenue=0.0015,
            limits_mm=50,
            retention_mm=1.0,
            carrier="Chubb / AIG / Hiscox",
            renewal_date="2026-04-30",
            market_trend="stable",
        ),
        InsuranceCoverage(
            coverage_type="General Liability",
            annual_premium_mm=round(revenue_mm * 0.0018, 2),
            pct_of_revenue=0.0018,
            limits_mm=10,
            retention_mm=0.05,
            carrier="Travelers / Zurich",
            renewal_date="2026-07-15",
            market_trend="stable",
        ),
        InsuranceCoverage(
            coverage_type="Cyber Liability",
            annual_premium_mm=round(revenue_mm * 0.0022, 2),
            pct_of_revenue=0.0022,
            limits_mm=25,
            retention_mm=0.25,
            carrier="Beazley / AIG / Coalition",
            renewal_date="2026-02-28",
            market_trend="hardening",
        ),
        InsuranceCoverage(
            coverage_type="Workers Compensation",
            annual_premium_mm=round(revenue_mm * 0.012, 2),
            pct_of_revenue=0.012,
            limits_mm=1,
            retention_mm=0.5,
            carrier="State-specific + Liberty Mutual",
            renewal_date="varies",
            market_trend="softening",
        ),
        InsuranceCoverage(
            coverage_type="Employment Practices Liability (EPLI)",
            annual_premium_mm=round(revenue_mm * 0.0005, 2),
            pct_of_revenue=0.0005,
            limits_mm=5,
            retention_mm=0.10,
            carrier="Chubb / Axa",
            renewal_date="2026-04-30",
            market_trend="hardening",
        ),
        InsuranceCoverage(
            coverage_type="Property / Business Interruption",
            annual_premium_mm=round(revenue_mm * 0.0008, 2),
            pct_of_revenue=0.0008,
            limits_mm=20,
            retention_mm=0.05,
            carrier="Travelers / CNA",
            renewal_date="varies",
            market_trend="stable",
        ),
        InsuranceCoverage(
            coverage_type="Auto / Fleet",
            annual_premium_mm=round(revenue_mm * 0.0003, 2),
            pct_of_revenue=0.0003,
            limits_mm=1,
            retention_mm=0.01,
            carrier="Progressive / Hartford",
            renewal_date="varies",
            market_trend="hardening",
        ),
    ]


def _build_open_claims() -> List[ClaimReserve]:
    import hashlib
    rows = []
    specs = ["Orthopedics", "OB/GYN", "General Surgery", "Emergency Medicine", "Oncology", "Primary Care"]
    for i in range(12):
        h = int(hashlib.md5(f"claim{i}".encode()).hexdigest()[:6], 16)
        specialty = specs[h % len(specs)]
        year = 2020 + (h % 5)
        reserve = 0.2 + (h % 50) / 10
        case_mm = 0.05 + (h % 30) / 100
        statuses = ["open", "open", "litigation", "settled", "closed"]
        status = statuses[h % len(statuses)]
        rows.append(ClaimReserve(
            claim_id=f"CL-{2020 + i:04d}",
            specialty=specialty,
            accident_year=year,
            reserve_mm=round(reserve, 3),
            case_mm=round(case_mm, 3),
            status=status,
            projected_resolution=f"Q{(h % 4) + 1} {year + 2}",
        ))
    return rows


def _build_tail_coverage(malpractice_mm: float) -> List[TailCoverage]:
    return [
        TailCoverage(
            structure="Unlimited Tail (PE-preferred)",
            upfront_cost_mm=round(malpractice_mm * 2.0, 2),
            coverage_period_yrs=99,
            ongoing_risk_mm=0,
            recommended=True,
        ),
        TailCoverage(
            structure="5-Year Extended Reporting",
            upfront_cost_mm=round(malpractice_mm * 1.3, 2),
            coverage_period_yrs=5,
            ongoing_risk_mm=round(malpractice_mm * 1.2, 2),
            recommended=False,
        ),
        TailCoverage(
            structure="Nose Coverage (prior-acts with new carrier)",
            upfront_cost_mm=round(malpractice_mm * 1.1, 2),
            coverage_period_yrs=99,
            ongoing_risk_mm=round(malpractice_mm * 0.1, 2),
            recommended=False,
        ),
        TailCoverage(
            structure="Self-Insured via Captive",
            upfront_cost_mm=0,
            coverage_period_yrs=99,
            ongoing_risk_mm=round(malpractice_mm * 2.5, 2),
            recommended=False,
        ),
    ]


def _build_captive(malpractice_mm: float) -> List[CaptiveAnalysis]:
    return [
        CaptiveAnalysis(
            structure="Single-Parent Captive (Cayman / VT)",
            annual_retained_loss_mm=round(malpractice_mm * 0.35, 2),
            tax_benefit_mm=round(malpractice_mm * 0.12, 2),
            admin_cost_mm=0.35,
            net_benefit_mm=round(malpractice_mm * 0.45, 2),
            viable=malpractice_mm >= 2.0,
        ),
        CaptiveAnalysis(
            structure="Cell / Rent-a-Captive",
            annual_retained_loss_mm=round(malpractice_mm * 0.20, 2),
            tax_benefit_mm=round(malpractice_mm * 0.06, 2),
            admin_cost_mm=0.12,
            net_benefit_mm=round(malpractice_mm * 0.22, 2),
            viable=malpractice_mm >= 1.0,
        ),
        CaptiveAnalysis(
            structure="Group Captive (join existing)",
            annual_retained_loss_mm=round(malpractice_mm * 0.15, 2),
            tax_benefit_mm=round(malpractice_mm * 0.04, 2),
            admin_cost_mm=0.08,
            net_benefit_mm=round(malpractice_mm * 0.15, 2),
            viable=True,
        ),
        CaptiveAnalysis(
            structure="Status Quo (commercial market)",
            annual_retained_loss_mm=0,
            tax_benefit_mm=0,
            admin_cost_mm=0,
            net_benefit_mm=0,
            viable=True,
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_insurance(
    sector: str = "Physician Services",
    revenue_mm: float = 100.0,
    total_providers: int = 50,
) -> InsuranceResult:
    corpus = _load_corpus()

    specialty_prems = _build_specialty_premiums(sector, total_providers)
    malpractice_total_mm = sum(s.total_annual_k for s in specialty_prems) / 1000

    coverages = _build_coverages(revenue_mm, malpractice_total_mm)
    claims = _build_open_claims()
    tail = _build_tail_coverage(malpractice_total_mm)
    captive = _build_captive(malpractice_total_mm)

    total_insurance = sum(c.annual_premium_mm for c in coverages)
    total_limits = sum(c.limits_mm for c in coverages)
    total_reserves = sum(c.reserve_mm for c in claims if c.status in ("open", "litigation"))

    # Deal insurance cost = tail + annual inflation impact
    deal_cost = tail[0].upfront_cost_mm if tail else 0
    market_hardening = sum(c.annual_premium_mm for c in coverages if c.market_trend == "hardening") * 0.12

    return InsuranceResult(
        total_annual_insurance_mm=round(total_insurance, 2),
        insurance_pct_of_revenue=round(total_insurance / revenue_mm if revenue_mm else 0, 4),
        total_coverage_limits_mm=round(total_limits, 0),
        risk_adjusted_reserve_mm=round(total_reserves, 2),
        coverages=coverages,
        specialty_premiums=specialty_prems,
        open_claims=claims,
        tail_coverage=tail,
        captive=captive,
        total_deal_insurance_cost_mm=round(deal_cost, 2),
        market_hardening_impact_mm=round(market_hardening, 2),
        corpus_deal_count=len(corpus),
    )
