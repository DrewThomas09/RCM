"""Clinical Integration Network (CIN) Analyzer.

Models CIN economics for platforms with network-based value capture:
- Provider membership roster
- Shared-savings contracts with payers
- Quality measure performance (HEDIS/STARS)
- PCP/Specialist mix
- Distribution methodology (per-member, quality-weighted)
- Anti-kickback safe harbor compliance (FTC)
- Network adequacy by geography
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ProviderMember:
    provider_group: str
    specialty_category: str
    provider_count: int
    attributed_lives: int
    annual_contribution_mm: float
    quality_score: float
    engagement_score: int
    tenure_years: float


@dataclass
class NetworkContract:
    payer_name: str
    contract_type: str
    attributed_lives: int
    annual_premium_pmpy: float
    shared_savings_pct: float
    quality_weight: float
    expected_savings_mm: float
    expected_distribution_mm: float


@dataclass
class QualityMeasure:
    measure: str
    domain: str
    current_performance: float
    benchmark: float
    weight: float
    financial_impact_mm: float


@dataclass
class GeographicCoverage:
    market: str
    attributed_lives: int
    pcp_count: int
    specialist_count: int
    adequacy_score: str
    growth_opportunity: str


@dataclass
class DistributionCohort:
    cohort: str
    provider_count: int
    avg_distribution_per_provider_k: float
    quality_bonus_k: float
    productivity_bonus_k: float
    total_distribution_mm: float


@dataclass
class CINCompliance:
    regulation: str
    status: str
    last_review: str
    remediation_needed: str
    exposure_mm: float


@dataclass
class CINResult:
    total_providers: int
    total_attributed_lives: int
    total_annual_contribution_mm: float
    total_expected_distribution_mm: float
    weighted_quality_score: float
    network_adequacy_pct: float
    providers: List[ProviderMember]
    contracts: List[NetworkContract]
    quality_measures: List[QualityMeasure]
    geography: List[GeographicCoverage]
    distributions: List[DistributionCohort]
    compliance: List[CINCompliance]
    corpus_deal_count: int
    cin_value_rating: str


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 88):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_providers(network_size: int) -> List[ProviderMember]:
    import hashlib
    specs = [
        ("Primary Care Network", "PCP", 0.38),
        ("Cardiology Associates", "Specialist", 0.08),
        ("Orthopedic Group", "Specialist", 0.07),
        ("Gastroenterology", "Specialist", 0.05),
        ("OB/GYN Women's Health", "Specialist", 0.06),
        ("Psychiatry / Behavioral", "Specialist", 0.05),
        ("Endocrinology", "Specialist", 0.04),
        ("Pulmonology", "Specialist", 0.04),
        ("Oncology", "Specialist", 0.05),
        ("Dermatology", "Specialist", 0.03),
        ("Urology", "Specialist", 0.03),
        ("Ophthalmology", "Specialist", 0.04),
        ("Nephrology", "Specialist", 0.03),
        ("Pediatrics", "PCP", 0.05),
    ]
    rows = []
    for name, cat, share in specs:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        pc = max(1, int(network_size * share))
        lives = pc * (380 + (h % 250))
        contrib = pc * (0.008 + (h % 6) / 1000)
        quality = 0.68 + (h % 22) / 100
        engage = 55 + (h % 40)
        tenure = 2.0 + (h % 7)
        rows.append(ProviderMember(
            provider_group=name,
            specialty_category=cat,
            provider_count=pc,
            attributed_lives=lives,
            annual_contribution_mm=round(contrib, 3),
            quality_score=round(quality, 3),
            engagement_score=engage,
            tenure_years=round(tenure, 1),
        ))
    return rows


def _build_contracts(total_lives: int) -> List[NetworkContract]:
    import hashlib
    cs = [
        ("BCBS Network PPO", "Shared Savings", 0.26, 4950, 0.50, 0.35),
        ("UHC Commercial", "Shared Savings", 0.22, 4850, 0.45, 0.30),
        ("MA Global Risk (UHC)", "Full-Risk MA", 0.18, 11800, 0.95, 0.25),
        ("MA Shared Savings (Humana)", "MSSP/Shared", 0.12, 10950, 0.65, 0.40),
        ("Aetna Commercial", "Shared Savings", 0.10, 4550, 0.40, 0.30),
        ("Medicare ACO REACH", "Full-Risk", 0.08, 12800, 0.90, 0.50),
        ("State Medicaid MCO", "Quality Bonus", 0.04, 5850, 0.00, 0.70),
    ]
    rows = []
    for name, ctype, share, ppmy, ss_pct, qw in cs:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        lives = int(total_lives * share)
        premium_total = lives * ppmy
        # Savings = 3-6% of premium typical
        savings_rate = 0.035 + (h % 25) / 1000
        expected_savings = premium_total * savings_rate / 1000000
        distribution = expected_savings * ss_pct * (0.70 + qw * 0.30)
        rows.append(NetworkContract(
            payer_name=name,
            contract_type=ctype,
            attributed_lives=lives,
            annual_premium_pmpy=round(ppmy, 2),
            shared_savings_pct=round(ss_pct, 3),
            quality_weight=round(qw, 3),
            expected_savings_mm=round(expected_savings, 2),
            expected_distribution_mm=round(distribution, 2),
        ))
    return rows


def _build_quality_measures() -> List[QualityMeasure]:
    return [
        QualityMeasure("Diabetes HbA1c Control <8", "Chronic", 0.72, 0.78, 0.12, 1.85),
        QualityMeasure("Hypertension BP Control <140/90", "Chronic", 0.68, 0.75, 0.10, 1.42),
        QualityMeasure("Breast Cancer Screening 50-74", "Preventive", 0.74, 0.80, 0.08, 0.95),
        QualityMeasure("Colorectal Cancer Screening 50-75", "Preventive", 0.61, 0.72, 0.08, 1.18),
        QualityMeasure("Annual Wellness Visit Completion", "Preventive", 0.82, 0.88, 0.06, 0.68),
        QualityMeasure("Behavioral Health Follow-Up 7d", "Behavioral", 0.48, 0.60, 0.08, 1.32),
        QualityMeasure("Readmission Rate 30-Day", "Utilization", 0.148, 0.125, 0.10, 2.45),
        QualityMeasure("ED Utilization / 1000", "Utilization", 385, 340, 0.08, 1.85),
        QualityMeasure("Generic Dispensing Rate", "Pharmacy", 0.86, 0.90, 0.05, 0.48),
        QualityMeasure("Medicare Wellness (AWV + PHA)", "Preventive", 0.68, 0.78, 0.05, 0.72),
        QualityMeasure("Care Gap Closure < 90d", "Chronic", 0.54, 0.70, 0.10, 1.22),
        QualityMeasure("Patient Experience (CAHPS)", "Experience", 82.5, 88.0, 0.10, 1.15),
    ]


def _build_geography(total_lives: int) -> List[GeographicCoverage]:
    import hashlib
    markets = [
        ("Metro Core", 0.35),
        ("Metro Suburban", 0.28),
        ("Secondary Cities", 0.18),
        ("Tertiary / Rural Adjacent", 0.12),
        ("Border Counties", 0.07),
    ]
    rows = []
    for name, share in markets:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        lives = int(total_lives * share)
        pcp = 35 + (h % 50) + int(share * 120)
        spec = pcp * 2 + (h % 25)
        ratio = lives / (pcp + 1)
        adeq = "strong" if ratio < 350 else ("adequate" if ratio < 600 else "gap")
        growth = "priority expansion" if adeq == "gap" else ("fill-in needed" if adeq == "adequate" else "well-served")
        rows.append(GeographicCoverage(
            market=name,
            attributed_lives=lives,
            pcp_count=pcp,
            specialist_count=spec,
            adequacy_score=adeq,
            growth_opportunity=growth,
        ))
    return rows


def _build_distributions(total_dist: float, provider_count: int) -> List[DistributionCohort]:
    cohorts = [
        ("Top Quartile Quality", int(provider_count * 0.25), 0.48),
        ("Above Avg", int(provider_count * 0.30), 0.28),
        ("Avg", int(provider_count * 0.30), 0.18),
        ("Below Avg", int(provider_count * 0.12), 0.05),
        ("Bottom Quartile", int(provider_count * 0.03), 0.01),
    ]
    rows = []
    for name, pc, share in cohorts:
        cohort_total = total_dist * share
        per_provider = cohort_total / max(pc, 1) * 1000   # k
        quality_bonus = per_provider * 0.55
        prod_bonus = per_provider * 0.45
        rows.append(DistributionCohort(
            cohort=name,
            provider_count=pc,
            avg_distribution_per_provider_k=round(per_provider, 1),
            quality_bonus_k=round(quality_bonus, 1),
            productivity_bonus_k=round(prod_bonus, 1),
            total_distribution_mm=round(cohort_total, 2),
        ))
    return rows


def _build_compliance() -> List[CINCompliance]:
    return [
        CINCompliance("FTC Statement 9 (CIN Safety Zone)", "compliant", "2024-09-15", "none", 0),
        CINCompliance("Stark Law In-Office Ancillary", "compliant", "2024-07-22", "none", 0),
        CINCompliance("Anti-Kickback Statute", "compliant", "2024-10-02", "none", 0),
        CINCompliance("State Insurance Licensure (risk-bearing)", "monitoring", "2024-06-15", "file update Q1 2027", 150),
        CINCompliance("Medicare ACO Waiver Compliance", "compliant", "2024-08-30", "none", 0),
        CINCompliance("Data Use Agreement (payer-shared PHI)", "minor gap", "2024-05-12", "6 pending signatures", 85),
        CINCompliance("HIPAA Security (data exchange)", "compliant", "2024-09-01", "none", 0),
        CINCompliance("OIG Advisory Opinion - Distribution", "monitoring", "2023-11-20", "methodology review", 240),
    ]


def compute_cin_analyzer(
    network_provider_count: int = 600,
    total_attributed_lives: int = 250000,
) -> CINResult:
    corpus = _load_corpus()

    providers = _build_providers(network_provider_count)
    contracts = _build_contracts(total_attributed_lives)
    qm = _build_quality_measures()
    geo = _build_geography(total_attributed_lives)
    compliance = _build_compliance()

    total_contrib = sum(p.annual_contribution_mm for p in providers)
    total_dist = sum(c.expected_distribution_mm for c in contracts)
    distributions = _build_distributions(total_dist, network_provider_count)

    total_lives_covered = sum(p.attributed_lives for p in providers)
    wquality = sum(p.quality_score * p.provider_count for p in providers) / sum(p.provider_count for p in providers) if providers else 0
    adequate_lives = sum(g.attributed_lives for g in geo if g.adequacy_score in ("strong", "adequate"))
    adequacy_pct = adequate_lives / total_attributed_lives if total_attributed_lives else 0

    if wquality >= 0.80 and adequacy_pct >= 0.85:
        rating = "trust-grade"
    elif wquality >= 0.72 and adequacy_pct >= 0.75:
        rating = "solid"
    else:
        rating = "developing"

    return CINResult(
        total_providers=network_provider_count,
        total_attributed_lives=total_attributed_lives,
        total_annual_contribution_mm=round(total_contrib, 2),
        total_expected_distribution_mm=round(total_dist, 2),
        weighted_quality_score=round(wquality, 3),
        network_adequacy_pct=round(adequacy_pct, 3),
        providers=providers,
        contracts=contracts,
        quality_measures=qm,
        geography=geo,
        distributions=distributions,
        compliance=compliance,
        corpus_deal_count=len(corpus),
        cin_value_rating=rating,
    )
