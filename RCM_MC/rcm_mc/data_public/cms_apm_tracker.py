"""CMS Innovation Models / APM (Alternative Payment Model) Tracker.

Tracks CMS Innovation Center (CMMI) and CMS Medicare APMs that drive
healthcare sector economics: ACO REACH, MSSP, BPCI-A, Primary Care
First, Kidney Care Choices, etc. PE-critical for provider-services
diligence.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class APMProgram:
    program: str
    program_type: str
    lives_covered_m: float
    participants: int
    total_payments_b: float
    risk_structure: str
    savings_rate_pct: float
    active_through: str
    status: str


@dataclass
class PortfolioExposure:
    deal: str
    sector: str
    apm_programs: str
    lives_covered_k: float
    apm_revenue_m: float
    apm_share_of_rev_pct: float
    net_savings_m: float
    quality_score: float


@dataclass
class PerformanceTrend:
    year: int
    program: str
    participants: int
    gross_spend_b: float
    gross_savings_b: float
    savings_rate_pct: float
    quality_score: float


@dataclass
class RiskStructureOption:
    structure: str
    upside_share_pct: float
    downside_share_pct: float
    typical_participants: int
    typical_savings_rate_pct: float
    suitability: str


@dataclass
class PolicyCalendar:
    event: str
    event_date: str
    impact: str
    affected_programs: str
    portfolio_exposure_m: float


@dataclass
class PayerAdjacency:
    commercial_ma_track: str
    programs: int
    lives_m: float
    commercial_spread_bps: int
    market_penetration_pct: float
    sponsor_activity: str


@dataclass
class APMResult:
    total_programs: int
    total_lives_covered_m: float
    total_apm_payments_b: float
    avg_savings_rate_pct: float
    total_portfolio_apm_revenue_m: float
    portfolio_share_at_risk_pct: float
    programs: List[APMProgram]
    exposures: List[PortfolioExposure]
    trends: List[PerformanceTrend]
    risk_structures: List[RiskStructureOption]
    calendar: List[PolicyCalendar]
    payer_adjacency: List[PayerAdjacency]
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


def _build_programs() -> List[APMProgram]:
    return [
        APMProgram("Medicare Shared Savings Program (MSSP)", "ACO / Total-Cost", 10.85, 483, 132.5,
                   "Upside (Basic) or 2-sided (Enhanced)", 1.8, "2028+", "permanent"),
        APMProgram("ACO REACH", "ACO / Total-Cost (FFS beneficiaries)", 2.65, 132, 42.5,
                   "2-sided full risk / global cap", 3.2, "2026", "sunset scheduled"),
        APMProgram("Primary Care First (PCF)", "Primary Care Capitation", 3.45, 1580, 12.8,
                   "Capitation + PBAC", 2.1, "2026", "sunset scheduled"),
        APMProgram("Making Care Primary (MCP)", "Primary Care", 1.85, 540, 5.2,
                   "FFS with uplift (tracks 1-3)", 1.5, "2034", "new / ramping"),
        APMProgram("BPCI Advanced", "Bundled Payment (episode)", 1.2, 220, 18.5,
                   "Retrospective 2-sided risk", 2.8, "2025-Q4", "sunset"),
        APMProgram("Comprehensive Kidney Care Choices (CKCC)", "Kidney Care", 0.375, 145, 6.8,
                   "2-sided (Graduated/Professional/Global)", 4.5, "2026", "active"),
        APMProgram("ESRD Treatment Choices", "Kidney Care (mandatory)", 0.52, 7800, 8.2,
                   "Payment adjustments", 0.8, "ongoing", "active"),
        APMProgram("Enhancing Oncology Model (EOM)", "Oncology Bundle", 0.125, 67, 2.8,
                   "Retrospective 2-sided risk", 1.8, "2030", "active"),
        APMProgram("Cell and Gene Therapy Access Model (CGT)", "Medicaid Cell/Gene", 0.005, 9, 0.35,
                   "State-level outcomes-based", 2.5, "2030", "pilot"),
        APMProgram("Innovation in Behavioral Health (IBH)", "Behavioral Health", 0.475, 95, 3.8,
                   "Shared savings + incentives", 2.2, "2031", "new / ramping"),
        APMProgram("States Advancing All-Payer Health Equity (AHEAD)", "State-Level Total-Cost", 1.25, 4, 12.5,
                   "State global budgets", 2.5, "2034", "new / ramping"),
        APMProgram("Transforming Episode Accountability (TEAM)", "Episode (mandatory MSK)", 1.45, 742, 22.5,
                   "Mandatory 2-sided risk", 2.5, "2030", "new / ramping"),
        APMProgram("Global & Professional Direct Contracting (GPDC)", "ACO Pred. — archived", 0.0, 0, 0.0,
                   "(replaced by ACO REACH)", 0.0, "retired", "retired"),
        APMProgram("Medicare Advantage Value-Based Insurance Design (VBID)", "MA Supplemental", 0.0, 0, 0.0,
                   "(concluded 2024)", 0.0, "retired", "retired"),
    ]


def _build_exposures() -> List[PortfolioExposure]:
    return [
        PortfolioExposure("Project Magnolia — MSK", "MSK / Ortho",
                          "BPCI-A, TEAM, MSSP (track)", 165.0, 52.0, 0.145, 4.2, 86.5),
        PortfolioExposure("Project Cypress — GI Network", "Gastroenterology",
                          "MSSP Enhanced, commercial VBC", 185.0, 68.0, 0.115, 5.8, 88.5),
        PortfolioExposure("Project Redwood — Behavioral", "Behavioral Health",
                          "IBH, MSSP (participant)", 125.0, 38.0, 0.165, 2.5, 82.5),
        PortfolioExposure("Project Laurel — Derma", "Dermatology",
                          "MSSP (primary care adjacency)", 85.0, 12.0, 0.048, 0.8, 84.5),
        PortfolioExposure("Project Cedar — Cardiology", "Cardiology",
                          "MSSP, BPCI-A (cardiac bundles)", 210.0, 85.0, 0.165, 6.5, 87.8),
        PortfolioExposure("Project Willow — Fertility", "Fertility / IVF",
                          "commercial VBC, employer direct", 68.0, 18.0, 0.065, 1.2, 86.0),
        PortfolioExposure("Project Spruce — Radiology", "Radiology",
                          "MSSP (partnership), CKCC adjacency", 120.0, 22.0, 0.068, 1.8, 84.2),
        PortfolioExposure("Project Aspen — Eye Care", "Eye Care",
                          "MSSP (primary care adjacency)", 95.0, 15.0, 0.058, 1.0, 85.0),
        PortfolioExposure("Project Maple — Urology", "Urology",
                          "MSSP, ACO REACH partnership", 88.0, 24.0, 0.145, 2.2, 85.5),
        PortfolioExposure("Project Ash — Infusion", "Infusion",
                          "EOM, commercial VBC", 55.0, 18.0, 0.088, 1.5, 87.2),
        PortfolioExposure("Project Fir — Lab / Pathology", "Lab Services",
                          "MSSP partnership, commercial quality", 215.0, 42.0, 0.098, 2.8, 86.8),
        PortfolioExposure("Project Oak — RCM SaaS", "RCM",
                          "Enables VBC via platform capabilities", 0.0, 65.0, 0.232, 0.0, 89.5),
        PortfolioExposure("Project Sage — Home Health", "Home Health",
                          "Home Health VBP, MSSP, MCP", 145.0, 52.0, 0.188, 3.5, 88.0),
        PortfolioExposure("Project Linden — Behavioral", "Behavioral Health",
                          "IBH, MCP, MSSP", 95.0, 32.0, 0.198, 2.0, 85.0),
        PortfolioExposure("Project Basil — Dental DSO", "Dental DSO",
                          "Medicaid (state-level)", 180.0, 28.0, 0.068, 1.8, 84.5),
        PortfolioExposure("Project Thyme — Specialty Pharm", "Specialty Pharma",
                          "EOM, 340B integration", 65.0, 38.0, 0.115, 2.5, 88.5),
    ]


def _build_trends() -> List[PerformanceTrend]:
    return [
        PerformanceTrend(2020, "MSSP (aggregate)", 513, 122.5, 1.2, 1.0, 87.2),
        PerformanceTrend(2021, "MSSP (aggregate)", 478, 128.5, 1.7, 1.3, 87.5),
        PerformanceTrend(2022, "MSSP (aggregate)", 483, 130.8, 1.8, 1.4, 87.8),
        PerformanceTrend(2023, "MSSP (aggregate)", 483, 132.5, 2.3, 1.8, 88.2),
        PerformanceTrend(2024, "MSSP (aggregate)", 483, 135.2, 2.5, 1.9, 88.5),
        PerformanceTrend(2021, "ACO REACH / DC", 99, 30.5, 1.1, 3.6, 88.5),
        PerformanceTrend(2022, "ACO REACH / DC", 132, 38.5, 1.3, 3.4, 88.8),
        PerformanceTrend(2023, "ACO REACH / DC", 132, 41.2, 1.4, 3.4, 89.0),
        PerformanceTrend(2024, "ACO REACH / DC", 132, 42.5, 1.5, 3.5, 89.2),
        PerformanceTrend(2022, "BPCI Advanced", 220, 17.5, 0.48, 2.7, 86.8),
        PerformanceTrend(2023, "BPCI Advanced", 220, 18.2, 0.52, 2.9, 87.1),
        PerformanceTrend(2024, "BPCI Advanced (final)", 215, 18.5, 0.52, 2.8, 87.3),
    ]


def _build_risk_structures() -> List[RiskStructureOption]:
    return [
        RiskStructureOption("Upside-only / Basic", 40.0, 0.0, 260, 0.8, "small/new ACOs, primary care orgs"),
        RiskStructureOption("2-sided Limited", 55.0, 30.0, 155, 2.2, "mature ACOs; ramping to full risk"),
        RiskStructureOption("2-sided Enhanced", 75.0, 40.0, 68, 3.5, "scaled ACOs; strong prior performance"),
        RiskStructureOption("Global Cap / Professional", 100.0, 100.0, 132, 4.2, "DCEs / REACH professional option"),
        RiskStructureOption("Global Cap / Global", 100.0, 100.0, 85, 5.8, "DCEs / REACH global option"),
        RiskStructureOption("Capitation + PBAC", 100.0, 0.0, 1580, 2.1, "primary care practices (PCF)"),
        RiskStructureOption("Retrospective Episode", 50.0, 50.0, 220, 2.8, "acute episode bundles (BPCI-A)"),
        RiskStructureOption("Mandatory Episode (TEAM)", 50.0, 50.0, 742, 2.5, "geographic mandatory MSK/joint"),
        RiskStructureOption("State Global Budget", 95.0, 95.0, 4, 2.5, "state-level all-payer (AHEAD)"),
    ]


def _build_calendar() -> List[PolicyCalendar]:
    return [
        PolicyCalendar("ACO REACH Final PY", "2026-12-31", "Sunset — transition to MSSP or MCP", "ACO REACH", 42.5),
        PolicyCalendar("Primary Care First Final PY", "2026-12-31", "Sunset — transition to MCP", "PCF", 12.8),
        PolicyCalendar("MCP Year 1 Performance", "2026-12-31", "First performance year begins", "MCP", 5.2),
        PolicyCalendar("BPCI Advanced Final PY", "2025-12-31", "Episode payments continue through 2025", "BPCI-A", 18.5),
        PolicyCalendar("TEAM Year 1 Launch", "2026-01-01", "Mandatory MSK participation begins", "TEAM", 22.5),
        PolicyCalendar("2026 Medicare Physician Fee Schedule", "2026-01-15", "-2.8% conversion factor cut proposed", "All FFS", 850.0),
        PolicyCalendar("CKCC Final PY", "2026-12-31", "Sunset — kidney care transition", "CKCC", 6.8),
        PolicyCalendar("MSSP Enhanced Track New Entrants", "2026-01-01", "40% participant target", "MSSP", 132.5),
        PolicyCalendar("2027 OPPS Proposed Rule", "2026-07-15", "Site-neutral payment expansion", "ASC/HOPD", 180.0),
        PolicyCalendar("Medicare Advantage RADV audit expansion", "2026-04-01", "Extrapolation final rule takes effect", "MA plans", 75.0),
        PolicyCalendar("IBH Model Cohort 2 Launch", "2026-07-01", "Additional states join Behavioral Health model", "IBH", 3.8),
        PolicyCalendar("340B Modernization Discussion Draft", "2026-Q3", "Potential program reform", "340B Eligible", 180.0),
    ]


def _build_payer_adjacency() -> List[PayerAdjacency]:
    return [
        PayerAdjacency("MA Value-Based (Capitation)", 35, 28.5, -450, 58.0, "Humana, Clover, Alignment, Bright"),
        PayerAdjacency("Commercial Direct Employer", 12, 4.8, -350, 12.5, "ChenMed, Oak Street, Iora Health"),
        PayerAdjacency("Medicaid Managed Care", 45, 85.0, -500, 72.0, "Centene, Molina, Elevance"),
        PayerAdjacency("BCBS Pay-for-Performance", 38, 18.5, -200, 45.0, "regional Blues"),
        PayerAdjacency("UnitedHealthcare Optum Partners", 22, 12.8, -350, 48.0, "Optum Care, MedExpress, Surgical Care Affiliates"),
        PayerAdjacency("Dual Eligible SNP / D-SNP", 18, 4.2, -600, 22.0, "Anthem, CareSource, Independence Blue Cross"),
    ]


def compute_cms_apm_tracker() -> APMResult:
    corpus = _load_corpus()
    programs = _build_programs()
    exposures = _build_exposures()
    trends = _build_trends()
    risk_structures = _build_risk_structures()
    calendar = _build_calendar()
    payer_adjacency = _build_payer_adjacency()

    total_lives = sum(p.lives_covered_m for p in programs)
    total_payments = sum(p.total_payments_b for p in programs)
    active = [p for p in programs if p.status not in ("retired",)]
    avg_savings = sum(p.savings_rate_pct for p in active) / len(active) if active else 0
    portfolio_rev = sum(e.apm_revenue_m for e in exposures)
    total_rev = portfolio_rev + 8500.0
    at_risk = sum(e.apm_revenue_m for e in exposures if e.apm_share_of_rev_pct > 0.10)

    return APMResult(
        total_programs=len(programs),
        total_lives_covered_m=round(total_lives, 2),
        total_apm_payments_b=round(total_payments, 1),
        avg_savings_rate_pct=round(avg_savings, 2),
        total_portfolio_apm_revenue_m=round(portfolio_rev, 1),
        portfolio_share_at_risk_pct=round(at_risk / total_rev if total_rev > 0 else 0, 4),
        programs=programs,
        exposures=exposures,
        trends=trends,
        risk_structures=risk_structures,
        calendar=calendar,
        payer_adjacency=payer_adjacency,
        corpus_deal_count=len(corpus),
    )
