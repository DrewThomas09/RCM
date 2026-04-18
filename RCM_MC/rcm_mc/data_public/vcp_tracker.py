"""Value Creation Plan (VCP) / 100-Day Plan Tracker.

Tracks post-close value creation initiatives across portfolio:
value levers, 100-day plan execution, KPI scorecards, sponsor
interventions, and EBITDA-bridge attribution.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ValueLever:
    deal: str
    sector: str
    lever_category: str
    initiative: str
    target_ebitda_m: float
    realized_ebitda_m: float
    realization_pct: float
    status: str
    owner: str
    target_completion: str


@dataclass
class HundredDayPlan:
    deal: str
    days_post_close: int
    total_milestones: int
    complete: int
    on_track: int
    at_risk: int
    overdue: int
    completion_pct: float
    plan_status: str


@dataclass
class KPIScorecard:
    deal: str
    revenue_growth_pct: float
    ebitda_growth_pct: float
    margin_expansion_bps: int
    same_store_volume_pct: float
    wc_days_change: int
    ebitda_beat_budget_pct: float
    scorecard: str


@dataclass
class SponsorIntervention:
    deal: str
    intervention_date: str
    intervention_type: str
    severity: str
    rationale: str
    outcome: str


@dataclass
class EBITDABridge:
    lever_category: str
    deals: int
    aggregate_target_m: float
    aggregate_realized_m: float
    realization_pct: float
    contribution_to_growth_pct: float


@dataclass
class TopInitiative:
    initiative: str
    deals_deployed: int
    median_realization_pct: float
    top_quartile_pct: float
    typical_timeline_days: int
    avg_ebitda_lift_pct: float


@dataclass
class VCPResult:
    total_deals: int
    total_target_ebitda_m: float
    total_realized_ebitda_m: float
    realization_pct: float
    on_track_pct: float
    avg_days_post_close: int
    levers: List[ValueLever]
    hundred_day_plans: List[HundredDayPlan]
    kpi_scorecards: List[KPIScorecard]
    interventions: List[SponsorIntervention]
    bridges: List[EBITDABridge]
    top_initiatives: List[TopInitiative]
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


def _build_levers() -> List[ValueLever]:
    return [
        ValueLever("Project Magnolia — MSK", "MSK / Ortho", "Commercial", "Managed-care rate renegotiation", 8.5, 7.2, 0.847, "on track", "Ops Partner", "2026-06-30"),
        ValueLever("Project Magnolia — MSK", "MSK / Ortho", "Operational", "RCM platform migration", 6.0, 2.5, 0.417, "behind", "CFO", "2026-09-30"),
        ValueLever("Project Magnolia — MSK", "MSK / Ortho", "Growth", "2 de novo clinics per year", 3.5, 1.8, 0.514, "on track", "CEO", "2027-12-31"),
        ValueLever("Project Magnolia — MSK", "MSK / Ortho", "M&A", "3 bolt-on acquisitions", 12.0, 8.5, 0.708, "on track", "Sponsor", "2027-12-31"),
        ValueLever("Project Cypress — GI Network", "Gastroenterology", "Commercial", "Site-of-service optimization (ASC shift)", 15.0, 11.5, 0.767, "on track", "COO", "2026-12-31"),
        ValueLever("Project Cypress — GI Network", "Gastroenterology", "Operational", "Labor productivity (MLR)", 8.5, 9.2, 1.082, "complete", "CFO", "2026-06-30"),
        ValueLever("Project Cypress — GI Network", "Gastroenterology", "Growth", "Anesthesia integration", 6.5, 6.8, 1.046, "complete", "CEO", "2026-06-30"),
        ValueLever("Project Cypress — GI Network", "Gastroenterology", "M&A", "5 bolt-on practices", 22.0, 14.5, 0.659, "on track", "Sponsor", "2027-12-31"),
        ValueLever("Project Redwood — Behavioral", "Behavioral Health", "Commercial", "Payer mix optimization", 7.0, 4.2, 0.600, "behind", "CFO", "2026-12-31"),
        ValueLever("Project Redwood — Behavioral", "Behavioral Health", "Operational", "Telehealth scale-up", 5.5, 5.8, 1.055, "complete", "CEO", "2026-06-30"),
        ValueLever("Project Redwood — Behavioral", "Behavioral Health", "Growth", "Medicaid ACO participation", 4.0, 2.8, 0.700, "on track", "COO", "2026-12-31"),
        ValueLever("Project Laurel — Derma", "Dermatology", "Commercial", "Cosmetic/aesthetic upsell", 5.5, 4.8, 0.873, "on track", "CMO", "2026-12-31"),
        ValueLever("Project Laurel — Derma", "Dermatology", "Operational", "Central support services", 3.5, 3.2, 0.914, "on track", "COO", "2026-09-30"),
        ValueLever("Project Laurel — Derma", "Dermatology", "Growth", "4 bolt-on clinics", 8.5, 5.5, 0.647, "on track", "Sponsor", "2027-06-30"),
        ValueLever("Project Cedar — Cardiology", "Cardiology", "Commercial", "OBL/ASC conversion", 11.0, 9.5, 0.864, "on track", "COO", "2026-12-31"),
        ValueLever("Project Cedar — Cardiology", "Cardiology", "Operational", "Cath lab utilization", 6.5, 6.1, 0.938, "on track", "CMO", "2026-09-30"),
        ValueLever("Project Cedar — Cardiology", "Cardiology", "Growth", "Structural heart program launch", 4.5, 1.8, 0.400, "behind", "CMO", "2027-03-31"),
        ValueLever("Project Willow — Fertility", "Fertility / IVF", "Commercial", "Employer direct contracting", 7.0, 3.5, 0.500, "on track", "CCO", "2026-12-31"),
        ValueLever("Project Willow — Fertility", "Fertility / IVF", "Growth", "4 new market entries", 12.0, 6.5, 0.542, "behind", "CEO", "2027-06-30"),
        ValueLever("Project Willow — Fertility", "Fertility / IVF", "Operational", "Lab consolidation", 4.0, 3.8, 0.950, "complete", "COO", "2026-06-30"),
        ValueLever("Project Spruce — Radiology", "Radiology", "Operational", "Teleradiology centralization", 5.5, 4.8, 0.873, "on track", "CMO", "2026-09-30"),
        ValueLever("Project Spruce — Radiology", "Radiology", "Commercial", "Hospital-direct contracts", 4.0, 3.2, 0.800, "on track", "CCO", "2026-12-31"),
        ValueLever("Project Spruce — Radiology", "Radiology", "Growth", "AI-enabled service lines", 6.0, 2.5, 0.417, "behind", "CTO", "2027-06-30"),
        ValueLever("Project Aspen — Eye Care", "Eye Care", "Commercial", "LASIK/ASC expansion", 8.5, 7.2, 0.847, "on track", "CMO", "2026-12-31"),
        ValueLever("Project Aspen — Eye Care", "Eye Care", "Operational", "OD/MD integration", 5.0, 4.5, 0.900, "on track", "COO", "2026-09-30"),
        ValueLever("Project Aspen — Eye Care", "Eye Care", "M&A", "3 bolt-on acquisitions", 6.5, 4.0, 0.615, "on track", "Sponsor", "2027-12-31"),
    ]


def _build_hundred_day() -> List[HundredDayPlan]:
    return [
        HundredDayPlan("Project Magnolia — MSK", 185, 38, 32, 4, 2, 0, 0.842, "green"),
        HundredDayPlan("Project Cypress — GI Network", 155, 42, 38, 3, 1, 0, 0.905, "green"),
        HundredDayPlan("Project Redwood — Behavioral", 310, 35, 28, 4, 2, 1, 0.800, "amber"),
        HundredDayPlan("Project Laurel — Derma", 230, 32, 28, 3, 1, 0, 0.875, "green"),
        HundredDayPlan("Project Cedar — Cardiology", 275, 40, 33, 4, 2, 1, 0.825, "amber"),
        HundredDayPlan("Project Willow — Fertility", 120, 36, 24, 8, 3, 1, 0.667, "amber"),
        HundredDayPlan("Project Spruce — Radiology", 245, 32, 26, 4, 1, 1, 0.813, "green"),
        HundredDayPlan("Project Aspen — Eye Care", 95, 34, 25, 7, 2, 0, 0.735, "green"),
        HundredDayPlan("Project Maple — Urology", 195, 28, 24, 3, 1, 0, 0.857, "green"),
        HundredDayPlan("Project Ash — Infusion", 65, 40, 20, 14, 5, 1, 0.500, "amber"),
        HundredDayPlan("Project Fir — Lab / Pathology", 215, 38, 34, 3, 1, 0, 0.895, "green"),
        HundredDayPlan("Project Oak — RCM SaaS", 265, 30, 27, 2, 1, 0, 0.900, "green"),
    ]


def _build_kpis() -> List[KPIScorecard]:
    return [
        KPIScorecard("Project Magnolia — MSK", 0.128, 0.175, 180, 0.085, -8, 1.045, "beat"),
        KPIScorecard("Project Cypress — GI Network", 0.155, 0.225, 240, 0.095, -12, 1.082, "beat"),
        KPIScorecard("Project Redwood — Behavioral", 0.088, 0.095, 80, 0.045, -5, 0.932, "miss"),
        KPIScorecard("Project Laurel — Derma", 0.165, 0.185, 160, 0.105, -6, 1.038, "beat"),
        KPIScorecard("Project Cedar — Cardiology", 0.105, 0.135, 130, 0.065, -9, 1.018, "beat"),
        KPIScorecard("Project Willow — Fertility", 0.175, 0.145, 90, 0.115, -3, 0.948, "miss"),
        KPIScorecard("Project Spruce — Radiology", 0.095, 0.118, 110, 0.055, -7, 1.022, "beat"),
        KPIScorecard("Project Aspen — Eye Care", 0.135, 0.155, 150, 0.075, -4, 1.012, "beat"),
        KPIScorecard("Project Maple — Urology", 0.102, 0.128, 120, 0.068, -6, 1.028, "beat"),
        KPIScorecard("Project Ash — Infusion", 0.215, 0.195, 85, 0.125, -2, 0.958, "miss"),
        KPIScorecard("Project Fir — Lab / Pathology", 0.115, 0.145, 145, 0.065, -11, 1.058, "beat"),
        KPIScorecard("Project Oak — RCM SaaS", 0.185, 0.225, 220, 0.155, -9, 1.095, "beat"),
    ]


def _build_interventions() -> List[SponsorIntervention]:
    return [
        SponsorIntervention("Project Redwood — Behavioral", "2025-11-15", "CEO replacement", "critical",
                             "EBITDA miss + culture concerns", "new CEO Q1 2026, turning"),
        SponsorIntervention("Project Willow — Fertility", "2026-01-20", "CFO replacement", "high",
                             "Reporting gaps + working capital issues", "new CFO 30-day, stabilizing"),
        SponsorIntervention("Project Cedar — Cardiology", "2025-09-10", "Board composition change", "medium",
                             "Add 2 independent clinical directors", "improved board fabric"),
        SponsorIntervention("Project Ash — Infusion", "2026-02-05", "CFO replacement", "critical",
                             "Budget miss + cash management", "new CFO installed"),
        SponsorIntervention("Project Magnolia — MSK", "2025-12-08", "Strategy pivot", "medium",
                             "RCM migration delayed 6mo — resource augment", "on track post-pivot"),
        SponsorIntervention("Project Cypress — GI Network", "2025-08-15", "M&A accelerated", "low",
                             "2 quick bolt-ons to hit synergy target", "synergies delivered ahead"),
        SponsorIntervention("Project Laurel — Derma", "2025-11-02", "Capital injection", "medium",
                             "$12M follow-on for 3 bolt-ons", "transactions closed"),
        SponsorIntervention("Project Redwood — Behavioral", "2026-03-20", "Strategic review", "high",
                             "Path-to-exit evaluation given market dynamics", "in progress"),
    ]


def _build_bridges(levers: List[ValueLever]) -> List[EBITDABridge]:
    buckets: dict = {}
    total_realized = sum(l.realized_ebitda_m for l in levers)
    for l in levers:
        b = buckets.setdefault(l.lever_category, {"deals": set(), "target": 0.0, "realized": 0.0})
        b["deals"].add(l.deal)
        b["target"] += l.target_ebitda_m
        b["realized"] += l.realized_ebitda_m
    rows = []
    for cat, d in buckets.items():
        rp = d["realized"] / d["target"] if d["target"] > 0 else 0
        contrib = d["realized"] / total_realized if total_realized > 0 else 0
        rows.append(EBITDABridge(
            lever_category=cat, deals=len(d["deals"]),
            aggregate_target_m=round(d["target"], 1),
            aggregate_realized_m=round(d["realized"], 1),
            realization_pct=round(rp, 4),
            contribution_to_growth_pct=round(contrib, 4),
        ))
    return sorted(rows, key=lambda x: x.aggregate_realized_m, reverse=True)


def _build_top_initiatives() -> List[TopInitiative]:
    return [
        TopInitiative("Managed-care rate renegotiation", 14, 0.840, 0.925, 240, 0.068),
        TopInitiative("RCM platform migration", 18, 0.620, 0.810, 365, 0.055),
        TopInitiative("Bolt-on M&A (≤3 deals)", 22, 0.780, 0.895, 540, 0.145),
        TopInitiative("Site-of-service shift (ASC)", 8, 0.820, 0.945, 300, 0.088),
        TopInitiative("Labor productivity / MLR", 16, 0.880, 0.965, 180, 0.042),
        TopInitiative("Telehealth scale-up", 12, 0.720, 0.890, 240, 0.035),
        TopInitiative("Payer mix optimization", 15, 0.700, 0.845, 300, 0.048),
        TopInitiative("De novo clinic expansion", 10, 0.680, 0.845, 540, 0.072),
        TopInitiative("Clinical service-line addition", 7, 0.650, 0.825, 420, 0.065),
        TopInitiative("Central support / back-office consolidation", 19, 0.890, 0.960, 210, 0.038),
        TopInitiative("Physician productivity / RVU alignment", 11, 0.770, 0.870, 210, 0.045),
        TopInitiative("AI / digital workflow automation", 6, 0.580, 0.790, 390, 0.032),
    ]


def compute_vcp_tracker() -> VCPResult:
    corpus = _load_corpus()
    levers = _build_levers()
    hundred_day = _build_hundred_day()
    kpis = _build_kpis()
    interventions = _build_interventions()
    bridges = _build_bridges(levers)
    top_init = _build_top_initiatives()

    deals = {l.deal for l in levers}
    total_target = sum(l.target_ebitda_m for l in levers)
    total_realized = sum(l.realized_ebitda_m for l in levers)
    realization = total_realized / total_target if total_target > 0 else 0
    on_track = sum(1 for l in levers if l.status in ("on track", "complete"))
    on_track_pct = on_track / len(levers) if levers else 0
    avg_days = sum(h.days_post_close for h in hundred_day) / len(hundred_day) if hundred_day else 0

    return VCPResult(
        total_deals=len(deals),
        total_target_ebitda_m=round(total_target, 1),
        total_realized_ebitda_m=round(total_realized, 1),
        realization_pct=round(realization, 4),
        on_track_pct=round(on_track_pct, 4),
        avg_days_post_close=int(round(avg_days)),
        levers=levers,
        hundred_day_plans=hundred_day,
        kpi_scorecards=kpis,
        interventions=interventions,
        bridges=bridges,
        top_initiatives=top_init,
        corpus_deal_count=len(corpus),
    )
