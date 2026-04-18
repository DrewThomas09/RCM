"""Post-Merger Integration Playbook.

Tracks integration progress for a specific M&A transaction:
workstream milestones, synergy capture vs plan, Day 1/Day 100/12-month
achievement, integration cost burn, and key risks.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class Workstream:
    workstream: str
    owner: str
    total_milestones: int
    completed_milestones: int
    on_track_pct: float
    status: str
    budget_mm: float
    spent_mm: float
    next_milestone: str
    due_date: str


@dataclass
class SynergyCapture:
    synergy_category: str
    annualized_target_mm: float
    run_rate_achieved_mm: float
    pct_of_target: float
    timing_status: str
    risk_level: str


@dataclass
class DayXMilestone:
    horizon: str
    target_milestones: int
    completed: int
    in_progress: int
    slipped: int
    completion_pct: float


@dataclass
class IntegrationRisk:
    risk_area: str
    description: str
    probability: str
    impact_mm: float
    mitigation_status: str
    owner: str


@dataclass
class TMSCheckpoint:
    function: str
    pre_integration_cost_mm: float
    post_integration_cost_mm: float
    actual_savings_mm: float
    targeted_savings_mm: float
    variance_pct: float


@dataclass
class PMIResult:
    target_acquisition: str
    close_date: str
    days_since_close: int
    overall_progress_pct: float
    total_synergies_target_mm: float
    run_rate_synergies_mm: float
    integration_spend_mm: float
    integration_budget_mm: float
    workstreams: List[Workstream]
    synergies: List[SynergyCapture]
    milestones: List[DayXMilestone]
    risks: List[IntegrationRisk]
    tms: List[TMSCheckpoint]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 105):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_workstreams() -> List[Workstream]:
    items = [
        ("Financial Reporting / Close", "CFO Team", 28, 22, 0.79, "on track", 1.85, 1.42, "Month-12 consolidated close process", "2026-06-15"),
        ("IT / EHR Unification", "CIO Team", 62, 28, 0.45, "at risk", 8.5, 5.85, "Epic instance single-tenant migration", "2026-08-30"),
        ("RCM / Billing Consolidation", "SVP Revenue Cycle", 42, 34, 0.81, "on track", 3.2, 2.45, "Single-tenant Waystar cutover", "2026-05-20"),
        ("Payer Contract Renegotiation", "VP Managed Care", 18, 8, 0.44, "lagging", 0.85, 0.42, "BCBS consolidated contract LOI", "2026-07-15"),
        ("Compliance Program Harmonization", "Chief Compliance Officer", 35, 32, 0.91, "on track", 1.2, 1.05, "HIPAA risk assessment completion", "2026-05-01"),
        ("Clinical Ops Standardization", "CMO", 55, 42, 0.76, "on track", 2.8, 2.15, "Standard order set rollout", "2026-06-30"),
        ("HR / Benefits Integration", "CHRO", 32, 28, 0.88, "on track", 1.4, 1.18, "Unified benefits plan active", "2026-04-30"),
        ("Real Estate / Facilities", "VP Real Estate", 22, 18, 0.82, "on track", 0.75, 0.58, "Lease consolidation (3 markets)", "2026-07-01"),
        ("Procurement / Supply Chain", "VP Supply Chain", 28, 22, 0.79, "on track", 1.1, 0.85, "GPO contract unification", "2026-05-15"),
        ("Marketing / Brand", "CMO (Mkt)", 18, 12, 0.67, "on track", 0.95, 0.62, "Unified brand launch", "2026-06-01"),
        ("Data & Analytics", "Chief Data Officer", 38, 18, 0.47, "at risk", 2.4, 1.28, "Single data warehouse launch", "2026-09-30"),
        ("Legal / Regulatory", "General Counsel", 25, 23, 0.92, "on track", 1.85, 1.65, "CMS notification of ownership change", "2026-04-20"),
    ]
    rows = []
    for w, o, tot, comp, ot, st, bud, spent, next_m, due in items:
        rows.append(Workstream(
            workstream=w, owner=o,
            total_milestones=tot, completed_milestones=comp,
            on_track_pct=ot, status=st,
            budget_mm=bud, spent_mm=spent,
            next_milestone=next_m, due_date=due,
        ))
    return rows


def _build_synergies() -> List[SynergyCapture]:
    return [
        SynergyCapture("Back Office Consolidation (HR/Finance)", 4.2, 3.18, 0.76, "ahead", "low"),
        SynergyCapture("RCM / Billing Efficiency", 6.5, 4.55, 0.70, "on track", "low"),
        SynergyCapture("Payer Rate Improvement", 8.8, 2.45, 0.28, "behind", "high"),
        SynergyCapture("Supply Chain / GPO Savings", 3.5, 2.85, 0.81, "on track", "low"),
        SynergyCapture("Malpractice Insurance Pooling", 1.8, 1.62, 0.90, "ahead", "low"),
        SynergyCapture("IT System Unification", 2.5, 0.85, 0.34, "behind", "medium"),
        SynergyCapture("Clinical Ops Standardization", 4.8, 2.95, 0.61, "on track", "medium"),
        SynergyCapture("Cross-Sell Revenue Synergy", 3.2, 0.95, 0.30, "behind", "high"),
        SynergyCapture("Facilities / Lease Consolidation", 1.5, 1.32, 0.88, "ahead", "low"),
        SynergyCapture("Compliance / Legal Efficiency", 1.2, 0.98, 0.82, "on track", "low"),
    ]


def _build_milestones() -> List[DayXMilestone]:
    return [
        DayXMilestone("Day 1 (Close)", 38, 38, 0, 0, 1.00),
        DayXMilestone("Day 30", 45, 44, 1, 0, 0.98),
        DayXMilestone("Day 60", 58, 55, 2, 1, 0.95),
        DayXMilestone("Day 100", 72, 65, 5, 2, 0.90),
        DayXMilestone("Day 180", 118, 98, 15, 5, 0.83),
        DayXMilestone("Day 270", 185, 148, 28, 9, 0.80),
        DayXMilestone("Day 365 (Year 1)", 258, 205, 42, 11, 0.79),
        DayXMilestone("Day 540 (18-mo Plan)", 325, 215, 85, 25, 0.66),
    ]


def _build_risks() -> List[IntegrationRisk]:
    return [
        IntegrationRisk("Clinician Retention Post-Close", "MD attrition running 14% vs 9% baseline", "medium", 3.8, "in progress", "CMO"),
        IntegrationRisk("EHR Migration Delay", "Epic single-tenant migration 3 months behind", "high", 5.2, "escalated", "CIO"),
        IntegrationRisk("Payer Contract Transition", "BCBS has not ratified consolidated contract", "high", 8.5, "active negotiation", "VP Managed Care"),
        IntegrationRisk("Cross-Sell Synergy Miss", "Cross-sell running 30% of target", "high", 2.2, "remediation plan", "CRO"),
        IntegrationRisk("Compliance Program Gaps", "Legacy acquired site missed 2 DEA recerts", "medium", 1.5, "closed", "CCO"),
        IntegrationRisk("Data Integration Complexity", "2 legacy data warehouses not yet merged", "medium", 1.8, "in progress", "CDO"),
        IntegrationRisk("Cultural Integration", "Employee NPS down 12pp at acquired co", "medium", 0.0, "active", "CHRO"),
        IntegrationRisk("Vendor Contract Cleanup", "18 duplicative SaaS subscriptions not yet cut", "low", 0.85, "in progress", "Procurement"),
    ]


def _build_tms() -> List[TMSCheckpoint]:
    return [
        TMSCheckpoint("Finance & Accounting", 8.5, 5.8, 2.7, 3.1, -0.129),
        TMSCheckpoint("Human Resources", 4.2, 3.1, 1.1, 1.2, -0.083),
        TMSCheckpoint("IT / Tech Ops", 12.5, 10.8, 1.7, 2.5, -0.32),
        TMSCheckpoint("Legal / Compliance", 3.2, 2.5, 0.7, 0.8, -0.125),
        TMSCheckpoint("Revenue Cycle", 15.8, 10.2, 5.6, 6.5, -0.138),
        TMSCheckpoint("Marketing", 2.8, 1.9, 0.9, 1.0, -0.10),
        TMSCheckpoint("Procurement", 3.5, 2.1, 1.4, 1.5, -0.067),
        TMSCheckpoint("Facilities", 2.2, 1.5, 0.7, 0.8, -0.125),
    ]


def compute_pmi_playbook() -> PMIResult:
    corpus = _load_corpus()

    workstreams = _build_workstreams()
    synergies = _build_synergies()
    milestones = _build_milestones()
    risks = _build_risks()
    tms = _build_tms()

    total_milestones = sum(w.total_milestones for w in workstreams)
    completed = sum(w.completed_milestones for w in workstreams)
    overall = completed / total_milestones if total_milestones else 0

    total_synergy_target = sum(s.annualized_target_mm for s in synergies)
    run_rate = sum(s.run_rate_achieved_mm for s in synergies)

    budget = sum(w.budget_mm for w in workstreams)
    spent = sum(w.spent_mm for w in workstreams)

    return PMIResult(
        target_acquisition="Project Beacon (Q2 2025 close)",
        close_date="2025-06-30",
        days_since_close=275,
        overall_progress_pct=round(overall, 4),
        total_synergies_target_mm=round(total_synergy_target, 2),
        run_rate_synergies_mm=round(run_rate, 2),
        integration_spend_mm=round(spent, 2),
        integration_budget_mm=round(budget, 2),
        workstreams=workstreams,
        synergies=synergies,
        milestones=milestones,
        risks=risks,
        tms=tms,
        corpus_deal_count=len(corpus),
    )
