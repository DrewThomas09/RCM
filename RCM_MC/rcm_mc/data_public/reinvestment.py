"""Reinvestment / Compounding Analyzer.

Models capital allocation of operating cash flow over hold:
- FCF generation and reinvestment options
- Bolt-on M&A vs debt paydown vs organic capex vs dividends
- Compounding MOIC with reinvested capital
- Marginal ROI of each allocation option
- 5-year capital allocation plan
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CashFlowYear:
    year: int
    ebitda_mm: float
    interest_paid_mm: float
    taxes_mm: float
    capex_maintenance_mm: float
    free_cash_flow_mm: float
    cumulative_fcf_mm: float


@dataclass
class AllocationOption:
    option: str
    capital_deployed_mm: float
    expected_roi_irr: float
    expected_moic: float
    risk: str
    strategic_value: str
    marginal_impact_on_exit_mm: float


@dataclass
class CompoundingScenario:
    scenario: str
    total_fcf_deployed_mm: float
    boltons_acquired: int
    organic_capex_mm: float
    debt_paydown_mm: float
    dividends_mm: float
    terminal_ebitda_mm: float
    terminal_ev_mm: float
    equity_moic: float
    equity_irr: float


@dataclass
class YearlyAllocation:
    year: int
    available_fcf_mm: float
    boltons_mm: float
    organic_mm: float
    debt_paydown_mm: float
    dividend_mm: float
    retained_cash_mm: float


@dataclass
class ReinvestmentResult:
    entry_ev_mm: float
    entry_equity_mm: float
    hold_years: int
    cumulative_fcf_mm: float
    base_case_moic: float
    compounded_moic: float
    moic_lift_from_reinvestment: float
    cash_flow_years: List[CashFlowYear]
    allocation_options: List[AllocationOption]
    scenarios: List[CompoundingScenario]
    yearly_allocation: List[YearlyAllocation]
    recommended_allocation_mix: Dict[str, float]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 77):
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


def _build_cash_flow(
    entry_ebitda: float, growth_pct: float, hold_years: int,
    entry_debt: float, interest_rate: float,
) -> List[CashFlowYear]:
    rows = []
    cum_fcf = 0
    current_debt = entry_debt
    for yr in range(1, hold_years + 1):
        ebitda = entry_ebitda * ((1 + growth_pct) ** yr)
        # Interest (declining as debt paid down)
        interest = current_debt * interest_rate
        # Taxes at 25% of EBIT (EBITDA less D&A approx)
        taxable_income = max(0, ebitda - interest - ebitda * 0.04)  # 4% D&A
        taxes = taxable_income * 0.25
        # Maintenance capex ~ 2% of revenue ~ 11% of ebitda
        capex = ebitda * 0.11
        fcf = ebitda - interest - taxes - capex
        cum_fcf += fcf
        # Assume 30% of FCF goes to debt paydown
        current_debt = max(0, current_debt - fcf * 0.30)
        rows.append(CashFlowYear(
            year=yr,
            ebitda_mm=round(ebitda, 2),
            interest_paid_mm=round(interest, 2),
            taxes_mm=round(taxes, 2),
            capex_maintenance_mm=round(capex, 2),
            free_cash_flow_mm=round(fcf, 2),
            cumulative_fcf_mm=round(cum_fcf, 2),
        ))
    return rows


def _build_allocation_options(total_fcf: float) -> List[AllocationOption]:
    return [
        AllocationOption(
            option="Bolt-on M&A (multiple arbitrage)",
            capital_deployed_mm=round(total_fcf * 0.35, 1),
            expected_roi_irr=0.22,
            expected_moic=2.4,
            risk="medium",
            strategic_value="Highest — scale + multiple arbitrage",
            marginal_impact_on_exit_mm=round(total_fcf * 0.35 * 1.4, 1),
        ),
        AllocationOption(
            option="Organic De Novo Sites",
            capital_deployed_mm=round(total_fcf * 0.20, 1),
            expected_roi_irr=0.18,
            expected_moic=2.1,
            risk="medium",
            strategic_value="High — controlled growth",
            marginal_impact_on_exit_mm=round(total_fcf * 0.20 * 1.1, 1),
        ),
        AllocationOption(
            option="Debt Paydown",
            capital_deployed_mm=round(total_fcf * 0.25, 1),
            expected_roi_irr=0.085,
            expected_moic=1.4,
            risk="low",
            strategic_value="Low — deleveraging for exit",
            marginal_impact_on_exit_mm=round(total_fcf * 0.25 * 0.4, 1),
        ),
        AllocationOption(
            option="Technology / Platform Investment",
            capital_deployed_mm=round(total_fcf * 0.08, 1),
            expected_roi_irr=0.15,
            expected_moic=1.9,
            risk="medium",
            strategic_value="Medium — quality + efficiency",
            marginal_impact_on_exit_mm=round(total_fcf * 0.08 * 0.9, 1),
        ),
        AllocationOption(
            option="Dividend Recap to LPs",
            capital_deployed_mm=round(total_fcf * 0.10, 1),
            expected_roi_irr=0.0,
            expected_moic=1.0,
            risk="low",
            strategic_value="Low — pure cash return",
            marginal_impact_on_exit_mm=0,
        ),
        AllocationOption(
            option="Working Capital Investment",
            capital_deployed_mm=round(total_fcf * 0.02, 1),
            expected_roi_irr=0.12,
            expected_moic=1.6,
            risk="low",
            strategic_value="Low — operations",
            marginal_impact_on_exit_mm=round(total_fcf * 0.02 * 0.6, 1),
        ),
    ]


def _build_scenarios(
    entry_ev: float, entry_equity: float, base_ebitda: float,
    hold_years: int, total_fcf: float,
) -> List[CompoundingScenario]:
    # Base case: all FCF → debt paydown
    base_terminal_ebitda = base_ebitda * ((1.06) ** hold_years)
    base_exit_ev = base_terminal_ebitda * 12
    base_equity = base_exit_ev - (entry_ev - entry_equity) + total_fcf * 0.60
    base_moic = base_equity / entry_equity

    scenarios = []

    # Scenario A: All into bolt-ons (2.5x on deployed)
    sa_bolton_ebitda = total_fcf * 0.8 / 7.5   # bolt-on avg at 7.5x
    sa_terminal = base_terminal_ebitda + sa_bolton_ebitda * 1.15   # synergies
    sa_exit = sa_terminal * 12
    sa_equity = sa_exit - (entry_ev - entry_equity) * 0.60  # less debt paydown
    scenarios.append(CompoundingScenario(
        scenario="Aggressive M&A (80% to bolt-ons)",
        total_fcf_deployed_mm=total_fcf, boltons_acquired=5,
        organic_capex_mm=total_fcf * 0.10,
        debt_paydown_mm=total_fcf * 0.05,
        dividends_mm=total_fcf * 0.05,
        terminal_ebitda_mm=round(sa_terminal, 1),
        terminal_ev_mm=round(sa_exit, 1),
        equity_moic=round(sa_equity / entry_equity, 2) if entry_equity else 0,
        equity_irr=round(((sa_equity / entry_equity) ** (1 / hold_years) - 1), 4) if entry_equity else 0,
    ))

    # Scenario B: Balanced (35/20/25/10/10)
    sb_bolton_ebitda = total_fcf * 0.35 / 7.5
    sb_organic_ebitda = total_fcf * 0.20 * 0.15  # 15% IRR on organic
    sb_terminal = base_terminal_ebitda + sb_bolton_ebitda * 1.15 + sb_organic_ebitda
    sb_exit = sb_terminal * 12
    sb_equity = sb_exit - (entry_ev - entry_equity) * 0.60 + total_fcf * 0.10
    scenarios.append(CompoundingScenario(
        scenario="Balanced (35% M&A / 20% organic)",
        total_fcf_deployed_mm=total_fcf, boltons_acquired=3,
        organic_capex_mm=total_fcf * 0.20,
        debt_paydown_mm=total_fcf * 0.25,
        dividends_mm=total_fcf * 0.10,
        terminal_ebitda_mm=round(sb_terminal, 1),
        terminal_ev_mm=round(sb_exit, 1),
        equity_moic=round(sb_equity / entry_equity, 2) if entry_equity else 0,
        equity_irr=round(((sb_equity / entry_equity) ** (1 / hold_years) - 1), 4) if entry_equity else 0,
    ))

    # Scenario C: Deleverage focus
    sc_terminal = base_terminal_ebitda
    sc_exit = sc_terminal * 12
    sc_equity = sc_exit - (entry_ev - entry_equity) * 0.25
    scenarios.append(CompoundingScenario(
        scenario="Deleverage Focus (70% to debt)",
        total_fcf_deployed_mm=total_fcf, boltons_acquired=1,
        organic_capex_mm=total_fcf * 0.15,
        debt_paydown_mm=total_fcf * 0.70,
        dividends_mm=total_fcf * 0.05,
        terminal_ebitda_mm=round(sc_terminal, 1),
        terminal_ev_mm=round(sc_exit, 1),
        equity_moic=round(sc_equity / entry_equity, 2) if entry_equity else 0,
        equity_irr=round(((sc_equity / entry_equity) ** (1 / hold_years) - 1), 4) if entry_equity else 0,
    ))

    # Scenario D: Dividend recap
    sd_terminal = base_terminal_ebitda
    sd_exit = sd_terminal * 12
    sd_equity = sd_exit - (entry_ev - entry_equity) * 0.40 + total_fcf * 0.45  # big dividend
    scenarios.append(CompoundingScenario(
        scenario="Dividend Recap Heavy (45% to LPs)",
        total_fcf_deployed_mm=total_fcf, boltons_acquired=1,
        organic_capex_mm=total_fcf * 0.10,
        debt_paydown_mm=total_fcf * 0.30,
        dividends_mm=total_fcf * 0.45,
        terminal_ebitda_mm=round(sd_terminal, 1),
        terminal_ev_mm=round(sd_exit, 1),
        equity_moic=round(sd_equity / entry_equity, 2) if entry_equity else 0,
        equity_irr=round(((sd_equity / entry_equity) ** (1 / hold_years) - 1), 4) if entry_equity else 0,
    ))

    return scenarios


def _build_yearly_allocation(cash_flow: List[CashFlowYear]) -> List[YearlyAllocation]:
    rows = []
    for cf in cash_flow:
        fcf = cf.free_cash_flow_mm
        # Balanced allocation
        rows.append(YearlyAllocation(
            year=cf.year,
            available_fcf_mm=round(fcf, 2),
            boltons_mm=round(fcf * 0.35, 2),
            organic_mm=round(fcf * 0.20, 2),
            debt_paydown_mm=round(fcf * 0.25, 2),
            dividend_mm=round(fcf * 0.10, 2),
            retained_cash_mm=round(fcf * 0.10, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_reinvestment(
    entry_ev_mm: float = 300.0,
    entry_ebitda_mm: float = 25.0,
    entry_debt_pct: float = 0.55,
    hold_years: int = 5,
    ebitda_growth_pct: float = 0.06,
    interest_rate: float = 0.085,
) -> ReinvestmentResult:
    corpus = _load_corpus()

    entry_debt = entry_ev_mm * entry_debt_pct
    entry_equity = entry_ev_mm - entry_debt

    cash_flow = _build_cash_flow(entry_ebitda_mm, ebitda_growth_pct, hold_years,
                                    entry_debt, interest_rate)
    total_fcf = cash_flow[-1].cumulative_fcf_mm if cash_flow else 0

    options = _build_allocation_options(total_fcf)
    scenarios = _build_scenarios(entry_ev_mm, entry_equity, entry_ebitda_mm,
                                   hold_years, total_fcf)
    yearly = _build_yearly_allocation(cash_flow)

    # Base case = scenario C (deleverage)
    base_moic = next((s.equity_moic for s in scenarios if "Deleverage" in s.scenario), 2.0)
    # Compounded = scenario B (balanced)
    comp_moic = next((s.equity_moic for s in scenarios if "Balanced" in s.scenario), 2.3)
    lift = comp_moic - base_moic

    recommended = {
        "Bolt-on M&A": 0.35,
        "Organic Capex": 0.20,
        "Debt Paydown": 0.25,
        "Technology": 0.08,
        "Dividend": 0.10,
        "Working Capital": 0.02,
    }

    return ReinvestmentResult(
        entry_ev_mm=round(entry_ev_mm, 1),
        entry_equity_mm=round(entry_equity, 1),
        hold_years=hold_years,
        cumulative_fcf_mm=round(total_fcf, 2),
        base_case_moic=round(base_moic, 2),
        compounded_moic=round(comp_moic, 2),
        moic_lift_from_reinvestment=round(lift, 2),
        cash_flow_years=cash_flow,
        allocation_options=options,
        scenarios=scenarios,
        yearly_allocation=yearly,
        recommended_allocation_mix=recommended,
        corpus_deal_count=len(corpus),
    )
