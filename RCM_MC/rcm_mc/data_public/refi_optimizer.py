"""Debt Capital Markets / Refinance Optimizer.

Tracks refi opportunities across a sponsor's entire portfolio — existing
debt maturity schedule, current vs market pricing, covenant profile,
refi NPV per holdco. Helps sponsors time refis, extend maturities, or
re-cut deals to optimize portfolio-wide interest burden.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PortfolioDebt:
    holdco: str
    sector: str
    original_face_mm: float
    current_balance_mm: float
    current_rate_pct: float
    maturity_year: int
    years_remaining: float
    covenant_type: str
    refi_window_status: str


@dataclass
class RefiOpportunity:
    holdco: str
    current_rate_pct: float
    achievable_rate_pct: float
    rate_savings_bps: int
    amount_mm: float
    annual_interest_savings_mm: float
    npv_savings_mm: float
    refi_cost_mm: float
    net_npv_mm: float
    priority: str


@dataclass
class MarketWindow:
    period: str
    spread_trend: str
    primary_issuance_b: float
    dl_issuance_b: float
    investor_demand: str
    commentary: str


@dataclass
class LenderQuote:
    lender: str
    product: str
    facility_size_mm: float
    spread_sofr_bps: int
    term_years: int
    cov_lite: bool
    oid_pct: float
    closing_fee_bps: int
    confidence: str


@dataclass
class MaturityProfile:
    year: int
    holdcos_maturing: int
    total_balance_mm: float
    refi_status: str


@dataclass
class CovenantRelief:
    holdco: str
    current_leverage: float
    covenant_leverage: float
    headroom_x: float
    remediation: str


@dataclass
class RefiResult:
    total_portfolio_debt_mm: float
    weighted_rate_pct: float
    refi_opportunities_identified: int
    total_refi_npv_mm: float
    near_term_maturities_mm: float
    portfolio: List[PortfolioDebt]
    opportunities: List[RefiOpportunity]
    market_windows: List[MarketWindow]
    quotes: List[LenderQuote]
    maturity: List[MaturityProfile]
    covenant: List[CovenantRelief]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 118):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_portfolio() -> List[PortfolioDebt]:
    return [
        PortfolioDebt("Project Azalea (GI Network)", "Gastroenterology", 285.0, 252.5, 9.45, 2031, 5.8, "maintenance", "in-window"),
        PortfolioDebt("Project Beacon (Dermatology)", "Dermatology", 245.0, 218.0, 9.20, 2030, 4.5, "cov-lite", "approaching-window"),
        PortfolioDebt("Project Cadence (Path Lab)", "Pathology / Labs", 185.0, 162.0, 10.20, 2029, 3.8, "maintenance", "in-window"),
        PortfolioDebt("Project Denali (ASC Platform)", "ASC Network", 425.0, 385.0, 9.35, 2031, 5.5, "cov-lite", "in-window"),
        PortfolioDebt("Project Everest (Behavioral)", "Behavioral Health", 325.0, 292.0, 10.85, 2030, 4.8, "maintenance", "priority"),
        PortfolioDebt("Project Flagstaff (Ortho)", "Orthopedics", 225.0, 201.0, 9.85, 2031, 5.2, "cov-lite", "in-window"),
        PortfolioDebt("Project Glacier (Home Health)", "Home Health", 165.0, 148.0, 10.35, 2029, 3.6, "maintenance", "in-window"),
        PortfolioDebt("Project Ironwood (Cardiology)", "Cardiology", 385.0, 345.0, 9.15, 2032, 6.5, "cov-lite", "long-dated"),
        PortfolioDebt("Project Juniper (Specialty Rx)", "Specialty Pharmacy", 225.0, 202.0, 9.05, 2031, 5.4, "cov-lite", "in-window"),
        PortfolioDebt("Project Kestrel (Fertility)", "Fertility / IVF", 475.0, 428.0, 9.25, 2032, 6.3, "cov-lite", "long-dated"),
        PortfolioDebt("Project Larkspur (Dental DSO)", "Dental DSO", 85.0, 75.0, 11.25, 2028, 2.8, "maintenance", "priority"),
        PortfolioDebt("Project Meridian (MSK)", "MSK Platform", 325.0, 292.0, 9.40, 2031, 5.4, "cov-lite", "in-window"),
        PortfolioDebt("Project Nevada (Oncology Services)", "Oncology", 185.0, 168.0, 9.95, 2030, 4.3, "cov-lite", "in-window"),
        PortfolioDebt("Project Ovation (Urgent Care)", "Urgent Care", 115.0, 102.0, 10.65, 2029, 3.5, "maintenance", "in-window"),
        PortfolioDebt("Project Pacifica (HCIT/SaaS)", "HCIT / SaaS", 145.0, 128.0, 9.05, 2032, 6.2, "cov-lite", "long-dated"),
    ]


def _build_opportunities(portfolio: List[PortfolioDebt]) -> List[RefiOpportunity]:
    current_market_rate = 8.75
    rows = []
    for p in portfolio:
        if p.refi_window_status == "long-dated":
            continue
        savings_bps = int((p.current_rate_pct - current_market_rate) * 100)
        if savings_bps < 20:
            continue
        annual_savings = p.current_balance_mm * savings_bps / 10000
        refi_cost = p.current_balance_mm * 0.015  # 1.5% refi cost
        npv_savings = annual_savings * p.years_remaining * 0.85   # discount ~8%
        net_npv = npv_savings - refi_cost
        if net_npv < 1.0:
            priority = "monitor"
        elif net_npv < 4.0:
            priority = "standard"
        else:
            priority = "urgent"
        rows.append(RefiOpportunity(
            holdco=p.holdco,
            current_rate_pct=p.current_rate_pct,
            achievable_rate_pct=current_market_rate,
            rate_savings_bps=savings_bps,
            amount_mm=p.current_balance_mm,
            annual_interest_savings_mm=round(annual_savings, 2),
            npv_savings_mm=round(npv_savings, 2),
            refi_cost_mm=round(refi_cost, 2),
            net_npv_mm=round(net_npv, 2),
            priority=priority,
        ))
    return sorted(rows, key=lambda r: r.net_npv_mm, reverse=True)


def _build_market_windows() -> List[MarketWindow]:
    return [
        MarketWindow("2024Q1", "widening (SVB fallout)", 85.0, 125.0, "selective", "Flight to quality; tight pricing"),
        MarketWindow("2024Q2", "tightening", 115.0, 158.0, "broad", "Base rates stabilize; demand returns"),
        MarketWindow("2024Q3", "stable", 128.0, 185.0, "strong", "Healthcare-specific demand robust"),
        MarketWindow("2024Q4", "tightening", 152.0, 215.0, "very strong", "Year-end issuance surge"),
        MarketWindow("2025Q1", "stable", 142.0, 225.0, "strong", "Issuance pace remains healthy"),
        MarketWindow("2025Q2", "tightening", 168.0, 245.0, "very strong", "Best window for refinancing"),
        MarketWindow("2025Q3", "widening", 145.0, 218.0, "moderate", "Market digesting supply"),
        MarketWindow("2025Q4", "stable", 158.0, 232.0, "strong", "Window re-opens"),
        MarketWindow("2026Q1", "tightening", 175.0, 265.0, "very strong", "Anticipate rate-cut tailwind"),
    ]


def _build_quotes() -> List[LenderQuote]:
    return [
        LenderQuote("Ares Capital (Direct Lender)", "Unitranche", 325.0, 450, 6, True, 0.010, 225, "firm"),
        LenderQuote("Blue Owl Capital", "Unitranche", 285.0, 425, 7, True, 0.010, 200, "firm"),
        LenderQuote("Golub Capital", "Unitranche", 245.0, 475, 6, True, 0.012, 225, "firm"),
        LenderQuote("Apollo Credit", "First-Lien + Second-Lien", 385.0, 475, 7, True, 0.010, 225, "firm"),
        LenderQuote("KKR Credit (captive)", "Unitranche", 425.0, 425, 7, True, 0.008, 200, "firm"),
        LenderQuote("Bain Capital Credit", "Unitranche", 350.0, 450, 7, True, 0.010, 200, "firm"),
        LenderQuote("HPS Investment Partners", "Unitranche + PIK Option", 285.0, 475, 7, True, 0.012, 225, "indicative"),
        LenderQuote("Antares Capital", "Unitranche", 325.0, 460, 6, True, 0.010, 225, "firm"),
        LenderQuote("JPMorgan TL-B Syndicated", "First-Lien TL-B", 500.0, 375, 7, True, 0.005, 150, "indicative (BBB-)"),
        LenderQuote("Goldman Syndicated TL-B", "First-Lien TL-B", 475.0, 400, 7, True, 0.006, 150, "indicative"),
        LenderQuote("Monroe Capital", "Unitranche", 225.0, 525, 6, False, 0.015, 275, "firm"),
        LenderQuote("Churchill AM", "Unitranche", 245.0, 475, 6, True, 0.010, 200, "firm"),
    ]


def _build_maturity(portfolio: List[PortfolioDebt]) -> List[MaturityProfile]:
    years = {}
    for p in portfolio:
        years.setdefault(p.maturity_year, []).append(p)
    rows = []
    for year in sorted(years.keys()):
        ps = years[year]
        total = sum(p.current_balance_mm for p in ps)
        if year <= 2029:
            status = "near-term"
        elif year <= 2031:
            status = "intermediate"
        else:
            status = "long-dated"
        rows.append(MaturityProfile(
            year=year, holdcos_maturing=len(ps),
            total_balance_mm=round(total, 2), refi_status=status,
        ))
    return rows


def _build_covenant() -> List[CovenantRelief]:
    return [
        CovenantRelief("Project Azalea", 4.85, 6.25, 1.40, "in compliance"),
        CovenantRelief("Project Beacon", 5.55, 6.25, 0.70, "watch list"),
        CovenantRelief("Project Cadence", 4.25, 6.25, 2.00, "healthy"),
        CovenantRelief("Project Denali", 5.10, 6.25, 1.15, "in compliance"),
        CovenantRelief("Project Everest", 6.45, 6.75, 0.30, "tight — cure rights activated"),
        CovenantRelief("Project Flagstaff", 4.95, 6.25, 1.30, "in compliance"),
        CovenantRelief("Project Glacier", 5.80, 6.25, 0.45, "watch list"),
        CovenantRelief("Project Ironwood", 4.55, 6.25, 1.70, "healthy"),
        CovenantRelief("Project Juniper", 4.75, 6.25, 1.50, "healthy"),
        CovenantRelief("Project Kestrel", 5.35, 6.25, 0.90, "in compliance"),
        CovenantRelief("Project Larkspur", 5.95, 6.50, 0.55, "tight — refi priority"),
        CovenantRelief("Project Meridian", 4.85, 6.25, 1.40, "in compliance"),
    ]


def compute_refi_optimizer() -> RefiResult:
    corpus = _load_corpus()

    portfolio = _build_portfolio()
    opportunities = _build_opportunities(portfolio)
    market_windows = _build_market_windows()
    quotes = _build_quotes()
    maturity = _build_maturity(portfolio)
    covenant = _build_covenant()

    total_debt = sum(p.current_balance_mm for p in portfolio)
    weighted_rate = sum(p.current_rate_pct * p.current_balance_mm for p in portfolio) / total_debt if total_debt else 0
    total_npv = sum(o.net_npv_mm for o in opportunities)
    near_term = sum(m.total_balance_mm for m in maturity if m.year <= 2029)

    return RefiResult(
        total_portfolio_debt_mm=round(total_debt, 2),
        weighted_rate_pct=round(weighted_rate, 3),
        refi_opportunities_identified=len(opportunities),
        total_refi_npv_mm=round(total_npv, 2),
        near_term_maturities_mm=round(near_term, 2),
        portfolio=portfolio,
        opportunities=opportunities,
        market_windows=market_windows,
        quotes=quotes,
        maturity=maturity,
        covenant=covenant,
        corpus_deal_count=len(corpus),
    )
