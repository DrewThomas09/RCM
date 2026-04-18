"""Diligence Vendor / Provider Directory.

Catalog of the diligence ecosystem a PE firm works with across deals —
QoE firms, healthcare consultants, legal counsel, insurance advisors,
IT consultants, HR advisors. Includes tier, typical spend per deal,
turnaround time, and firm-level quality scores from past engagements.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class Vendor:
    firm: str
    category: str
    tier: str
    deals_last_24mo: int
    median_spend_per_deal_k: float
    turnaround_days: int
    nps_from_deal_teams: int
    quality_score: int
    partner_contact: str


@dataclass
class CategorySpend:
    category: str
    total_deals: int
    total_spend_mm: float
    median_spend_k: float
    top_vendor: str
    concentration_pct: float


@dataclass
class VendorScorecard:
    firm: str
    on_time_delivery_pct: float
    quality_of_insights: int
    responsiveness: int
    value_for_money: int
    overall_rating: str


@dataclass
class NewVendorPipeline:
    firm: str
    category: str
    referred_by: str
    meeting_scheduled: str
    stage: str
    likelihood_engage_pct: float


@dataclass
class SpendByPhase:
    phase: str
    categories: str
    typical_spend_mm: float
    timeline_weeks: int
    notes: str


@dataclass
class VendorResult:
    total_vendors: int
    total_deals_covered: int
    total_spend_ltm_mm: float
    avg_nps: int
    vendors: List[Vendor]
    categories: List[CategorySpend]
    scorecards: List[VendorScorecard]
    pipeline: List[NewVendorPipeline]
    phase_spend: List[SpendByPhase]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 117):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_vendors() -> List[Vendor]:
    return [
        Vendor("Alvarez & Marsal (A&M)", "QoE / Financial DD", "Tier 1", 18, 425.0, 35, 82, 92, "Sarah K."),
        Vendor("FTI Consulting", "QoE / Financial DD", "Tier 1", 15, 385.0, 32, 78, 88, "Marcus R."),
        Vendor("Deloitte M&A Advisory", "QoE / Financial DD", "Tier 1", 22, 525.0, 38, 72, 85, "Jennifer P."),
        Vendor("KPMG Deal Advisory", "QoE / Financial DD", "Tier 1", 20, 485.0, 36, 75, 86, "David M."),
        Vendor("PwC Deals", "QoE / Financial DD", "Tier 1", 12, 445.0, 40, 72, 82, "Robert L."),
        Vendor("BDO USA", "QoE (mid-market)", "Tier 2", 28, 185.0, 25, 85, 88, "Michelle W."),
        Vendor("Grant Thornton", "QoE (mid-market)", "Tier 2", 18, 225.0, 28, 78, 82, "Patricia H."),
        Vendor("CohnReznick", "QoE (lower-mid)", "Tier 2", 22, 145.0, 22, 82, 85, "James T."),
        # Healthcare-specific
        Vendor("Chartis Group", "Healthcare Strategy / Commercial DD", "Tier 1", 12, 425.0, 45, 85, 90, "Amy S."),
        Vendor("Bain & Company (HC Practice)", "Healthcare Strategy / Commercial DD", "Tier 1", 8, 850.0, 60, 82, 92, "Michael B."),
        Vendor("ECG Management Consultants", "Healthcare Strategy", "Tier 1", 10, 385.0, 42, 80, 85, "Carol D."),
        Vendor("Sullivan Cotter", "Healthcare Physician Comp", "Tier 1", 14, 145.0, 30, 88, 90, "Kevin J."),
        Vendor("MGMA", "Physician Benchmarking", "Tier 2", 22, 45.0, 10, 85, 82, "Janet P."),
        Vendor("Milliman (Healthcare Actuarial)", "Actuarial / MA Pricing", "Tier 1", 8, 285.0, 45, 82, 90, "Thomas K."),
        # Legal
        Vendor("Kirkland & Ellis", "M&A Legal", "Tier 1", 28, 3850.0, 45, 78, 88, "Emily H."),
        Vendor("Ropes & Gray", "M&A Legal", "Tier 1", 22, 3250.0, 42, 82, 90, "Daniel F."),
        Vendor("Latham & Watkins", "M&A Legal", "Tier 1", 18, 3650.0, 48, 75, 85, "Susan R."),
        Vendor("Paul Weiss", "M&A Legal", "Tier 1", 12, 4200.0, 50, 72, 85, "Mark A."),
        Vendor("Proskauer", "Employment / Benefits Counsel", "Tier 1", 25, 485.0, 30, 82, 88, "Lisa W."),
        # IT / Cyber
        Vendor("Guidehouse", "IT/Cyber Diligence", "Tier 1", 18, 225.0, 28, 80, 85, "Brian K."),
        Vendor("Aon Cyber Solutions", "Cyber Diligence", "Tier 2", 12, 145.0, 21, 82, 85, "Samantha L."),
        Vendor("Mercer", "HR / Benefits Diligence", "Tier 1", 25, 165.0, 28, 82, 88, "George H."),
        Vendor("Aon Healthcare", "Insurance / Benefits", "Tier 1", 22, 225.0, 25, 85, 88, "Karen M."),
        # Tax
        Vendor("Ernst & Young Tax", "Tax Diligence & Structuring", "Tier 1", 28, 285.0, 32, 80, 88, "Christopher D."),
        Vendor("Deloitte Tax", "Tax Diligence & Structuring", "Tier 1", 24, 265.0, 30, 78, 85, "Rachel F."),
        # Environmental / Real Estate
        Vendor("EBI Consulting", "Environmental / RE Diligence", "Tier 1", 42, 28.0, 14, 88, 90, "Frank D."),
        # Specialty / Niche
        Vendor("NERA Economic Consulting", "Antitrust Economist", "Tier 1", 6, 825.0, 60, 82, 92, "Professor T."),
        Vendor("CRA International", "Regulatory / Antitrust", "Tier 1", 5, 725.0, 58, 78, 88, "Dr. H."),
        # Insurance / Reps & Warranties
        Vendor("Marsh M&A", "R&W Insurance", "Tier 1", 32, 285.0, 18, 82, 85, "Richard G."),
        Vendor("Aon M&A Insurance", "R&W Insurance", "Tier 1", 28, 265.0, 16, 85, 88, "Laura K."),
    ]


def _build_categories(vendors: List[Vendor]) -> List[CategorySpend]:
    buckets: dict = {}
    for v in vendors:
        buckets.setdefault(v.category, []).append(v)
    rows = []
    for cat, vs in buckets.items():
        total_deals = sum(v.deals_last_24mo for v in vs)
        total_spend = sum(v.deals_last_24mo * v.median_spend_per_deal_k / 1000 for v in vs)
        median_spend = sum(v.median_spend_per_deal_k for v in vs) / len(vs)
        top = max(vs, key=lambda v: v.deals_last_24mo)
        conc = top.deals_last_24mo / total_deals if total_deals else 0
        rows.append(CategorySpend(
            category=cat, total_deals=total_deals, total_spend_mm=round(total_spend, 2),
            median_spend_k=round(median_spend, 1),
            top_vendor=top.firm, concentration_pct=round(conc, 3),
        ))
    return sorted(rows, key=lambda c: c.total_spend_mm, reverse=True)


def _build_scorecards() -> List[VendorScorecard]:
    return [
        VendorScorecard("Alvarez & Marsal (A&M)", 0.95, 88, 85, 82, "A (top-tier)"),
        VendorScorecard("FTI Consulting", 0.92, 85, 82, 85, "A"),
        VendorScorecard("Deloitte M&A Advisory", 0.88, 82, 78, 75, "B+"),
        VendorScorecard("KPMG Deal Advisory", 0.90, 82, 82, 80, "A-"),
        VendorScorecard("BDO USA", 0.95, 85, 88, 92, "A (best-value)"),
        VendorScorecard("Chartis Group", 0.92, 92, 88, 85, "A (HC specialist)"),
        VendorScorecard("Bain HC Practice", 0.85, 95, 78, 68, "A (expensive)"),
        VendorScorecard("Sullivan Cotter", 0.95, 90, 92, 88, "A+ (specialist)"),
        VendorScorecard("Kirkland & Ellis", 0.88, 92, 78, 65, "A (law firm)"),
        VendorScorecard("Ropes & Gray", 0.92, 90, 85, 72, "A"),
        VendorScorecard("Proskauer", 0.90, 88, 85, 82, "A"),
        VendorScorecard("Guidehouse", 0.88, 82, 85, 82, "B+"),
        VendorScorecard("Mercer", 0.92, 85, 85, 85, "A-"),
        VendorScorecard("EBI Consulting", 0.95, 88, 92, 95, "A+ (envelope vendor)"),
        VendorScorecard("Marsh M&A", 0.95, 85, 88, 88, "A"),
    ]


def _build_pipeline() -> List[NewVendorPipeline]:
    return [
        NewVendorPipeline("Riveron Consulting", "QoE / Financial DD", "A&M Alumnus referral", "2025-03-15", "initial meeting", 0.65),
        NewVendorPipeline("Navigant (Guidehouse-spin)", "Healthcare Strategy", "LinkedIn outreach", "2025-03-22", "formal RFP", 0.45),
        NewVendorPipeline("Berkeley Research Group", "Antitrust / Economic", "Kirkland partner ref", "2025-04-02", "initial meeting", 0.55),
        NewVendorPipeline("Charles River Associates", "Regulatory / Industry", "Recent hire ex-FTC", "2025-04-08", "RFP submitted", 0.78),
        NewVendorPipeline("Oliver Wyman Healthcare", "Healthcare Strategy", "CEO connection", "2025-04-15", "initial meeting", 0.42),
        NewVendorPipeline("ERM Group", "ESG / Environmental", "Sustainability lead ref", "2025-04-22", "initial meeting", 0.52),
        NewVendorPipeline("WTW (Willis Towers Watson)", "HR / Benefits", "Switching from Aon", "2025-05-05", "formal pitch", 0.68),
    ]


def _build_phase_spend() -> List[SpendByPhase]:
    return [
        SpendByPhase("IOI / LOI Phase", "QoE-lite, commercial DD, tax scan", 0.185, 3, "Abbreviated scope"),
        SpendByPhase("Deep Diligence (Pre-SPA)", "Full QoE, commercial, tax, legal, cyber, IT",
                     4.25, 6, "Primary spend; concurrent workstreams"),
        SpendByPhase("Confirmatory (Pre-Close)", "Close-out QoE, R&W pre-close updates, cyber pen test",
                     0.85, 4, "Focused confirmation; SPA negotiation overlap"),
        SpendByPhase("Integration Planning (Post-SPA)", "PMO consultant, IT integration planning",
                     0.45, 8, "Ramp parallel with PMI execution"),
        SpendByPhase("Post-Close 100-Day Sprint", "IT stabilization, operational audit, brand",
                     1.2, 14, "Execution-focused; typically 100+ day engagement"),
    ]


def compute_diligence_vendors() -> VendorResult:
    corpus = _load_corpus()

    vendors = _build_vendors()
    categories = _build_categories(vendors)
    scorecards = _build_scorecards()
    pipeline = _build_pipeline()
    phase_spend = _build_phase_spend()

    total_deals = sum(v.deals_last_24mo for v in vendors)
    total_spend = sum(v.deals_last_24mo * v.median_spend_per_deal_k / 1000 for v in vendors)
    avg_nps = int(sum(v.nps_from_deal_teams for v in vendors) / len(vendors))

    return VendorResult(
        total_vendors=len(vendors),
        total_deals_covered=total_deals,
        total_spend_ltm_mm=round(total_spend, 2),
        avg_nps=avg_nps,
        vendors=vendors,
        categories=categories,
        scorecards=scorecards,
        pipeline=pipeline,
        phase_spend=phase_spend,
        corpus_deal_count=len(corpus),
    )
