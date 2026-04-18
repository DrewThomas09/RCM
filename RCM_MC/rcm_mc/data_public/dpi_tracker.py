"""DPI / Distribution Tracker.

Tracks distributed-to-paid-in (DPI), residual value (RVPI), total value
(TVPI), cash distributions vs capital called, by fund vintage — the
metric LPs care about most right now given the prolonged exit drought.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class FundVintage:
    sponsor: str
    fund_name: str
    vintage: int
    fund_size_b: float
    called_pct: float
    dpi: float
    rvpi: float
    tvpi: float
    net_irr_pct: float
    quartile: int
    benchmark_dpi: float


@dataclass
class DistributionEvent:
    sponsor: str
    fund: str
    event_date: str
    portfolio_company: str
    distribution_m: float
    event_type: str
    hold_years: float
    moic: float


@dataclass
class SectorDPI:
    sector: str
    sponsors: int
    funds: int
    total_commitment_b: float
    aggregate_dpi: float
    median_hold_years: float
    exit_volume_m: float


@dataclass
class ExitDroughtMetric:
    metric: str
    current_value: str
    prior_year: str
    delta: str
    impact_on_lps: str


@dataclass
class LPRequest:
    lp_name: str
    lp_type: str
    request_type: str
    commitment_m: float
    dpi_shortfall_m: float
    request_date: str
    sponsor_response: str


@dataclass
class PathToExit:
    portfolio_company: str
    sector: str
    sponsor: str
    hold_years: float
    target_exit_year: int
    exit_path: str
    projected_moic: float
    confidence: str


@dataclass
class DPIResult:
    total_funds: int
    weighted_dpi: float
    weighted_tvpi: float
    total_distributions_b: float
    pending_exits_m: float
    below_benchmark_funds: int
    funds: List[FundVintage]
    distributions: List[DistributionEvent]
    sectors: List[SectorDPI]
    drought_metrics: List[ExitDroughtMetric]
    lp_requests: List[LPRequest]
    exit_paths: List[PathToExit]
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


def _build_funds() -> List[FundVintage]:
    return [
        FundVintage("Welsh Carson Anderson Stowe", "WCAS Healthcare XIII", 2018, 4.10, 0.98, 1.45, 0.92, 2.37, 18.5, 2, 1.50),
        FundVintage("Welsh Carson Anderson Stowe", "WCAS Healthcare XIV", 2021, 5.20, 0.82, 0.25, 1.52, 1.77, 15.2, 3, 0.35),
        FundVintage("Welsh Carson Anderson Stowe", "WCAS Healthcare XV", 2024, 6.50, 0.35, 0.0, 1.08, 1.08, 8.5, 0, 0.0),
        FundVintage("KKR", "KKR Health Care Strategic Growth II", 2019, 4.00, 0.95, 1.28, 1.05, 2.33, 16.8, 2, 1.35),
        FundVintage("KKR", "KKR Health Care Strategic Growth III", 2022, 5.80, 0.65, 0.18, 1.32, 1.50, 11.5, 3, 0.25),
        FundVintage("Bain Capital", "Bain Capital Life Sciences III", 2019, 3.20, 0.92, 1.52, 0.85, 2.37, 19.5, 1, 1.35),
        FundVintage("Bain Capital", "Bain Capital Life Sciences IV", 2022, 4.50, 0.58, 0.12, 1.25, 1.37, 10.2, 3, 0.20),
        FundVintage("Apollo", "Apollo Healthcare Growth I", 2020, 3.50, 0.88, 0.95, 1.15, 2.10, 15.8, 2, 1.10),
        FundVintage("Apollo", "Apollo Healthcare Growth II", 2023, 5.00, 0.45, 0.05, 1.15, 1.20, 8.5, 0, 0.10),
        FundVintage("TPG Growth", "TPG Healthcare Partners", 2020, 3.75, 0.90, 1.08, 1.08, 2.16, 16.2, 2, 1.20),
        FundVintage("TPG Growth", "TPG Healthcare Partners II", 2023, 4.80, 0.48, 0.02, 1.15, 1.17, 7.8, 0, 0.08),
        FundVintage("Advent International", "Advent GPE X (Healthcare Allocation)", 2018, 4.50, 0.99, 1.62, 0.72, 2.34, 19.2, 1, 1.55),
        FundVintage("Advent International", "Advent GPE XI (Healthcare Allocation)", 2021, 5.50, 0.78, 0.22, 1.38, 1.60, 12.8, 3, 0.30),
        FundVintage("Carlyle Group", "Carlyle Healthcare II", 2019, 2.80, 0.94, 1.35, 0.95, 2.30, 17.5, 2, 1.28),
        FundVintage("Carlyle Group", "Carlyle Healthcare III", 2022, 3.50, 0.62, 0.08, 1.28, 1.36, 9.5, 3, 0.18),
        FundVintage("Warburg Pincus", "Warburg XIII (Healthcare Focus)", 2020, 4.20, 0.87, 0.85, 1.12, 1.97, 14.2, 2, 1.00),
        FundVintage("L Catterton", "L Catterton Growth Partners III", 2019, 2.10, 0.95, 1.18, 0.88, 2.06, 14.5, 2, 1.15),
        FundVintage("Summit Partners", "Summit Growth Equity XII", 2020, 4.00, 0.92, 0.98, 1.08, 2.06, 14.8, 2, 1.05),
        FundVintage("Silver Lake", "Silver Lake Healthcare Tech II", 2019, 3.50, 0.96, 1.85, 0.92, 2.77, 22.5, 1, 1.75),
        FundVintage("Silver Lake", "Silver Lake Healthcare Tech III", 2022, 5.20, 0.68, 0.32, 1.45, 1.77, 13.8, 2, 0.40),
    ]


def _build_distributions() -> List[DistributionEvent]:
    return [
        DistributionEvent("Welsh Carson", "WCAS Healthcare XIII", "2025-Q4", "Clarity Women's Health", 285.0, "strategic sale", 5.2, 2.85),
        DistributionEvent("KKR", "KKR Healthcare II", "2025-Q3", "Orthopedic Care Platform", 420.0, "secondary buyout", 4.8, 2.70),
        DistributionEvent("Bain Capital", "Bain Life Sciences III", "2025-Q4", "PathGroup Labs", 380.0, "strategic sale", 5.5, 2.95),
        DistributionEvent("Apollo", "Apollo Healthcare I", "2025-Q3", "U.S. Anesthesia Partners recap", 225.0, "dividend recap", 3.5, 1.45),
        DistributionEvent("Advent International", "Advent GPE X", "2025-Q4", "Home Health Platform", 465.0, "strategic sale", 6.0, 3.10),
        DistributionEvent("Silver Lake", "Silver Lake Healthcare Tech II", "2025-Q3", "Cohere Health", 550.0, "IPO secondary", 4.2, 3.25),
        DistributionEvent("Carlyle", "Carlyle Healthcare II", "2025-Q4", "Anatomic Path Platform", 210.0, "secondary buyout", 4.5, 2.40),
        DistributionEvent("Summit Partners", "Summit Growth Equity XII", "2025-Q3", "DSO Platform", 180.0, "strategic sale", 4.8, 2.55),
        DistributionEvent("L Catterton", "L Catterton III", "2026-Q1", "Fertility Platform (partial)", 125.0, "continuation vehicle", 4.2, 2.15),
        DistributionEvent("TPG Growth", "TPG Healthcare Partners", "2026-Q1", "Cardiology Platform", 195.0, "secondary buyout", 4.0, 1.95),
        DistributionEvent("Warburg Pincus", "Warburg XIII", "2026-Q1", "Behavioral Health Platform", 150.0, "strategic sale", 3.8, 1.80),
        DistributionEvent("Welsh Carson", "WCAS Healthcare XIV", "2026-Q1", "GI Network (partial)", 165.0, "dividend recap", 3.2, 1.55),
        DistributionEvent("KKR", "KKR Healthcare III", "2026-Q1", "Derma Platform", 285.0, "strategic sale", 3.5, 1.80),
        DistributionEvent("Bain Capital", "Bain Life Sciences IV", "2026-Q1", "MSK Platform (partial)", 155.0, "dividend recap", 2.8, 1.40),
    ]


def _build_sectors() -> List[SectorDPI]:
    return [
        SectorDPI("Gastroenterology", 6, 9, 18.2, 1.42, 5.1, 2850.0),
        SectorDPI("MSK / Ortho", 7, 12, 24.5, 1.35, 5.3, 3620.0),
        SectorDPI("Dermatology", 5, 9, 15.8, 1.52, 4.8, 2480.0),
        SectorDPI("Behavioral Health", 6, 8, 14.2, 1.28, 5.8, 1920.0),
        SectorDPI("Fertility / IVF", 4, 6, 9.5, 1.58, 4.5, 1350.0),
        SectorDPI("Eye Care / Ophthalmology", 5, 7, 13.8, 1.65, 4.6, 1980.0),
        SectorDPI("Cardiology", 5, 7, 12.5, 1.38, 5.0, 1820.0),
        SectorDPI("Home Health / Hospice", 6, 9, 15.8, 1.45, 5.2, 2340.0),
        SectorDPI("Lab / Pathology", 4, 5, 8.5, 1.72, 4.2, 1485.0),
        SectorDPI("RCM / Healthtech SaaS", 5, 8, 12.8, 1.95, 4.0, 2380.0),
        SectorDPI("Specialty Pharmacy", 5, 7, 11.5, 1.68, 4.5, 1780.0),
        SectorDPI("Dental DSO", 7, 11, 16.5, 1.42, 5.4, 2280.0),
        SectorDPI("Infusion", 4, 6, 9.8, 1.38, 4.8, 1350.0),
        SectorDPI("Radiology / Imaging", 5, 7, 10.2, 1.55, 4.5, 1620.0),
    ]


def _build_drought() -> List[ExitDroughtMetric]:
    return [
        ExitDroughtMetric("PE HC Exit Volume (YTD)", "$38.5B", "$52.8B", "-27.1%", "elongated hold periods; DPI pressure building"),
        ExitDroughtMetric("Median Hold Period (Realized)", "6.2 years", "5.1 years", "+1.1 years", "carry crystallization delayed; LP patience tested"),
        ExitDroughtMetric("Secondary Buyout % of Exits", "48%", "38%", "+10 pts", "sponsor-to-sponsor market taking share from strategic"),
        ExitDroughtMetric("Continuation Vehicle $ Volume", "$24.5B", "$11.2B", "+118.8%", "single-asset CV providing liquidity valve"),
        ExitDroughtMetric("Dividend Recap % Increase", "+62%", "baseline", "+62%", "interim liquidity mechanism; cov headroom dependent"),
        ExitDroughtMetric("LP Secondary Market Pricing (NAV)", "88-92%", "84-88%", "+4 pts", "LP demand strong for HC fund secondaries"),
        ExitDroughtMetric("Strategic Buyer Activity", "Moderate", "High", "Down", "health systems cautious; pharma/medtech selective"),
        ExitDroughtMetric("IPO Window (Healthcare)", "Thin", "Closed", "Modest open", "2 HC IPOs priced Q1 2026"),
    ]


def _build_lp_requests() -> List[LPRequest]:
    return [
        LPRequest("CalPERS", "Public Pension", "DPI recovery plan", 850.0, 425.0, "2026-02-15", "continuation vehicle proposed"),
        LPRequest("Texas Teachers", "Public Pension", "Informal GP check-in", 710.0, 320.0, "2026-03-05", "quarterly update scheduled"),
        LPRequest("HOOPP", "Canadian Pension", "Liquidity option inquiry", 420.0, 165.0, "2026-02-28", "secondary market intro offered"),
        LPRequest("Harvard Management", "Endowment", "Formal LP request", 285.0, 135.0, "2026-01-20", "dividend recap planned"),
        LPRequest("Yale Investments", "Endowment", "DPI benchmarking request", 325.0, 85.0, "2026-02-10", "peer data shared"),
        LPRequest("Ford Foundation", "Foundation", "Exit timing review", 165.0, 55.0, "2026-03-12", "3-deal exit sequencing memo"),
        LPRequest("CPPIB", "Canadian Pension", "GP extension request", 925.0, 245.0, "2026-02-22", "1-year extension granted"),
        LPRequest("ADIA", "Sovereign Wealth", "Secondary bid inquiry", 780.0, 180.0, "2026-01-30", "GP-led offer formulated"),
        LPRequest("NBIM (Norway)", "Sovereign Wealth", "Return attribution analysis", 685.0, 95.0, "2026-02-18", "detailed bridge provided"),
        LPRequest("Gates Foundation", "Foundation", "Strategic review", 380.0, 112.0, "2026-03-01", "3-exit sequencing accelerated"),
    ]


def _build_exit_paths() -> List[PathToExit]:
    return [
        PathToExit("Cardiology Specialty Platform", "Cardiology", "Bain Capital", 5.8, 2026, "strategic sale", 2.75, "high"),
        PathToExit("GI Network SE", "Gastroenterology", "Welsh Carson", 5.2, 2026, "strategic or secondary", 2.95, "high"),
        PathToExit("MSK Platform Nat'l", "MSK / Ortho", "KKR", 6.1, 2026, "secondary buyout", 2.45, "high"),
        PathToExit("Fertility Network US", "Fertility / IVF", "Apollo", 4.8, 2027, "strategic sale", 3.15, "medium"),
        PathToExit("Behavioral Health National", "Behavioral Health", "Warburg Pincus", 6.5, 2026, "continuation vehicle", 1.85, "medium"),
        PathToExit("Derma Platform National", "Dermatology", "Advent", 5.5, 2026, "IPO or strategic", 2.80, "high"),
        PathToExit("DSO Multi-State", "Dental DSO", "L Catterton", 5.8, 2027, "secondary buyout", 2.55, "medium"),
        PathToExit("Home Health / Hospice", "Home Health", "Apollo", 4.2, 2027, "strategic sale", 2.20, "medium"),
        PathToExit("Lab Services Platform", "Lab Services", "Carlyle", 4.5, 2026, "strategic sale", 2.85, "high"),
        PathToExit("RCM SaaS Platform", "RCM SaaS", "Silver Lake", 5.2, 2026, "IPO", 3.50, "medium"),
        PathToExit("Infusion Specialty Platform", "Infusion", "TPG", 6.0, 2027, "continuation vehicle", 2.15, "medium"),
        PathToExit("Specialty Pharmacy Rollup", "Specialty Pharma", "Summit Partners", 5.5, 2027, "strategic sale", 2.65, "medium"),
    ]


def compute_dpi_tracker() -> DPIResult:
    corpus = _load_corpus()
    funds = _build_funds()
    distributions = _build_distributions()
    sectors = _build_sectors()
    drought = _build_drought()
    lp_requests = _build_lp_requests()
    exit_paths = _build_exit_paths()

    weighted_dpi = (sum(f.dpi * f.fund_size_b for f in funds) /
                    sum(f.fund_size_b for f in funds)) if funds else 0
    weighted_tvpi = (sum(f.tvpi * f.fund_size_b for f in funds) /
                     sum(f.fund_size_b for f in funds)) if funds else 0
    total_dist = sum(d.distribution_m for d in distributions) / 1000.0
    pending = sum(p.projected_moic * 100 for p in exit_paths)
    below = sum(1 for f in funds if f.dpi < f.benchmark_dpi)

    return DPIResult(
        total_funds=len(funds),
        weighted_dpi=round(weighted_dpi, 2),
        weighted_tvpi=round(weighted_tvpi, 2),
        total_distributions_b=round(total_dist, 2),
        pending_exits_m=round(pending, 1),
        below_benchmark_funds=below,
        funds=funds,
        distributions=distributions,
        sectors=sectors,
        drought_metrics=drought,
        lp_requests=lp_requests,
        exit_paths=exit_paths,
        corpus_deal_count=len(corpus),
    )
