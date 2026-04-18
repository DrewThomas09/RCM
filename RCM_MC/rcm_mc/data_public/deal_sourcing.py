"""Deal Sourcing / Proprietary Flow Tracker.

Tracks deal sourcing funnel, intermediary relationships, proprietary
origination channels, conversion rates, sourcing team productivity.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SourcingFunnel:
    stage: str
    count_ltm: int
    avg_size_m: float
    cycle_time_days: int
    conversion_to_next_pct: float
    annualized_run_rate: int


@dataclass
class SourceChannel:
    channel: str
    leads_ltm: int
    qualified_pct: float
    deals_closed: int
    close_rate_pct: float
    total_closed_value_m: float
    median_close_size_m: float


@dataclass
class IntermediaryRelationship:
    firm: str
    firm_type: str
    contacts_primary: int
    deals_shown_ltm: int
    deals_closed: int
    conversion_rate_pct: float
    reverse_inquiry_count: int
    relationship_score: float


@dataclass
class ProprietaryOpportunity:
    target: str
    sector: str
    introducer: str
    stage: str
    estimated_size_m: float
    proprietary_advantage: str
    days_since_intro: int
    probability_pct: float


@dataclass
class SourcingTeam:
    partner: str
    coverage: str
    deals_sourced_ltm: int
    deals_closed_ltm: int
    total_closed_value_m: float
    avg_markup_pct: float
    proprietary_deal_pct: float


@dataclass
class ClosedDealBridge:
    deal: str
    sector: str
    source: str
    introducer: str
    process_type: str
    deal_value_m: float
    deal_date: str


@dataclass
class DealSourcingResult:
    total_annualized_pipeline: int
    total_proprietary_opportunities: int
    total_closed_ltm: int
    total_closed_value_m: float
    weighted_close_rate_pct: float
    funnel: List[SourcingFunnel]
    channels: List[SourceChannel]
    intermediaries: List[IntermediaryRelationship]
    proprietary: List[ProprietaryOpportunity]
    team: List[SourcingTeam]
    closed_bridge: List[ClosedDealBridge]
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


def _build_funnel() -> List[SourcingFunnel]:
    return [
        SourcingFunnel("Initial Screen", 485, 125.0, 15, 0.482, 485),
        SourcingFunnel("Preliminary DD (CIM review)", 234, 185.0, 28, 0.444, 234),
        SourcingFunnel("IOI / LOI Submitted", 104, 315.0, 22, 0.375, 104),
        SourcingFunnel("Management Presentation", 39, 445.0, 18, 0.513, 39),
        SourcingFunnel("Confirmatory DD", 20, 525.0, 45, 0.750, 20),
        SourcingFunnel("Signed / Closed", 15, 580.0, 60, 0.0, 15),
    ]


def _build_channels() -> List[SourceChannel]:
    return [
        SourceChannel("Investment Banker (intermediated process)", 285, 0.585, 6, 0.036, 3850.0, 685.0),
        SourceChannel("Proprietary / Direct Sourcing", 125, 0.745, 4, 0.258, 2150.0, 485.0),
        SourceChannel("Portfolio Company Introduction (intra-platform)", 62, 0.825, 2, 0.322, 485.0, 185.0),
        SourceChannel("Operating Partner Rolodex", 48, 0.712, 1, 0.204, 385.0, 385.0),
        SourceChannel("Secondary Market (GP-led / direct secondary)", 35, 0.685, 1, 0.282, 1250.0, 1250.0),
        SourceChannel("Co-Invest Partner Introduction", 22, 0.612, 1, 0.152, 385.0, 385.0),
        SourceChannel("Conference / Industry Event", 18, 0.385, 0, 0.0, 0.0, 0.0),
        SourceChannel("Unsolicited Inbound (cold)", 82, 0.125, 0, 0.0, 0.0, 0.0),
    ]


def _build_intermediaries() -> List[IntermediaryRelationship]:
    return [
        IntermediaryRelationship("Goldman Sachs", "Bulge Bracket", 4, 22, 2, 0.091, 5, 9.2),
        IntermediaryRelationship("JPMorgan", "Bulge Bracket", 3, 28, 1, 0.036, 4, 8.5),
        IntermediaryRelationship("Morgan Stanley", "Bulge Bracket", 3, 18, 1, 0.056, 3, 8.8),
        IntermediaryRelationship("BofA Securities", "Bulge Bracket", 2, 15, 0, 0.0, 2, 7.5),
        IntermediaryRelationship("Jefferies", "Middle Market", 4, 42, 2, 0.048, 8, 9.0),
        IntermediaryRelationship("Houlihan Lokey", "Middle Market", 3, 35, 1, 0.029, 6, 8.8),
        IntermediaryRelationship("Moelis & Company", "Middle Market", 3, 28, 1, 0.036, 4, 8.5),
        IntermediaryRelationship("Edgemont Partners", "Healthcare Specialist", 5, 48, 3, 0.063, 12, 9.5),
        IntermediaryRelationship("Triple Tree", "Healthcare Specialist", 3, 32, 1, 0.031, 8, 8.8),
        IntermediaryRelationship("Cain Brothers (KeyBank)", "Healthcare Specialist", 3, 38, 1, 0.026, 9, 9.0),
        IntermediaryRelationship("Lincoln International", "Middle Market", 2, 28, 1, 0.036, 5, 8.2),
        IntermediaryRelationship("Harris Williams", "Middle Market", 2, 22, 0, 0.0, 3, 7.8),
        IntermediaryRelationship("Piper Sandler", "Middle Market", 2, 25, 0, 0.0, 4, 7.5),
        IntermediaryRelationship("William Blair", "Middle Market", 2, 20, 0, 0.0, 2, 7.2),
        IntermediaryRelationship("Coker Capital", "Healthcare Specialist (lower middle)", 2, 38, 1, 0.026, 6, 8.5),
        IntermediaryRelationship("Provident Healthcare Partners", "Healthcare Specialist (lower middle)", 2, 32, 0, 0.0, 4, 7.8),
    ]


def _build_proprietary() -> List[ProprietaryOpportunity]:
    return [
        ProprietaryOpportunity("Southeast Ophthalmology Partners", "Eye Care", "Dr. Angela Lee (Aspen CCO)",
                               "Confirmatory DD", 185.0, "Portfolio introduction + physician leadership", 125, 72),
        ProprietaryOpportunity("Midwest Behavioral Health Network", "Behavioral Health", "David Martinez (Sponsor)",
                               "Management Presentation", 285.0, "Proprietary via CCBHC relationships", 95, 62),
        ProprietaryOpportunity("Pacific NW MSK Platform", "MSK / Ortho", "Michael Boyd (Ops Partner)",
                               "IOI Submitted", 145.0, "Relationship with outgoing CEO", 185, 55),
        ProprietaryOpportunity("Texas Urology Rollup", "Urology", "Dr. Karen Sullivan (Ops Partner)",
                               "Preliminary DD", 85.0, "VBC thesis + physician partnerships", 45, 42),
        ProprietaryOpportunity("Mountain West Fertility", "Fertility / IVF", "Jonathan Pierce (Ops Partner)",
                               "Preliminary DD", 125.0, "Proprietary intro + Willow synergy", 65, 48),
        ProprietaryOpportunity("Southeast GI Partners", "Gastroenterology", "Thomas Yang (Ops Partner)",
                               "IOI Submitted", 225.0, "Cross-reference with Cypress", 145, 58),
        ProprietaryOpportunity("California Derma Network", "Dermatology", "Sponsor — Tier 1", "Preliminary DD",
                               135.0, "Geographic adjacency to Laurel", 55, 52),
        ProprietaryOpportunity("MedTech-enabled Primary Care", "VBC / Primary Care", "Sarah Chen (Ops Partner)",
                               "Management Presentation", 325.0, "Tech-enabled VBC thesis + ChenMed comparable", 105, 65),
        ProprietaryOpportunity("Midwest Infusion Services", "Infusion", "Sponsor — Tier 2", "Preliminary DD",
                               98.0, "Proprietary via chair relationships", 78, 48),
        ProprietaryOpportunity("Southern Specialty Pharmacy", "Specialty Pharma", "Linda Foster (Ops Partner)",
                               "Preliminary DD", 165.0, "Proprietary — not in active auction", 55, 55),
        ProprietaryOpportunity("Boston Cardiology Group", "Cardiology", "Sponsor — Tier 1", "Initial Screen",
                               115.0, "Not yet in process — pre-outreach stage", 25, 35),
        ProprietaryOpportunity("Gulf Coast Home Health", "Home Health", "Dr. Jennifer Williams (Ops Partner)",
                               "IOI Submitted", 185.0, "Sage platform integration synergy", 165, 52),
        ProprietaryOpportunity("Mid-Atlantic Dental Network", "Dental DSO", "Sponsor — Tier 1", "Initial Screen",
                               95.0, "Early stage — competitive situation possible", 15, 38),
    ]


def _build_team() -> List[SourcingTeam]:
    return [
        SourcingTeam("Sr. Partner 1 (Healthcare)", "Multi-specialty, VBC, primary care", 85, 3, 1450.0, 4.5, 0.42),
        SourcingTeam("Sr. Partner 2 (Healthcare)", "MSK, GI, procedural services", 78, 3, 1200.0, 3.8, 0.38),
        SourcingTeam("Sr. Partner 3 (Healthtech)", "RCM, HCIT, clinical AI", 62, 2, 720.0, 4.2, 0.55),
        SourcingTeam("Partner 1 (Healthcare)", "Behavioral health, home health", 68, 2, 385.0, 3.5, 0.48),
        SourcingTeam("Partner 2 (Healthcare)", "Specialty pharma, infusion", 55, 2, 625.0, 4.0, 0.52),
        SourcingTeam("Mgr Director 1", "Derma, eye care, urology, fertility", 75, 2, 280.0, 3.2, 0.45),
        SourcingTeam("Mgr Director 2", "Cardiology, pulmonology, neurology", 58, 1, 420.0, 3.8, 0.35),
        SourcingTeam("Director 1 (Multi-sector)", "Dental, optometry, consumer", 45, 0, 0.0, 0.0, 0.0),
        SourcingTeam("Director 2 (Healthcare)", "Lab services, imaging, rad/path", 38, 0, 0.0, 0.0, 0.0),
    ]


def _build_closed_bridge() -> List[ClosedDealBridge]:
    return [
        ClosedDealBridge("Project Azalea — GI Network SE", "Gastroenterology", "Investment Banker (intermediated)",
                         "JPMorgan", "Broad auction", 1650.0, "2026-04-15"),
        ClosedDealBridge("Project Magnolia — MSK Platform", "MSK / Ortho", "Investment Banker (intermediated)",
                         "Jefferies", "Limited auction", 485.0, "2025-08-22"),
        ClosedDealBridge("Project Cypress — GI Network", "Gastroenterology", "Proprietary / Direct",
                         "Introduced via Cedar Cardiology Board", "Bilateral", 525.0, "2025-06-18"),
        ClosedDealBridge("Project Redwood — Behavioral Health", "Behavioral Health", "Investment Banker (intermediated)",
                         "Houlihan Lokey", "Limited auction", 320.0, "2025-04-10"),
        ClosedDealBridge("Project Cedar — Cardiology", "Cardiology", "Portfolio Company Intro",
                         "USAP management introduction", "Bilateral + limited check", 445.0, "2025-02-28"),
        ClosedDealBridge("Project Willow — Fertility", "Fertility / IVF", "Operating Partner Rolodex",
                         "David Martinez (ex-ChenMed)", "Bilateral", 395.0, "2024-12-15"),
        ClosedDealBridge("Project Laurel — Derma", "Dermatology", "Proprietary / Direct",
                         "Ops Partner cold outreach + physician champion", "Bilateral", 225.0, "2024-10-18"),
        ClosedDealBridge("Project Spruce — Radiology", "Radiology", "Investment Banker (intermediated)",
                         "Jefferies", "Broad auction", 340.0, "2024-08-25"),
        ClosedDealBridge("Project Aspen — Eye Care", "Eye Care", "Investment Banker (intermediated)",
                         "Triple Tree", "Limited auction", 195.0, "2024-06-28"),
        ClosedDealBridge("Project Maple — Urology", "Urology", "Proprietary / Direct",
                         "Sr. Partner 2 relationship", "Bilateral", 165.0, "2024-04-15"),
        ClosedDealBridge("Project Ash — Infusion", "Infusion", "Investment Banker (intermediated)",
                         "Moelis & Company", "Limited auction", 485.0, "2024-02-28"),
        ClosedDealBridge("Project Fir — Lab / Pathology", "Lab Services", "Co-Invest Partner Introduction",
                         "CPPIB + GIC intro", "Bilateral", 425.0, "2023-12-15"),
        ClosedDealBridge("Project Oak — RCM SaaS", "RCM / HCIT", "Secondary Market",
                         "Silver Lake GP-led secondary", "Single-asset continuation", 1250.0, "2023-10-22"),
        ClosedDealBridge("Project Sage — Home Health", "Home Health", "Investment Banker (intermediated)",
                         "Cain Brothers", "Limited auction", 385.0, "2023-08-18"),
        ClosedDealBridge("Project Basil — Dental DSO", "Dental DSO", "Operating Partner Rolodex",
                         "Sr. Partner 2 + Edgemont intro", "Bilateral + limited check", 385.0, "2023-06-25"),
    ]


def compute_deal_sourcing() -> DealSourcingResult:
    corpus = _load_corpus()
    funnel = _build_funnel()
    channels = _build_channels()
    intermediaries = _build_intermediaries()
    proprietary = _build_proprietary()
    team = _build_team()
    closed_bridge = _build_closed_bridge()

    total_closed = sum(c.deals_closed for c in channels)
    total_closed_val = sum(c.total_closed_value_m for c in channels)
    total_leads = sum(c.leads_ltm for c in channels)
    wtd_close = total_closed / total_leads if total_leads > 0 else 0

    return DealSourcingResult(
        total_annualized_pipeline=funnel[0].annualized_run_rate if funnel else 0,
        total_proprietary_opportunities=len(proprietary),
        total_closed_ltm=total_closed,
        total_closed_value_m=round(total_closed_val, 1),
        weighted_close_rate_pct=round(wtd_close, 4),
        funnel=funnel,
        channels=channels,
        intermediaries=intermediaries,
        proprietary=proprietary,
        team=team,
        closed_bridge=closed_bridge,
        corpus_deal_count=len(corpus),
    )
