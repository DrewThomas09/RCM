"""Transition Services Agreement (TSA) Tracker — post-close and pre-exit planning.

Models TSA economics that often get underweighted in diligence:
- TSA cost per function (IT, HR, finance, clinical)
- Duration and extension fees
- Transition milestones and deliverables
- Standalone cost bridge (carve-out companies)
- Integration cost overruns
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TSAService:
    function: str
    baseline_months: int
    extension_months: int
    monthly_cost_k: float
    total_cost_mm: float
    transition_complexity: str       # "low", "medium", "high"
    sparrow_of_termination: str      # "clean", "at_risk", "critical"
    owner: str


@dataclass
class StandaloneCostBridge:
    function: str
    shared_cost_baseline_k: float    # under parent
    standalone_cost_k: float         # post-separation
    delta_k: float
    pct_increase: float
    one_time_stand_up_mm: float


@dataclass
class TSAMilestone:
    milestone: str
    target_date: str                  # ISO
    status: str                       # "on-track", "at-risk", "delayed", "complete"
    days_from_close: int
    dependencies: int


@dataclass
class IntegrationPhase:
    phase: str
    start_month: int
    end_month: int
    focus: str
    cost_mm: float
    headcount_impact: int
    risk_level: str


@dataclass
class TransitionResult:
    scenario: str                     # "Carve-out" or "Bolt-on"
    total_tsa_cost_mm: float
    total_standup_cost_mm: float
    total_integration_cost_mm: float
    services: List[TSAService]
    standalone_bridge: List[StandaloneCostBridge]
    milestones: List[TSAMilestone]
    integration_phases: List[IntegrationPhase]
    tsa_duration_months: int
    tsa_complexity_score: int         # 1-10
    earliest_exit_ready: str          # ISO date
    total_delta_mm: float             # Total standalone cost step-up annual
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 65):
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


def _build_services(revenue_mm: float, scenario: str) -> List[TSAService]:
    """Typical TSA service catalog with sector-appropriate sizing."""
    is_carveout = scenario == "Carve-out"
    services = [
        ("IT Infrastructure & Hosting",
         12 if is_carveout else 6, 6, revenue_mm * 0.055, "high",
         "at_risk" if is_carveout else "clean", "Seller CIO"),
        ("HR / Payroll / Benefits Admin",
         9 if is_carveout else 4, 3, revenue_mm * 0.028, "medium",
         "at_risk" if is_carveout else "clean", "Seller CHRO"),
        ("Finance / Accounting / Tax",
         9 if is_carveout else 3, 3, revenue_mm * 0.035, "medium",
         "clean", "Seller CFO"),
        ("Procurement / AP",
         6, 3, revenue_mm * 0.012, "low", "clean", "Seller Treasury"),
        ("Clinical IT / EHR Hosting",
         18 if is_carveout else 9, 6, revenue_mm * 0.045, "high",
         "critical", "Seller CIO"),
        ("Billing / RCM Platform",
         12 if is_carveout else 6, 6, revenue_mm * 0.042, "high",
         "critical" if is_carveout else "at_risk", "Seller Revenue Ops"),
        ("Data Center / Network",
         12 if is_carveout else 4, 6, revenue_mm * 0.022, "medium",
         "at_risk", "Seller CIO"),
        ("Legal / Contracts Support",
         6, 2, revenue_mm * 0.008, "low", "clean", "Seller GC"),
        ("Compliance / Internal Audit",
         9 if is_carveout else 4, 3, revenue_mm * 0.015, "medium", "clean", "Seller CCO"),
        ("Marketing / Brand / Website",
         3 if is_carveout else 6, 3, revenue_mm * 0.004, "low", "clean", "Seller CMO"),
    ]
    rows = []
    for (func, months, ext, monthly, comp, spar, owner) in services:
        monthly_k = monthly * 1000 / 12    # convert annual % to monthly k
        total = monthly * months / 12
        rows.append(TSAService(
            function=func, baseline_months=months, extension_months=ext,
            monthly_cost_k=round(monthly_k, 1),
            total_cost_mm=round(total, 3),
            transition_complexity=comp,
            sparrow_of_termination=spar,
            owner=owner,
        ))
    return rows


def _build_standalone_bridge(revenue_mm: float, scenario: str) -> List[StandaloneCostBridge]:
    if scenario != "Carve-out":
        return []

    items = [
        ("IT Infrastructure",     revenue_mm * 0.020, revenue_mm * 0.035, revenue_mm * 2.5),
        ("HR / Benefits",         revenue_mm * 0.012, revenue_mm * 0.018, revenue_mm * 0.5),
        ("Finance / Accounting",  revenue_mm * 0.015, revenue_mm * 0.022, revenue_mm * 0.8),
        ("Corporate Overhead",    revenue_mm * 0.012, revenue_mm * 0.018, revenue_mm * 0.3),
        ("D&O Insurance (new)",   0, revenue_mm * 0.003, revenue_mm * 0.1),
        ("External Audit",        revenue_mm * 0.002, revenue_mm * 0.004, revenue_mm * 0.05),
        ("Brand / Marketing",     revenue_mm * 0.005, revenue_mm * 0.008, revenue_mm * 0.4),
    ]
    rows = []
    for func, shared, stand, standup_mm in items:
        stand_k = stand * 1000
        shared_k = shared * 1000
        delta = stand_k - shared_k
        pct = delta / shared_k if shared_k else 1.0
        rows.append(StandaloneCostBridge(
            function=func,
            shared_cost_baseline_k=round(shared_k, 0),
            standalone_cost_k=round(stand_k, 0),
            delta_k=round(delta, 0),
            pct_increase=round(pct, 3),
            one_time_stand_up_mm=round(standup_mm / 1000, 3),
        ))
    return rows


def _build_milestones(scenario: str) -> List[TSAMilestone]:
    is_carveout = scenario == "Carve-out"
    items = [
        ("Close / Day 1 Operating Readiness", "2026-07-01", "on-track", 0, 0),
        ("First Payroll Run Under New Entity", "2026-07-15", "on-track", 14, 2),
        ("AR Cutover (bills sent under new name)", "2026-08-01", "on-track" if is_carveout else "complete", 31, 4),
        ("Bank Account / Treasury Cutover", "2026-08-15", "on-track", 45, 2),
        ("Employee Benefits Cutover", "2026-09-01", "at-risk" if is_carveout else "on-track", 62, 3),
        ("ERP Separation Complete", "2026-11-01", "at-risk" if is_carveout else "on-track", 123, 5),
        ("Clinical IT Separation Complete", "2027-01-01", "at-risk" if is_carveout else "on-track", 184, 7),
        ("RCM Platform Cutover", "2026-12-15", "at-risk", 167, 6),
        ("Website / Brand Refresh", "2026-10-01", "on-track", 92, 1),
        ("Audit Firm Transition", "2027-02-28", "on-track", 242, 2),
        ("TSA Exit (all services)", "2027-07-01", "on-track" if is_carveout else "complete", 365, 12),
        ("Full Standalone Operations", "2027-09-01", "on-track", 427, 15),
    ]
    return [TSAMilestone(
        milestone=m, target_date=d, status=s, days_from_close=days, dependencies=deps,
    ) for m, d, s, days, deps in items]


def _build_integration_phases(revenue_mm: float, scenario: str) -> List[IntegrationPhase]:
    is_carveout = scenario == "Carve-out"
    if is_carveout:
        phases = [
            ("Day 1 Stabilization", 0, 3, "Operational continuity, payroll, vendors", revenue_mm * 0.015, 2, "high"),
            ("Infrastructure Separation", 3, 12, "IT, network, ERP separation", revenue_mm * 0.045, 8, "high"),
            ("Platform Build-out", 6, 18, "Standalone RCM, data warehouse, reporting", revenue_mm * 0.035, 12, "medium"),
            ("Organizational Design", 6, 15, "Hiring standalone HR/Finance/IT leaders", revenue_mm * 0.020, 25, "medium"),
            ("Synergy Capture", 12, 30, "Cost reduction, vendor consolidation", -revenue_mm * 0.025, -5, "low"),
        ]
    else:
        phases = [
            ("Day 1 Integration", 0, 2, "ERP/payroll/brand migration", revenue_mm * 0.008, 1, "medium"),
            ("System Consolidation", 2, 9, "Single ERP/HRIS instance", revenue_mm * 0.015, 3, "medium"),
            ("Org Design & Synergies", 3, 12, "Eliminate duplicate roles, consolidate vendors", revenue_mm * 0.010, -15, "low"),
            ("Revenue Synergy Realization", 6, 24, "Cross-sell, pricing alignment", -revenue_mm * 0.020, 0, "low"),
        ]

    return [IntegrationPhase(
        phase=ph, start_month=s, end_month=e, focus=f,
        cost_mm=round(cost, 2), headcount_impact=hc, risk_level=risk,
    ) for ph, s, e, f, cost, hc, risk in phases]


def _complexity_score(services: List[TSAService]) -> int:
    """1-10 scale."""
    high = sum(1 for s in services if s.transition_complexity == "high")
    critical = sum(1 for s in services if s.sparrow_of_termination == "critical")
    at_risk = sum(1 for s in services if s.sparrow_of_termination == "at_risk")
    return min(10, high * 2 + critical * 3 + at_risk + 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_transition_services(
    revenue_mm: float = 80.0,
    scenario: str = "Carve-out",
) -> TransitionResult:
    corpus = _load_corpus()

    services = _build_services(revenue_mm, scenario)
    bridge = _build_standalone_bridge(revenue_mm, scenario)
    milestones = _build_milestones(scenario)
    phases = _build_integration_phases(revenue_mm, scenario)

    total_tsa = sum(s.total_cost_mm for s in services)
    total_standup = sum(b.one_time_stand_up_mm for b in bridge)
    total_integration = sum(p.cost_mm for p in phases)
    total_delta = sum(b.delta_k for b in bridge) / 1000    # to MM

    max_months = max((s.baseline_months + s.extension_months) for s in services)
    complexity = _complexity_score(services)

    # Earliest exit ready: once all milestones complete
    max_days = max(m.days_from_close for m in milestones)
    earliest = f"2026-07-01 + {max_days}d ≈ 2027-Q{max(1, min(4, max_days // 90))}"

    return TransitionResult(
        scenario=scenario,
        total_tsa_cost_mm=round(total_tsa, 2),
        total_standup_cost_mm=round(total_standup, 2),
        total_integration_cost_mm=round(total_integration, 2),
        services=services,
        standalone_bridge=bridge,
        milestones=milestones,
        integration_phases=phases,
        tsa_duration_months=max_months,
        tsa_complexity_score=complexity,
        earliest_exit_ready=earliest,
        total_delta_mm=round(total_delta, 2),
        corpus_deal_count=len(corpus),
    )
