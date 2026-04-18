"""Provider Retention / Churn Analyzer.

Provider departures are the #1 near-term value destroyer post-close.
Models:
- Current turnover by specialty/role
- Cost per departure (recruiting, lost productivity, patient leakage)
- Retention lever catalog (comp, culture, career, compliance)
- 12-month churn risk ranking
- Intervention ROI
- Knowledge transfer / succession readiness
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProviderCohort:
    role: str
    headcount: int
    turnover_12mo_pct: float
    expected_departures: int
    replacement_cost_per_dept_mm: float
    annual_revenue_per_provider_mm: float
    annual_lost_revenue_mm: float
    severity: str               # "critical", "high", "medium", "low"


@dataclass
class ChurnDriver:
    driver: str
    contribution_pct: float
    trend: str                  # "rising", "stable", "declining"
    addressable: bool
    typical_fix_timeline: str


@dataclass
class AtRiskProvider:
    anon_id: str
    role: str
    tenure_yrs: float
    wrvu_pctile: int
    revenue_contribution_mm: float
    retention_score: int        # 0-100 (higher = more likely to stay)
    flight_risk_factors: str


@dataclass
class RetentionLever:
    lever: str
    one_time_cost_mm: float
    annual_cost_mm: float
    retention_lift_pp: float
    addressable_headcount: int
    expected_retained_revenue_mm: float
    roi_multiple: float
    priority: str


@dataclass
class SuccessionGap:
    role: str
    current_holder_tenure_yrs: float
    successor_identified: str   # "yes", "developing", "no"
    gap_severity: str
    readiness_pct: float


@dataclass
class ProviderRetentionResult:
    total_providers: int
    overall_turnover_pct: float
    expected_12mo_departures: int
    cost_of_churn_mm: float
    cost_per_departure_k: float
    cohorts: List[ProviderCohort]
    drivers: List[ChurnDriver]
    at_risk: List[AtRiskProvider]
    levers: List[RetentionLever]
    succession: List[SuccessionGap]
    total_retention_investment_mm: float
    total_savings_from_retention_mm: float
    ev_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 75):
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


def _severity_for(churn_pct: float, role: str) -> str:
    if role.startswith("Physician") and churn_pct >= 0.15:
        return "critical"
    if churn_pct >= 0.30:
        return "high"
    if churn_pct >= 0.18:
        return "medium"
    return "low"


def _build_cohorts(sector: str, revenue_mm: float, total_providers: int) -> List[ProviderCohort]:
    # Sector-specific role mix
    if sector in ("Primary Care", "Physician Services"):
        mix = [
            ("Physician (MD/DO)", 0.28, 0.145, 8.5, revenue_mm / total_providers * 1.5),
            ("Nurse Practitioner", 0.14, 0.18, 2.5, revenue_mm / total_providers * 0.9),
            ("Physician Assistant", 0.12, 0.17, 2.2, revenue_mm / total_providers * 0.85),
            ("Registered Nurse", 0.22, 0.25, 0.85, revenue_mm / total_providers * 0.40),
            ("Medical Assistant", 0.24, 0.38, 0.38, revenue_mm / total_providers * 0.20),
        ]
    elif sector in ("ASC", "Surgery Center"):
        mix = [
            ("Physician (Surgeon)", 0.18, 0.08, 18.5, revenue_mm / total_providers * 3.2),
            ("Anesthesiologist / CRNA", 0.16, 0.12, 6.5, revenue_mm / total_providers * 1.6),
            ("OR Nurse", 0.35, 0.22, 1.2, revenue_mm / total_providers * 0.50),
            ("Tech / Circulator", 0.18, 0.28, 0.65, revenue_mm / total_providers * 0.30),
            ("Admin", 0.13, 0.18, 0.40, revenue_mm / total_providers * 0.15),
        ]
    elif sector in ("Home Health", "Hospice"):
        mix = [
            ("Registered Nurse (Home)", 0.42, 0.28, 1.5, revenue_mm / total_providers * 0.70),
            ("Aide / HHA", 0.28, 0.42, 0.35, revenue_mm / total_providers * 0.15),
            ("Physical Therapist", 0.12, 0.18, 2.2, revenue_mm / total_providers * 0.75),
            ("Social Worker", 0.06, 0.22, 1.0, revenue_mm / total_providers * 0.30),
            ("Admin", 0.12, 0.15, 0.38, revenue_mm / total_providers * 0.20),
        ]
    else:
        mix = [
            ("Physician (MD/DO)", 0.22, 0.12, 8.5, revenue_mm / total_providers * 1.8),
            ("Nurse Practitioner", 0.16, 0.16, 2.5, revenue_mm / total_providers * 0.95),
            ("Registered Nurse", 0.28, 0.24, 1.0, revenue_mm / total_providers * 0.45),
            ("Medical Assistant", 0.18, 0.32, 0.42, revenue_mm / total_providers * 0.22),
            ("Admin / Billing", 0.16, 0.20, 0.48, revenue_mm / total_providers * 0.18),
        ]

    rows = []
    for role, pct, churn, repl_cost, rev_per in mix:
        hc = int(total_providers * pct)
        exp_dep = int(hc * churn)
        lost_rev = exp_dep * rev_per * 0.35    # typical revenue leakage before backfill
        severity = _severity_for(churn, role)
        rows.append(ProviderCohort(
            role=role,
            headcount=hc,
            turnover_12mo_pct=round(churn, 3),
            expected_departures=exp_dep,
            replacement_cost_per_dept_mm=round(repl_cost, 2),
            annual_revenue_per_provider_mm=round(rev_per, 2),
            annual_lost_revenue_mm=round(lost_rev, 2),
            severity=severity,
        ))
    return rows


def _build_drivers() -> List[ChurnDriver]:
    return [
        ChurnDriver("Compensation below market", 0.22, "rising", True, "6-12 months"),
        ChurnDriver("Administrative burden / EHR frustration", 0.18, "stable", True, "12-24 months"),
        ChurnDriver("Burnout / workload", 0.16, "rising", True, "6-12 months"),
        ChurnDriver("Culture fit / leadership change", 0.12, "stable", True, "12-18 months"),
        ChurnDriver("Geographic / family relocation", 0.10, "stable", False, "n/a"),
        ChurnDriver("Career advancement opportunity", 0.08, "stable", True, "18-36 months"),
        ChurnDriver("Compensation model change concerns", 0.06, "rising", True, "3-6 months"),
        ChurnDriver("Clinical disagreement / practice style", 0.05, "stable", True, "12 months"),
        ChurnDriver("Retirement", 0.03, "stable", False, "n/a"),
    ]


def _build_at_risk() -> List[AtRiskProvider]:
    import hashlib
    providers = []
    roles = ["Physician (MD)", "Physician (MD)", "Physician (MD)", "NP", "RN Lead", "MD Department Chief",
             "PA", "MD Specialist", "NP Lead", "MD Specialist"]
    for i, role in enumerate(roles):
        h = int(hashlib.md5(f"provider{i}".encode()).hexdigest()[:6], 16)
        tenure = 3 + (h % 12)
        wrvu = 40 + (h % 60)
        rev_contrib = (0.8 + (h % 50) / 100) * (3.5 if "Physician" in role else (1.2 if "NP" in role or "PA" in role else 0.4))
        retention_score = 25 + (h % 70)

        factors_pool = ["comp below market", "burnout", "admin burden", "culture fit", "career growth"]
        factors = ", ".join(factors_pool[(h % 3):(h % 3) + 2])

        providers.append(AtRiskProvider(
            anon_id=f"P-{i + 1:03d}",
            role=role,
            tenure_yrs=round(tenure, 1),
            wrvu_pctile=wrvu,
            revenue_contribution_mm=round(rev_contrib, 2),
            retention_score=retention_score,
            flight_risk_factors=factors,
        ))
    # Sort by retention score ascending (most at-risk first)
    providers.sort(key=lambda p: p.retention_score)
    return providers


def _build_levers(revenue_mm: float, total_providers: int) -> List[RetentionLever]:
    items = [
        ("Market-Based Comp Review + Adjustment", 0.05, revenue_mm * 0.025, 0.08, int(total_providers * 0.35), "high"),
        ("Retention Bonus (2-yr vesting, top 20%)", 0.12, revenue_mm * 0.015, 0.12, int(total_providers * 0.20), "high"),
        ("Equity Participation Plan", 0.08, revenue_mm * 0.010, 0.15, int(total_providers * 0.10), "high"),
        ("EHR / Admin Burden Reduction", 0.45, 0.18, 0.05, total_providers, "medium"),
        ("Burnout Program (coaching, flex)", 0.18, 0.28, 0.06, total_providers, "medium"),
        ("Career Path / Internal Mobility", 0.12, 0.08, 0.04, int(total_providers * 0.6), "medium"),
        ("Physician Leadership Council", 0.05, 0.06, 0.03, total_providers, "low"),
        ("Spouse / Family Support Program", 0.08, 0.04, 0.025, total_providers, "low"),
        ("Scribe / Documentation Support", 0.22, revenue_mm * 0.008, 0.04, int(total_providers * 0.40), "medium"),
        ("Non-Compete / Non-Solicit Tightening", 0.04, 0.01, 0.06, total_providers, "high"),
    ]
    rows = []
    for lever, one_time, annual, retention_lift, addressable, prio in items:
        # Expected retained revenue = addressable × retention_lift × avg revenue per provider
        avg_rev = revenue_mm / total_providers if total_providers else 1
        retained = addressable * retention_lift * avg_rev * 0.35  # lost rev avoided
        total_cost_yr1 = one_time + annual
        roi = retained / total_cost_yr1 if total_cost_yr1 else 0
        rows.append(RetentionLever(
            lever=lever,
            one_time_cost_mm=round(one_time, 2),
            annual_cost_mm=round(annual, 2),
            retention_lift_pp=round(retention_lift, 3),
            addressable_headcount=addressable,
            expected_retained_revenue_mm=round(retained, 2),
            roi_multiple=round(roi, 1),
            priority=prio,
        ))
    return rows


def _build_succession() -> List[SuccessionGap]:
    return [
        SuccessionGap("CEO", 9.0, "developing", "medium", 0.55),
        SuccessionGap("CMO / Chief Medical Officer", 6.5, "no", "critical", 0.15),
        SuccessionGap("CFO", 4.0, "yes", "low", 0.85),
        SuccessionGap("COO", 7.0, "developing", "medium", 0.62),
        SuccessionGap("Dept Chief — Surgery", 14.0, "no", "critical", 0.20),
        SuccessionGap("Dept Chief — Primary Care", 10.0, "developing", "medium", 0.58),
        SuccessionGap("Regional Medical Director", 8.0, "yes", "low", 0.90),
        SuccessionGap("VP Revenue Cycle", 3.5, "yes", "low", 0.88),
        SuccessionGap("VP Clinical Operations", 6.0, "developing", "medium", 0.55),
        SuccessionGap("VP Compliance / CCO", 5.5, "no", "high", 0.25),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_provider_retention(
    sector: str = "Physician Services",
    total_providers: int = 250,
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> ProviderRetentionResult:
    corpus = _load_corpus()

    cohorts = _build_cohorts(sector, revenue_mm, total_providers)
    drivers = _build_drivers()
    at_risk = _build_at_risk()
    levers = _build_levers(revenue_mm, total_providers)
    succession = _build_succession()

    total_expected_dep = sum(c.expected_departures for c in cohorts)
    total_cost_churn = sum(c.expected_departures * c.replacement_cost_per_dept_mm + c.annual_lost_revenue_mm for c in cohorts)
    overall_churn = sum(c.headcount * c.turnover_12mo_pct for c in cohorts) / sum(c.headcount for c in cohorts) if cohorts else 0
    cost_per_dep = total_cost_churn / total_expected_dep * 1000 if total_expected_dep else 0

    total_retention_inv = sum(l.one_time_cost_mm + l.annual_cost_mm for l in levers if l.priority == "high")
    total_savings = sum(l.expected_retained_revenue_mm for l in levers if l.priority in ("high", "medium"))
    ev_impact = total_savings * exit_multiple

    return ProviderRetentionResult(
        total_providers=sum(c.headcount for c in cohorts),
        overall_turnover_pct=round(overall_churn, 4),
        expected_12mo_departures=total_expected_dep,
        cost_of_churn_mm=round(total_cost_churn, 2),
        cost_per_departure_k=round(cost_per_dep, 1),
        cohorts=cohorts,
        drivers=drivers,
        at_risk=at_risk,
        levers=levers,
        succession=succession,
        total_retention_investment_mm=round(total_retention_inv, 2),
        total_savings_from_retention_mm=round(total_savings, 2),
        ev_impact_mm=round(ev_impact, 1),
        corpus_deal_count=len(corpus),
    )
