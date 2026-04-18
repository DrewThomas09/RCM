"""Vintage Year / Cohort Performance Tracker.

Compares portfolio performance by investment vintage year: deployment,
DPI, TVPI, IRR vs benchmarks, sector mix, hold period, exit realization.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class VintageCohort:
    vintage_year: int
    deals: int
    total_deployed_m: float
    total_nav_m: float
    total_distributed_m: float
    dpi: float
    rvpi: float
    tvpi: float
    net_irr_pct: float
    gross_irr_pct: float
    benchmark_tvpi: float
    quartile_vs_cambridge: int


@dataclass
class SectorVintage:
    sector: str
    vintage_year: int
    deals: int
    deployed_m: float
    current_tvpi: float
    realized_m: float
    best_deal: str
    best_moic: float


@dataclass
class HoldTrend:
    vintage_year: int
    median_hold_years: float
    earliest_exit: float
    latest_exit: float
    hold_target_years: float
    exits_complete: int
    exits_pending: int


@dataclass
class ExitMixByVintage:
    vintage_year: int
    strategic_sale_count: int
    secondary_buyout_count: int
    continuation_vehicle_count: int
    ipo_count: int
    recap_count: int
    total_exits: int
    median_exit_multiple: float


@dataclass
class MarketEnvironment:
    vintage_year: int
    ma_yield_curve_10y: float
    sofr_spread_hc_pe: int
    typical_entry_multiple: float
    typical_leverage: float
    fed_regime: str
    macro_overlay: str


@dataclass
class DeploymentPacing:
    vintage_year: int
    target_deployment_m: float
    actual_deployment_m: float
    deployment_rate_pct: float
    deals_in_market: int
    deals_closed_lib: int
    missed_deals: int


@dataclass
class VintageResult:
    vintages_tracked: int
    total_deployed_b: float
    portfolio_dpi: float
    portfolio_tvpi: float
    best_vintage: int
    worst_vintage: int
    cohorts: List[VintageCohort]
    sector_vintages: List[SectorVintage]
    holds: List[HoldTrend]
    exits: List[ExitMixByVintage]
    environments: List[MarketEnvironment]
    pacings: List[DeploymentPacing]
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


def _build_cohorts() -> List[VintageCohort]:
    return [
        VintageCohort(2015, 8, 1850.0, 285.0, 4685.0, 2.53, 0.154, 2.69, 19.5, 22.8, 2.10, 1),
        VintageCohort(2016, 9, 2250.0, 425.0, 5085.0, 2.26, 0.189, 2.45, 17.8, 20.5, 2.05, 1),
        VintageCohort(2017, 11, 2650.0, 625.0, 5450.0, 2.06, 0.236, 2.29, 16.8, 19.5, 1.95, 2),
        VintageCohort(2018, 13, 3250.0, 1285.0, 5935.0, 1.83, 0.395, 2.22, 17.2, 19.8, 1.85, 1),
        VintageCohort(2019, 15, 3850.0, 2485.0, 5985.0, 1.55, 0.645, 2.20, 16.5, 18.5, 1.85, 1),
        VintageCohort(2020, 14, 3550.0, 3250.0, 3985.0, 1.12, 0.915, 2.04, 15.2, 17.5, 1.75, 2),
        VintageCohort(2021, 17, 4850.0, 5485.0, 2385.0, 0.49, 1.131, 1.62, 12.5, 14.8, 1.65, 2),
        VintageCohort(2022, 15, 4250.0, 5250.0, 625.0, 0.15, 1.235, 1.38, 11.0, 13.5, 1.40, 3),
        VintageCohort(2023, 12, 3450.0, 4125.0, 125.0, 0.04, 1.196, 1.23, 9.5, 12.0, 1.15, 3),
        VintageCohort(2024, 9, 2650.0, 2925.0, 0.0, 0.00, 1.104, 1.10, 7.5, 10.5, 0.95, 0),
        VintageCohort(2025, 5, 1550.0, 1625.0, 0.0, 0.00, 1.048, 1.05, 5.5, 8.5, 0.60, 0),
    ]


def _build_sector_vintages() -> List[SectorVintage]:
    return [
        SectorVintage("Gastroenterology", 2018, 3, 545.0, 2.58, 1225.0, "Project Oak — GI Network", 3.00),
        SectorVintage("Gastroenterology", 2019, 4, 725.0, 2.38, 1045.0, "Project Cypress (legacy)", 2.75),
        SectorVintage("Gastroenterology", 2021, 2, 485.0, 1.75, 0.0, "Project Cypress — GI Network", 1.75),
        SectorVintage("MSK / Ortho", 2019, 3, 585.0, 2.42, 985.0, "Project Pine — MSK", 2.50),
        SectorVintage("MSK / Ortho", 2020, 2, 425.0, 1.95, 285.0, "Project Summit — Ortho", 2.10),
        SectorVintage("MSK / Ortho", 2022, 3, 685.0, 1.55, 0.0, "Project Magnolia — MSK Platform", 1.55),
        SectorVintage("Dermatology", 2018, 3, 425.0, 2.65, 812.0, "Project Birch — Derma", 2.85),
        SectorVintage("Dermatology", 2023, 2, 325.0, 1.45, 0.0, "Project Laurel — Derma", 1.45),
        SectorVintage("Cardiology", 2019, 2, 385.0, 2.28, 625.0, "Project Maple1 — Cardiology", 2.40),
        SectorVintage("Cardiology", 2021, 2, 485.0, 1.85, 0.0, "Project Cedar — Cardiology", 1.85),
        SectorVintage("RCM / HCIT", 2019, 2, 195.0, 3.45, 585.0, "Project Elm — RCM SaaS", 3.60),
        SectorVintage("RCM / HCIT", 2021, 1, 285.0, 2.18, 0.0, "Project Oak — RCM SaaS (continuation)", 2.18),
        SectorVintage("Fertility / IVF", 2020, 2, 325.0, 2.25, 225.0, "Project Cedar1 — Fertility", 2.50),
        SectorVintage("Fertility / IVF", 2022, 2, 385.0, 1.55, 0.0, "Project Willow — Fertility", 1.55),
        SectorVintage("Home Health", 2019, 2, 285.0, 2.18, 485.0, "Project Hawthorn — Home Health", 2.30),
        SectorVintage("Behavioral Health", 2020, 2, 245.0, 1.82, 126.0, "Project Birch — Behavioral", 2.10),
        SectorVintage("Behavioral Health", 2022, 2, 385.0, 1.42, 0.0, "Project Redwood — Behavioral", 1.42),
    ]


def _build_holds() -> List[HoldTrend]:
    return [
        HoldTrend(2015, 5.5, 4.2, 7.8, 5.0, 7, 1),
        HoldTrend(2016, 5.8, 4.5, 7.5, 5.0, 8, 1),
        HoldTrend(2017, 5.8, 4.8, 7.2, 5.0, 9, 2),
        HoldTrend(2018, 6.2, 5.0, 8.0, 5.0, 8, 5),
        HoldTrend(2019, 6.5, 5.2, 7.8, 5.0, 6, 9),
        HoldTrend(2020, 5.8, 4.2, 7.5, 5.0, 4, 10),
        HoldTrend(2021, 4.5, 3.5, 5.8, 5.0, 2, 15),
        HoldTrend(2022, 3.5, 2.5, 4.5, 5.0, 1, 14),
        HoldTrend(2023, 2.5, 2.0, 3.2, 5.0, 0, 12),
    ]


def _build_exits() -> List[ExitMixByVintage]:
    return [
        ExitMixByVintage(2015, 4, 2, 1, 1, 0, 8, 2.68),
        ExitMixByVintage(2016, 4, 3, 1, 1, 0, 9, 2.45),
        ExitMixByVintage(2017, 5, 3, 1, 1, 1, 11, 2.32),
        ExitMixByVintage(2018, 4, 3, 1, 0, 0, 8, 2.42),
        ExitMixByVintage(2019, 2, 2, 1, 0, 1, 6, 2.55),
        ExitMixByVintage(2020, 1, 2, 1, 0, 0, 4, 2.10),
        ExitMixByVintage(2021, 0, 1, 1, 0, 0, 2, 1.85),
        ExitMixByVintage(2022, 0, 0, 1, 0, 0, 1, 1.65),
        ExitMixByVintage(2023, 0, 0, 0, 0, 0, 0, 0.0),
    ]


def _build_environments() -> List[MarketEnvironment]:
    return [
        MarketEnvironment(2015, 2.15, 425, 11.8, 5.5, "ZIRP",
                          "Low rates, competitive middle-market, healthcare rollup wave"),
        MarketEnvironment(2016, 2.45, 450, 12.2, 5.8, "slow tightening",
                          "Mid-cycle; derma/ortho/ophtho rollup saturation"),
        MarketEnvironment(2017, 2.35, 475, 12.5, 5.5, "continued tightening",
                          "Trump tax reform tailwind; corp tax rate cut"),
        MarketEnvironment(2018, 2.90, 500, 13.2, 5.8, "Fed tightening peak",
                          "COVID not yet; peak cycle multiples"),
        MarketEnvironment(2019, 1.85, 475, 13.8, 5.5, "easing cycle",
                          "Rate cuts; continued M&A activity"),
        MarketEnvironment(2020, 0.92, 425, 14.5, 5.2, "emergency stimulus (COVID)",
                          "COVID disruption; defensive PE allocation"),
        MarketEnvironment(2021, 1.42, 400, 16.8, 5.5, "stimulus bubble",
                          "Peak valuations; record deployment; high-competition"),
        MarketEnvironment(2022, 3.85, 500, 14.2, 5.8, "aggressive tightening",
                          "Fed hiking + inflation shock; multiple compression"),
        MarketEnvironment(2023, 3.95, 525, 13.5, 5.5, "higher-for-longer",
                          "Deal slowdown; valuation reset"),
        MarketEnvironment(2024, 4.15, 500, 13.8, 5.5, "peak rates",
                          "Deal flow recovering; normalized market"),
        MarketEnvironment(2025, 3.85, 485, 13.8, 5.5, "easing cycle",
                          "Rate cuts beginning; deal flow accelerating"),
    ]


def _build_pacings() -> List[DeploymentPacing]:
    return [
        DeploymentPacing(2019, 3500.0, 3850.0, 1.10, 145, 15, 3),
        DeploymentPacing(2020, 3500.0, 3550.0, 1.01, 128, 14, 5),
        DeploymentPacing(2021, 4500.0, 4850.0, 1.08, 185, 17, 8),
        DeploymentPacing(2022, 4500.0, 4250.0, 0.94, 165, 15, 4),
        DeploymentPacing(2023, 4000.0, 3450.0, 0.86, 152, 12, 6),
        DeploymentPacing(2024, 3500.0, 2650.0, 0.76, 118, 9, 3),
        DeploymentPacing(2025, 3000.0, 1550.0, 0.52, 78, 5, 2),
    ]


def compute_vintage_cohorts() -> VintageResult:
    corpus = _load_corpus()
    cohorts = _build_cohorts()
    sector_vintages = _build_sector_vintages()
    holds = _build_holds()
    exits = _build_exits()
    environments = _build_environments()
    pacings = _build_pacings()

    total_deployed = sum(c.total_deployed_m for c in cohorts) / 1000.0
    total_dist = sum(c.total_distributed_m for c in cohorts)
    total_nav = sum(c.total_nav_m for c in cohorts)
    port_dpi = total_dist / (total_deployed * 1000.0) if total_deployed > 0 else 0
    port_tvpi = (total_dist + total_nav) / (total_deployed * 1000.0) if total_deployed > 0 else 0
    best = max(cohorts, key=lambda c: c.tvpi).vintage_year if cohorts else 0
    worst = min(cohorts, key=lambda c: c.tvpi).vintage_year if cohorts else 0

    return VintageResult(
        vintages_tracked=len(cohorts),
        total_deployed_b=round(total_deployed, 2),
        portfolio_dpi=round(port_dpi, 2),
        portfolio_tvpi=round(port_tvpi, 2),
        best_vintage=best,
        worst_vintage=worst,
        cohorts=cohorts,
        sector_vintages=sector_vintages,
        holds=holds,
        exits=exits,
        environments=environments,
        pacings=pacings,
        corpus_deal_count=len(corpus),
    )
