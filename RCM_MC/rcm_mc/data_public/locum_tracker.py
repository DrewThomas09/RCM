"""Locum & Contract Workforce Tracker.

Tracks contract clinician spend — a top-5 diligence issue for PE healthcare
platforms post-COVID. Covers locum tenens physicians, agency RNs, travel
therapists, and 1099 contractors. Models:

- Spend by specialty / role
- Rate premium vs permanent FTE
- Coverage gap days
- Permanent conversion pipeline
- Agency fee bleed
- 1099 vs W-2 compliance exposure
- Scenario plans (internal float, hospitalist, aggressive convert)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Role benchmarks
# ---------------------------------------------------------------------------

_ROLE_BENCHMARKS = {
    "Hospitalist":          {"locum_hourly": 235, "perm_hourly": 140, "agency_fee_pct": 0.18},
    "Emergency Medicine":   {"locum_hourly": 285, "perm_hourly": 165, "agency_fee_pct": 0.20},
    "Anesthesiologist":     {"locum_hourly": 325, "perm_hourly": 195, "agency_fee_pct": 0.19},
    "CRNA":                 {"locum_hourly": 195, "perm_hourly": 120, "agency_fee_pct": 0.18},
    "Psychiatrist":         {"locum_hourly": 265, "perm_hourly": 145, "agency_fee_pct": 0.22},
    "Radiologist":          {"locum_hourly": 295, "perm_hourly": 175, "agency_fee_pct": 0.17},
    "Travel RN (ICU)":      {"locum_hourly": 125, "perm_hourly": 62,  "agency_fee_pct": 0.22},
    "Travel RN (Med-Surg)": {"locum_hourly": 98,  "perm_hourly": 48,  "agency_fee_pct": 0.22},
    "Travel RN (ED)":       {"locum_hourly": 115, "perm_hourly": 55,  "agency_fee_pct": 0.22},
    "Travel PT":            {"locum_hourly": 68,  "perm_hourly": 42,  "agency_fee_pct": 0.20},
    "1099 Specialist":      {"locum_hourly": 215, "perm_hourly": 130, "agency_fee_pct": 0.12},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ContractRole:
    role: str
    headcount_fte: float
    hours_per_month: int
    locum_rate_per_hour: float
    perm_equiv_rate: float
    monthly_spend_k: float
    annual_spend_mm: float
    rate_premium_pct: float
    agency_fee_pct: float
    conversion_viable: bool


@dataclass
class CoverageGap:
    department: str
    open_positions: int
    avg_gap_days: int
    locum_coverage_pct: float
    uncovered_pct: float
    revenue_at_risk_mm: float
    priority: str


@dataclass
class ConversionPipeline:
    role: str
    in_pipeline_fte: int
    perm_offer_made: int
    accepted_perm: int
    monthly_savings_k: float
    annual_savings_mm: float
    conversion_rate_pct: float


@dataclass
class ComplianceExposure:
    category: str
    finding: str
    exposure_k: float
    remediation_days: int
    severity: str


@dataclass
class WorkforceScenario:
    scenario: str
    locum_spend_mm: float
    permanent_cost_mm: float
    total_labor_mm: float
    labor_pct_of_revenue: float
    retention_risk: str
    implementation_months: int
    year_one_savings_mm: float


@dataclass
class LocumResult:
    total_revenue_mm: float
    total_labor_mm: float
    locum_spend_mm: float
    locum_pct_of_labor: float
    total_contract_fte: float
    total_permanent_fte: float
    roles: List[ContractRole]
    gaps: List[CoverageGap]
    conversions: List[ConversionPipeline]
    compliance: List[ComplianceExposure]
    scenarios: List[WorkforceScenario]
    recommended_scenario: str
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 82):
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


def _build_roles(revenue_mm: float, sector: str) -> List[ContractRole]:
    import hashlib
    # Sector-specific role mix
    if sector in ("Hospital", "Inpatient"):
        role_mix = [
            ("Hospitalist", 4.5, 180), ("Emergency Medicine", 3.5, 160),
            ("Anesthesiologist", 2.0, 170), ("Travel RN (ICU)", 12.0, 160),
            ("Travel RN (Med-Surg)", 18.0, 156), ("Travel RN (ED)", 8.0, 160),
            ("Radiologist", 1.8, 150), ("CRNA", 2.2, 170),
        ]
    elif sector in ("ASC", "Surgery Center"):
        role_mix = [
            ("Anesthesiologist", 3.5, 170), ("CRNA", 4.0, 170),
            ("Travel RN (ICU)", 3.0, 160), ("1099 Specialist", 2.5, 120),
        ]
    elif sector in ("Behavioral Health", "Psychiatry"):
        role_mix = [
            ("Psychiatrist", 6.0, 140), ("Travel RN (Med-Surg)", 8.0, 160),
            ("1099 Specialist", 3.0, 120),
        ]
    else:
        # Physician services, outpatient
        role_mix = [
            ("1099 Specialist", 5.5, 140), ("Travel RN (Med-Surg)", 4.0, 160),
            ("Travel PT", 3.0, 160), ("Psychiatrist", 1.5, 130),
        ]

    # Scale by revenue
    scale = max(revenue_mm / 100, 0.4)

    rows = []
    for role, fte, hours in role_mix:
        h = int(hashlib.md5(role.encode()).hexdigest()[:6], 16)
        bench = _ROLE_BENCHMARKS[role]
        locum_rate = bench["locum_hourly"] * (0.95 + (h % 11) / 100)
        perm_rate = bench["perm_hourly"]
        scaled_fte = round(fte * scale, 1)
        monthly_spend = scaled_fte * hours * locum_rate / 1000
        annual = monthly_spend * 12 / 1000
        premium = (locum_rate - perm_rate) / perm_rate if perm_rate else 0
        convertible = scaled_fte >= 1.0 and premium > 0.45
        rows.append(ContractRole(
            role=role,
            headcount_fte=scaled_fte,
            hours_per_month=hours,
            locum_rate_per_hour=round(locum_rate, 2),
            perm_equiv_rate=round(perm_rate, 2),
            monthly_spend_k=round(monthly_spend, 1),
            annual_spend_mm=round(annual, 3),
            rate_premium_pct=round(premium, 4),
            agency_fee_pct=round(bench["agency_fee_pct"], 3),
            conversion_viable=convertible,
        ))
    return rows


def _build_gaps(revenue_mm: float, sector: str) -> List[CoverageGap]:
    import hashlib
    if sector in ("Hospital", "Inpatient"):
        depts = [
            ("ICU", 4, 142, 0.82),
            ("Emergency Department", 5, 96, 0.88),
            ("Med-Surg Floor", 9, 68, 0.74),
            ("Operating Room", 3, 85, 0.70),
            ("Behavioral Health Unit", 2, 185, 0.55),
        ]
    elif sector in ("ASC", "Surgery Center"):
        depts = [
            ("Operating Room", 2, 72, 0.88),
            ("Pre-Op/PACU", 3, 48, 0.85),
            ("Sterile Processing", 1, 95, 0.30),
        ]
    elif sector in ("Behavioral Health", "Psychiatry"):
        depts = [
            ("Psychiatric Unit", 4, 152, 0.72),
            ("Adolescent Unit", 2, 218, 0.58),
            ("Intake / Assessment", 2, 85, 0.68),
        ]
    else:
        depts = [
            ("Primary Care Float", 3, 45, 0.78),
            ("Specialty Coverage", 2, 95, 0.62),
            ("Outpatient Therapy", 2, 62, 0.72),
        ]

    rows = []
    for dept, positions, gap_days, cov_pct in depts:
        h = int(hashlib.md5(dept.encode()).hexdigest()[:6], 16)
        scaled_positions = max(1, int(positions * max(revenue_mm / 200, 0.5)))
        uncov = max(0, 1 - cov_pct)
        risk = uncov * scaled_positions * gap_days * 0.08 * (revenue_mm / 50)
        if gap_days > 120 or cov_pct < 0.60:
            priority = "critical"
        elif gap_days > 80 or cov_pct < 0.75:
            priority = "high"
        else:
            priority = "standard"
        rows.append(CoverageGap(
            department=dept,
            open_positions=scaled_positions,
            avg_gap_days=gap_days + (h % 20),
            locum_coverage_pct=round(cov_pct, 3),
            uncovered_pct=round(uncov, 3),
            revenue_at_risk_mm=round(risk / 100, 3),
            priority=priority,
        ))
    return rows


def _build_conversions(roles: List[ContractRole]) -> List[ConversionPipeline]:
    import hashlib
    rows = []
    for r in roles:
        if not r.conversion_viable:
            continue
        h = int(hashlib.md5(r.role.encode()).hexdigest()[:6], 16)
        pipeline = max(1, int(r.headcount_fte * 0.6))
        offer = max(1, int(pipeline * 0.5))
        accepted = max(0, int(offer * (0.45 + (h % 30) / 100)))
        monthly_savings = accepted * r.hours_per_month * (r.locum_rate_per_hour - r.perm_equiv_rate) / 1000
        annual = monthly_savings * 12 / 1000
        cr = accepted / pipeline if pipeline else 0
        rows.append(ConversionPipeline(
            role=r.role,
            in_pipeline_fte=pipeline,
            perm_offer_made=offer,
            accepted_perm=accepted,
            monthly_savings_k=round(monthly_savings, 1),
            annual_savings_mm=round(annual, 3),
            conversion_rate_pct=round(cr, 3),
        ))
    return rows


def _build_compliance() -> List[ComplianceExposure]:
    return [
        ComplianceExposure("1099 Misclassification", "6 workers classified 1099 meet W-2 test",
                           385.0, 90, "high"),
        ComplianceExposure("Credentialing Lag", "Avg credentialing 62 days vs 21 target",
                           142.0, 120, "medium"),
        ComplianceExposure("Malpractice Coverage Gap", "3 locum MDs lack current cert-of-insurance",
                           520.0, 30, "high"),
        ComplianceExposure("Contract Overruns", "4 locum contracts past expiry on auto-extend",
                           215.0, 45, "medium"),
        ComplianceExposure("Background Recheck Overdue", "11 contract RNs past 12-mo recheck",
                           68.0, 60, "low"),
        ComplianceExposure("Agency Fee Markup", "Agency fee avg 19% vs 15% industry median",
                           488.0, 180, "medium"),
        ComplianceExposure("Wage-and-Hour Exposure", "Travel RNs stipend structure under review",
                           720.0, 150, "high"),
    ]


def _build_scenarios(revenue_mm: float, total_labor_mm: float,
                     locum_spend_mm: float) -> List[WorkforceScenario]:
    scenarios = []
    # Current baseline
    scenarios.append(WorkforceScenario(
        scenario="Current Baseline",
        locum_spend_mm=round(locum_spend_mm, 2),
        permanent_cost_mm=round(total_labor_mm - locum_spend_mm, 2),
        total_labor_mm=round(total_labor_mm, 2),
        labor_pct_of_revenue=round(total_labor_mm / revenue_mm, 4),
        retention_risk="elevated",
        implementation_months=0,
        year_one_savings_mm=0.0,
    ))
    # Aggressive convert
    convert_savings = locum_spend_mm * 0.35
    new_locum = locum_spend_mm - convert_savings
    new_perm = (total_labor_mm - locum_spend_mm) + (convert_savings * 0.55)
    scenarios.append(WorkforceScenario(
        scenario="Aggressive Conversion Campaign",
        locum_spend_mm=round(new_locum, 2),
        permanent_cost_mm=round(new_perm, 2),
        total_labor_mm=round(new_locum + new_perm, 2),
        labor_pct_of_revenue=round((new_locum + new_perm) / revenue_mm, 4),
        retention_risk="improved",
        implementation_months=9,
        year_one_savings_mm=round(locum_spend_mm * 0.18, 2),
    ))
    # Internal float pool
    float_savings = locum_spend_mm * 0.25
    new_locum2 = locum_spend_mm - float_savings
    new_perm2 = (total_labor_mm - locum_spend_mm) + (float_savings * 0.60)
    scenarios.append(WorkforceScenario(
        scenario="Internal Float Pool",
        locum_spend_mm=round(new_locum2, 2),
        permanent_cost_mm=round(new_perm2, 2),
        total_labor_mm=round(new_locum2 + new_perm2, 2),
        labor_pct_of_revenue=round((new_locum2 + new_perm2) / revenue_mm, 4),
        retention_risk="stable",
        implementation_months=6,
        year_one_savings_mm=round(locum_spend_mm * 0.12, 2),
    ))
    # Hospitalist model (MD-specific)
    hosp_savings = locum_spend_mm * 0.22
    new_locum3 = locum_spend_mm - hosp_savings
    new_perm3 = (total_labor_mm - locum_spend_mm) + (hosp_savings * 0.62)
    scenarios.append(WorkforceScenario(
        scenario="Hospitalist Direct-Hire Model",
        locum_spend_mm=round(new_locum3, 2),
        permanent_cost_mm=round(new_perm3, 2),
        total_labor_mm=round(new_locum3 + new_perm3, 2),
        labor_pct_of_revenue=round((new_locum3 + new_perm3) / revenue_mm, 4),
        retention_risk="stable",
        implementation_months=12,
        year_one_savings_mm=round(locum_spend_mm * 0.10, 2),
    ))
    # Agency renegotiation
    agency_savings = locum_spend_mm * 0.08
    scenarios.append(WorkforceScenario(
        scenario="Agency Rate Renegotiation",
        locum_spend_mm=round(locum_spend_mm - agency_savings, 2),
        permanent_cost_mm=round(total_labor_mm - locum_spend_mm, 2),
        total_labor_mm=round(total_labor_mm - agency_savings, 2),
        labor_pct_of_revenue=round((total_labor_mm - agency_savings) / revenue_mm, 4),
        retention_risk="neutral",
        implementation_months=3,
        year_one_savings_mm=round(agency_savings, 2),
    ))
    return scenarios


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_locum_tracker(
    sector: str = "Hospital",
    revenue_mm: float = 250.0,
    labor_pct_of_revenue: float = 0.44,
) -> LocumResult:
    corpus = _load_corpus()
    total_labor = revenue_mm * labor_pct_of_revenue

    roles = _build_roles(revenue_mm, sector)
    gaps = _build_gaps(revenue_mm, sector)
    compliance = _build_compliance()

    locum_spend = sum(r.annual_spend_mm for r in roles)
    locum_pct_labor = locum_spend / total_labor if total_labor else 0

    total_contract_fte = sum(r.headcount_fte for r in roles)
    # Permanent FTE estimated from labor — assume $95k avg fully-loaded for non-contract
    perm_labor_mm = total_labor - locum_spend
    total_perm_fte = perm_labor_mm * 1000 / 95 if perm_labor_mm > 0 else 0

    conversions = _build_conversions(roles)
    scenarios = _build_scenarios(revenue_mm, total_labor, locum_spend)

    # Pick scenario with best y1 savings
    recommended = max(scenarios[1:], key=lambda s: s.year_one_savings_mm).scenario

    return LocumResult(
        total_revenue_mm=round(revenue_mm, 2),
        total_labor_mm=round(total_labor, 2),
        locum_spend_mm=round(locum_spend, 2),
        locum_pct_of_labor=round(locum_pct_labor, 4),
        total_contract_fte=round(total_contract_fte, 1),
        total_permanent_fte=round(total_perm_fte, 0),
        roles=roles,
        gaps=gaps,
        conversions=conversions,
        compliance=compliance,
        scenarios=scenarios,
        recommended_scenario=recommended,
        corpus_deal_count=len(corpus),
    )
