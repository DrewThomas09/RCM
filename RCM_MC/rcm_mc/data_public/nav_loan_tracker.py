"""NAV Loan / Fund-Level Financing Tracker.

Tracks fund-level NAV-based financings: loan size, LTV, pricing,
use of proceeds, collateral coverage, stress-test results.
A topical instrument as GPs bridge exit timing for LPs.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class NAVLoan:
    fund: str
    sponsor: str
    vintage: int
    nav_at_close_b: float
    loan_size_m: float
    ltv_pct: float
    sofr_spread_bps: int
    maturity_years: int
    closed_date: str
    use_of_proceeds: str
    status: str


@dataclass
class LenderPosition:
    lender: str
    total_commitments_m: float
    loans: int
    median_ltv_pct: float
    sector_focus: str
    tier: str
    avg_spread_bps: int


@dataclass
class UseOfProceeds:
    category: str
    loan_count: int
    total_volume_m: float
    median_check_m: float
    typical_structure: str


@dataclass
class CoverageAnalysis:
    fund: str
    nav_current_b: float
    loan_outstanding_m: float
    current_ltv_pct: float
    maintenance_covenant_pct: float
    headroom_pct: float
    collateral_count: int
    liquidity_stress_headroom_pct: float


@dataclass
class StressTest:
    scenario: str
    nav_markdown_pct: float
    resulting_ltv_pct: float
    covenant_trip: bool
    required_cure_m: float
    impact_on_portfolio: str


@dataclass
class MarketBenchmark:
    loan_type: str
    typical_ltv_pct: float
    typical_spread_bps: int
    typical_tenor_years: int
    market_volume_24_b: float
    pricing_trend: str


@dataclass
class NAVLoanResult:
    total_loans: int
    total_outstanding_m: float
    weighted_ltv_pct: float
    weighted_spread_bps: int
    loans_near_maturity: int
    covenant_trip_scenarios: int
    loans: List[NAVLoan]
    lenders: List[LenderPosition]
    uses: List[UseOfProceeds]
    coverage: List[CoverageAnalysis]
    stress: List[StressTest]
    benchmarks: List[MarketBenchmark]
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


def _build_loans() -> List[NAVLoan]:
    return [
        NAVLoan("WCAS Healthcare XIII", "Welsh Carson", 2018, 5.80, 750.0, 0.129, 525, 4, "2025-03-15",
                "DPI distribution bridge", "active"),
        NAVLoan("KKR Healthcare II", "KKR", 2019, 5.20, 650.0, 0.125, 500, 4, "2025-06-20",
                "LP distribution + add-on financing", "active"),
        NAVLoan("Bain Capital Life Sciences III", "Bain Capital", 2019, 4.50, 550.0, 0.122, 525, 4, "2025-08-10",
                "LP liquidity + capex reinvestment", "active"),
        NAVLoan("Apollo Healthcare I", "Apollo", 2020, 4.80, 600.0, 0.125, 550, 5, "2025-11-05",
                "LP distribution bridge", "active"),
        NAVLoan("Advent GPE X HC", "Advent International", 2018, 5.50, 680.0, 0.124, 475, 4, "2025-05-15",
                "DPI distribution bridge", "active"),
        NAVLoan("Carlyle Healthcare II", "Carlyle Group", 2019, 3.60, 450.0, 0.125, 525, 4, "2025-09-20",
                "LP distribution + follow-on M&A", "active"),
        NAVLoan("Warburg XIII HC", "Warburg Pincus", 2020, 5.10, 620.0, 0.122, 500, 5, "2025-12-10",
                "LP liquidity bridge", "active"),
        NAVLoan("L Catterton III", "L Catterton", 2019, 2.85, 340.0, 0.119, 550, 4, "2026-01-08",
                "LP liquidity + continuation bridge", "active"),
        NAVLoan("TPG Healthcare Partners", "TPG Growth", 2020, 4.25, 520.0, 0.122, 525, 5, "2025-10-22",
                "LP distribution", "active"),
        NAVLoan("Summit Growth XII", "Summit Partners", 2020, 4.85, 595.0, 0.123, 500, 4, "2026-02-12",
                "LP distribution bridge", "active"),
        NAVLoan("Silver Lake HC Tech II", "Silver Lake", 2019, 4.90, 600.0, 0.122, 475, 5, "2025-07-18",
                "LP liquidity + add-on", "active"),
        NAVLoan("Bain Life Sciences IV", "Bain Capital", 2022, 4.10, 180.0, 0.044, 475, 4, "2026-03-25",
                "Capex reinvestment / add-on M&A", "active"),
    ]


def _build_lenders() -> List[LenderPosition]:
    return [
        LenderPosition("17Capital", 1850.0, 4, 12.4, "Healthcare + GP financings", "tier 1 specialist", 515),
        LenderPosition("Hark Capital", 985.0, 3, 12.2, "Multi-sector", "tier 1 specialist", 525),
        LenderPosition("Ares Capital", 750.0, 2, 12.5, "Healthcare + GP financings", "tier 1 diversified", 510),
        LenderPosition("Apollo (Fund-Level Solutions)", 680.0, 2, 12.6, "Healthcare + tech", "tier 1 diversified", 525),
        LenderPosition("Blackstone Strategic Partners", 620.0, 2, 12.8, "Diversified PE", "tier 1 diversified", 500),
        LenderPosition("Pantheon GP Solutions", 565.0, 2, 12.5, "Diversified PE", "tier 1 specialist", 530),
        LenderPosition("HPS Investment Partners", 510.0, 2, 12.7, "Multi-sector", "tier 1 diversified", 515),
        LenderPosition("Crescent Capital", 385.0, 1, 12.4, "Healthcare focus", "tier 2", 550),
        LenderPosition("Golub Capital", 295.0, 1, 12.2, "Healthcare + RCM", "tier 2", 525),
        LenderPosition("PineBridge Investments", 250.0, 1, 12.5, "Multi-sector", "tier 2", 540),
    ]


def _build_uses() -> List[UseOfProceeds]:
    return [
        UseOfProceeds("LP distribution bridge", 8, 4945.0, 600.0, "5yr bullet, cash-pay, 500-550bps SOFR+"),
        UseOfProceeds("Capex reinvestment / add-on M&A", 2, 360.0, 180.0, "5yr bullet, delayed draw, 475-525bps"),
        UseOfProceeds("Continuation vehicle bridge", 1, 340.0, 340.0, "2-3yr, repay on CV close, 550bps"),
        UseOfProceeds("LP liquidity + add-on", 3, 1680.0, 560.0, "5yr bullet, 475-525bps"),
        UseOfProceeds("GP commit financing", 0, 0.0, 0.0, "not yet in current book"),
        UseOfProceeds("Special sits / restructuring", 0, 0.0, 0.0, "not yet in current book"),
    ]


def _build_coverage() -> List[CoverageAnalysis]:
    return [
        CoverageAnalysis("WCAS Healthcare XIII", 5.45, 700.0, 0.128, 0.200, 0.360, 12, 0.245),
        CoverageAnalysis("KKR Healthcare II", 5.10, 620.0, 0.122, 0.200, 0.390, 14, 0.250),
        CoverageAnalysis("Bain Life Sciences III", 4.30, 500.0, 0.116, 0.200, 0.420, 10, 0.285),
        CoverageAnalysis("Apollo Healthcare I", 4.55, 580.0, 0.127, 0.200, 0.365, 13, 0.225),
        CoverageAnalysis("Advent GPE X HC", 5.35, 640.0, 0.120, 0.200, 0.400, 15, 0.265),
        CoverageAnalysis("Carlyle Healthcare II", 3.45, 420.0, 0.122, 0.200, 0.390, 9, 0.215),
        CoverageAnalysis("Warburg XIII HC", 4.85, 600.0, 0.124, 0.200, 0.380, 11, 0.225),
        CoverageAnalysis("L Catterton III", 2.70, 320.0, 0.119, 0.200, 0.405, 8, 0.230),
        CoverageAnalysis("TPG Healthcare Partners", 4.05, 490.0, 0.121, 0.200, 0.395, 10, 0.245),
        CoverageAnalysis("Summit Growth XII", 4.70, 580.0, 0.123, 0.200, 0.385, 11, 0.230),
        CoverageAnalysis("Silver Lake HC Tech II", 4.65, 575.0, 0.124, 0.200, 0.380, 10, 0.218),
        CoverageAnalysis("Bain Life Sciences IV", 4.08, 180.0, 0.044, 0.200, 0.780, 9, 0.540),
    ]


def _build_stress() -> List[StressTest]:
    return [
        StressTest("Base case (no markdown)", 0.0, 0.125, False, 0.0, "comfortable headroom 35-40%"),
        StressTest("Moderate markdown (-10%)", -0.10, 0.139, False, 0.0, "headroom compresses to 30%"),
        StressTest("Severe markdown (-20%)", -0.20, 0.156, False, 0.0, "approaches 75% of covenant"),
        StressTest("Distressed markdown (-30%)", -0.30, 0.179, False, 0.0, "approaches 90% of covenant; cure advisable"),
        StressTest("Worst-case markdown (-40%)", -0.40, 0.208, True, 115.0, "3 funds trip; ~$115M cure total"),
        StressTest("Catastrophic (-50%)", -0.50, 0.250, True, 285.0, "7 of 12 funds trip; partial paydown required"),
    ]


def _build_benchmarks() -> List[MarketBenchmark]:
    return [
        MarketBenchmark("NAV Loan - Healthcare PE", 12.0, 500, 5, 22.5, "widening (+25bps YTD)"),
        MarketBenchmark("NAV Loan - Multi-Sector PE", 13.5, 475, 5, 68.5, "widening (+25bps YTD)"),
        MarketBenchmark("NAV Loan - Tech PE", 15.0, 450, 5, 18.5, "flat (stable)"),
        MarketBenchmark("NAV Loan - Real Estate", 35.0, 400, 7, 45.0, "widening (+50bps YTD)"),
        MarketBenchmark("GP-led CV Bridge", 25.0, 575, 3, 12.5, "widening (+50bps YTD)"),
        MarketBenchmark("GP Commitment Financing", 65.0, 650, 7, 8.5, "widening (+100bps YTD)"),
    ]


def compute_nav_loan_tracker() -> NAVLoanResult:
    corpus = _load_corpus()
    loans = _build_loans()
    lenders = _build_lenders()
    uses = _build_uses()
    coverage = _build_coverage()
    stress = _build_stress()
    benchmarks = _build_benchmarks()

    total_out = sum(l.loan_size_m for l in loans)
    wtd_ltv = (sum(l.ltv_pct * l.loan_size_m for l in loans) / total_out) if total_out > 0 else 0
    wtd_spread = (sum(l.sofr_spread_bps * l.loan_size_m for l in loans) / total_out) if total_out > 0 else 0
    near_maturity = sum(1 for l in loans if l.maturity_years <= 4)
    trip_scenarios = sum(1 for s in stress if s.covenant_trip)

    return NAVLoanResult(
        total_loans=len(loans),
        total_outstanding_m=round(total_out, 1),
        weighted_ltv_pct=round(wtd_ltv, 4),
        weighted_spread_bps=int(round(wtd_spread)),
        loans_near_maturity=near_maturity,
        covenant_trip_scenarios=trip_scenarios,
        loans=loans,
        lenders=lenders,
        uses=uses,
        coverage=coverage,
        stress=stress,
        benchmarks=benchmarks,
        corpus_deal_count=len(corpus),
    )
