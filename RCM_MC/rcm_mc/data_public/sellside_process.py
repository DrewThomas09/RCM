"""Sell-Side Process Tracker.

Tracks active sell-side processes: banker engagement, sell-side diligence
prep, CIM / QoE / legal DD status, buyer universe, bid stage,
valuation range, negotiation posture.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ActiveProcess:
    deal: str
    sector: str
    banker: str
    banker_type: str
    stage: str
    process_launch: str
    round_1_bids_due: str
    round_2_bids_due: str
    target_signing: str
    target_closing: str


@dataclass
class BuyerEngagement:
    deal: str
    buyer: str
    buyer_type: str
    first_touch: str
    stage: str
    ioi_amount_m: float
    key_conditions: str
    probability_advance_pct: float


@dataclass
class DiligencePrep:
    deal: str
    item: str
    status: str
    completion_pct: float
    advisor: str
    due_date: str
    criticality: str


@dataclass
class ValuationAnalytical:
    deal: str
    ltm_ebitda_m: float
    run_rate_ebitda_m: float
    base_multiple: float
    ask_multiple: float
    strategic_premium_range: str
    entry_value_m: float
    target_ev_m: float
    target_moic: float


@dataclass
class ProcessMilestone:
    deal: str
    milestone: str
    target_date: str
    actual_date: str
    status: str
    owner: str


@dataclass
class NegotiationPosture:
    deal: str
    current_round: str
    active_buyers: int
    high_bid_m: float
    sponsor_min_acceptable_m: float
    bid_dispersion_m: float
    posture: str
    next_action: str


@dataclass
class SellsideResult:
    total_active_processes: int
    total_buyers_engaged: int
    total_target_ev_m: float
    weighted_target_moic: float
    processes_closing_12mo: int
    top_stage_counts: dict
    processes: List[ActiveProcess]
    engagements: List[BuyerEngagement]
    diligence: List[DiligencePrep]
    valuations: List[ValuationAnalytical]
    milestones: List[ProcessMilestone]
    postures: List[NegotiationPosture]
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


def _build_processes() -> List[ActiveProcess]:
    return [
        ActiveProcess("Project Oak — RCM SaaS", "RCM / HCIT", "Goldman Sachs + Morgan Stanley", "Bulge bracket (co-advisor)",
                      "S-1 drafting", "2026-03-15", "IPO structure — no bids", "IPO structure — no bids",
                      "2026-09-30", "2026-09-30 (IPO pricing)"),
        ActiveProcess("Project Laurel — Derma", "Dermatology", "Goldman Sachs", "Bulge bracket",
                      "Process launch", "2026-04-01", "2026-05-30", "2026-07-15",
                      "2026-09-30", "2026-12-15"),
        ActiveProcess("Project Cypress — GI Network", "Gastroenterology", "Jefferies", "Healthcare specialist (middle)",
                      "Pre-launch / final prep", "2026-05-15", "2026-07-01", "2026-08-15",
                      "2026-10-31", "2027-01-15"),
        ActiveProcess("Project Fir — Lab / Pathology", "Lab Services", "Evercore", "Boutique",
                      "Pre-launch / final prep", "2026-06-01", "2026-07-15", "2026-09-01",
                      "2026-11-15", "2027-02-28"),
        ActiveProcess("Project Magnolia — MSK Platform", "MSK / Ortho", "Morgan Stanley + Triple Tree", "Bulge + specialist",
                      "Diligence prep active", "2026-08-01", "2026-09-30", "2026-11-15",
                      "2027-01-31", "2027-04-30"),
        ActiveProcess("Project Cedar — Cardiology", "Cardiology", "JPMorgan", "Bulge bracket",
                      "Diligence prep active", "2026-09-01", "2026-10-31", "2026-12-15",
                      "2027-02-28", "2027-05-31"),
        ActiveProcess("Project Ash — Infusion", "Infusion", "Goldman Sachs + Edgemont", "Bulge + specialist",
                      "Diligence prep active", "2026-10-01", "2026-11-30", "2027-01-15",
                      "2027-03-31", "2027-06-30"),
        ActiveProcess("Project Spruce — Radiology", "Radiology", "Jefferies", "Healthcare specialist (middle)",
                      "Diligence prep active", "2026-10-15", "2026-12-15", "2027-01-31",
                      "2027-04-15", "2027-07-31"),
        ActiveProcess("Project Thyme — Specialty Pharm", "Specialty Pharma", "JPMorgan + Cain Brothers", "Bulge + specialist",
                      "Diligence prep active", "2026-11-15", "2027-01-15", "2027-02-28",
                      "2027-05-15", "2027-08-31"),
        ActiveProcess("Project Willow — Fertility", "Fertility / IVF", "TBD (interview stage)", "Bulge or specialist (TBD)",
                      "Banker selection", "2027-02-15", "2027-04-15", "2027-05-31",
                      "2027-08-31", "2027-11-30"),
        ActiveProcess("Project Aspen — Eye Care", "Eye Care", "Triple Tree (engaged)", "Healthcare specialist",
                      "Banker engaged / prep", "2026-12-01", "2027-01-31", "2027-03-15",
                      "2027-05-31", "2027-08-31"),
    ]


def _build_engagements() -> List[BuyerEngagement]:
    return [
        BuyerEngagement("Project Laurel — Derma", "Advent International", "Large PE", "2026-02-15", "Management meeting completed",
                        850.0, "Bolt-on commitment + $12M incremental capex", 85),
        BuyerEngagement("Project Laurel — Derma", "Hellman & Friedman", "Large PE", "2026-02-22", "IOI submitted",
                        780.0, "Full business + ops partners package", 72),
        BuyerEngagement("Project Laurel — Derma", "Apollo", "Large PE", "2026-03-01", "IOI submitted",
                        825.0, "Fund XIII commitment subject to diligence", 68),
        BuyerEngagement("Project Laurel — Derma", "Optum Care Health (UHG)", "Strategic", "2026-02-18", "IOI submitted",
                        915.0, "Full deal + post-close integration plan", 55),
        BuyerEngagement("Project Laurel — Derma", "Morgan Stanley Infrastructure", "Infra-style PE", "2026-03-15", "Management meeting completed",
                        755.0, "Long-hold + lower leverage", 35),
        BuyerEngagement("Project Cypress — GI Network", "UnitedHealth Group (Optum)", "Strategic", "2026-03-10", "NDA signed + CIM reviewed",
                        2350.0, "Full business + 20% insider option", 62),
        BuyerEngagement("Project Cypress — GI Network", "Welsh Carson XIV", "Existing sponsor (CV)", "2026-01-15", "Structuring",
                        1950.0, "Single-asset continuation vehicle", 75),
        BuyerEngagement("Project Cypress — GI Network", "Bain Capital", "Large PE", "2026-03-20", "NDA signed + CIM reviewed",
                        2185.0, "Bolt-on M&A roadmap commitment", 58),
        BuyerEngagement("Project Cypress — GI Network", "Apollo", "Large PE", "2026-03-22", "NDA signed + CIM reviewed",
                        2085.0, "Full business + operating partners", 52),
        BuyerEngagement("Project Oak — RCM SaaS", "Public markets", "IPO", "2026-02-01", "S-1 drafting",
                        1650.0, "Syndicate banks: Goldman + MS + Cowen", 82),
        BuyerEngagement("Project Oak — RCM SaaS", "Thoma Bravo", "Large PE (HCIT)", "2026-02-20", "Alternative process (PE vs IPO)",
                        1450.0, "Take-private PE scenario", 35),
        BuyerEngagement("Project Oak — RCM SaaS", "Silver Lake (existing)", "Existing sponsor (CV)", "2026-02-15", "CV discussion",
                        1350.0, "Single-asset continuation / partial", 48),
        BuyerEngagement("Project Fir — Lab / Pathology", "LabCorp", "Strategic", "2026-04-15", "Pre-NDA outreach",
                        1560.0, "Strategic premium; pathology-focused", 45),
        BuyerEngagement("Project Fir — Lab / Pathology", "Quest Diagnostics", "Strategic", "2026-04-20", "Pre-NDA outreach",
                        1520.0, "Digital pathology integration", 42),
        BuyerEngagement("Project Fir — Lab / Pathology", "Carlyle (existing)", "Existing sponsor (CV)", "2026-01-22", "CV discussion",
                        1425.0, "Partial continuation", 55),
    ]


def _build_diligence() -> List[DiligencePrep]:
    return [
        DiligencePrep("Project Laurel — Derma", "CIM Production", "complete", 1.00, "Goldman Sachs", "2026-04-01", "critical"),
        DiligencePrep("Project Laurel — Derma", "Quality of Earnings", "complete", 1.00, "EY", "2026-03-31", "critical"),
        DiligencePrep("Project Laurel — Derma", "Legal Diligence", "complete", 1.00, "Kirkland & Ellis", "2026-03-31", "critical"),
        DiligencePrep("Project Laurel — Derma", "VDR Population", "complete", 1.00, "Intralinks", "2026-03-31", "critical"),
        DiligencePrep("Project Laurel — Derma", "Tax Diligence", "complete", 1.00, "KPMG", "2026-03-25", "high"),
        DiligencePrep("Project Laurel — Derma", "Environmental Diligence", "complete", 1.00, "AECOM", "2026-03-22", "medium"),
        DiligencePrep("Project Oak — RCM SaaS", "S-1 Registration Statement", "drafting", 0.85, "Ropes & Gray + internal", "2026-03-15", "critical"),
        DiligencePrep("Project Oak — RCM SaaS", "Audited Financials (IFRS + GAAP)", "complete", 1.00, "KPMG", "2025-12-31", "critical"),
        DiligencePrep("Project Oak — RCM SaaS", "IPO Readiness", "in progress", 0.92, "Sponsor + Management", "2026-06-15", "critical"),
        DiligencePrep("Project Cypress — GI Network", "CIM Production", "final review", 0.92, "Jefferies", "2026-05-01", "critical"),
        DiligencePrep("Project Cypress — GI Network", "Quality of Earnings", "final", 0.98, "EY", "2026-04-30", "critical"),
        DiligencePrep("Project Cypress — GI Network", "Legal Diligence", "complete", 1.00, "Ropes & Gray", "2026-04-22", "critical"),
        DiligencePrep("Project Cypress — GI Network", "VDR Population", "in progress", 0.85, "Intralinks", "2026-05-10", "critical"),
        DiligencePrep("Project Fir — Lab / Pathology", "CIM Production", "final", 0.95, "Evercore", "2026-05-22", "critical"),
        DiligencePrep("Project Fir — Lab / Pathology", "Quality of Earnings", "complete", 1.00, "PwC", "2026-04-28", "critical"),
        DiligencePrep("Project Fir — Lab / Pathology", "Legal Diligence", "final", 0.95, "Latham & Watkins", "2026-05-15", "critical"),
        DiligencePrep("Project Magnolia — MSK Platform", "CIM Production", "drafting", 0.45, "Morgan Stanley", "2026-07-15", "critical"),
        DiligencePrep("Project Magnolia — MSK Platform", "Quality of Earnings", "in progress", 0.65, "EY", "2026-07-01", "critical"),
        DiligencePrep("Project Cedar — Cardiology", "CIM Production", "drafting", 0.40, "JPMorgan", "2026-08-15", "critical"),
        DiligencePrep("Project Cedar — Cardiology", "Quality of Earnings", "in progress", 0.55, "PwC", "2026-08-15", "critical"),
        DiligencePrep("Project Ash — Infusion", "CIM Production", "drafting", 0.35, "Goldman Sachs", "2026-09-15", "critical"),
        DiligencePrep("Project Ash — Infusion", "340B Compliance Review", "in progress", 0.62, "Hogan Lovells", "2026-08-15", "critical"),
    ]


def _build_valuations() -> List[ValuationAnalytical]:
    return [
        ValuationAnalytical("Project Oak — RCM SaaS", 78.0, 85.0, 16.0, 22.0, "+35-50% vs private PE",
                            525.0, 1650.0, 3.50),
        ValuationAnalytical("Project Laurel — Derma", 62.0, 68.0, 13.0, 15.5, "+10-15% vs median",
                            225.0, 806.0, 2.68),
        ValuationAnalytical("Project Cypress — GI Network", 142.0, 148.0, 14.5, 17.0, "+15-20% for strategic",
                            525.0, 2059.0, 2.85),
        ValuationAnalytical("Project Fir — Lab / Pathology", 112.0, 118.0, 13.0, 15.5, "+10-15% for strategic",
                            425.0, 1456.0, 2.78),
        ValuationAnalytical("Project Magnolia — MSK Platform", 82.0, 85.0, 13.5, 16.0, "+10-12% for consolidation",
                            485.0, 1107.0, 2.45),
        ValuationAnalytical("Project Cedar — Cardiology", 118.0, 122.0, 13.5, 16.5, "+15-18% for strategic",
                            445.0, 1593.0, 2.75),
        ValuationAnalytical("Project Ash — Infusion", 95.0, 98.0, 13.5, 16.5, "+10-15% for strategic",
                            485.0, 1283.0, 2.65),
        ValuationAnalytical("Project Spruce — Radiology", 88.0, 92.0, 12.0, 14.5, "+8-12% for strategic",
                            340.0, 1056.0, 2.52),
        ValuationAnalytical("Project Thyme — Specialty Pharm", 92.0, 95.0, 13.0, 16.0, "+10-18% for strategic",
                            450.0, 1196.0, 2.68),
        ValuationAnalytical("Project Willow — Fertility", 58.0, 62.0, 15.0, 18.0, "+15-20% for strategic",
                            395.0, 870.0, 2.95),
        ValuationAnalytical("Project Aspen — Eye Care", 48.0, 52.0, 13.0, 15.5, "+8-12% for strategic",
                            195.0, 624.0, 2.32),
    ]


def _build_milestones() -> List[ProcessMilestone]:
    return [
        ProcessMilestone("Project Oak — RCM SaaS", "S-1 initial filing (confidential)", "2026-03-15", "2026-03-12",
                         "ahead", "CFO + Ropes & Gray"),
        ProcessMilestone("Project Oak — RCM SaaS", "S-1 public filing", "2026-05-30", "",
                         "on track", "CFO + Ropes & Gray"),
        ProcessMilestone("Project Oak — RCM SaaS", "IPO pricing", "2026-09-30", "",
                         "on track", "CFO + Goldman/MS"),
        ProcessMilestone("Project Laurel — Derma", "Process launch (CIM release)", "2026-04-01", "",
                         "on track", "Goldman Sachs"),
        ProcessMilestone("Project Laurel — Derma", "IOI deadline", "2026-04-15", "",
                         "on track", "Goldman Sachs"),
        ProcessMilestone("Project Laurel — Derma", "Management presentations", "2026-05-01", "",
                         "on track", "CEO + CFO + Goldman"),
        ProcessMilestone("Project Cypress — GI Network", "Launch readiness review", "2026-04-30", "",
                         "on track", "Sponsor + Jefferies"),
        ProcessMilestone("Project Cypress — GI Network", "CIM finalization", "2026-05-05", "",
                         "on track", "Jefferies"),
        ProcessMilestone("Project Fir — Lab / Pathology", "Pre-launch diligence complete", "2026-05-22", "",
                         "on track", "Evercore"),
        ProcessMilestone("Project Oak — RCM SaaS", "Roadshow", "2026-07-15", "",
                         "on track", "IPO syndicate"),
    ]


def _build_postures() -> List[NegotiationPosture]:
    return [
        NegotiationPosture("Project Oak — RCM SaaS", "IPO", 1, 1650.0, 1250.0, 300.0,
                           "IPO preferred; PE backup", "S-1 public filing Q2 + roadshow Q3"),
        NegotiationPosture("Project Laurel — Derma", "Round 2 / Management", 5, 915.0, 750.0, 160.0,
                           "Strategic premium evaluation", "MP week of 2026-05-01; bids 2026-05-30"),
        NegotiationPosture("Project Cypress — GI Network", "Round 1 / IOI", 4, 2350.0, 1850.0, 400.0,
                           "CV alternative + strategic optionality", "Launch 2026-05-15; IOI by 2026-07-01"),
        NegotiationPosture("Project Fir — Lab / Pathology", "Pre-launch", 3, 1560.0, 1250.0, 135.0,
                           "Strategic-friendly positioning", "Launch 2026-06-01; buyer targeting"),
    ]


def compute_sellside_process() -> SellsideResult:
    corpus = _load_corpus()
    processes = _build_processes()
    engagements = _build_engagements()
    diligence = _build_diligence()
    valuations = _build_valuations()
    milestones = _build_milestones()
    postures = _build_postures()

    total_ev = sum(v.target_ev_m for v in valuations)
    wtd_moic = sum(v.target_moic * v.target_ev_m for v in valuations) / total_ev if total_ev > 0 else 0

    stage_counts = {}
    for p in processes:
        stage_counts[p.stage] = stage_counts.get(p.stage, 0) + 1

    closing_12 = sum(1 for p in processes if p.target_closing <= "2027-01-31")

    return SellsideResult(
        total_active_processes=len(processes),
        total_buyers_engaged=len(engagements),
        total_target_ev_m=round(total_ev, 1),
        weighted_target_moic=round(wtd_moic, 2),
        processes_closing_12mo=closing_12,
        top_stage_counts=stage_counts,
        processes=processes,
        engagements=engagements,
        diligence=diligence,
        valuations=valuations,
        milestones=milestones,
        postures=postures,
        corpus_deal_count=len(corpus),
    )
