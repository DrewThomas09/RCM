"""Board of Directors / Governance Tracker.

Portfolio-wide board composition and governance analytics: director
independence, diversity, committee coverage, tenure, meeting attendance,
and governance best-practice scorecard per holdco.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class HoldcoBoard:
    holdco: str
    sector: str
    board_size: int
    independent_directors: int
    independence_pct: float
    diversity_pct: float
    avg_tenure_years: float
    meetings_ltm: int
    attendance_pct: float
    governance_score: int


@dataclass
class DirectorProfile:
    director: str
    holdcos_served: int
    specialty: str
    tenure_years: float
    independent: bool
    diversity_category: str
    committees: str


@dataclass
class CommitteeCoverage:
    holdco: str
    audit_committee: bool
    compensation_committee: bool
    nominating_gov_committee: bool
    risk_committee: bool
    clinical_quality_committee: bool
    esg_committee: bool
    gap_score: int


@dataclass
class SponsorRepresentation:
    sponsor_firm: str
    holdcos: int
    total_board_seats: int
    observer_seats: int
    affiliated_independents: int
    effective_voting_pct: float


@dataclass
class BestPracticeGap:
    practice: str
    holdcos_implemented: int
    holdcos_total: int
    coverage_pct: float
    remediation_owner: str
    priority: str


@dataclass
class ExecCompensation:
    role: str
    median_comp_k: float
    quartile_top_k: float
    quartile_bottom_k: float
    equity_pct: float
    typical_vesting: str


@dataclass
class BoardResult:
    total_holdcos: int
    total_directors: int
    avg_board_size: float
    avg_independence_pct: float
    avg_diversity_pct: float
    avg_governance_score: float
    holdcos: List[HoldcoBoard]
    directors: List[DirectorProfile]
    committees: List[CommitteeCoverage]
    sponsors: List[SponsorRepresentation]
    gaps: List[BestPracticeGap]
    compensation: List[ExecCompensation]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 121):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_holdcos() -> List[HoldcoBoard]:
    items = [
        ("Azalea GI Partners", "Gastroenterology", 9, 4, 12, 11, 32, 88),
        ("Beacon Derm Group", "Dermatology", 7, 3, 10, 10, 28, 82),
        ("Cadence Pathology", "Pathology Labs", 7, 3, 8, 9, 24, 78),
        ("Denali ASC Network", "ASC Platform", 11, 5, 15, 12, 42, 92),
        ("Everest Behavioral Health", "Behavioral Health", 9, 4, 8, 8, 30, 78),
        ("Flagstaff Ortho", "Orthopedics", 7, 3, 10, 11, 26, 85),
        ("Glacier Home Health", "Home Health", 7, 3, 9, 10, 24, 80),
        ("Ironwood Cardiology", "Cardiology", 9, 4, 10, 12, 30, 88),
        ("Juniper Specialty Rx", "Specialty Pharmacy", 7, 3, 8, 9, 26, 82),
        ("Kestrel Fertility", "Fertility / IVF", 9, 4, 12, 10, 32, 88),
        ("Larkspur Dental", "Dental DSO", 7, 3, 9, 10, 22, 75),
        ("Meridian MSK", "MSK Platform", 7, 3, 11, 11, 26, 82),
    ]
    rows = []
    for name, sector, board_size, indep, div_pct, tenure, meetings, score in items:
        rows.append(HoldcoBoard(
            holdco=name,
            sector=sector,
            board_size=board_size,
            independent_directors=indep,
            independence_pct=round(indep / board_size, 4),
            diversity_pct=div_pct / 100,
            avg_tenure_years=tenure / 4,
            meetings_ltm=meetings,
            attendance_pct=0.92,
            governance_score=score,
        ))
    return rows


def _build_directors() -> List[DirectorProfile]:
    return [
        DirectorProfile("Dr. Sarah Chen", 3, "Clinical (CMO alum)", 4.5, True, "female / Asian", "Clinical Quality, Audit"),
        DirectorProfile("Robert Martinez", 4, "Healthcare Operations", 5.2, True, "male / Hispanic", "Compensation, Nominating"),
        DirectorProfile("Dr. Emily Thompson", 2, "Healthcare Strategy (MBB alum)", 3.1, True, "female / white", "Clinical Quality"),
        DirectorProfile("James Patel", 5, "Finance / CFO alum", 6.8, True, "male / Indian", "Audit Chair, Risk"),
        DirectorProfile("Dr. Michael Johnson", 3, "Healthcare IT / HCIT exec", 4.2, True, "male / Black", "Risk, Technology"),
        DirectorProfile("Laura Wang", 2, "Healthcare Policy / Govt Affairs", 2.8, True, "female / Asian", "ESG, Risk"),
        DirectorProfile("David Kim", 4, "Regulatory / Compliance", 5.5, True, "male / Asian", "Compliance, Audit"),
        DirectorProfile("Dr. Jennifer Williams", 2, "Behavioral Health / Clinical", 3.5, True, "female / white", "Clinical Quality"),
        DirectorProfile("Thomas O'Brien", 5, "Payer Relations / MCO alum", 7.2, True, "male / white", "Commercial"),
        DirectorProfile("Rachel Garcia", 3, "HR / People Operations", 4.8, True, "female / Hispanic", "Compensation Chair"),
        DirectorProfile("Kevin Nakamura", 2, "Investment Banker / Healthcare IB alum", 2.5, True, "male / Asian", "Risk, Audit"),
        DirectorProfile("Prof. Amanda Ross", 1, "Academic Medicine / Health Policy", 1.8, True, "female / white", "ESG, Clinical Quality"),
    ]


def _build_committees() -> List[CommitteeCoverage]:
    items = [
        ("Azalea GI Partners", True, True, True, True, True, False, 85),
        ("Beacon Derm Group", True, True, False, True, False, False, 65),
        ("Cadence Pathology", True, True, False, True, True, False, 75),
        ("Denali ASC Network", True, True, True, True, True, True, 100),
        ("Everest Behavioral Health", True, True, False, True, True, False, 75),
        ("Flagstaff Ortho", True, True, True, False, True, False, 75),
        ("Glacier Home Health", True, True, False, True, False, False, 65),
        ("Ironwood Cardiology", True, True, True, True, True, False, 85),
        ("Juniper Specialty Rx", True, True, False, True, False, False, 65),
        ("Kestrel Fertility", True, True, True, True, True, True, 100),
        ("Larkspur Dental", True, True, False, False, False, False, 50),
        ("Meridian MSK", True, True, False, True, False, False, 65),
    ]
    rows = []
    for h, a, c, n, r_, cq, e, score in items:
        rows.append(CommitteeCoverage(
            holdco=h,
            audit_committee=a,
            compensation_committee=c,
            nominating_gov_committee=n,
            risk_committee=r_,
            clinical_quality_committee=cq,
            esg_committee=e,
            gap_score=score,
        ))
    return rows


def _build_sponsors() -> List[SponsorRepresentation]:
    return [
        SponsorRepresentation("Lead PE Sponsor (Platform Investor)", 12, 24, 6, 8, 0.42),
        SponsorRepresentation("Co-Investor A (Strategic Capital)", 4, 4, 2, 0, 0.08),
        SponsorRepresentation("Co-Investor B (Secondary Capital)", 2, 2, 1, 0, 0.04),
        SponsorRepresentation("Management Board Representation", 12, 12, 0, 0, 0.18),
        SponsorRepresentation("Independent / External Directors", 12, 42, 0, 0, 0.28),
    ]


def _build_gaps() -> List[BestPracticeGap]:
    return [
        BestPracticeGap("ESG Committee (formal)", 2, 12, 0.167, "General Counsel", "high"),
        BestPracticeGap("Annual Board Evaluation", 8, 12, 0.667, "Corporate Secretary", "medium"),
        BestPracticeGap("Director Independence Majority", 12, 12, 1.000, "n/a", "complete"),
        BestPracticeGap("Diverse Board (>30% women + minorities)", 5, 12, 0.417, "Nominating Committee", "high"),
        BestPracticeGap("Stand-Alone Risk Committee", 10, 12, 0.833, "Lead Director", "medium"),
        BestPracticeGap("Clinical Quality Committee", 7, 12, 0.583, "CMO", "medium"),
        BestPracticeGap("Cybersecurity Committee Oversight", 4, 12, 0.333, "CIO", "high"),
        BestPracticeGap("Compensation Clawback Policy", 9, 12, 0.750, "Compensation Chair", "medium"),
        BestPracticeGap("Majority Independent Audit Committee", 12, 12, 1.000, "n/a", "complete"),
        BestPracticeGap("Board Meeting Attendance >90%", 11, 12, 0.917, "Lead Director", "low"),
    ]


def _build_compensation() -> List[ExecCompensation]:
    return [
        ExecCompensation("CEO", 485.0, 650.0, 385.0, 0.035, "4-year, 25% annual vest"),
        ExecCompensation("CFO", 285.0, 385.0, 225.0, 0.018, "4-year, 25% annual vest"),
        ExecCompensation("COO", 325.0, 425.0, 265.0, 0.022, "4-year, 25% annual vest"),
        ExecCompensation("CMO (Chief Medical Officer)", 325.0, 425.0, 285.0, 0.018, "3-year, cliff + annual"),
        ExecCompensation("Chief Legal Officer", 245.0, 325.0, 195.0, 0.012, "4-year, 25% annual vest"),
        ExecCompensation("CHRO", 225.0, 285.0, 185.0, 0.010, "4-year, 25% annual vest"),
        ExecCompensation("CIO / CTO", 265.0, 365.0, 215.0, 0.015, "4-year, 25% annual vest"),
        ExecCompensation("Chief Revenue Officer", 285.0, 385.0, 225.0, 0.015, "4-year, 25% annual vest"),
        ExecCompensation("Chief Compliance Officer", 215.0, 285.0, 175.0, 0.008, "4-year, 25% annual vest"),
        ExecCompensation("Independent Director (Avg)", 125.0, 185.0, 85.0, 0.005, "Annual retainer + meeting fees"),
        ExecCompensation("Lead Independent Director", 185.0, 245.0, 145.0, 0.008, "Annual retainer + chair premium"),
        ExecCompensation("Committee Chair Premium", 35.0, 55.0, 25.0, 0.0, "Additional retainer"),
    ]


def compute_board_governance() -> BoardResult:
    corpus = _load_corpus()

    holdcos = _build_holdcos()
    directors = _build_directors()
    committees = _build_committees()
    sponsors = _build_sponsors()
    gaps = _build_gaps()
    compensation = _build_compensation()

    avg_size = sum(h.board_size for h in holdcos) / len(holdcos) if holdcos else 0
    avg_indep = sum(h.independence_pct for h in holdcos) / len(holdcos) if holdcos else 0
    avg_div = sum(h.diversity_pct for h in holdcos) / len(holdcos) if holdcos else 0
    avg_gov = sum(h.governance_score for h in holdcos) / len(holdcos) if holdcos else 0
    total_directors = sum(h.board_size for h in holdcos)

    return BoardResult(
        total_holdcos=len(holdcos),
        total_directors=total_directors,
        avg_board_size=round(avg_size, 1),
        avg_independence_pct=round(avg_indep, 4),
        avg_diversity_pct=round(avg_div, 4),
        avg_governance_score=round(avg_gov, 1),
        holdcos=holdcos,
        directors=directors,
        committees=committees,
        sponsors=sponsors,
        gaps=gaps,
        compensation=compensation,
        corpus_deal_count=len(corpus),
    )
