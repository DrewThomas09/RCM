"""Technology Stack Analyzer — EHR, RCM, clinical systems, cybersecurity.

Evaluates current IT stack and modernization opportunities:
- EHR fragmentation (single vs multiple instances)
- RCM platform vintage and vendor concentration
- Clinical systems (imaging, lab, e-Rx, telehealth)
- Cybersecurity posture (SOC 2, HITRUST, insurance)
- Tech debt and modernization roadmap
- Annual IT spend vs revenue benchmark
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# EHR vendor benchmarks
# ---------------------------------------------------------------------------

_EHR_VENDORS = {
    "Epic":                  {"modernness": 95, "cost_per_provider_k": 62, "interop_score": 85},
    "Cerner (Oracle Health)":{"modernness": 82, "cost_per_provider_k": 55, "interop_score": 78},
    "eClinicalWorks":        {"modernness": 72, "cost_per_provider_k": 18, "interop_score": 68},
    "athenahealth":          {"modernness": 85, "cost_per_provider_k": 25, "interop_score": 82},
    "NextGen":               {"modernness": 68, "cost_per_provider_k": 22, "interop_score": 65},
    "Greenway":              {"modernness": 65, "cost_per_provider_k": 16, "interop_score": 62},
    "Allscripts":            {"modernness": 58, "cost_per_provider_k": 19, "interop_score": 60},
    "AdvancedMD":            {"modernness": 70, "cost_per_provider_k": 12, "interop_score": 68},
    "DrChrono":              {"modernness": 74, "cost_per_provider_k": 11, "interop_score": 70},
    "Practice Fusion":       {"modernness": 55, "cost_per_provider_k": 5, "interop_score": 55},
    "Meditech":              {"modernness": 62, "cost_per_provider_k": 38, "interop_score": 65},
    "Legacy / Proprietary":  {"modernness": 35, "cost_per_provider_k": 0, "interop_score": 40},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SystemRow:
    system_type: str              # "EHR", "RCM", "Practice Mgmt", "Clinical Dict.", etc.
    vendor: str
    sites_using: int
    version_vintage: str
    annual_cost_mm: float
    modernness_score: int         # 0-100
    interop_score: int
    status: str                   # "modern", "stable", "aging", "legacy"


@dataclass
class ModernizationProject:
    project: str
    scope: str
    one_time_cost_mm: float
    annual_run_rate_delta_mm: float
    timeline_months: int
    risk: str
    moic_lift_pct: float
    priority: str


@dataclass
class CyberMetric:
    metric: str
    current_state: str
    target_state: str
    gap: str
    remediation_cost_mm: float
    urgency: str


@dataclass
class ITSpendBucket:
    category: str
    annual_spend_mm: float
    pct_of_revenue: float
    benchmark_pct: float
    variance: str


@dataclass
class TechStackResult:
    sector: str
    ehr_vendor: str
    ehr_fragmentation_score: int
    total_it_spend_mm: float
    it_spend_pct_revenue: float
    modernness_composite: int
    cyber_posture_score: int
    systems: List[SystemRow]
    modernization_projects: List[ModernizationProject]
    cyber_metrics: List[CyberMetric]
    spend_buckets: List[ITSpendBucket]
    total_modernization_cost_mm: float
    total_ev_uplift_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 69):
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


def _status_for_modernness(score: int) -> str:
    if score >= 85: return "modern"
    if score >= 70: return "stable"
    if score >= 50: return "aging"
    return "legacy"


def _build_systems(sector: str, revenue_mm: float, n_providers: int) -> List[SystemRow]:
    ehr = "eClinicalWorks" if revenue_mm < 100 else ("athenahealth" if revenue_mm < 300 else "Epic")
    ehr_bench = _EHR_VENDORS[ehr]

    return [
        SystemRow(
            system_type="EHR (Primary)", vendor=ehr,
            sites_using=int(revenue_mm / 4), version_vintage="v2021 / 2022",
            annual_cost_mm=round(n_providers * ehr_bench["cost_per_provider_k"] / 1000, 2),
            modernness_score=ehr_bench["modernness"],
            interop_score=ehr_bench["interop_score"],
            status=_status_for_modernness(ehr_bench["modernness"]),
        ),
        SystemRow(
            system_type="EHR (Secondary - acquired site)", vendor="Legacy / Proprietary",
            sites_using=3, version_vintage="v2014",
            annual_cost_mm=0.08,
            modernness_score=35, interop_score=40,
            status="legacy",
        ),
        SystemRow(
            system_type="RCM Platform", vendor="R1 RCM" if revenue_mm >= 200 else "Change Healthcare",
            sites_using=int(revenue_mm / 3),
            version_vintage="v2023",
            annual_cost_mm=round(revenue_mm * 0.018, 2),
            modernness_score=78, interop_score=72,
            status="stable",
        ),
        SystemRow(
            system_type="Practice Management", vendor="Kareo / Tebra",
            sites_using=int(revenue_mm / 4),
            version_vintage="v2022",
            annual_cost_mm=round(revenue_mm * 0.008, 2),
            modernness_score=72, interop_score=68,
            status="stable",
        ),
        SystemRow(
            system_type="Clinical Decision Support", vendor="UpToDate / Elsevier",
            sites_using=int(revenue_mm / 5),
            version_vintage="current",
            annual_cost_mm=round(revenue_mm * 0.004, 2),
            modernness_score=88, interop_score=80,
            status="modern",
        ),
        SystemRow(
            system_type="e-Prescribing", vendor="Surescripts",
            sites_using=int(revenue_mm / 4),
            version_vintage="current",
            annual_cost_mm=round(revenue_mm * 0.003, 2),
            modernness_score=90, interop_score=92,
            status="modern",
        ),
        SystemRow(
            system_type="Telehealth", vendor="Zoom Healthcare",
            sites_using=int(revenue_mm / 5),
            version_vintage="current",
            annual_cost_mm=round(revenue_mm * 0.005, 2),
            modernness_score=85, interop_score=75,
            status="modern",
        ),
        SystemRow(
            system_type="Lab Integration", vendor="Quest / LabCorp API",
            sites_using=int(revenue_mm / 4),
            version_vintage="v2021",
            annual_cost_mm=round(revenue_mm * 0.004, 2),
            modernness_score=70, interop_score=68,
            status="stable",
        ),
        SystemRow(
            system_type="Imaging / PACS",
            vendor="Sectra" if "Imaging" in sector or "Radiology" in sector else "Internal HCO",
            sites_using=int(revenue_mm / 10),
            version_vintage="v2019",
            annual_cost_mm=round(revenue_mm * 0.012, 2),
            modernness_score=65, interop_score=60,
            status="aging",
        ),
        SystemRow(
            system_type="Data Warehouse / Analytics",
            vendor="Snowflake + Tableau",
            sites_using=1, version_vintage="current",
            annual_cost_mm=round(revenue_mm * 0.008, 2),
            modernness_score=92, interop_score=88,
            status="modern",
        ),
        SystemRow(
            system_type="Security / SIEM", vendor="CrowdStrike / Splunk",
            sites_using=1, version_vintage="current",
            annual_cost_mm=round(revenue_mm * 0.006, 2),
            modernness_score=88, interop_score=80,
            status="modern",
        ),
        SystemRow(
            system_type="ERP / Finance", vendor="NetSuite / Workday",
            sites_using=1, version_vintage="v2023",
            annual_cost_mm=round(revenue_mm * 0.005, 2),
            modernness_score=85, interop_score=75,
            status="modern",
        ),
    ]


def _build_modernization(systems: List[SystemRow], revenue_mm: float, exit_multiple: float) -> List[ModernizationProject]:
    return [
        ModernizationProject(
            project="EHR Consolidation to Single Instance",
            scope="Retire 3 legacy EHR instances at acquired sites",
            one_time_cost_mm=round(revenue_mm * 0.035, 2),
            annual_run_rate_delta_mm=-round(revenue_mm * 0.012, 2),    # savings
            timeline_months=18,
            risk="high",
            moic_lift_pct=0.08,
            priority="high",
        ),
        ModernizationProject(
            project="RCM Platform Upgrade",
            scope="Move to cloud-native RCM, automate denials",
            one_time_cost_mm=round(revenue_mm * 0.022, 2),
            annual_run_rate_delta_mm=-round(revenue_mm * 0.018, 2),
            timeline_months=12,
            risk="medium",
            moic_lift_pct=0.06,
            priority="high",
        ),
        ModernizationProject(
            project="PACS / Imaging Modernization",
            scope="Retire on-prem, move to cloud PACS",
            one_time_cost_mm=round(revenue_mm * 0.025, 2),
            annual_run_rate_delta_mm=-round(revenue_mm * 0.006, 2),
            timeline_months=15,
            risk="medium",
            moic_lift_pct=0.02,
            priority="medium",
        ),
        ModernizationProject(
            project="Data Warehouse / BI Platform",
            scope="Build unified analytics stack",
            one_time_cost_mm=round(revenue_mm * 0.012, 2),
            annual_run_rate_delta_mm=round(revenue_mm * 0.002, 2),
            timeline_months=9,
            risk="low",
            moic_lift_pct=0.03,
            priority="medium",
        ),
        ModernizationProject(
            project="Cybersecurity Hardening (SOC 2 Type II)",
            scope="Formalize SOC 2 certification + HITRUST",
            one_time_cost_mm=round(revenue_mm * 0.008, 2),
            annual_run_rate_delta_mm=round(revenue_mm * 0.004, 2),    # ongoing cost
            timeline_months=12,
            risk="medium",
            moic_lift_pct=0.02,
            priority="high",
        ),
        ModernizationProject(
            project="Telehealth Platform Integration",
            scope="Native EHR telehealth, reduce 3rd-party vendor",
            one_time_cost_mm=round(revenue_mm * 0.005, 2),
            annual_run_rate_delta_mm=-round(revenue_mm * 0.003, 2),
            timeline_months=6,
            risk="low",
            moic_lift_pct=0.01,
            priority="low",
        ),
    ]


def _build_cyber_metrics() -> List[CyberMetric]:
    return [
        CyberMetric("SOC 2 Type II", "Type I only", "Type II certified",
                    "Need 12-month audit period", 0.25, "high"),
        CyberMetric("HIPAA Security Rule", "Compliant (last audit 18mo ago)", "Annual SRA",
                    "Gap: SRA outdated", 0.10, "medium"),
        CyberMetric("HITRUST CSF r2", "Not certified", "HITRUST r2 certified",
                    "Missing framework alignment", 0.35, "high"),
        CyberMetric("Penetration Testing", "Annual (vendor)", "Quarterly",
                    "Frequency gap", 0.08, "medium"),
        CyberMetric("Cyber Insurance Coverage", "$15M tower", "$50M tower",
                    "Underinsured for current risk profile", 0.22, "high"),
        CyberMetric("Endpoint Detection & Response", "CrowdStrike deployed", "Full coverage + MDR",
                    "No 24/7 managed detection", 0.15, "medium"),
        CyberMetric("Data Backup / DR", "Daily backup, 48-hr RTO", "Hourly + 4-hr RTO",
                    "Ransomware exposure", 0.18, "high"),
        CyberMetric("Identity & Access Management", "Basic AD + MFA", "Zero trust, privileged access mgmt",
                    "Privileged credentials exposure", 0.12, "medium"),
        CyberMetric("Vendor Risk Management", "Ad hoc reviews", "Formal TPRM program",
                    "Supply chain risk", 0.06, "low"),
        CyberMetric("Incident Response Plan", "Plan exists, not tested", "Tabletop quarterly",
                    "Playbook gap", 0.04, "medium"),
    ]


def _build_spend_buckets(systems: List[SystemRow], revenue_mm: float) -> List[ITSpendBucket]:
    total_systems = sum(s.annual_cost_mm for s in systems)
    # Allocate to canonical buckets
    infra_cost = total_systems * 0.25
    app_cost = total_systems * 0.55
    personnel = revenue_mm * 0.012   # IT staff
    cyber = revenue_mm * 0.006
    other = revenue_mm * 0.004

    buckets = [
        ("Applications (EHR, RCM, etc.)", app_cost, 0.035),
        ("Infrastructure (Cloud, Network)", infra_cost, 0.010),
        ("Personnel (IT Staff, Vendors)", personnel, 0.014),
        ("Cybersecurity", cyber, 0.008),
        ("Other (Licenses, Consulting)", other, 0.005),
    ]
    rows = []
    for cat, spend, bench in buckets:
        pct = spend / revenue_mm if revenue_mm else 0
        variance = "above" if pct > bench * 1.15 else ("benchmark" if pct >= bench * 0.85 else "below")
        rows.append(ITSpendBucket(
            category=cat,
            annual_spend_mm=round(spend, 2),
            pct_of_revenue=round(pct, 4),
            benchmark_pct=round(bench, 4),
            variance=variance,
        ))
    return rows


def _composite_modernness(systems: List[SystemRow]) -> int:
    if not systems:
        return 50
    weights = sum(s.annual_cost_mm for s in systems) or 1
    return int(sum(s.modernness_score * s.annual_cost_mm for s in systems) / weights)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_tech_stack(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    n_providers: int = 45,
    exit_multiple: float = 11.0,
) -> TechStackResult:
    corpus = _load_corpus()

    systems = _build_systems(sector, revenue_mm, n_providers)
    total_it = sum(s.annual_cost_mm for s in systems)
    it_pct = total_it / revenue_mm if revenue_mm else 0

    ehr_system = next((s for s in systems if "EHR (Primary)" in s.system_type), None)
    ehr_vendor = ehr_system.vendor if ehr_system else "Unknown"

    # Fragmentation: count distinct EHR vendors
    ehr_vendors = {s.vendor for s in systems if "EHR" in s.system_type}
    fragmentation = min(100, len(ehr_vendors) * 40 + 10)

    projects = _build_modernization(systems, revenue_mm, exit_multiple)
    cyber = _build_cyber_metrics()
    buckets = _build_spend_buckets(systems, revenue_mm)

    total_mod_cost = sum(p.one_time_cost_mm for p in projects)
    total_ev_uplift = sum(p.moic_lift_pct * revenue_mm * 0.18 * exit_multiple for p in projects)

    modernness = _composite_modernness(systems)
    # Cyber score = 100 - (sum of high-urgency gaps × 10)
    cyber_gaps = sum(1 for c in cyber if c.urgency == "high")
    cyber_score = max(0, 100 - cyber_gaps * 12)

    return TechStackResult(
        sector=sector,
        ehr_vendor=ehr_vendor,
        ehr_fragmentation_score=fragmentation,
        total_it_spend_mm=round(total_it, 2),
        it_spend_pct_revenue=round(it_pct, 4),
        modernness_composite=modernness,
        cyber_posture_score=cyber_score,
        systems=systems,
        modernization_projects=projects,
        cyber_metrics=cyber,
        spend_buckets=buckets,
        total_modernization_cost_mm=round(total_mod_cost, 2),
        total_ev_uplift_mm=round(total_ev_uplift, 1),
        corpus_deal_count=len(corpus),
    )
