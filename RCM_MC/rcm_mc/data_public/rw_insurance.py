"""Rep & Warranty Insurance / M&A Insurance Tracker.

Tracks R&W insurance policies across portfolio deals: primary coverage,
excess towers, retention, premium rates, claim history, exclusions,
specialty coverages (tax indemnity, contingent liability, litigation).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class RWPolicy:
    deal: str
    policy_type: str
    deal_size_m: float
    primary_limit_m: float
    total_tower_m: float
    retention_m: float
    retention_pct: float
    premium_m: float
    rate_pct: float
    policy_period_years: int
    primary_carrier: str
    broker: str


@dataclass
class CarrierExposure:
    carrier: str
    primary_policies: int
    excess_layers: int
    total_limit_deployed_m: float
    avg_rate_pct: float
    open_claims: int
    notable_strengths: str
    rating: str


@dataclass
class PolicyExclusion:
    deal: str
    exclusion_type: str
    scope: str
    standalone_coverage: str
    annual_premium_m: float
    retention_m: float


@dataclass
class ClaimActivity:
    deal: str
    claim_date: str
    claim_type: str
    claimed_amount_m: float
    paid_amount_m: float
    carrier: str
    status: str
    root_cause: str


@dataclass
class SpecialtyCoverage:
    coverage_type: str
    deal: str
    limit_m: float
    retention_m: float
    premium_m: float
    rate_pct: float
    period_years: int
    trigger: str


@dataclass
class MarketBenchmark:
    deal_size_band: str
    typical_primary_limit_pct: float
    typical_retention_pct: float
    median_rate_pct: float
    market_trend: str
    typical_tower_layers: int


@dataclass
class RWResult:
    total_policies: int
    total_primary_limit_m: float
    total_tower_limit_m: float
    total_premium_m: float
    weighted_avg_rate_pct: float
    weighted_avg_retention_pct: float
    open_claims: int
    policies: List[RWPolicy]
    carriers: List[CarrierExposure]
    exclusions: List[PolicyExclusion]
    claims: List[ClaimActivity]
    specialty: List[SpecialtyCoverage]
    benchmarks: List[MarketBenchmark]
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


def _build_policies() -> List[RWPolicy]:
    return [
        RWPolicy("Project Azalea — GI Network SE", "Buy-Side R&W", 1650.0, 25.0, 115.0, 8.25, 0.005, 3.45, 0.030, 6,
                 "Beazley", "Marsh"),
        RWPolicy("Project Magnolia — MSK Platform", "Buy-Side R&W", 485.0, 25.0, 75.0, 2.42, 0.005, 1.28, 0.028, 6,
                 "AIG / Euclid", "Aon"),
        RWPolicy("Project Cypress — GI Network", "Buy-Side R&W", 525.0, 25.0, 75.0, 2.63, 0.005, 1.45, 0.030, 6,
                 "Beazley", "Marsh"),
        RWPolicy("Project Redwood — Behavioral", "Buy-Side R&W", 320.0, 25.0, 60.0, 1.60, 0.005, 1.02, 0.033, 6,
                 "Liberty Mutual", "Aon"),
        RWPolicy("Project Laurel — Derma", "Buy-Side R&W", 225.0, 25.0, 55.0, 1.13, 0.005, 0.82, 0.030, 6,
                 "Beazley", "Marsh"),
        RWPolicy("Project Cedar — Cardiology", "Buy-Side R&W", 445.0, 25.0, 75.0, 2.23, 0.005, 1.25, 0.028, 6,
                 "Euclid Transactional", "Aon"),
        RWPolicy("Project Willow — Fertility", "Buy-Side R&W", 395.0, 25.0, 75.0, 1.98, 0.005, 1.18, 0.030, 6,
                 "AIG / Euclid", "Marsh"),
        RWPolicy("Project Spruce — Radiology", "Buy-Side R&W", 340.0, 25.0, 65.0, 1.70, 0.005, 0.95, 0.028, 6,
                 "Tokio Marine HCC", "WTW"),
        RWPolicy("Project Aspen — Eye Care", "Buy-Side R&W", 195.0, 25.0, 50.0, 0.98, 0.005, 0.62, 0.031, 6,
                 "Beazley", "Marsh"),
        RWPolicy("Project Maple — Urology", "Buy-Side R&W", 165.0, 20.0, 40.0, 0.83, 0.005, 0.45, 0.028, 6,
                 "Liberty Mutual", "Aon"),
        RWPolicy("Project Ash — Infusion", "Buy-Side R&W", 485.0, 25.0, 75.0, 2.43, 0.005, 1.28, 0.028, 6,
                 "Euclid Transactional", "Marsh"),
        RWPolicy("Project Fir — Lab / Pathology", "Buy-Side R&W", 425.0, 25.0, 75.0, 2.13, 0.005, 1.05, 0.025, 6,
                 "AIG / Euclid", "Aon"),
        RWPolicy("Project Sage — Home Health", "Buy-Side R&W", 385.0, 25.0, 65.0, 1.93, 0.005, 1.18, 0.032, 6,
                 "Beazley", "Marsh"),
        RWPolicy("Project Linden — Behavioral", "Buy-Side R&W", 265.0, 25.0, 60.0, 1.33, 0.005, 0.95, 0.035, 6,
                 "AIG / Euclid", "Aon"),
        RWPolicy("Project Oak — RCM SaaS", "Sell-Side R&W (sponsor-led)", 525.0, 25.0, 75.0, 2.63, 0.005, 1.42, 0.028, 6,
                 "Euclid Transactional", "WTW"),
        RWPolicy("Project Basil — Dental DSO", "Buy-Side R&W", 385.0, 25.0, 65.0, 1.93, 0.005, 1.08, 0.030, 6,
                 "Liberty Mutual", "Aon"),
        RWPolicy("Project Thyme — Specialty Pharm", "Buy-Side R&W", 450.0, 25.0, 75.0, 2.25, 0.005, 1.22, 0.028, 6,
                 "Beazley", "Marsh"),
    ]


def _build_carriers() -> List[CarrierExposure]:
    return [
        CarrierExposure("Beazley", 6, 18, 385.0, 0.0310, 2, "Healthcare focus + speed + commercial balance",
                        "A+ (A.M. Best)"),
        CarrierExposure("AIG / Euclid Transactional", 5, 15, 325.0, 0.0285, 1, "Lead market, global reach, cap markets",
                        "A (A.M. Best)"),
        CarrierExposure("Euclid Transactional (Ambac subsidiary)", 3, 10, 185.0, 0.0285, 0, "US middle-market specialist",
                        "A- (A.M. Best)"),
        CarrierExposure("Liberty Mutual", 3, 8, 145.0, 0.0315, 0, "Cost-competitive + tax indemnity",
                        "A (A.M. Best)"),
        CarrierExposure("Tokio Marine HCC", 1, 5, 85.0, 0.0280, 0, "Japanese reinsurance strength",
                        "A++ (A.M. Best)"),
        CarrierExposure("CFC Underwriting", 0, 8, 125.0, 0.0295, 0, "Specialty + cyber crossover",
                        "A (A.M. Best)"),
        CarrierExposure("Allianz Global Corporate", 0, 6, 95.0, 0.0320, 0, "Excess layers specialist",
                        "A+ (A.M. Best)"),
        CarrierExposure("Swiss Re Corporate Solutions", 0, 5, 82.0, 0.0315, 0, "High excess layers",
                        "A+ (A.M. Best)"),
    ]


def _build_exclusions() -> List[PolicyExclusion]:
    return [
        PolicyExclusion("Project Cedar — Cardiology", "Stark Law + Anti-Kickback", "All physician comp + referral patterns",
                        "Tax + regulatory indemnity (standalone)", 0.35, 2.5),
        PolicyExclusion("Project Redwood — Behavioral", "FCA / DOJ Inquiry (2024 known matter)", "Active DOJ investigation",
                        "Contingent liability insurance (standalone)", 0.85, 5.0),
        PolicyExclusion("Project Aspen — Eye Care", "Feb 2024 HIPAA Breach", "Pre-close known cyber incident",
                        "Cyber standalone + contingent liability", 0.55, 2.5),
        PolicyExclusion("Project Magnolia — MSK Platform", "Pre-close state tax exposure", "Multi-state sales tax nexus",
                        "Tax indemnity (standalone)", 0.48, 2.5),
        PolicyExclusion("Project Basil — Dental DSO", "DOJ upcoding investigation", "Active DOJ matter",
                        "Contingent liability insurance", 0.65, 3.5),
        PolicyExclusion("Project Sage — Home Health", "OIG FCA Inquiry (2024)", "Active OIG matter",
                        "Contingent liability insurance", 0.75, 4.0),
        PolicyExclusion("Project Cypress — GI Network", "Anesthesia related parties", "Related-party anesthesia arrangements",
                        "Tax + regulatory bespoke rider", 0.25, 1.5),
        PolicyExclusion("Project Willow — Fertility", "Consent / IVF tort history", "Historical IVF tort matters",
                        "Warranty shield rider", 0.42, 2.2),
        PolicyExclusion("Project Thyme — Specialty Pharm", "340B diversion risk", "Ongoing HRSA framework uncertainty",
                        "Bespoke 340B contingent coverage", 0.38, 1.5),
    ]


def _build_claims() -> List[ClaimActivity]:
    return [
        ClaimActivity("Project Redwood — Behavioral", "2025-11-05", "Undisclosed DOJ inquiry letter",
                      1.85, 0.0, "Liberty Mutual", "notified / investigating", "Pre-close notice received but not disclosed"),
        ClaimActivity("Project Cedar — Cardiology", "2026-01-10", "Undisclosed litigation",
                      2.00, 0.0, "Euclid Transactional", "settling", "Omitted medical malpractice claim"),
        ClaimActivity("Project Cypress — GI Network", "2025-01-22", "Environmental / asbestos abatement",
                      1.20, 1.00, "Beazley", "resolved (paid)", "Phase I environmental finding missed in DD"),
        ClaimActivity("Project Magnolia — MSK Platform", "2024-08-12", "Working capital true-up",
                      2.50, 2.30, "AIG / Euclid", "resolved (paid)", "Net working capital understatement"),
        ClaimActivity("Project Iris — Dental DSO (closed 2022)", "2024-11-15", "IP infringement",
                      18.5, 12.50, "Beazley", "resolved (settled)", "Undisclosed patent claim"),
        ClaimActivity("Project Cedar — Cardiology", "2025-06-15", "Medicare overpayment (RAC)",
                      3.20, 2.50, "Euclid Transactional", "resolved (paid)", "Pre-close RAC audit not disclosed"),
        ClaimActivity("Project Birch — Home Health (closed 2022)", "2024-08-20", "Medicare F2F docs",
                      8.50, 7.00, "Liberty Mutual", "resolved (settled)", "F2F documentation gap not disclosed"),
        ClaimActivity("Project Sage — Home Health", "2025-08-22", "Data breach (misconfig S3)",
                      2.50, 0.0, "Beazley + CFC cyber", "ongoing", "Post-close security finding disputed"),
        ClaimActivity("Project Aspen — Eye Care", "2026-02-22", "HIPAA breach OCR CAP cost",
                      4.20, 0.0, "CFC Underwriting (cyber)", "active", "Covered under standalone cyber (not R&W)"),
        ClaimActivity("Project Cedar — Cardiology", "2025-09-28", "Stark Law safe harbor gap",
                      2.80, 2.20, "Euclid Transactional", "resolved (paid)", "Excluded from base R&W; tax indemnity covered"),
    ]


def _build_specialty() -> List[SpecialtyCoverage]:
    return [
        SpecialtyCoverage("Tax Indemnity Insurance", "Project Magnolia — MSK Platform", 15.0, 0.75, 0.42, 0.028, 6,
                          "State sales/use tax pre-close exposure"),
        SpecialtyCoverage("Tax Indemnity Insurance", "Project Oak — RCM SaaS", 12.0, 0.60, 0.32, 0.027, 6,
                          "IRS transfer pricing challenge"),
        SpecialtyCoverage("Contingent Liability (FCA)", "Project Redwood — Behavioral", 10.0, 3.0, 0.72, 0.072, 6,
                          "DOJ FCA matter outcome"),
        SpecialtyCoverage("Contingent Liability (DOJ)", "Project Basil — Dental DSO", 15.0, 4.0, 0.95, 0.063, 6,
                          "DOJ upcoding investigation outcome"),
        SpecialtyCoverage("Litigation Buyout", "Project Cedar — Cardiology", 8.0, 1.0, 0.48, 0.060, 5,
                          "Known pre-close class action"),
        SpecialtyCoverage("Litigation Buyout", "Project Willow — Fertility", 12.0, 2.5, 0.85, 0.071, 5,
                          "Embryo tort lawsuits"),
        SpecialtyCoverage("Cyber Standalone", "Project Aspen — Eye Care", 25.0, 1.0, 1.85, 0.074, 3,
                          "Post-breach HIPAA + business interruption"),
        SpecialtyCoverage("Environmental Indemnity", "Project Cypress — GI Network", 12.0, 1.0, 0.35, 0.029, 10,
                          "Real estate Phase I exposure"),
        SpecialtyCoverage("Environmental Indemnity", "Project Magnolia — MSK Platform", 10.0, 1.0, 0.28, 0.028, 10,
                          "Real estate Phase I exposure"),
        SpecialtyCoverage("Warranty Extension", "Project Fir — Lab / Pathology", 15.0, 2.5, 0.45, 0.030, 4,
                          "Post-expiration matter uptick risk"),
    ]


def _build_benchmarks() -> List[MarketBenchmark]:
    return [
        MarketBenchmark("$50-100M", 0.10, 0.010, 0.0450, "tightening slightly", 3),
        MarketBenchmark("$100-250M", 0.07, 0.0075, 0.0350, "stable", 4),
        MarketBenchmark("$250-500M", 0.06, 0.005, 0.0300, "stable", 5),
        MarketBenchmark("$500M-1B", 0.05, 0.005, 0.0285, "softening", 6),
        MarketBenchmark("$1-2B", 0.05, 0.005, 0.0275, "softening", 7),
        MarketBenchmark("$2B+", 0.04, 0.0035, 0.0250, "softening", 8),
    ]


def compute_rw_insurance() -> RWResult:
    corpus = _load_corpus()
    policies = _build_policies()
    carriers = _build_carriers()
    exclusions = _build_exclusions()
    claims = _build_claims()
    specialty = _build_specialty()
    benchmarks = _build_benchmarks()

    total_primary = sum(p.primary_limit_m for p in policies)
    total_tower = sum(p.total_tower_m for p in policies)
    total_premium = sum(p.premium_m for p in policies)
    wtd_rate = sum(p.rate_pct * p.deal_size_m for p in policies) / sum(p.deal_size_m for p in policies) if policies else 0
    wtd_ret = sum(p.retention_pct * p.deal_size_m for p in policies) / sum(p.deal_size_m for p in policies) if policies else 0
    open_cl = sum(1 for c in claims if c.status in ("ongoing", "active", "settling", "notified / investigating"))

    return RWResult(
        total_policies=len(policies),
        total_primary_limit_m=round(total_primary, 1),
        total_tower_limit_m=round(total_tower, 1),
        total_premium_m=round(total_premium, 1),
        weighted_avg_rate_pct=round(wtd_rate, 4),
        weighted_avg_retention_pct=round(wtd_ret, 5),
        open_claims=open_cl,
        policies=policies,
        carriers=carriers,
        exclusions=exclusions,
        claims=claims,
        specialty=specialty,
        benchmarks=benchmarks,
        corpus_deal_count=len(corpus),
    )
