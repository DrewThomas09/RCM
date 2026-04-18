"""Private Credit / Direct Lending Tracker.

Models healthcare direct-lending market: outstanding credit, spread
trends, default rates, amend-and-extend volume, sponsor-lender matrix.
Essential context for any PE platform with unitranche or mezz debt.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class LenderFacility:
    lender: str
    lender_type: str
    commitment_mm: float
    outstanding_mm: float
    spread_sofr_bps: int
    all_in_rate_pct: float
    tenor_years: int
    cov_lite: bool


@dataclass
class MarketRate:
    deal_size_bucket: str
    unitranche_spread_bps: int
    first_lien_tl_spread_bps: int
    second_lien_spread_bps: int
    typical_oid_pct: float
    avg_closing_fee_bps: int


@dataclass
class SponsorLenderMatrix:
    sponsor: str
    primary_lender: str
    deals_financed_ltm: int
    total_committed_mm: float
    avg_leverage: float
    relationship_tier: str


@dataclass
class DefaultTrend:
    period: str
    healthcare_default_rate_pct: float
    overall_default_rate_pct: float
    amend_extend_volume_pct: float
    covenant_breach_count: int


@dataclass
class PortfolioMark:
    sector: str
    par_balance_mm: float
    current_mark_pct: float
    unrealized_loss_mm: float
    watch_list_flag: bool


@dataclass
class DirectLendingResult:
    total_facilities: int
    total_outstanding_mm: float
    blended_all_in_rate_pct: float
    weighted_leverage: float
    cov_lite_pct: float
    facilities: List[LenderFacility]
    rates: List[MarketRate]
    matrix: List[SponsorLenderMatrix]
    defaults: List[DefaultTrend]
    marks: List[PortfolioMark]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 104):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_facilities() -> List[LenderFacility]:
    items = [
        ("Ares Capital Corporation", "BDC", 285.0, 245.0, 500, 9.45, 6, True),
        ("Blue Owl Capital Lending", "Direct Lender", 185.0, 165.0, 475, 9.20, 6, True),
        ("Golub Capital", "Direct Lender", 155.0, 140.0, 485, 9.30, 7, True),
        ("Antares Capital", "Direct Lender", 225.0, 195.0, 500, 9.45, 6, True),
        ("Churchill Asset Management", "Direct Lender", 125.0, 108.0, 490, 9.35, 6, True),
        ("Bain Capital Credit", "Direct Lender", 165.0, 142.0, 510, 9.55, 7, True),
        ("KKR Credit", "Direct Lender", 145.0, 128.0, 495, 9.40, 6, True),
        ("Apollo Credit Management", "Direct Lender", 215.0, 188.0, 505, 9.50, 7, True),
        ("HPS Investment Partners", "Direct Lender", 195.0, 168.0, 500, 9.45, 6, True),
        ("Monroe Capital", "Direct Lender", 88.0, 72.0, 525, 9.70, 6, True),
        ("Owl Rock BDC", "BDC", 115.0, 98.0, 485, 9.30, 6, True),
        ("Main Street Capital", "BDC", 68.0, 58.0, 550, 9.95, 5, False),
    ]
    rows = []
    for lender, ltype, commit, out, spread, rate, tenor, covlite in items:
        rows.append(LenderFacility(
            lender=lender, lender_type=ltype,
            commitment_mm=commit, outstanding_mm=out,
            spread_sofr_bps=spread, all_in_rate_pct=rate,
            tenor_years=tenor, cov_lite=covlite,
        ))
    return rows


def _build_rates() -> List[MarketRate]:
    return [
        MarketRate("< $50M EBITDA", 575, 600, 925, 0.020, 350),
        MarketRate("$50-100M EBITDA", 500, 525, 825, 0.015, 300),
        MarketRate("$100-250M EBITDA", 450, 475, 750, 0.010, 250),
        MarketRate("$250M+ EBITDA", 400, 425, 700, 0.008, 200),
        MarketRate("Healthcare Services (Avg)", 495, 515, 815, 0.013, 275),
        MarketRate("Healthcare IT / SaaS", 425, 450, 725, 0.010, 225),
    ]


def _build_matrix() -> List[SponsorLenderMatrix]:
    return [
        SponsorLenderMatrix("Welsh Carson", "Ares Capital", 8, 945.0, 5.8, "platinum"),
        SponsorLenderMatrix("Warburg Pincus", "Apollo Credit", 6, 825.0, 5.9, "platinum"),
        SponsorLenderMatrix("TPG", "Blue Owl Capital", 7, 685.0, 5.7, "gold"),
        SponsorLenderMatrix("KKR", "KKR Credit (captive)", 9, 1250.0, 6.0, "captive"),
        SponsorLenderMatrix("Bain Capital", "Bain Credit (captive)", 7, 985.0, 5.9, "captive"),
        SponsorLenderMatrix("New Mountain", "Golub Capital", 5, 485.0, 5.6, "gold"),
        SponsorLenderMatrix("Audax Private Equity", "Antares Capital", 6, 425.0, 5.7, "gold"),
        SponsorLenderMatrix("Webster Equity", "HPS Investment Partners", 4, 325.0, 5.8, "gold"),
        SponsorLenderMatrix("Frazier Healthcare", "Churchill AM", 4, 285.0, 5.5, "silver"),
        SponsorLenderMatrix("Silversmith Capital", "Blue Owl", 3, 225.0, 5.4, "silver"),
    ]


def _build_defaults() -> List[DefaultTrend]:
    return [
        DefaultTrend("2021Q4", 0.008, 0.012, 0.032, 2),
        DefaultTrend("2022Q2", 0.012, 0.018, 0.048, 4),
        DefaultTrend("2022Q4", 0.018, 0.022, 0.065, 6),
        DefaultTrend("2023Q2", 0.028, 0.028, 0.085, 11),
        DefaultTrend("2023Q4", 0.035, 0.032, 0.095, 14),
        DefaultTrend("2024Q2", 0.042, 0.035, 0.112, 18),
        DefaultTrend("2024Q4", 0.045, 0.037, 0.125, 21),
        DefaultTrend("2025Q2", 0.048, 0.038, 0.135, 24),
        DefaultTrend("2025Q4", 0.042, 0.036, 0.128, 22),
        DefaultTrend("2026Q1", 0.038, 0.034, 0.118, 19),
    ]


def _build_marks() -> List[PortfolioMark]:
    return [
        PortfolioMark("ASC / Surgery", 485.0, 98.5, 7.28, False),
        PortfolioMark("Behavioral Health", 385.0, 94.2, 22.33, True),
        PortfolioMark("Home Health / Hospice", 325.0, 92.8, 23.40, True),
        PortfolioMark("Dental DSO", 245.0, 95.8, 10.29, False),
        PortfolioMark("Dermatology", 195.0, 99.2, 1.56, False),
        PortfolioMark("Primary Care", 285.0, 96.5, 9.98, False),
        PortfolioMark("Physical Therapy", 165.0, 97.8, 3.63, False),
        PortfolioMark("Fertility / IVF", 145.0, 101.2, -1.74, False),
        PortfolioMark("Telehealth Platform", 95.0, 88.5, 10.93, True),
        PortfolioMark("Specialty Pharmacy", 215.0, 97.2, 6.02, False),
        PortfolioMark("Skilled Nursing", 125.0, 86.5, 16.88, True),
        PortfolioMark("HCIT / SaaS", 175.0, 100.5, -0.88, False),
    ]


def compute_direct_lending() -> DirectLendingResult:
    corpus = _load_corpus()

    facilities = _build_facilities()
    rates = _build_rates()
    matrix = _build_matrix()
    defaults = _build_defaults()
    marks = _build_marks()

    total_out = sum(f.outstanding_mm for f in facilities)
    blended_rate = sum(f.all_in_rate_pct * f.outstanding_mm for f in facilities) / total_out if total_out else 0
    weighted_lev = sum(m.avg_leverage * m.total_committed_mm for m in matrix) / sum(m.total_committed_mm for m in matrix) if matrix else 0
    cov_lite_out = sum(f.outstanding_mm for f in facilities if f.cov_lite)
    cov_lite_pct = cov_lite_out / total_out if total_out else 0

    return DirectLendingResult(
        total_facilities=len(facilities),
        total_outstanding_mm=round(total_out, 2),
        blended_all_in_rate_pct=round(blended_rate, 3),
        weighted_leverage=round(weighted_lev, 2),
        cov_lite_pct=round(cov_lite_pct, 4),
        facilities=facilities,
        rates=rates,
        matrix=matrix,
        defaults=defaults,
        marks=marks,
        corpus_deal_count=len(corpus),
    )
