"""Treasury / Cash Position Tracker.

Tracks portfolio-wide liquidity: cash balances, revolver utilization,
cash burn rate, working capital, intercompany loans, hedging positions.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CashPosition:
    deal: str
    operating_cash_m: float
    restricted_cash_m: float
    investments_m: float
    total_liquidity_m: float
    revolver_drawn_m: float
    revolver_capacity_m: float
    revolver_availability_m: float
    days_of_opex: int


@dataclass
class WorkingCapital:
    deal: str
    ar_m: float
    ar_days: int
    inventory_m: float
    inventory_days: int
    ap_m: float
    ap_days: int
    nwc_m: float
    nwc_trend_pp: float


@dataclass
class CashBurnRate:
    deal: str
    monthly_revenue_m: float
    monthly_ebitda_m: float
    monthly_free_cash_flow_m: float
    monthly_capex_m: float
    monthly_interest_m: float
    cash_runway_months: float
    status: str


@dataclass
class BankAccount:
    deal: str
    bank: str
    account_type: str
    balance_m: float
    fdic_insured_pct: float
    sweep_enabled: bool
    yield_pct: float


@dataclass
class HedgingPosition:
    deal: str
    hedge_type: str
    notional_m: float
    fixed_rate_pct: float
    floating_benchmark: str
    expiration: str
    mtm_value_m: float


@dataclass
class IntercompanyBalance:
    from_entity: str
    to_entity: str
    balance_m: float
    rate_pct: float
    purpose: str
    expected_settlement: str


@dataclass
class TreasuryResult:
    total_portfolio_liquidity_m: float
    total_cash_and_investments_m: float
    total_revolver_capacity_m: float
    total_revolver_drawn_m: float
    weighted_revolver_utilization_pct: float
    at_risk_deals: int
    cash_positions: List[CashPosition]
    working_capital: List[WorkingCapital]
    burn_rate: List[CashBurnRate]
    accounts: List[BankAccount]
    hedging: List[HedgingPosition]
    intercompany: List[IntercompanyBalance]
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


def _build_cash_positions() -> List[CashPosition]:
    return [
        CashPosition("Project Cypress — GI Network", 42.5, 8.5, 35.0, 86.0, 25.0, 75.0, 50.0, 95),
        CashPosition("Project Magnolia — MSK Platform", 28.5, 6.2, 25.0, 59.7, 15.0, 60.0, 45.0, 82),
        CashPosition("Project Redwood — Behavioral", 18.5, 4.8, 12.0, 35.3, 35.0, 45.0, 10.0, 58),
        CashPosition("Project Laurel — Derma", 22.0, 3.5, 18.0, 43.5, 5.0, 30.0, 25.0, 105),
        CashPosition("Project Cedar — Cardiology", 38.5, 7.5, 32.0, 78.0, 20.0, 75.0, 55.0, 88),
        CashPosition("Project Willow — Fertility", 18.5, 5.2, 15.0, 38.7, 12.0, 45.0, 33.0, 72),
        CashPosition("Project Spruce — Radiology", 22.0, 4.5, 18.0, 44.5, 10.0, 40.0, 30.0, 92),
        CashPosition("Project Aspen — Eye Care", 15.5, 3.8, 12.0, 31.3, 8.0, 30.0, 22.0, 75),
        CashPosition("Project Maple — Urology", 8.5, 2.2, 6.0, 16.7, 6.0, 20.0, 14.0, 68),
        CashPosition("Project Ash — Infusion", 32.5, 7.2, 28.0, 67.7, 25.0, 80.0, 55.0, 82),
        CashPosition("Project Fir — Lab / Pathology", 38.5, 8.5, 32.0, 79.0, 18.0, 75.0, 57.0, 92),
        CashPosition("Project Sage — Home Health", 12.5, 3.8, 8.0, 24.3, 40.0, 60.0, 20.0, 48),
        CashPosition("Project Linden — Behavioral", 10.5, 2.8, 7.0, 20.3, 22.0, 35.0, 13.0, 55),
        CashPosition("Project Oak — RCM SaaS", 48.5, 5.5, 85.0, 139.0, 0.0, 50.0, 50.0, 245),
        CashPosition("Project Basil — Dental DSO", 22.5, 5.5, 18.0, 46.0, 18.0, 55.0, 37.0, 85),
        CashPosition("Project Thyme — Specialty Pharm", 35.5, 7.2, 28.0, 70.7, 15.0, 70.0, 55.0, 92),
    ]


def _build_working_capital() -> List[WorkingCapital]:
    return [
        WorkingCapital("Project Cypress — GI Network", 85.5, 42, 4.2, 18, 28.5, 32, 61.2, -2.5),
        WorkingCapital("Project Magnolia — MSK Platform", 62.5, 45, 3.5, 22, 22.0, 35, 44.0, -3.2),
        WorkingCapital("Project Redwood — Behavioral", 45.2, 68, 2.0, 25, 18.5, 45, 28.7, 4.5),
        WorkingCapital("Project Laurel — Derma", 28.5, 32, 5.2, 38, 12.0, 28, 21.7, -1.8),
        WorkingCapital("Project Cedar — Cardiology", 95.5, 48, 5.8, 25, 32.5, 35, 68.8, -2.2),
        WorkingCapital("Project Willow — Fertility", 38.5, 38, 3.8, 28, 12.5, 32, 29.8, -2.5),
        WorkingCapital("Project Spruce — Radiology", 52.5, 42, 2.2, 18, 18.5, 35, 36.2, -1.5),
        WorkingCapital("Project Aspen — Eye Care", 42.5, 45, 4.5, 32, 16.5, 35, 30.5, -2.0),
        WorkingCapital("Project Maple — Urology", 22.5, 48, 2.8, 28, 8.5, 35, 16.8, -1.8),
        WorkingCapital("Project Ash — Infusion", 85.5, 52, 18.5, 45, 28.5, 38, 75.5, 2.8),
        WorkingCapital("Project Fir — Lab / Pathology", 65.5, 42, 5.2, 25, 22.5, 38, 48.2, -2.2),
        WorkingCapital("Project Sage — Home Health", 85.5, 78, 2.5, 12, 25.0, 45, 63.0, 8.5),
        WorkingCapital("Project Linden — Behavioral", 48.5, 72, 1.8, 15, 18.0, 42, 32.3, 6.2),
        WorkingCapital("Project Oak — RCM SaaS", 35.5, 48, 0.5, 15, 12.0, 35, 24.0, -3.8),
        WorkingCapital("Project Basil — Dental DSO", 42.5, 38, 3.8, 35, 16.5, 32, 29.8, -2.8),
        WorkingCapital("Project Thyme — Specialty Pharm", 95.5, 45, 45.5, 38, 48.5, 42, 92.5, -3.2),
    ]


def _build_burn_rate() -> List[CashBurnRate]:
    return [
        CashBurnRate("Project Cypress — GI Network", 42.5, 11.8, 8.5, 1.8, 1.5, 12.5, "healthy"),
        CashBurnRate("Project Magnolia — MSK Platform", 38.5, 9.5, 6.8, 2.2, 1.2, 10.5, "healthy"),
        CashBurnRate("Project Redwood — Behavioral", 24.5, 4.2, 2.2, 1.2, 1.5, 6.2, "monitor"),
        CashBurnRate("Project Laurel — Derma", 22.5, 7.0, 5.8, 0.8, 0.3, 15.5, "healthy"),
        CashBurnRate("Project Cedar — Cardiology", 52.5, 15.2, 10.5, 2.2, 2.5, 13.5, "healthy"),
        CashBurnRate("Project Willow — Fertility", 26.5, 6.2, 4.8, 1.2, 0.8, 9.8, "healthy"),
        CashBurnRate("Project Spruce — Radiology", 36.5, 9.5, 6.2, 1.8, 1.5, 11.5, "healthy"),
        CashBurnRate("Project Aspen — Eye Care", 28.5, 7.0, 4.5, 1.5, 1.0, 9.2, "healthy"),
        CashBurnRate("Project Maple — Urology", 14.5, 4.0, 2.5, 0.8, 0.7, 7.8, "monitor"),
        CashBurnRate("Project Ash — Infusion", 48.5, 10.5, 7.2, 1.8, 1.5, 12.2, "healthy"),
        CashBurnRate("Project Fir — Lab / Pathology", 42.5, 11.5, 8.2, 2.0, 1.3, 12.5, "healthy"),
        CashBurnRate("Project Sage — Home Health", 52.5, 7.2, 3.5, 2.5, 1.8, 5.8, "monitor"),
        CashBurnRate("Project Linden — Behavioral", 18.5, 2.8, 1.2, 1.2, 1.0, 4.5, "watch"),
        CashBurnRate("Project Oak — RCM SaaS", 21.5, 7.8, 6.8, 0.5, 0.0, 34.5, "healthy"),
        CashBurnRate("Project Basil — Dental DSO", 28.5, 7.2, 4.5, 1.8, 1.0, 9.8, "healthy"),
        CashBurnRate("Project Thyme — Specialty Pharm", 68.5, 8.5, 5.2, 1.5, 0.8, 12.5, "healthy"),
    ]


def _build_accounts() -> List[BankAccount]:
    return [
        BankAccount("Project Cypress — GI Network", "JPMorgan Chase", "Treasury Sweep", 42.5, 1.00, True, 5.25),
        BankAccount("Project Magnolia — MSK Platform", "JPMorgan Chase", "Treasury Sweep", 28.5, 1.00, True, 5.25),
        BankAccount("Project Redwood — Behavioral", "BofA", "Treasury Sweep", 18.5, 1.00, True, 5.10),
        BankAccount("Project Laurel — Derma", "JPMorgan Chase", "Treasury Sweep", 22.0, 1.00, True, 5.25),
        BankAccount("Project Cedar — Cardiology", "BofA", "Treasury Sweep", 38.5, 1.00, True, 5.10),
        BankAccount("Project Willow — Fertility", "Citi", "Treasury Sweep", 18.5, 1.00, True, 5.05),
        BankAccount("Project Spruce — Radiology", "Wells Fargo", "Treasury Sweep", 22.0, 1.00, True, 5.05),
        BankAccount("Project Aspen — Eye Care", "BofA", "Treasury Sweep", 15.5, 1.00, True, 5.10),
        BankAccount("Project Maple — Urology", "JPMorgan Chase", "Treasury Sweep", 8.5, 1.00, True, 5.25),
        BankAccount("Project Ash — Infusion", "Citi", "Treasury Sweep", 32.5, 1.00, True, 5.05),
        BankAccount("Project Fir — Lab / Pathology", "JPMorgan Chase", "Treasury Sweep", 38.5, 1.00, True, 5.25),
        BankAccount("Project Sage — Home Health", "Wells Fargo", "Operating", 12.5, 0.08, False, 0.15),
        BankAccount("Project Linden — Behavioral", "BofA", "Operating", 10.5, 0.12, False, 0.15),
        BankAccount("Project Oak — RCM SaaS", "JPMorgan Chase + Goldman Private Wealth", "Treasury + Investments", 48.5, 0.12, True, 5.35),
        BankAccount("Project Basil — Dental DSO", "BofA", "Treasury Sweep", 22.5, 1.00, True, 5.10),
        BankAccount("Project Thyme — Specialty Pharm", "JPMorgan Chase", "Treasury Sweep", 35.5, 1.00, True, 5.25),
    ]


def _build_hedging() -> List[HedgingPosition]:
    return [
        HedgingPosition("Project Cypress — GI Network", "Interest Rate Swap", 225.0, 3.75, "SOFR 1-month", "2029-06-30", 8.5),
        HedgingPosition("Project Magnolia — MSK Platform", "Interest Rate Swap", 185.0, 3.85, "SOFR 1-month", "2029-03-31", 7.2),
        HedgingPosition("Project Cedar — Cardiology", "Interest Rate Swap", 210.0, 3.75, "SOFR 1-month", "2029-09-30", 8.8),
        HedgingPosition("Project Fir — Lab / Pathology", "Interest Rate Swap", 215.0, 3.75, "SOFR 1-month", "2029-12-31", 8.5),
        HedgingPosition("Project Ash — Infusion", "Interest Rate Swap", 245.0, 3.90, "SOFR 1-month", "2030-03-31", 9.2),
        HedgingPosition("Project Willow — Fertility", "Interest Rate Swap", 145.0, 3.95, "SOFR 1-month", "2030-06-30", 5.5),
        HedgingPosition("Project Spruce — Radiology", "Interest Rate Swap", 170.0, 3.85, "SOFR 1-month", "2029-09-30", 6.8),
        HedgingPosition("Project Thyme — Specialty Pharm", "Interest Rate Swap", 225.0, 3.85, "SOFR 1-month", "2029-12-31", 8.8),
        HedgingPosition("Project Aspen — Eye Care", "Interest Rate Cap", 100.0, 4.50, "SOFR 1-month", "2029-06-30", 2.2),
        HedgingPosition("Project Magnolia — MSK Platform", "FX Forward (USD / MXN)", 15.0, 17.50, "MXN spot", "2026-09-30", 0.4),
    ]


def _build_intercompany() -> List[IntercompanyBalance]:
    return [
        IntercompanyBalance("Project Oak — RCM SaaS (US)", "Oak Ireland HoldCo", 45.0, 5.50, "IP royalty payment buffer", "2026-09-30"),
        IntercompanyBalance("Project Thyme — Specialty Pharm (US)", "Thyme PR IP HoldCo", 28.5, 5.25, "Working capital + IP royalty", "2026-12-31"),
        IntercompanyBalance("Project Fir — Lab / Pathology (US)", "Fir Cayman HoldCo", 12.5, 6.00, "Lab services TP settlement", "2026-08-31"),
        IntercompanyBalance("Project Willow — Fertility (US)", "Willow Asia-Pacific HoldCo", 8.5, 5.75, "Technology licensing", "2027-03-31"),
        IntercompanyBalance("Project Cypress — GI Network (Platform)", "Cypress FL SubCo", 18.5, 4.50, "ASC working capital bridge", "2026-06-30"),
        IntercompanyBalance("Project Magnolia — MSK Platform", "Magnolia Austin De Novo", 5.5, 4.25, "Austin clinic ramp", "2026-12-31"),
        IntercompanyBalance("Project Redwood — Behavioral (Platform)", "Redwood East SubCo", 4.8, 4.00, "Working capital support", "2026-09-30"),
        IntercompanyBalance("Project Cedar — Cardiology (Platform)", "Cedar AZ SubCo", 8.5, 4.50, "Cath lab CapEx bridge", "2026-10-31"),
    ]


def compute_treasury_tracker() -> TreasuryResult:
    corpus = _load_corpus()
    cash_positions = _build_cash_positions()
    working_capital = _build_working_capital()
    burn_rate = _build_burn_rate()
    accounts = _build_accounts()
    hedging = _build_hedging()
    intercompany = _build_intercompany()

    total_liquidity = sum(c.total_liquidity_m for c in cash_positions)
    total_cash = sum(c.operating_cash_m + c.restricted_cash_m + c.investments_m for c in cash_positions)
    total_rev_cap = sum(c.revolver_capacity_m for c in cash_positions)
    total_rev_drawn = sum(c.revolver_drawn_m for c in cash_positions)
    wtd_util = total_rev_drawn / total_rev_cap if total_rev_cap > 0 else 0
    at_risk = sum(1 for b in burn_rate if b.status in ("watch", "critical"))

    return TreasuryResult(
        total_portfolio_liquidity_m=round(total_liquidity, 1),
        total_cash_and_investments_m=round(total_cash, 1),
        total_revolver_capacity_m=round(total_rev_cap, 1),
        total_revolver_drawn_m=round(total_rev_drawn, 1),
        weighted_revolver_utilization_pct=round(wtd_util, 4),
        at_risk_deals=at_risk,
        cash_positions=cash_positions,
        working_capital=working_capital,
        burn_rate=burn_rate,
        accounts=accounts,
        hedging=hedging,
        intercompany=intercompany,
        corpus_deal_count=len(corpus),
    )
