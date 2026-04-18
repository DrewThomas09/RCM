"""Capex Planning / Capital Budget Tracker.

Tracks portfolio capital budget and approved / pipeline capex projects:
maintenance, growth, IT/integration, de novo, ASC build-out — with ROI,
payback, and governance oversight.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CapexProject:
    project_id: str
    deal: str
    category: str
    description: str
    budget_m: float
    spent_m: float
    percent_complete: float
    planned_finish: str
    roi_pct: float
    payback_months: int
    status: str


@dataclass
class CategoryRollup:
    category: str
    projects: int
    total_budget_m: float
    deployed_m: float
    avg_roi_pct: float
    avg_payback_months: float
    typical_lifespan_years: int


@dataclass
class DealBudget:
    deal: str
    annual_capex_budget_m: float
    mx_capex_m: float
    growth_capex_m: float
    it_capex_m: float
    yoy_change_pct: float
    capex_as_pct_of_revenue: float
    capex_as_pct_of_ebitda: float


@dataclass
class GovernanceApproval:
    project: str
    deal: str
    budget_m: float
    approver: str
    approval_date: str
    committee: str
    conditions: str


@dataclass
class TechInvestment:
    category: str
    project_count: int
    total_budget_m: float
    typical_implementation_months: int
    typical_annual_savings_m: float
    deployed_deals: int


@dataclass
class DenovoProject:
    project: str
    deal: str
    market: str
    build_type: str
    budget_m: float
    planned_open: str
    projected_year_1_revenue_m: float
    projected_year_3_ebitda_m: float
    status: str


@dataclass
class CapexResult:
    total_annual_budget_m: float
    total_ytd_spent_m: float
    total_projects: int
    weighted_avg_roi_pct: float
    portfolio_capex_ratio_pct: float
    projects_at_risk: int
    projects: List[CapexProject]
    categories: List[CategoryRollup]
    deal_budgets: List[DealBudget]
    approvals: List[GovernanceApproval]
    tech: List[TechInvestment]
    denovo: List[DenovoProject]
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


def _build_projects() -> List[CapexProject]:
    return [
        CapexProject("CAP-001", "Project Magnolia — MSK", "EHR Consolidation",
                     "Epic migration from legacy athenaOne + NextGen", 18.5, 11.2, 0.60, "2026-09-30", 0.22, 36, "on track"),
        CapexProject("CAP-002", "Project Magnolia — MSK", "De Novo Clinic",
                     "3 new MSK clinics — Austin TX metro", 12.5, 4.8, 0.38, "2026-12-31", 0.28, 28, "on track"),
        CapexProject("CAP-003", "Project Cypress — GI Network", "ASC Build-Out",
                     "2 endoscopy ASCs — Atlanta + Nashville", 22.5, 18.5, 0.82, "2026-05-31", 0.35, 24, "on track"),
        CapexProject("CAP-004", "Project Cypress — GI Network", "Anesthesia Integration",
                     "In-house anesthesia platform — 12 sites", 8.5, 5.5, 0.65, "2026-06-30", 0.38, 18, "on track"),
        CapexProject("CAP-005", "Project Cedar — Cardiology", "Cath Lab Refresh",
                     "3 new interventional cath labs + structural heart", 18.5, 8.5, 0.46, "2026-12-31", 0.25, 30, "on track"),
        CapexProject("CAP-006", "Project Cedar — Cardiology", "Clinical AI Deployment",
                     "Ultromics + Heartflow + Cleerly across 28 sites", 3.5, 2.5, 0.72, "2026-07-31", 0.48, 15, "on track"),
        CapexProject("CAP-007", "Project Redwood — Behavioral", "Telehealth Platform",
                     "Proprietary telehealth build + integration", 5.2, 2.5, 0.48, "2026-09-30", 0.32, 22, "behind"),
        CapexProject("CAP-008", "Project Laurel — Derma", "Clinic Expansion",
                     "6 new derma clinics — Southeast markets", 10.5, 6.2, 0.59, "2026-10-31", 0.32, 22, "on track"),
        CapexProject("CAP-009", "Project Laurel — Derma", "Mohs + Laser Upgrade",
                     "Laser + Mohs histology equipment refresh", 4.5, 3.8, 0.84, "2026-06-30", 0.35, 20, "on track"),
        CapexProject("CAP-010", "Project Willow — Fertility", "New Market Entry",
                     "2 new IVF centers — Chicago + Denver", 18.5, 9.5, 0.51, "2027-03-31", 0.25, 36, "on track"),
        CapexProject("CAP-011", "Project Willow — Fertility", "Lab Automation",
                     "Embryoscope + AI-enabled IVF lab automation", 6.5, 4.8, 0.74, "2026-08-31", 0.42, 18, "on track"),
        CapexProject("CAP-012", "Project Spruce — Radiology", "AI Platform Expansion",
                     "Aidoc + Viz.ai rollout to remaining 20 sites", 4.2, 2.8, 0.67, "2026-07-31", 0.55, 12, "on track"),
        CapexProject("CAP-013", "Project Spruce — Radiology", "MRI Capital Refresh",
                     "4 new MRI machines — replacement cycle", 12.5, 4.8, 0.38, "2026-12-31", 0.18, 48, "on track"),
        CapexProject("CAP-014", "Project Aspen — Eye Care", "ASC Conversion",
                     "Convert 4 office-based surgery to ASCs", 16.5, 10.5, 0.64, "2026-09-30", 0.32, 22, "on track"),
        CapexProject("CAP-015", "Project Aspen — Eye Care", "LASIK Upgrade",
                     "Femtosecond laser refresh — 8 centers", 6.8, 5.2, 0.76, "2026-05-31", 0.38, 18, "on track"),
        CapexProject("CAP-016", "Project Sage — Home Health", "Route Optimization System",
                     "AI-driven clinician routing + workforce mgmt", 2.8, 1.5, 0.54, "2026-09-30", 0.55, 15, "on track"),
        CapexProject("CAP-017", "Project Oak — RCM SaaS", "Platform Modernization",
                     "Microservices + API modernization", 8.5, 5.5, 0.65, "2026-11-30", 0.22, 36, "on track"),
        CapexProject("CAP-018", "Project Fir — Lab / Pathology", "Digital Pathology",
                     "Paige + Ibex expansion to additional 18 sites", 5.5, 2.2, 0.40, "2026-12-31", 0.32, 24, "on track"),
        CapexProject("CAP-019", "Project Basil — Dental DSO", "DSO Platform Consolidation",
                     "Practice management + EHR consolidation", 12.5, 5.5, 0.44, "2027-03-31", 0.22, 30, "on track"),
        CapexProject("CAP-020", "Project Thyme — Specialty Pharm", "340B Capability Expansion",
                     "Specialty pharmacy TPA infrastructure", 4.5, 2.8, 0.62, "2026-08-31", 0.45, 18, "on track"),
    ]


def _build_categories(projects: List[CapexProject]) -> List[CategoryRollup]:
    buckets: dict = {}
    for p in projects:
        b = buckets.setdefault(p.category, {"count": 0, "budget": 0, "spent": 0, "roi_sum": 0, "pay_sum": 0})
        b["count"] += 1
        b["budget"] += p.budget_m
        b["spent"] += p.spent_m
        b["roi_sum"] += p.roi_pct
        b["pay_sum"] += p.payback_months
    lifespan_map = {
        "EHR Consolidation": 10, "De Novo Clinic": 15, "ASC Build-Out": 12, "Anesthesia Integration": 8,
        "Cath Lab Refresh": 10, "Clinical AI Deployment": 5, "Telehealth Platform": 7, "Clinic Expansion": 12,
        "Mohs + Laser Upgrade": 8, "New Market Entry": 15, "Lab Automation": 10, "AI Platform Expansion": 5,
        "MRI Capital Refresh": 10, "ASC Conversion": 12, "LASIK Upgrade": 8, "Route Optimization System": 5,
        "Platform Modernization": 7, "Digital Pathology": 8, "DSO Platform Consolidation": 10,
        "340B Capability Expansion": 8,
    }
    rows = []
    for cat, d in buckets.items():
        rows.append(CategoryRollup(
            category=cat, projects=d["count"],
            total_budget_m=round(d["budget"], 1),
            deployed_m=round(d["spent"], 1),
            avg_roi_pct=round(d["roi_sum"] / d["count"], 4),
            avg_payback_months=round(d["pay_sum"] / d["count"], 1),
            typical_lifespan_years=lifespan_map.get(cat, 10),
        ))
    return sorted(rows, key=lambda x: x.total_budget_m, reverse=True)


def _build_deal_budgets() -> List[DealBudget]:
    return [
        DealBudget("Project Cypress — GI Network", 31.0, 8.5, 17.5, 5.0, 0.225, 0.065, 0.245),
        DealBudget("Project Magnolia — MSK Platform", 31.0, 6.2, 13.5, 11.3, 0.185, 0.058, 0.215),
        DealBudget("Project Cedar — Cardiology", 22.0, 5.8, 12.5, 3.7, 0.165, 0.048, 0.195),
        DealBudget("Project Redwood — Behavioral", 7.5, 2.5, 2.8, 2.2, 0.085, 0.032, 0.145),
        DealBudget("Project Laurel — Derma", 15.0, 3.5, 8.5, 3.0, 0.245, 0.062, 0.185),
        DealBudget("Project Willow — Fertility", 25.0, 4.8, 15.0, 5.2, 0.285, 0.095, 0.285),
        DealBudget("Project Spruce — Radiology", 16.7, 7.2, 3.5, 6.0, 0.125, 0.045, 0.145),
        DealBudget("Project Aspen — Eye Care", 23.3, 4.5, 15.0, 3.8, 0.215, 0.082, 0.285),
        DealBudget("Project Maple — Urology", 8.5, 2.8, 3.5, 2.2, 0.135, 0.042, 0.162),
        DealBudget("Project Ash — Infusion", 12.5, 4.5, 4.2, 3.8, 0.125, 0.052, 0.165),
        DealBudget("Project Fir — Lab / Pathology", 18.5, 6.2, 4.5, 7.8, 0.155, 0.058, 0.175),
        DealBudget("Project Sage — Home Health", 5.8, 1.5, 1.2, 3.1, 0.115, 0.022, 0.128),
        DealBudget("Project Oak — RCM SaaS", 12.5, 0.5, 3.5, 8.5, 0.285, 0.115, 0.152),
        DealBudget("Project Basil — Dental DSO", 18.5, 5.5, 8.5, 4.5, 0.145, 0.062, 0.195),
        DealBudget("Project Thyme — Specialty Pharm", 8.5, 2.2, 3.5, 2.8, 0.115, 0.025, 0.085),
    ]


def _build_approvals() -> List[GovernanceApproval]:
    return [
        GovernanceApproval("ASC Build-Out (Cypress)", "Project Cypress — GI Network", 22.5, "Board + Sponsor (Welsh Carson)",
                           "2025-11-15", "Capex + Growth Committee", "Pre-lease + permitting complete; rate lock"),
        GovernanceApproval("EHR Consolidation (Magnolia)", "Project Magnolia — MSK Platform", 18.5, "Board + Sponsor (KKR)",
                           "2025-09-20", "Capex Committee", "Epic contract negotiated; implementation partner selected"),
        GovernanceApproval("Cath Lab Refresh (Cedar)", "Project Cedar — Cardiology", 18.5, "Sponsor (Bain)",
                           "2025-12-10", "Capex + Clinical Committee", "Physician leadership sign-off + CON where required"),
        GovernanceApproval("New Market Entry (Willow)", "Project Willow — Fertility", 18.5, "Board + Sponsor (Apollo)",
                           "2026-02-05", "Growth + Strategy Committee", "Market study + staffing plan approved"),
        GovernanceApproval("Platform Modernization (Oak)", "Project Oak — RCM SaaS", 8.5, "Sponsor (Silver Lake)",
                           "2025-10-22", "Product Committee", "Architecture review + phased rollout"),
        GovernanceApproval("ASC Conversion (Aspen)", "Project Aspen — Eye Care", 16.5, "Board + Sponsor (CVC)",
                           "2025-10-15", "Capex Committee", "State licensure confirmed; Medicare enrollment pending"),
        GovernanceApproval("DSO Platform Consolidation (Basil)", "Project Basil — Dental DSO", 12.5, "Sponsor (L Catterton)",
                           "2026-01-08", "Technology Committee", "Vendor selection + data migration plan"),
    ]


def _build_tech() -> List[TechInvestment]:
    return [
        TechInvestment("EHR / Practice Management", 4, 42.0, 24, 5.5, 7),
        TechInvestment("Clinical AI / ML", 3, 9.0, 9, 12.5, 10),
        TechInvestment("RCM Platform / Automation", 3, 16.5, 18, 4.8, 6),
        TechInvestment("Digital Front Door (Portal + Scheduling)", 6, 22.5, 9, 6.5, 10),
        TechInvestment("Telehealth Infrastructure", 3, 7.5, 9, 3.5, 10),
        TechInvestment("Cybersecurity + HITRUST", 8, 18.5, 12, 0.0, 8),
        TechInvestment("Data + Analytics Platform", 5, 11.5, 12, 4.5, 8),
        TechInvestment("Route Optimization / WFM", 2, 5.5, 9, 3.8, 8),
    ]


def _build_denovo() -> List[DenovoProject]:
    return [
        DenovoProject("Project Willow — Chicago IVF", "Project Willow — Fertility", "Chicago, IL", "New IVF Center",
                      8.5, "2026-08-31", 4.2, 2.8, "construction"),
        DenovoProject("Project Willow — Denver IVF", "Project Willow — Fertility", "Denver, CO", "New IVF Center",
                      8.5, "2027-02-28", 3.8, 2.5, "pre-construction"),
        DenovoProject("Project Cypress — Atlanta ASC", "Project Cypress — GI Network", "Atlanta, GA", "New Endoscopy ASC",
                      11.5, "2026-05-31", 18.5, 5.5, "construction"),
        DenovoProject("Project Cypress — Nashville ASC", "Project Cypress — GI Network", "Nashville, TN", "New Endoscopy ASC",
                      11.0, "2026-05-31", 15.5, 4.8, "construction"),
        DenovoProject("Project Magnolia — Austin 1", "Project Magnolia — MSK", "Austin, TX", "New MSK + PT Clinic",
                      4.5, "2026-12-31", 8.5, 2.2, "construction"),
        DenovoProject("Project Magnolia — Austin 2", "Project Magnolia — MSK", "Austin, TX", "New MSK + PT Clinic",
                      4.5, "2026-12-31", 8.5, 2.2, "permitting"),
        DenovoProject("Project Magnolia — Austin 3", "Project Magnolia — MSK", "Austin, TX", "New MSK + PT Clinic",
                      3.5, "2027-03-31", 7.5, 2.0, "site selection"),
        DenovoProject("Project Laurel — Charleston", "Project Laurel — Derma", "Charleston, SC", "New Derma Clinic",
                      1.8, "2026-07-31", 2.8, 0.85, "construction"),
        DenovoProject("Project Laurel — Savannah", "Project Laurel — Derma", "Savannah, GA", "New Derma Clinic",
                      1.5, "2026-09-30", 2.5, 0.75, "permitting"),
        DenovoProject("Project Laurel — Raleigh (2)", "Project Laurel — Derma", "Raleigh, NC", "New Derma Clinic",
                      1.8, "2026-10-31", 2.8, 0.85, "construction"),
    ]


def compute_capex_budget() -> CapexResult:
    corpus = _load_corpus()
    projects = _build_projects()
    categories = _build_categories(projects)
    deal_budgets = _build_deal_budgets()
    approvals = _build_approvals()
    tech = _build_tech()
    denovo = _build_denovo()

    total_budget = sum(p.budget_m for p in projects)
    ytd_spent = sum(p.spent_m for p in projects)
    wtd_roi = sum(p.roi_pct * p.budget_m for p in projects) / total_budget if total_budget > 0 else 0
    portfolio_capex_ratio = sum(d.capex_as_pct_of_revenue for d in deal_budgets) / len(deal_budgets) if deal_budgets else 0
    at_risk = sum(1 for p in projects if p.status in ("behind", "at risk"))

    return CapexResult(
        total_annual_budget_m=round(total_budget, 1),
        total_ytd_spent_m=round(ytd_spent, 1),
        total_projects=len(projects),
        weighted_avg_roi_pct=round(wtd_roi, 4),
        portfolio_capex_ratio_pct=round(portfolio_capex_ratio, 4),
        projects_at_risk=at_risk,
        projects=projects,
        categories=categories,
        deal_budgets=deal_budgets,
        approvals=approvals,
        tech=tech,
        denovo=denovo,
        corpus_deal_count=len(corpus),
    )
