"""Competitive Intelligence Dashboard — track competitors and identify share shift opportunities.

For each sector, builds:
- Top competitor landscape with estimated market share
- Strategic move tracker (acquisitions, capital raises, expansion)
- Relative strength scoring (scale, geography, payer access, VBC position)
- Threat level to portfolio co
- Share-shift / white-space opportunities
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Competitor catalog (representative leaders per sector)
# ---------------------------------------------------------------------------

_COMPETITOR_CATALOG = {
    "Physician Services": [
        ("Optum Health (UnitedHealth)", "Strategic", 8.5, "National", 5000,
         "Vertical integration w/ payer", "scale"),
        ("CVS Health / Oak Street", "Strategic", 3.2, "National", 1200,
         "Senior PC roll-up + payer ownership", "scale"),
        ("Privia Health", "Public", 2.8, "Multi-state", 2800,
         "Technology-enabled MSO", "tech"),
        ("American Physician Partners", "PE (Warburg)", 1.2, "Southeast", 900,
         "ED + hospitalist focus", "focused"),
        ("TeamHealth", "PE (Blackstone)", 1.5, "National", 1500,
         "Hospital-based physician staffing", "scale"),
    ],
    "Dermatology": [
        ("US Dermatology Partners", "PE (ABRY)", 12.5, "Multi-state", 125,
         "Large platform roll-up", "scale"),
        ("Epiphany Dermatology", "PE (Ares)", 8.2, "Multi-state", 95,
         "Consolidator", "scale"),
        ("QualDerm Partners", "PE (Harvest)", 6.8, "Southeast/Midwest", 78,
         "Regional focus", "focused"),
        ("SkinLogix (formerly Pinnacle Derm)", "PE (Goldman)", 5.5, "National", 65,
         "Technology-enabled", "tech"),
        ("United Derm Partners", "PE (Nautic)", 4.2, "Sun Belt", 48,
         "De novo expansion", "focused"),
    ],
    "Home Health": [
        ("Encompass Health (HH division)", "Public", 8.5, "National", 375,
         "Integrated with rehab hospital", "scale"),
        ("Amedisys", "Public", 7.2, "National", 430,
         "Pure-play HH/hospice", "focused"),
        ("Enhabit (spin of Encompass)", "Public", 5.8, "National", 280,
         "Specialized care", "focused"),
        ("BrightSpring Health", "PE (KKR)", 4.5, "National", 350,
         "Multi-service provider", "scale"),
        ("LHC Group (UnitedHealth)", "Strategic", 9.2, "National", 400,
         "Vertical integration w/ payer", "scale"),
    ],
    "Dialysis": [
        ("DaVita", "Public", 35.0, "National", 2700,
         "Duopoly leader", "scale"),
        ("Fresenius Medical Care", "Public", 30.5, "National", 2500,
         "Vertically integrated (devices+care)", "scale"),
        ("US Renal Care", "PE (Bain)", 5.8, "Multi-state", 340,
         "3rd largest operator", "scale"),
        ("American Renal Associates", "PE (Centerbridge)", 3.2, "Multi-state", 250,
         "JV with nephrologists", "focused"),
    ],
    "Behavioral Health": [
        ("Acadia Healthcare", "Public", 8.5, "National", 260,
         "Inpatient + residential", "scale"),
        ("Universal Health (BH division)", "Public", 7.2, "National", 380,
         "Hospital-based BH", "scale"),
        ("BayMark Partners", "PE (Webster)", 4.5, "National", 145,
         "Addiction treatment focus", "focused"),
        ("LifeStance Health", "Public", 3.8, "National", 650,
         "Outpatient mental health roll-up", "tech"),
        ("Pathways Health / Summit BHC", "PE (FFL)", 2.8, "Multi-state", 180,
         "Integrated BH services", "focused"),
    ],
    "ASC": [
        ("USPI / United Surgical Partners", "Strategic (Tenet)", 15.8, "National", 470,
         "Market leader", "scale"),
        ("SCA Health (Optum)", "Strategic (UHG)", 12.5, "National", 330,
         "Payer-owned ASC network", "scale"),
        ("SurgCenter Development", "PE (Welsh Carson)", 8.2, "National", 180,
         "Development + joint ventures", "scale"),
        ("ValueHealth / CompuSurg", "PE (Evergreen)", 5.5, "Multi-state", 85,
         "Specialty focus", "focused"),
    ],
    "Primary Care": [
        ("Oak Street Health (CVS)", "Strategic", 4.5, "National", 250,
         "Senior-focused PCPs w/ MA risk", "focused"),
        ("ChenMed (JenCare / Chen)", "Private", 3.8, "Multi-state", 145,
         "Senior PC risk-based", "focused"),
        ("Iora Health / One Medical (Amazon)", "Strategic (Amazon)", 2.2, "National", 200,
         "Tech + PC combined", "tech"),
        ("VillageMD (Walgreens)", "Strategic", 3.5, "National", 720,
         "Retail + PC integration", "scale"),
        ("Cano Health", "Public", 1.8, "FL/TX", 170,
         "Risk-based MA focus", "focused"),
    ],
    "Default": [
        ("Large Strategic Incumbent", "Strategic", 15.0, "National", 500,
         "Scale advantage", "scale"),
        ("PE-Backed Platform #1", "PE", 8.5, "Multi-state", 250,
         "Active consolidator", "scale"),
        ("PE-Backed Platform #2", "PE", 6.8, "Regional", 180,
         "Tuck-in roll-up", "focused"),
        ("Public Mid-cap", "Public", 5.2, "National", 320,
         "Operational excellence", "focused"),
        ("Emerging / Tech-enabled", "Growth Eq", 2.5, "Emerging", 85,
         "AI / tech differentiation", "tech"),
    ],
}


# ---------------------------------------------------------------------------
# Strategic moves (recent events)
# ---------------------------------------------------------------------------

_RECENT_MOVES = [
    ("2025-Q1", "US Dermatology Partners", "Acquisition", 85.0,
     "Acquired Pacific NW Derm (6 clinics)", "medium"),
    ("2024-Q4", "Optum Health", "Expansion", 0.0,
     "Opened 12 new clinics in AZ/NV/CO", "high"),
    ("2024-Q4", "Privia Health", "Capital Raise", 450.0,
     "Secondary offering to fund MSO expansion", "low"),
    ("2024-Q3", "LifeStance Health", "Restructuring", 0.0,
     "CEO transition + 200 clinician layoffs", "low"),
    ("2024-Q3", "Village MD / Walgreens", "Divestiture", -1800.0,
     "Walgreens writing down investment, potential sale", "high"),
    ("2024-Q2", "BrightSpring Health", "IPO", 630.0,
     "Public offering raised growth capital", "medium"),
    ("2024-Q2", "ChenMed", "Expansion", 0.0,
     "Entered 4 new states (GA, NC, SC, AL)", "medium"),
    ("2024-Q1", "Acadia Healthcare", "Acquisition", 125.0,
     "Bought Turning Point Centers (2 facilities)", "low"),
    ("2023-Q4", "Oak Street Health", "M&A", -10000.0,
     "Acquired by CVS for $10.6B", "high"),
    ("2023-Q3", "Summit BHC", "Recapitalization", 0.0,
     "FFL-led dividend recap", "low"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Competitor:
    name: str
    ownership: str              # "Public", "PE (firm)", "Strategic"
    est_market_share_pct: float
    footprint: str
    est_revenue_mm: float
    positioning: str
    competitive_strategy: str   # "scale", "focused", "tech"
    threat_level: str           # "high", "medium", "low"


@dataclass
class StrategicMove:
    quarter: str
    company: str
    move_type: str              # "Acquisition", "IPO", "Capital Raise", etc.
    value_mm: float
    description: str
    threat_to_us: str


@dataclass
class CompetitorVsUs:
    dimension: str
    our_score: int              # 0-100
    top_competitor_score: int
    gap: int
    action: str


@dataclass
class ShareShiftOpportunity:
    segment: str
    current_leader: str
    displacement_pct: float
    implied_revenue_mm: float
    time_horizon: str
    feasibility: str


@dataclass
class CompetitiveIntelResult:
    sector: str
    our_market_share_est: float
    top_5_share: float
    market_hhi: int
    competitors: List[Competitor]
    recent_moves: List[StrategicMove]
    vs_us: List[CompetitorVsUs]
    share_opportunities: List[ShareShiftOpportunity]
    competitive_intensity_score: int
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 73):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _get_competitors(sector: str) -> List[tuple]:
    return _COMPETITOR_CATALOG.get(sector, _COMPETITOR_CATALOG["Default"])


def _build_competitors(sector: str) -> List[Competitor]:
    raw = _get_competitors(sector)
    rows = []
    for name, own, share, footprint, rev, pos, strategy in raw:
        threat = "high" if share >= 8 else ("medium" if share >= 3 else "low")
        rows.append(Competitor(
            name=name, ownership=own,
            est_market_share_pct=round(share, 2),
            footprint=footprint,
            est_revenue_mm=round(rev, 1),
            positioning=pos,
            competitive_strategy=strategy,
            threat_level=threat,
        ))
    return rows


def _filter_moves(sector: str, competitors: List[Competitor]) -> List[StrategicMove]:
    comp_names = {c.name for c in competitors}
    rows = []
    for q, co, mtype, val, desc, threat in _RECENT_MOVES:
        # Include if company matches or if this is a sector-relevant event
        if co in comp_names or any(cn.split()[0] in co for cn in comp_names):
            rows.append(StrategicMove(
                quarter=q, company=co, move_type=mtype,
                value_mm=round(val, 1),
                description=desc, threat_to_us=threat,
            ))
    # Always include a minimum of 5
    if len(rows) < 5:
        extra = [m for m in _RECENT_MOVES if m[1] not in {r.company for r in rows}][:10 - len(rows)]
        for q, co, mtype, val, desc, threat in extra:
            rows.append(StrategicMove(
                quarter=q, company=co, move_type=mtype,
                value_mm=round(val, 1),
                description=desc, threat_to_us=threat,
            ))
    return rows


def _build_vs_us() -> List[CompetitorVsUs]:
    return [
        CompetitorVsUs("Scale (Revenue)", 45, 85, -40,
                       "Accelerate M&A to close gap"),
        CompetitorVsUs("Geographic Footprint", 38, 92, -54,
                       "Expand Sun Belt presence"),
        CompetitorVsUs("Payer Access (Commercial)", 72, 88, -16,
                       "Target UHC/Aetna network expansion"),
        CompetitorVsUs("Payer Access (Medicare Advantage)", 58, 85, -27,
                       "Pursue MA risk contracts"),
        CompetitorVsUs("Technology / Platform", 68, 82, -14,
                       "Deploy clinical AI, RCM automation"),
        CompetitorVsUs("VBC Readiness", 65, 78, -13,
                       "Build VBC infrastructure (ACO enrollment)"),
        CompetitorVsUs("Clinical Quality / Stars", 72, 80, -8,
                       "Quality bonus program investment"),
        CompetitorVsUs("Brand / Marketing", 42, 78, -36,
                       "National brand buildout required"),
        CompetitorVsUs("Provider Network Size", 55, 88, -33,
                       "Recruiting / M&A flywheel"),
        CompetitorVsUs("RCM / Revenue Operations", 70, 85, -15,
                       "Consolidate platforms, automate denials"),
    ]


def _build_opportunities(revenue_mm: float) -> List[ShareShiftOpportunity]:
    return [
        ShareShiftOpportunity(
            segment="Commercial Self-Insured Employer",
            current_leader="Optum Health / UnitedHealth",
            displacement_pct=0.15,
            implied_revenue_mm=round(revenue_mm * 0.15, 2),
            time_horizon="24-36 months",
            feasibility="medium",
        ),
        ShareShiftOpportunity(
            segment="Medicare Advantage Lives (local market)",
            current_leader="CVS Oak Street",
            displacement_pct=0.08,
            implied_revenue_mm=round(revenue_mm * 0.08, 2),
            time_horizon="36 months",
            feasibility="medium",
        ),
        ShareShiftOpportunity(
            segment="Commercial Specialist Network",
            current_leader="Privia Health",
            displacement_pct=0.12,
            implied_revenue_mm=round(revenue_mm * 0.12, 2),
            time_horizon="18 months",
            feasibility="high",
        ),
        ShareShiftOpportunity(
            segment="Rural / Underserved Geography",
            current_leader="Regional independent practices",
            displacement_pct=0.22,
            implied_revenue_mm=round(revenue_mm * 0.22, 2),
            time_horizon="24-48 months",
            feasibility="medium",
        ),
        ShareShiftOpportunity(
            segment="Payer Platform Entry (Aetna, Cigna)",
            current_leader="Incumbent networks",
            displacement_pct=0.06,
            implied_revenue_mm=round(revenue_mm * 0.06, 2),
            time_horizon="18-24 months",
            feasibility="high",
        ),
        ShareShiftOpportunity(
            segment="Corporate Occ Health Accounts",
            current_leader="Concentra / US HealthWorks",
            displacement_pct=0.04,
            implied_revenue_mm=round(revenue_mm * 0.04, 2),
            time_horizon="12-24 months",
            feasibility="medium",
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_competitive_intel(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    our_market_share_pct: float = 0.8,
) -> CompetitiveIntelResult:
    corpus = _load_corpus()

    competitors = _build_competitors(sector)
    moves = _filter_moves(sector, competitors)
    vs_us = _build_vs_us()
    opps = _build_opportunities(revenue_mm)

    top_5_share = sum(c.est_market_share_pct for c in competitors[:5])
    hhi = int(sum(c.est_market_share_pct ** 2 for c in competitors) * 100)
    # Competitive intensity: HHI + threat count
    high_threats = sum(1 for c in competitors if c.threat_level == "high")
    intensity = min(100, hhi // 20 + high_threats * 10 + 25)

    return CompetitiveIntelResult(
        sector=sector,
        our_market_share_est=round(our_market_share_pct, 2),
        top_5_share=round(top_5_share, 1),
        market_hhi=hhi,
        competitors=competitors,
        recent_moves=moves,
        vs_us=vs_us,
        share_opportunities=opps,
        competitive_intensity_score=intensity,
        corpus_deal_count=len(corpus),
    )
