"""LP Reporting / Fund-Level Dashboard.

Quarterly LP report distilled to institutional dashboard: TVPI/DPI/RVPI
by fund, manager attribution, benchmark vs PitchBook quartile, capital
call & distribution cadence, realized vs unrealized split.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class FundPerformance:
    fund: str
    vintage: int
    fund_size_mm: float
    called_pct: float
    tvpi: float
    dpi: float
    rvpi: float
    net_irr_pct: float
    quartile: str


@dataclass
class QuarterlyMark:
    quarter: str
    nav_mm: float
    quarterly_value_change_pct: float
    contributions_mm: float
    distributions_mm: float
    cumulative_dpi: float
    cumulative_tvpi: float


@dataclass
class AttributionDriver:
    driver: str
    quarterly_contribution_mm: float
    ytd_contribution_mm: float
    pct_of_value_change: float
    commentary: str


@dataclass
class BenchmarkComparison:
    metric: str
    fund: float
    q1_benchmark: float
    q2_benchmark: float
    q3_benchmark: float
    q4_benchmark: float
    fund_quartile: str


@dataclass
class PortfolioCompanyUpdate:
    company: str
    sector: str
    cost_basis_mm: float
    current_fair_value_mm: float
    marked_moic: float
    ytd_valuation_change_pct: float
    status: str


@dataclass
class LPCommunication:
    date: str
    type: str
    topic: str
    status: str
    recipients_count: int


@dataclass
class LPReportingResult:
    reporting_quarter: str
    fund_count: int
    total_aum_mm: float
    blended_tvpi: float
    blended_dpi: float
    blended_irr_pct: float
    funds: List[FundPerformance]
    marks: List[QuarterlyMark]
    attribution: List[AttributionDriver]
    benchmarks: List[BenchmarkComparison]
    companies: List[PortfolioCompanyUpdate]
    communications: List[LPCommunication]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 119):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_funds() -> List[FundPerformance]:
    return [
        FundPerformance("Fund III Healthcare (2017)", 2017, 850.0, 0.98, 2.45, 1.82, 0.63, 18.5, "top quartile"),
        FundPerformance("Fund IV Healthcare (2019)", 2019, 1200.0, 0.92, 1.88, 0.68, 1.20, 15.2, "second quartile"),
        FundPerformance("Fund V Healthcare (2021)", 2021, 1850.0, 0.68, 1.42, 0.25, 1.17, 10.8, "second quartile"),
        FundPerformance("Healthcare Co-Invest Fund I (2020)", 2020, 425.0, 0.95, 2.12, 0.88, 1.24, 16.5, "top quartile"),
        FundPerformance("Healthcare Continuation Vehicle (2024)", 2024, 985.0, 0.45, 1.08, 0.02, 1.06, 8.5, "too early"),
        FundPerformance("HC Direct Lending Fund II (2022)", 2022, 1450.0, 0.85, 1.22, 0.18, 1.04, 10.2, "second quartile"),
        FundPerformance("HC Growth Equity Fund I (2023)", 2023, 625.0, 0.62, 1.18, 0.08, 1.10, 9.5, "third quartile"),
    ]


def _build_marks() -> List[QuarterlyMark]:
    return [
        QuarterlyMark("2024Q1", 6485.0, 0.032, 285.0, 125.0, 0.58, 1.78),
        QuarterlyMark("2024Q2", 6825.0, 0.042, 325.0, 162.0, 0.62, 1.85),
        QuarterlyMark("2024Q3", 7125.0, 0.038, 312.0, 215.0, 0.68, 1.92),
        QuarterlyMark("2024Q4", 7485.0, 0.045, 385.0, 285.0, 0.76, 2.02),
        QuarterlyMark("2025Q1", 7685.0, 0.022, 228.0, 245.0, 0.82, 2.08),
        QuarterlyMark("2025Q2", 7985.0, 0.035, 252.0, 295.0, 0.88, 2.15),
        QuarterlyMark("2025Q3", 8185.0, 0.028, 215.0, 325.0, 0.95, 2.22),
        QuarterlyMark("2025Q4", 8425.0, 0.032, 245.0, 385.0, 1.05, 2.30),
        QuarterlyMark("2026Q1 (current)", 8625.0, 0.024, 225.0, 352.0, 1.12, 2.38),
    ]


def _build_attribution() -> List[AttributionDriver]:
    return [
        AttributionDriver("EBITDA Growth (portfolio)", 185.0, 685.0, 0.54, "Strong organic + bolt-on performance"),
        AttributionDriver("Multiple Expansion (marks)", 85.0, 285.0, 0.22, "Public comps re-rated higher in Q1"),
        AttributionDriver("Realization Gains (exits)", 45.0, 195.0, 0.15, "Two exits closed in Q1"),
        AttributionDriver("FX / International", 5.0, 8.0, 0.01, "Minimal FX impact (US-focused)"),
        AttributionDriver("Interest Expense (portfolio)", -15.0, -55.0, -0.04, "Rate environment headwind"),
        AttributionDriver("Operating Expense (portfolio)", -20.0, -72.0, -0.06, "Wage inflation pass-through"),
        AttributionDriver("Other / Mix Effects", 12.0, 42.0, 0.04, "Sector rotation effects"),
    ]


def _build_benchmarks() -> List[BenchmarkComparison]:
    return [
        BenchmarkComparison("TVPI (Fund III)", 2.45, 1.92, 2.18, 2.42, 2.65, "top quartile"),
        BenchmarkComparison("IRR % (Fund III)", 18.5, 12.2, 15.8, 18.2, 22.5, "top quartile"),
        BenchmarkComparison("TVPI (Fund IV)", 1.88, 1.45, 1.75, 1.98, 2.25, "second quartile"),
        BenchmarkComparison("IRR % (Fund IV)", 15.2, 8.8, 13.5, 16.8, 20.5, "second quartile"),
        BenchmarkComparison("TVPI (Fund V)", 1.42, 1.18, 1.38, 1.55, 1.78, "second quartile"),
        BenchmarkComparison("DPI (Fund III)", 1.82, 1.22, 1.58, 1.85, 2.18, "top quartile"),
        BenchmarkComparison("Net IRR Portfolio Weighted", 14.8, 11.5, 14.2, 16.5, 19.8, "second quartile"),
        BenchmarkComparison("Loss Ratio %", 0.028, 0.085, 0.055, 0.032, 0.018, "top decile"),
    ]


def _build_companies() -> List[PortfolioCompanyUpdate]:
    return [
        PortfolioCompanyUpdate("Azalea GI Partners", "Gastroenterology", 285.0, 488.0, 1.71, 0.082, "Active"),
        PortfolioCompanyUpdate("Beacon Derm Group", "Dermatology", 245.0, 485.0, 1.98, 0.125, "Active"),
        PortfolioCompanyUpdate("Cadence Pathology", "Pathology Labs", 185.0, 285.0, 1.54, 0.045, "Active"),
        PortfolioCompanyUpdate("Denali ASC Network", "ASC Platform", 425.0, 825.0, 1.94, 0.098, "Active"),
        PortfolioCompanyUpdate("Everest Behavioral Health", "Behavioral Health", 325.0, 285.0, 0.88, -0.078, "Watch list"),
        PortfolioCompanyUpdate("Flagstaff Ortho", "Orthopedics", 225.0, 445.0, 1.98, 0.115, "Active"),
        PortfolioCompanyUpdate("Glacier Home Health", "Home Health", 165.0, 248.0, 1.50, 0.052, "Active"),
        PortfolioCompanyUpdate("Harbor Urgent Care", "Urgent Care", 95.0, 95.0, 1.00, -0.025, "Watch list"),
        PortfolioCompanyUpdate("Ironwood Cardiology", "Cardiology", 385.0, 625.0, 1.62, 0.068, "Active"),
        PortfolioCompanyUpdate("Juniper Specialty Rx", "Specialty Pharmacy", 225.0, 525.0, 2.33, 0.142, "Active"),
        PortfolioCompanyUpdate("Kestrel Fertility", "Fertility / IVF", 475.0, 1050.0, 2.21, 0.158, "Closing Q2 exit"),
        PortfolioCompanyUpdate("Larkspur Dental", "Dental DSO", 85.0, 112.0, 1.32, 0.018, "Active"),
    ]


def _build_communications() -> List[LPCommunication]:
    return [
        LPCommunication("2025-04-15", "Quarterly Report", "Q1 2026 Mid-Year Update", "sent", 48),
        LPCommunication("2025-03-28", "Fund Notice", "Distribution Notice - $385M", "sent", 48),
        LPCommunication("2025-03-15", "Portfolio Update", "Azalea Exit Closing Notice", "sent", 48),
        LPCommunication("2025-02-28", "Cap Call Notice", "Fund V Capital Call #12 - $225M", "sent", 28),
        LPCommunication("2025-02-15", "Annual Meeting", "Annual LP Meeting - NYC", "completed", 48),
        LPCommunication("2025-01-15", "Year-End Letter", "2024 Year-End Letter + Audited Financials", "sent", 48),
        LPCommunication("2024-12-15", "Portfolio Update", "Kestrel IPO Filing Notice", "sent", 48),
        LPCommunication("2025-04-22", "Upcoming", "Q2 2026 Portfolio Review Call", "scheduled", 35),
        LPCommunication("2025-05-15", "Upcoming", "Annual Valuation Committee Review", "scheduled", 15),
        LPCommunication("2025-06-01", "Upcoming", "Q1 2026 Audited Financials", "in progress", 48),
    ]


def compute_lp_reporting() -> LPReportingResult:
    corpus = _load_corpus()

    funds = _build_funds()
    marks = _build_marks()
    attribution = _build_attribution()
    benchmarks = _build_benchmarks()
    companies = _build_companies()
    communications = _build_communications()

    total_aum = sum(f.fund_size_mm for f in funds)
    weighted_tvpi = sum(f.tvpi * f.fund_size_mm for f in funds) / total_aum if total_aum else 0
    weighted_dpi = sum(f.dpi * f.fund_size_mm for f in funds) / total_aum if total_aum else 0
    weighted_irr = sum(f.net_irr_pct * f.fund_size_mm for f in funds) / total_aum if total_aum else 0

    return LPReportingResult(
        reporting_quarter="Q1 2026",
        fund_count=len(funds),
        total_aum_mm=round(total_aum, 2),
        blended_tvpi=round(weighted_tvpi, 2),
        blended_dpi=round(weighted_dpi, 2),
        blended_irr_pct=round(weighted_irr, 2),
        funds=funds,
        marks=marks,
        attribution=attribution,
        benchmarks=benchmarks,
        companies=companies,
        communications=communications,
        corpus_deal_count=len(corpus),
    )
