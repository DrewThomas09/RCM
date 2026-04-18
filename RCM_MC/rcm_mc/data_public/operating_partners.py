"""Operating Partner / CEO Rolodex Tracker.

Tracks healthcare PE operating partners, executive rolodex, CEO
placements, search pipeline, board seats, engagement hours.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class OperatingPartner:
    name: str
    title: str
    sector_expertise: str
    prior_ceo_roles: str
    active_deals: int
    board_seats: int
    engagement_hours_ltm: int
    retainer_annual_m: float
    compensation_structure: str
    tenure_years: int


@dataclass
class ExecutivePlacement:
    executive: str
    deal: str
    role: str
    placement_date: str
    source: str
    comp_package_m: float
    equity_pct: float
    status: str


@dataclass
class SearchPipeline:
    role: str
    deal: str
    sector: str
    launched: str
    stage: str
    candidates: int
    target_close: str
    search_firm: str
    comp_range_m: str


@dataclass
class BenchRoster:
    executive: str
    specialty: str
    active_status: str
    prior_roles: int
    relationship_tenure_years: int
    willingness_score: float
    last_interview: str


@dataclass
class EngagementMetric:
    operating_partner: str
    deal: str
    focus_area: str
    hours_ltm: int
    value_creation_m: float
    outcome_score: float


@dataclass
class CompensationBench:
    role: str
    sector: str
    p25_base_k: float
    median_base_k: float
    p75_base_k: float
    median_bonus_pct: float
    median_equity_pct: float
    typical_vest_years: int


@dataclass
class OperatingPartnersResult:
    total_operating_partners: int
    total_exec_placements: int
    active_searches: int
    total_bench_count: int
    total_engagement_hours_ltm: int
    total_value_creation_m: float
    partners: List[OperatingPartner]
    placements: List[ExecutivePlacement]
    searches: List[SearchPipeline]
    bench: List[BenchRoster]
    engagement: List[EngagementMetric]
    comp: List[CompensationBench]
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


def _build_partners() -> List[OperatingPartner]:
    return [
        OperatingPartner("Michael Boyd", "Sr. Operating Partner", "Multi-specialty / Rollup",
                         "CEO MedExpress, CEO Duly Health", 4, 6, 1850, 1.2, "fee + carry + follow-on", 8),
        OperatingPartner("Sarah Chen", "Operating Partner — Healthcare Tech",
                         "HCIT / RCM / Digital Health", "CEO Definitive Healthcare, EVP Change Healthcare", 3, 4, 1650, 1.0, "fee + carry", 6),
        OperatingPartner("Dr. James Whitmore", "Operating Partner — Clinical",
                         "MSK / Cardiology / Oncology", "CMO U.S. Anesthesia Partners", 3, 5, 1950, 1.1, "fee + carry + bonus", 10),
        OperatingPartner("David Martinez", "Operating Partner — Growth",
                         "Fertility / Behavioral / Multi-state growth", "CEO CVS MinuteClinic", 4, 5, 1750, 1.15, "fee + carry", 7),
        OperatingPartner("Dr. Rebecca Liu", "Operating Partner — Ops",
                         "ASC / Physician Services", "COO USPI, CFO Tenet", 4, 5, 1880, 1.05, "fee + carry + follow-on", 9),
        OperatingPartner("Jonathan Pierce", "Operating Partner — Credit",
                         "Healthcare Credit / Restructuring", "Managing Director Ares Capital", 3, 3, 1250, 0.95, "fee + carry", 5),
        OperatingPartner("Dr. Karen Sullivan", "Operating Partner — Value-Based Care",
                         "VBC / ACO / Primary Care", "CEO ChenMed, CMO Iora Health", 3, 4, 1520, 1.00, "fee + carry + equity on close", 6),
        OperatingPartner("Thomas Yang", "Operating Partner — M&A",
                         "Bolt-on integration / PMI", "VP Corporate Development Davita, Fresenius", 5, 6, 2050, 1.25, "fee + carry + deal success", 11),
        OperatingPartner("Linda Foster", "Operating Partner — Commercial",
                         "Payer contracting / Rev cycle", "EVP Optum Financial Services", 3, 4, 1580, 0.95, "fee + carry", 5),
        OperatingPartner("Dr. Marcus Ramirez", "Operating Partner — Clinical Quality",
                         "HEDIS / Stars / Clinical Quality", "VP Clinical Strategy Humana", 2, 3, 1120, 0.85, "fee + carry + bonus", 4),
        OperatingPartner("Dr. Jennifer Williams", "Operating Partner — Labor",
                         "Nursing / Physician workforce", "VP HR Genesis Healthcare", 3, 4, 1420, 0.90, "fee + carry", 5),
        OperatingPartner("Robert Nguyen", "Operating Partner — IT / Cyber",
                         "EHR / Data / Cyber", "CIO Ascension Health", 3, 4, 1380, 0.90, "fee + carry", 4),
    ]


def _build_placements() -> List[ExecutivePlacement]:
    return [
        ExecutivePlacement("Dr. Alicia Park (CEO)", "Project Redwood — Behavioral Health",
                           "CEO", "2025-12-15", "Russell Reynolds", 1.65, 0.035, "performing"),
        ExecutivePlacement("Michael Stern (CFO)", "Project Willow — Fertility",
                           "CFO", "2026-01-30", "Heidrick & Struggles", 0.95, 0.015, "early tenure"),
        ExecutivePlacement("Sarah Holden (CEO)", "Project Ash — Infusion",
                           "CEO", "2026-02-15", "Korn Ferry", 1.85, 0.040, "early tenure"),
        ExecutivePlacement("Dr. Kumar Patel (CMO)", "Project Cedar — Cardiology",
                           "Chief Medical Officer", "2025-09-20", "Spencer Stuart", 1.25, 0.020, "performing"),
        ExecutivePlacement("Lisa Rodriguez (COO)", "Project Magnolia — MSK",
                           "COO", "2025-11-18", "Egon Zehnder", 1.15, 0.022, "performing"),
        ExecutivePlacement("James Park (Chief People)", "Project Cypress — GI Network",
                           "Chief People Officer", "2026-02-05", "Internal Promotion", 0.65, 0.012, "early tenure"),
        ExecutivePlacement("Dr. Angela Lee (CCO)", "Project Aspen — Eye Care",
                           "Chief Commercial Officer", "2025-10-12", "Korn Ferry", 0.85, 0.015, "performing"),
        ExecutivePlacement("Brian Chen (CTO)", "Project Oak — RCM SaaS",
                           "CTO", "2025-08-28", "Executive Network", 1.35, 0.025, "exceeding"),
        ExecutivePlacement("Michelle Foster (CHRO)", "Project Sage — Home Health",
                           "Chief Human Resources", "2026-01-15", "Heidrick & Struggles", 0.75, 0.012, "early tenure"),
        ExecutivePlacement("Dr. Robert Lin (CMO)", "Project Linden — Behavioral",
                           "CMO", "2025-11-02", "Russell Reynolds", 0.95, 0.018, "performing"),
        ExecutivePlacement("Thomas Wright (CFO)", "Project Thyme — Specialty Pharm",
                           "CFO", "2026-03-05", "Internal Promotion", 0.75, 0.012, "new hire"),
        ExecutivePlacement("Dr. Patricia Evans (SVP Clinical)", "Project Fir — Lab / Pathology",
                           "SVP Clinical", "2025-10-28", "Spencer Stuart", 0.85, 0.015, "performing"),
    ]


def _build_searches() -> List[SearchPipeline]:
    return [
        SearchPipeline("CEO", "Project Azalea — GI Network SE", "Gastroenterology",
                       "2026-02-15", "finalist interviews", 5, "2026-06-01", "Spencer Stuart", "$1.8-2.2M + 4% equity"),
        SearchPipeline("COO", "Project Meridian — Multi-specialty", "Multi-specialty",
                       "2026-03-10", "candidate sourcing", 8, "2026-07-15", "Russell Reynolds", "$1.0-1.4M + 2% equity"),
        SearchPipeline("CMO", "Project Tundra — Neurology", "Neurology",
                       "2026-02-28", "candidate sourcing", 12, "2026-06-30", "Korn Ferry", "$0.9-1.2M + 1.5% equity"),
        SearchPipeline("CFO", "Project Ridge — Cardiology Services", "Cardiology",
                       "2026-03-20", "early sourcing", 4, "2026-08-15", "Heidrick & Struggles", "$0.7-0.9M + 1% equity"),
        SearchPipeline("CEO", "Project Sierra — Home Health Platform", "Home Health",
                       "2026-03-01", "final interviews", 3, "2026-05-15", "Russell Reynolds", "$1.6-1.9M + 3% equity"),
        SearchPipeline("Chief Growth Officer", "Project Terra — RCM Platform", "RCM / HCIT",
                       "2026-02-22", "offer stage", 2, "2026-04-30", "Korn Ferry", "$0.8-1.0M + 1.5% equity"),
        SearchPipeline("CEO", "Project Aurora — Ambulatory", "Ambulatory",
                       "2026-03-15", "final interviews", 4, "2026-06-01", "Spencer Stuart", "$1.5-1.8M + 3.5% equity"),
        SearchPipeline("CFO", "Project Horizon — Oncology", "Oncology",
                       "2026-02-20", "offer stage", 2, "2026-04-15", "Heidrick & Struggles", "$0.9-1.1M + 1.5% equity"),
    ]


def _build_bench() -> List[BenchRoster]:
    return [
        BenchRoster("Mark Thompson (former CEO, MSK platform)", "MSK / Ortho", "looking",
                    4, 8, 9.2, "2026-03-15"),
        BenchRoster("Dr. Elizabeth Carter (ex-Humana clinical)", "VBC / Primary Care", "advising",
                    3, 5, 8.5, "2026-02-28"),
        BenchRoster("David Kim (former CFO, 3 PE deals)", "Multi-sector CFO", "in role",
                    5, 7, 7.0, "2025-12-15"),
        BenchRoster("Dr. Sandra Liu (oncology rollup)", "Oncology", "available immediately",
                    3, 4, 9.5, "2026-03-22"),
        BenchRoster("James O'Connor (former CEO dental DSO)", "Dental DSO", "looking",
                    4, 6, 9.0, "2026-03-10"),
        BenchRoster("Dr. Michael Chen (fertility + gynecology)", "Fertility / Women's Health", "advising",
                    3, 5, 8.8, "2026-02-18"),
        BenchRoster("Lisa Evans (former COO, derma/vision)", "Dermatology / Vision", "available",
                    3, 4, 9.3, "2026-03-05"),
        BenchRoster("Robert Patel (ex-Ascension / health system)", "Hospital Ops", "in role",
                    4, 8, 7.5, "2025-11-20"),
        BenchRoster("Dr. Nancy Garcia (former CMO, radiology)", "Radiology", "looking",
                    3, 5, 8.8, "2026-03-18"),
        BenchRoster("Thomas Martinez (HCIT / digital health CEO)", "HCIT / RCM", "advising",
                    5, 6, 8.5, "2026-02-25"),
        BenchRoster("Dr. Patricia Yang (urology + men's health)", "Urology", "available",
                    2, 3, 9.0, "2026-03-20"),
        BenchRoster("Kevin Brown (former CEO lab services)", "Lab Services", "in role",
                    4, 6, 7.2, "2025-12-20"),
        BenchRoster("Dr. Rachel Kumar (physician exec, MSK)", "MSK / Ortho", "advising",
                    3, 4, 8.6, "2026-03-08"),
        BenchRoster("Michael Johnson (HCIT / RCM SaaS CEO)", "RCM / HCIT", "available",
                    4, 5, 9.1, "2026-03-15"),
        BenchRoster("Dr. Thomas Chen (former CMO home health)", "Home Health", "looking",
                    3, 4, 8.7, "2026-03-12"),
    ]


def _build_engagement() -> List[EngagementMetric]:
    return [
        EngagementMetric("Michael Boyd", "Project Cypress — GI Network", "Commercial + Integration", 485, 15.2, 8.8),
        EngagementMetric("Michael Boyd", "Project Magnolia — MSK Platform", "Rollup strategy", 420, 8.5, 8.2),
        EngagementMetric("Sarah Chen", "Project Oak — RCM SaaS", "Platform modernization", 585, 18.5, 9.2),
        EngagementMetric("Dr. James Whitmore", "Project Cedar — Cardiology", "Service-line strategy", 495, 12.5, 8.5),
        EngagementMetric("Dr. James Whitmore", "Project Magnolia — MSK", "Clinical quality + MIPS", 420, 6.8, 8.2),
        EngagementMetric("David Martinez", "Project Willow — Fertility", "New-market entry", 445, 11.2, 7.8),
        EngagementMetric("David Martinez", "Project Linden — Behavioral", "Geographic expansion", 385, 5.8, 7.5),
        EngagementMetric("Dr. Rebecca Liu", "Project Cypress — GI Network", "ASC integration", 465, 14.8, 9.0),
        EngagementMetric("Dr. Rebecca Liu", "Project Cedar — Cardiology", "Cath lab throughput", 380, 7.5, 8.3),
        EngagementMetric("Thomas Yang", "Project Laurel — Derma", "Bolt-on PMI", 520, 16.5, 9.1),
        EngagementMetric("Thomas Yang", "Project Aspen — Eye Care", "Bolt-on PMI", 445, 9.8, 8.7),
        EngagementMetric("Dr. Karen Sullivan", "Project Sage — Home Health", "VBC / APM participation", 420, 8.5, 8.5),
        EngagementMetric("Linda Foster", "Project Oak — RCM SaaS", "Payer contracting strategy", 385, 6.5, 8.3),
        EngagementMetric("Dr. Marcus Ramirez", "Project Linden — Behavioral", "HEDIS improvement", 320, 4.2, 8.0),
        EngagementMetric("Robert Nguyen", "Project Cedar — Cardiology", "EHR consolidation", 365, 8.5, 8.5),
    ]


def _build_comp() -> List[CompensationBench]:
    return [
        CompensationBench("CEO", "Multi-specialty / Rollup", 950, 1250, 1750, 85, 4.0, 4),
        CompensationBench("CEO", "Specialty / Platform", 750, 1000, 1400, 75, 3.5, 4),
        CompensationBench("CEO", "Healthcare Tech / RCM", 850, 1150, 1700, 80, 4.5, 4),
        CompensationBench("CFO", "Platform ($500M-$1B rev)", 550, 750, 1050, 60, 1.5, 4),
        CompensationBench("CFO", "Platform ($100-500M rev)", 400, 575, 825, 55, 1.25, 4),
        CompensationBench("COO", "Multi-specialty", 650, 900, 1200, 70, 2.0, 4),
        CompensationBench("CMO", "Physician Services", 550, 750, 1000, 50, 1.5, 4),
        CompensationBench("CMO", "Clinical Services", 500, 700, 950, 45, 1.25, 4),
        CompensationBench("CCO", "Multi-specialty", 450, 625, 850, 55, 1.25, 4),
        CompensationBench("Chief Growth Officer", "Healthcare Tech", 650, 875, 1150, 65, 1.5, 4),
        CompensationBench("CTO", "Healthcare Tech / RCM", 700, 950, 1350, 70, 2.25, 4),
        CompensationBench("CHRO", "Platform-level", 400, 550, 800, 50, 0.75, 4),
        CompensationBench("General Counsel", "Platform-level", 500, 725, 1050, 55, 1.0, 4),
        CompensationBench("VP Corp Dev / M&A", "Platform-level", 450, 625, 900, 60, 1.0, 4),
    ]


def compute_operating_partners_tracker() -> OperatingPartnersResult:
    corpus = _load_corpus()
    partners = _build_partners()
    placements = _build_placements()
    searches = _build_searches()
    bench = _build_bench()
    engagement = _build_engagement()
    comp = _build_comp()

    total_hours = sum(p.engagement_hours_ltm for p in partners)
    total_vc = sum(e.value_creation_m for e in engagement)

    return OperatingPartnersResult(
        total_operating_partners=len(partners),
        total_exec_placements=len(placements),
        active_searches=len(searches),
        total_bench_count=len(bench),
        total_engagement_hours_ltm=total_hours,
        total_value_creation_m=round(total_vc, 1),
        partners=partners,
        placements=placements,
        searches=searches,
        bench=bench,
        engagement=engagement,
        comp=comp,
        corpus_deal_count=len(corpus),
    )
