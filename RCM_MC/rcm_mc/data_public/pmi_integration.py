"""PMI / Post-Merger Integration Scorecard Tracker.

Tracks integration progress across bolt-on and platform acquisitions:
synergy realization, workstream completion, milestone achievement,
integration cost, value-capture trajectory.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class IntegrationDeal:
    platform: str
    bolt_on: str
    close_date: str
    months_post_close: int
    deal_value_m: float
    synergy_target_m: float
    synergy_realized_m: float
    realization_pct: float
    integration_cost_m: float
    integration_status: str


@dataclass
class Workstream:
    platform: str
    bolt_on: str
    workstream: str
    total_milestones: int
    completed: int
    in_progress: int
    blocked: int
    completion_pct: float
    owner: str


@dataclass
class SynergyCategory:
    category: str
    deals: int
    total_target_m: float
    total_realized_m: float
    realization_pct: float
    typical_timeline_months: int
    difficulty: str


@dataclass
class IntegrationRisk:
    platform: str
    bolt_on: str
    risk: str
    severity: str
    workstream: str
    mitigation: str
    owner: str


@dataclass
class TimelineMilestone:
    platform: str
    milestone: str
    target_date: str
    actual_date: str
    status: str
    variance_days: int


@dataclass
class RetentionMetric:
    platform: str
    bolt_on: str
    physicians_retained: int
    physicians_lost: int
    retention_rate_pct: float
    key_patients_retained_pct: float
    staff_retention_pct: float


@dataclass
class PMIResult:
    total_integrations: int
    total_synergy_target_m: float
    total_synergy_realized_m: float
    weighted_realization_pct: float
    total_integration_cost_m: float
    on_track_count: int
    integrations: List[IntegrationDeal]
    workstreams: List[Workstream]
    synergy_categories: List[SynergyCategory]
    risks: List[IntegrationRisk]
    milestones: List[TimelineMilestone]
    retention: List[RetentionMetric]
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


def _build_integrations() -> List[IntegrationDeal]:
    return [
        IntegrationDeal("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "2025-08-15", 8,
                        125.0, 12.5, 8.5, 0.68, 2.8, "on track"),
        IntegrationDeal("Project Cypress — GI Network", "Nashville GI Consultants", "2025-11-10", 5,
                        85.0, 8.5, 4.2, 0.49, 1.8, "on track"),
        IntegrationDeal("Project Cypress — GI Network", "Charlotte Gastro Partners", "2026-01-20", 3,
                        62.0, 6.5, 1.8, 0.28, 1.2, "early stage"),
        IntegrationDeal("Project Magnolia — MSK Platform", "Phoenix Orthopedic Group", "2025-06-10", 10,
                        85.0, 9.5, 7.2, 0.76, 2.2, "on track"),
        IntegrationDeal("Project Magnolia — MSK Platform", "Denver Sports Med Partners", "2025-09-22", 7,
                        52.0, 6.0, 3.5, 0.58, 1.5, "on track"),
        IntegrationDeal("Project Magnolia — MSK Platform", "Austin Spine Specialists", "2025-12-15", 4,
                        42.0, 4.5, 2.2, 0.49, 1.2, "early stage"),
        IntegrationDeal("Project Cedar — Cardiology", "Dallas Cardiology Associates", "2025-07-08", 9,
                        148.0, 16.5, 10.5, 0.64, 3.2, "on track"),
        IntegrationDeal("Project Cedar — Cardiology", "Phoenix Heart Group", "2025-10-15", 6,
                        85.0, 9.5, 4.8, 0.51, 2.0, "on track"),
        IntegrationDeal("Project Laurel — Derma", "Carolinas Dermatology", "2025-09-05", 7,
                        62.0, 7.0, 4.5, 0.64, 1.8, "on track"),
        IntegrationDeal("Project Laurel — Derma", "Florida Aesthetic Derm", "2025-11-22", 5,
                        45.0, 5.0, 2.5, 0.50, 1.2, "on track"),
        IntegrationDeal("Project Laurel — Derma", "Texas Skin Partners", "2026-02-10", 2,
                        38.0, 4.0, 0.8, 0.20, 0.8, "early stage"),
        IntegrationDeal("Project Willow — Fertility", "Florida IVF Network", "2025-08-28", 8,
                        95.0, 10.5, 6.8, 0.65, 2.5, "on track"),
        IntegrationDeal("Project Willow — Fertility", "California Fertility Group", "2025-11-18", 5,
                        125.0, 13.5, 5.8, 0.43, 2.8, "on track"),
        IntegrationDeal("Project Spruce — Radiology", "Midwest Imaging Partners", "2025-05-15", 11,
                        78.0, 8.5, 7.2, 0.85, 1.5, "on track"),
        IntegrationDeal("Project Spruce — Radiology", "Southeast Radiology Group", "2025-10-28", 6,
                        65.0, 7.0, 4.2, 0.60, 1.5, "on track"),
        IntegrationDeal("Project Aspen — Eye Care", "Midwest Eye Partners", "2025-07-22", 9,
                        85.0, 9.5, 7.0, 0.74, 2.0, "on track"),
        IntegrationDeal("Project Aspen — Eye Care", "Pacific Eye Associates", "2025-12-08", 4,
                        72.0, 8.0, 3.2, 0.40, 1.8, "behind"),
        IntegrationDeal("Project Ash — Infusion", "Boston Infusion Services", "2025-09-18", 7,
                        48.0, 5.5, 3.5, 0.64, 1.2, "on track"),
        IntegrationDeal("Project Basil — Dental DSO", "Midwest Dental Partners", "2025-06-25", 10,
                        85.0, 9.5, 7.8, 0.82, 2.2, "on track"),
        IntegrationDeal("Project Basil — Dental DSO", "Florida Dental Group", "2025-11-15", 5,
                        62.0, 7.0, 3.2, 0.46, 1.8, "on track"),
    ]


def _build_workstreams() -> List[Workstream]:
    return [
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "IT / EHR", 28, 22, 5, 1, 0.79, "CIO"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "RCM / Billing", 22, 20, 2, 0, 0.91, "RCM Director"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "Clinical / Quality", 18, 14, 4, 0, 0.78, "CMO"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "HR / Comp / Benefits", 24, 22, 2, 0, 0.92, "CHRO"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "Legal / Compliance", 15, 14, 1, 0, 0.93, "GC"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "Finance / Accounting", 20, 18, 2, 0, 0.90, "CFO"),
        Workstream("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "Marketing / Branding", 12, 8, 3, 1, 0.67, "CCO"),
        Workstream("Project Magnolia — MSK", "Phoenix Orthopedic Group", "IT / EHR", 32, 30, 2, 0, 0.94, "CIO"),
        Workstream("Project Magnolia — MSK", "Phoenix Orthopedic Group", "RCM / Billing", 24, 22, 2, 0, 0.92, "RCM Director"),
        Workstream("Project Magnolia — MSK", "Phoenix Orthopedic Group", "Clinical / Quality", 22, 18, 4, 0, 0.82, "CMO"),
        Workstream("Project Magnolia — MSK", "Phoenix Orthopedic Group", "HR / Comp / Benefits", 28, 26, 2, 0, 0.93, "CHRO"),
        Workstream("Project Cedar — Cardiology", "Dallas Cardiology Associates", "IT / EHR", 30, 24, 5, 1, 0.80, "CIO"),
        Workstream("Project Cedar — Cardiology", "Dallas Cardiology Associates", "Clinical / Quality", 22, 18, 3, 1, 0.82, "CMO"),
        Workstream("Project Cedar — Cardiology", "Dallas Cardiology Associates", "HR / Comp / Benefits", 25, 22, 3, 0, 0.88, "CHRO"),
        Workstream("Project Laurel — Derma", "Carolinas Dermatology", "IT / EHR", 24, 22, 2, 0, 0.92, "CIO"),
        Workstream("Project Willow — Fertility", "Florida IVF Network", "Clinical / Quality", 28, 24, 4, 0, 0.86, "CMO"),
        Workstream("Project Willow — Fertility", "California Fertility Group", "Clinical / Quality", 28, 18, 8, 2, 0.64, "CMO"),
        Workstream("Project Aspen — Eye Care", "Pacific Eye Associates", "IT / EHR", 28, 18, 6, 4, 0.64, "CIO"),
        Workstream("Project Aspen — Eye Care", "Pacific Eye Associates", "Clinical / Quality", 22, 16, 4, 2, 0.73, "CMO"),
    ]


def _build_synergy_categories() -> List[SynergyCategory]:
    return [
        SynergyCategory("GPO / Supply Chain Consolidation", 18, 18.5, 13.5, 0.730, 6, "low"),
        SynergyCategory("RCM / Billing Platform Consolidation", 18, 22.0, 15.2, 0.691, 12, "medium"),
        SynergyCategory("Payer Contract Consolidation", 16, 28.5, 15.5, 0.544, 18, "high"),
        SynergyCategory("Corporate G&A / Redundant Overhead", 18, 28.5, 22.5, 0.789, 6, "low"),
        SynergyCategory("EHR Consolidation + IT Integration", 18, 18.5, 8.5, 0.459, 18, "high"),
        SynergyCategory("Clinical Site Reconfiguration", 18, 15.0, 9.5, 0.633, 12, "medium"),
        SynergyCategory("ASC / Procedural Site Optimization", 10, 22.5, 12.5, 0.556, 12, "medium"),
        SynergyCategory("Ancillary Revenue Capture", 15, 18.5, 8.2, 0.443, 18, "medium"),
        SynergyCategory("Tax / Entity Structure Optimization", 18, 6.5, 4.8, 0.738, 9, "low"),
        SynergyCategory("Insurance / Risk Consolidation", 18, 4.8, 3.8, 0.792, 6, "low"),
        SynergyCategory("Revenue Cycle Automation", 12, 8.5, 4.2, 0.494, 12, "medium"),
        SynergyCategory("Same-Store Growth (from platform referral)", 15, 12.5, 6.5, 0.520, 24, "medium"),
    ]


def _build_risks() -> List[IntegrationRisk]:
    return [
        IntegrationRisk("Project Cypress — GI Network", "Charlotte Gastro Partners", "Legacy Athena → Epic migration lagging",
                        "medium", "IT / EHR", "Third-party implementation firm + physician champion deployment", "CIO + Deal Partner"),
        IntegrationRisk("Project Aspen — Eye Care", "Pacific Eye Associates", "3 senior ODs resigning within 90 days",
                        "high", "HR / Clinical", "Accelerated employment discussions + equity grant package for remaining", "CMO + HRBP"),
        IntegrationRisk("Project Aspen — Eye Care", "Pacific Eye Associates", "EHR migration IT workstream blocked on vendor response time",
                        "medium", "IT / EHR", "Executive escalation to EHR vendor; 60-day recovery plan", "CIO"),
        IntegrationRisk("Project Cedar — Cardiology", "Dallas Cardiology Associates", "BCBS TX network participation not finalized",
                        "medium", "Commercial Contracting", "Dual-track approach: interim OON + contract negotiation", "CCO + Legal"),
        IntegrationRisk("Project Cypress — GI Network", "Atlanta Endoscopy Associates", "ASC de novo location permit delay",
                        "low", "Real Estate / Construction", "Alternative site already identified as backup", "Real Estate Director"),
        IntegrationRisk("Project Willow — Fertility", "California Fertility Group", "Clinical guideline harmonization pushing back",
                        "medium", "Clinical / Quality", "Physician-led working group + shared KPI dashboard", "CMO"),
        IntegrationRisk("Project Magnolia — MSK", "Austin Spine Specialists", "Physician compensation migration creating tension",
                        "low", "HR / Comp", "Transition bridge payment + 2-year step-down to new comp model", "CMO + HRBP"),
        IntegrationRisk("Project Basil — Dental DSO", "Florida Dental Group", "Florida state dental board review pending",
                        "low", "Legal / Compliance", "Pre-filing completed; standard 60-90 day review; no pushback signaled", "GC"),
        IntegrationRisk("Project Laurel — Derma", "Texas Skin Partners", "Slow AI biopsy pathology adoption",
                        "low", "Clinical / Technology", "Champion physician deployment + pathology education track", "CMO"),
        IntegrationRisk("Project Willow — Fertility", "Florida IVF Network", "Lab consolidation timing risk",
                        "medium", "Clinical / Operations", "Phased lab consolidation + parallel operation during transition", "COO"),
    ]


def _build_milestones() -> List[TimelineMilestone]:
    return [
        TimelineMilestone("Project Cypress — GI Network", "Atlanta — legacy EHR migration complete", "2026-03-31", "2026-04-15",
                          "late", 15),
        TimelineMilestone("Project Cypress — GI Network", "Atlanta — payer contract migration", "2026-05-31", "",
                          "on track", 0),
        TimelineMilestone("Project Magnolia — MSK", "Phoenix Ortho — full EHR cutover", "2026-02-15", "2026-02-10",
                          "ahead", -5),
        TimelineMilestone("Project Magnolia — MSK", "Phoenix Ortho — billing integration", "2026-04-30", "",
                          "on track", 0),
        TimelineMilestone("Project Cedar — Cardiology", "Dallas — cath lab unification", "2026-06-30", "",
                          "on track", 0),
        TimelineMilestone("Project Willow — Fertility", "Florida — lab consolidation Phase 1", "2026-03-31", "2026-04-10",
                          "late", 10),
        TimelineMilestone("Project Willow — Fertility", "CA — clinical guidelines harmonization", "2026-06-30", "",
                          "behind", 45),
        TimelineMilestone("Project Aspen — Eye Care", "Pacific — EHR cutover", "2026-04-30", "",
                          "behind", 60),
        TimelineMilestone("Project Laurel — Derma", "Carolinas — ASC integration", "2026-02-28", "2026-02-18",
                          "ahead", -10),
        TimelineMilestone("Project Spruce — Radiology", "Midwest Imaging — AI platform rollout", "2026-03-15", "2026-03-15",
                          "on time", 0),
        TimelineMilestone("Project Basil — Dental DSO", "Midwest Dental — PMS migration Phase 1", "2026-05-31", "",
                          "on track", 0),
        TimelineMilestone("Project Ash — Infusion", "Boston Infusion — 340B program integration", "2026-06-30", "",
                          "on track", 0),
    ]


def _build_retention() -> List[RetentionMetric]:
    return [
        RetentionMetric("Project Cypress — GI Network", "Atlanta Endoscopy Associates", 18, 0, 1.00, 0.96, 0.92),
        RetentionMetric("Project Cypress — GI Network", "Nashville GI Consultants", 12, 1, 0.92, 0.94, 0.88),
        RetentionMetric("Project Cypress — GI Network", "Charlotte Gastro Partners", 15, 0, 1.00, 0.95, 0.90),
        RetentionMetric("Project Magnolia — MSK Platform", "Phoenix Orthopedic Group", 22, 1, 0.96, 0.93, 0.91),
        RetentionMetric("Project Magnolia — MSK Platform", "Denver Sports Med Partners", 15, 0, 1.00, 0.95, 0.89),
        RetentionMetric("Project Magnolia — MSK Platform", "Austin Spine Specialists", 12, 0, 1.00, 0.92, 0.85),
        RetentionMetric("Project Cedar — Cardiology", "Dallas Cardiology Associates", 28, 2, 0.93, 0.92, 0.88),
        RetentionMetric("Project Cedar — Cardiology", "Phoenix Heart Group", 18, 1, 0.95, 0.93, 0.90),
        RetentionMetric("Project Laurel — Derma", "Carolinas Dermatology", 14, 0, 1.00, 0.95, 0.92),
        RetentionMetric("Project Laurel — Derma", "Florida Aesthetic Derm", 10, 1, 0.91, 0.94, 0.86),
        RetentionMetric("Project Willow — Fertility", "Florida IVF Network", 16, 0, 1.00, 0.96, 0.90),
        RetentionMetric("Project Willow — Fertility", "California Fertility Group", 22, 1, 0.96, 0.95, 0.88),
        RetentionMetric("Project Spruce — Radiology", "Midwest Imaging Partners", 28, 0, 1.00, 0.98, 0.92),
        RetentionMetric("Project Aspen — Eye Care", "Pacific Eye Associates", 18, 3, 0.86, 0.90, 0.82),
        RetentionMetric("Project Basil — Dental DSO", "Midwest Dental Partners", 42, 2, 0.95, 0.93, 0.86),
    ]


def compute_pmi_integration() -> PMIResult:
    corpus = _load_corpus()
    integrations = _build_integrations()
    workstreams = _build_workstreams()
    synergy_categories = _build_synergy_categories()
    risks = _build_risks()
    milestones = _build_milestones()
    retention = _build_retention()

    total_target = sum(i.synergy_target_m for i in integrations)
    total_realized = sum(i.synergy_realized_m for i in integrations)
    wtd_realization = total_realized / total_target if total_target > 0 else 0
    total_cost = sum(i.integration_cost_m for i in integrations)
    on_track = sum(1 for i in integrations if i.integration_status == "on track")

    return PMIResult(
        total_integrations=len(integrations),
        total_synergy_target_m=round(total_target, 1),
        total_synergy_realized_m=round(total_realized, 1),
        weighted_realization_pct=round(wtd_realization, 4),
        total_integration_cost_m=round(total_cost, 1),
        on_track_count=on_track,
        integrations=integrations,
        workstreams=workstreams,
        synergy_categories=synergy_categories,
        risks=risks,
        milestones=milestones,
        retention=retention,
        corpus_deal_count=len(corpus),
    )
