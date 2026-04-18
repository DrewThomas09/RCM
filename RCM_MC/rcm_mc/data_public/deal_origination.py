"""Deal Origination / M&A Pipeline Tracker.

Models deal flow for a PE healthcare fund — active pipeline, broker
relationships, sector white-space, win/loss analysis, and sourcing velocity.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PipelineDeal:
    deal_name: str
    sector: str
    stage: str
    est_ev_mm: float
    target_ebitda_mm: float
    entry_multiple_proposed: float
    probability_pct: float
    weighted_ev_mm: float
    source: str
    owner: str
    next_milestone_date: str


@dataclass
class BrokerRelationship:
    banker_firm: str
    banker_type: str
    deals_seen_ltm: int
    deals_engaged_ltm: int
    deals_won_ltm: int
    win_rate_pct: float
    avg_deal_size_mm: float
    relationship_score: int


@dataclass
class SectorWhitespace:
    sector: str
    active_targets: int
    platforms_deployed: int
    concentration_pct: float
    whitespace_score: int
    priority: str


@dataclass
class WinLossAnalysis:
    category: str
    won: int
    lost_price: int
    lost_strategy: int
    lost_seller_relationship: int
    pass_rate_pct: float


@dataclass
class SourcingVelocity:
    quarter: str
    deals_screened: int
    deals_diligenced: int
    loi_signed: int
    closed: int
    conversion_rate_pct: float


@dataclass
class DealOriginationResult:
    total_pipeline_ev_mm: float
    weighted_pipeline_ev_mm: float
    active_deals: int
    loi_stage: int
    closing_stage: int
    pipeline: List[PipelineDeal]
    bankers: List[BrokerRelationship]
    whitespace: List[SectorWhitespace]
    winloss: List[WinLossAnalysis]
    velocity: List[SourcingVelocity]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 96):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_pipeline() -> List[PipelineDeal]:
    items = [
        ("Project Azalea (GI Network SE)", "Gastroenterology Practice", "LOI", 285.0, 22.0, 13.0, 0.75, "Jefferies", "JK"),
        ("Project Beacon (Dermatology W)", "Medical Dermatology", "Diligence", 185.0, 14.5, 12.8, 0.45, "Harris Williams", "SR"),
        ("Project Cypress (OB/GYN TX)", "Women's Health / OB", "Diligence", 145.0, 11.5, 12.6, 0.35, "Lincoln Intl", "MN"),
        ("Project Denali (ASC Platform NW)", "ASC Network", "IC Review", 425.0, 32.0, 13.3, 0.55, "Raymond James", "JK"),
        ("Project Everest (Behavioral SE)", "Behavioral Health", "LOI", 325.0, 26.0, 12.5, 0.65, "William Blair", "DT"),
        ("Project Flagstaff (Orthopedic)", "Orthopedics", "Screening", 225.0, 18.0, 12.5, 0.25, "Houlihan Lokey", "SR"),
        ("Project Glacier (Home Health)", "Home Health", "Diligence", 165.0, 14.0, 11.8, 0.40, "KPMG CF", "MN"),
        ("Project Harbor (Urgent Care)", "Urgent Care", "Screening", 95.0, 8.5, 11.2, 0.20, "Provident HP", "JK"),
        ("Project Ironwood (Cardiology Mid-Atl)", "Cardiology Practice", "IC Review", 385.0, 28.0, 13.8, 0.60, "Evercore", "DT"),
        ("Project Juniper (Specialty Pharmacy)", "Specialty Pharmacy", "LOI", 225.0, 17.5, 12.9, 0.70, "Houlihan Lokey", "SR"),
        ("Project Kestrel (Fertility National)", "Fertility / IVF", "Closing", 475.0, 36.0, 13.2, 0.90, "Jefferies", "DT"),
        ("Project Larkspur (Dental DSO)", "Dental DSO", "Screening", 85.0, 7.2, 11.8, 0.15, "Cain Brothers", "MN"),
        ("Project Meridian (MSK Platform)", "MSK Platform", "Diligence", 325.0, 24.0, 13.5, 0.50, "Lincoln Intl", "JK"),
    ]
    rows = []
    for name, sector, stage, ev, ebitda, mult, prob, broker, owner in items:
        weighted = ev * prob
        milestone = {
            "Screening": "2026-05-15 — Management meeting",
            "Diligence": "2026-05-22 — QoE complete",
            "IC Review": "2026-05-10 — IC vote",
            "LOI": "2026-06-01 — Definitive agreement",
            "Closing": "2026-04-30 — Closing",
        }.get(stage, "TBD")
        rows.append(PipelineDeal(
            deal_name=name, sector=sector, stage=stage,
            est_ev_mm=ev, target_ebitda_mm=ebitda,
            entry_multiple_proposed=mult,
            probability_pct=prob,
            weighted_ev_mm=round(weighted, 2),
            source=broker, owner=owner,
            next_milestone_date=milestone,
        ))
    return rows


def _build_bankers() -> List[BrokerRelationship]:
    items = [
        ("Jefferies Healthcare", "Bulge Bracket", 42, 18, 4, 0.22, 385.0, 92),
        ("Harris Williams", "Middle Market", 68, 28, 6, 0.21, 245.0, 88),
        ("William Blair", "Middle Market", 55, 22, 5, 0.23, 285.0, 85),
        ("Evercore Healthcare", "Elite Boutique", 35, 14, 3, 0.21, 485.0, 82),
        ("Houlihan Lokey", "Middle Market", 48, 20, 4, 0.20, 225.0, 78),
        ("Raymond James Healthcare", "Middle Market", 62, 24, 5, 0.21, 195.0, 75),
        ("Lincoln International", "Middle Market", 52, 22, 4, 0.18, 175.0, 72),
        ("Cain Brothers", "Healthcare Boutique", 28, 10, 2, 0.20, 125.0, 68),
        ("Provident Healthcare Partners", "Healthcare Boutique", 24, 8, 2, 0.25, 95.0, 65),
        ("KPMG Corporate Finance", "Accounting/Advisory", 32, 12, 1, 0.083, 165.0, 58),
        ("TripleTree", "Healthcare Boutique", 22, 9, 2, 0.22, 135.0, 70),
        ("Greenhill Healthcare", "Elite Boutique", 18, 6, 1, 0.167, 425.0, 62),
    ]
    rows = []
    for firm, btype, seen, eng, won, win_rate, size, score in items:
        rows.append(BrokerRelationship(
            banker_firm=firm, banker_type=btype,
            deals_seen_ltm=seen, deals_engaged_ltm=eng, deals_won_ltm=won,
            win_rate_pct=win_rate, avg_deal_size_mm=size,
            relationship_score=score,
        ))
    return rows


def _build_whitespace(corpus: List[dict]) -> List[SectorWhitespace]:
    import hashlib
    sector_counts: dict = {}
    for d in corpus:
        s = d.get("sector") or ""
        if s:
            sector_counts[s] = sector_counts.get(s, 0) + 1
    total = sum(sector_counts.values())

    sectors_of_interest = [
        ("Women's Health / OB", "high"),
        ("Fertility / IVF", "high"),
        ("Behavioral Health", "high"),
        ("Home Infusion", "high"),
        ("ASC Network", "medium"),
        ("Dermatology Group", "medium"),
        ("Orthopedics", "medium"),
        ("Medical Devices", "medium"),
        ("Urgent Care", "medium"),
        ("Ophthalmology", "medium"),
        ("Pediatric Therapy", "high"),
        ("Anesthesiology", "low"),
        ("Radiology", "low"),
        ("Urology", "medium"),
        ("Rheumatology", "medium"),
    ]
    rows = []
    for sector, priority in sectors_of_interest:
        h = int(hashlib.md5(sector.encode()).hexdigest()[:6], 16)
        platforms = sector_counts.get(sector, 0)
        # Whitespace is inverse of concentration
        conc = platforms / total if total else 0
        whitespace = max(15, min(95, int(95 - conc * 500 - (h % 20))))
        active = (h % 8) + 2
        rows.append(SectorWhitespace(
            sector=sector,
            active_targets=active,
            platforms_deployed=platforms,
            concentration_pct=round(conc, 4),
            whitespace_score=whitespace,
            priority=priority,
        ))
    return sorted(rows, key=lambda r: r.whitespace_score, reverse=True)


def _build_winloss() -> List[WinLossAnalysis]:
    return [
        WinLossAnalysis("Lost on Price", 0, 42, 0, 0, 0.0),
        WinLossAnalysis("Lost on Strategic Fit", 0, 0, 18, 0, 0.0),
        WinLossAnalysis("Lost on Seller Relationship", 0, 0, 0, 15, 0.0),
        WinLossAnalysis("Won (Closed)", 8, 0, 0, 0, 0.095),
        WinLossAnalysis("Passed - Quality Issues", 0, 12, 0, 0, 0.0),
        WinLossAnalysis("Passed - Strategic", 0, 8, 0, 0, 0.0),
        WinLossAnalysis("Passed - Timing", 0, 0, 5, 0, 0.0),
    ]


def _build_velocity() -> List[SourcingVelocity]:
    return [
        SourcingVelocity("2025Q1", 142, 28, 9, 2, 0.0141),
        SourcingVelocity("2025Q2", 156, 32, 12, 3, 0.0192),
        SourcingVelocity("2025Q3", 168, 38, 14, 3, 0.0179),
        SourcingVelocity("2025Q4", 138, 29, 11, 2, 0.0145),
        SourcingVelocity("2026Q1", 152, 35, 13, 3, 0.0197),
    ]


def compute_deal_origination() -> DealOriginationResult:
    corpus = _load_corpus()

    pipeline = _build_pipeline()
    bankers = _build_bankers()
    whitespace = _build_whitespace(corpus)
    winloss = _build_winloss()
    velocity = _build_velocity()

    total_ev = sum(d.est_ev_mm for d in pipeline)
    weighted_ev = sum(d.weighted_ev_mm for d in pipeline)
    loi = sum(1 for d in pipeline if d.stage == "LOI")
    closing = sum(1 for d in pipeline if d.stage == "Closing")

    return DealOriginationResult(
        total_pipeline_ev_mm=round(total_ev, 2),
        weighted_pipeline_ev_mm=round(weighted_ev, 2),
        active_deals=len(pipeline),
        loi_stage=loi,
        closing_stage=closing,
        pipeline=pipeline,
        bankers=bankers,
        whitespace=whitespace,
        winloss=winloss,
        velocity=velocity,
        corpus_deal_count=len(corpus),
    )
