"""Dividend Recap Analyzer — interim capital distribution via refinancing.

Models the economics of a dividend recapitalization:
- Current capital structure
- Proposed refinancing capacity
- Dividend to LPs (gross + net of carry)
- Impact on MOIC, post-recap leverage, remaining hold
- DSCR preservation
- Optimal recap timing
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RecapScenario:
    scenario: str
    target_leverage: float
    new_debt_mm: float
    net_dividend_mm: float
    recap_year: int
    post_recap_dscr: float
    covenant_headroom_pct: float
    moic_on_original_equity: float
    pct_of_invested_returned: float
    execution_risk: str


@dataclass
class TimingAnalysis:
    year: int
    ebitda_mm: float
    current_debt_mm: float
    available_capacity_mm: float
    potential_dividend_mm: float
    dscr: float
    post_recap_leverage: float
    recommendation: str


@dataclass
class CarryImpact:
    item: str
    pre_recap_mm: float
    post_recap_mm: float
    delta_mm: float
    notes: str


@dataclass
class MarketContext:
    metric: str
    value: str
    trend: str
    implication: str


@dataclass
class DividendRecapResult:
    ev_mm: float
    entry_ebitda_mm: float
    current_ebitda_mm: float
    entry_leverage: float
    current_leverage: float
    current_equity_value_mm: float
    total_invested_equity_mm: float
    recommended_scenario: str
    max_recap_dividend_mm: float
    scenarios: List[RecapScenario]
    timing_analysis: List[TimingAnalysis]
    carry_impact: List[CarryImpact]
    market_context: List[MarketContext]
    cash_multiple_from_recap: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 70):
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


def _cost_of_debt(leverage: float) -> float:
    if leverage <= 3.0: return 0.075
    if leverage <= 4.0: return 0.082
    if leverage <= 5.0: return 0.090
    if leverage <= 5.5: return 0.098
    if leverage <= 6.0: return 0.108
    if leverage <= 6.5: return 0.122
    return 0.140


def _build_timing_analysis(
    entry_ebitda: float, growth_pct: float, entry_debt: float, hold_years: int,
) -> List[TimingAnalysis]:
    rows = []
    for yr in range(1, hold_years + 1):
        ebitda = entry_ebitda * ((1 + growth_pct) ** yr)
        # Debt pays down at 8% per year
        debt = entry_debt * (1 - 0.08 * yr)
        current_leverage = debt / ebitda if ebitda else 0
        # Recap capacity: re-leverage back to 5.5x
        max_debt = ebitda * 5.5
        available = max(0, max_debt - debt)
        dividend = available * 0.92    # transaction costs
        dscr = ebitda / (max_debt * _cost_of_debt(5.5))

        # Recommendation
        if yr == 1:
            rec = "Too early — let EBITDA grow"
        elif yr == 2 and ebitda / entry_ebitda < 1.15:
            rec = "Wait — insufficient EBITDA growth"
        elif yr <= 3 and ebitda / entry_ebitda >= 1.15:
            rec = "Consider — growth + paydown enable capacity"
        elif 3 <= yr <= 4:
            rec = "Optimal window — max cash yield"
        elif yr >= 5:
            rec = "Late — exit preferred over recap"
        else:
            rec = "Evaluate"

        rows.append(TimingAnalysis(
            year=yr,
            ebitda_mm=round(ebitda, 2),
            current_debt_mm=round(debt, 1),
            available_capacity_mm=round(available, 1),
            potential_dividend_mm=round(dividend, 1),
            dscr=round(dscr, 2),
            post_recap_leverage=5.5,
            recommendation=rec,
        ))
    return rows


def _build_scenarios(
    current_ebitda: float, current_debt: float, entry_equity: float, current_year: int,
) -> List[RecapScenario]:
    rows = []
    scenarios_def = [
        ("Conservative — 5.0x target", 5.0, "low"),
        ("Market — 5.5x target", 5.5, "medium"),
        ("Aggressive — 6.0x target", 6.0, "medium"),
        ("Opportunistic — 6.5x target", 6.5, "high"),
    ]
    for label, target_lev, risk in scenarios_def:
        max_debt = current_ebitda * target_lev
        new_debt = max(0, max_debt - current_debt)
        # Net dividend = new debt - refinance fees (3%)
        net_div = new_debt * 0.94
        cod = _cost_of_debt(target_lev)
        int_expense = max_debt * cod
        amort = max_debt * 0.01
        dscr = current_ebitda / (int_expense + amort) if (int_expense + amort) else 0

        covenant_max = 6.0 if target_lev <= 6.0 else 7.0
        headroom = (covenant_max - target_lev) / covenant_max

        # MOIC implications
        moic = (net_div + entry_equity * 0.5) / entry_equity if entry_equity else 0    # assume 50% equity still out
        pct_returned = net_div / entry_equity if entry_equity else 0

        rows.append(RecapScenario(
            scenario=label,
            target_leverage=target_lev,
            new_debt_mm=round(new_debt, 1),
            net_dividend_mm=round(net_div, 1),
            recap_year=current_year,
            post_recap_dscr=round(dscr, 2),
            covenant_headroom_pct=round(headroom, 3),
            moic_on_original_equity=round(moic, 2),
            pct_of_invested_returned=round(pct_returned, 3),
            execution_risk=risk,
        ))
    return rows


def _build_carry_impact(
    recap_dividend: float, entry_equity: float, carry_rate: float = 0.20,
) -> List[CarryImpact]:
    # Simplified pre/post carry math
    pre_recap_gp = entry_equity * 2.5 * carry_rate - entry_equity * carry_rate    # gain × 20%
    pre_recap_lp = entry_equity * 2.5 - pre_recap_gp

    # Post recap: dividend triggers interim carry tier; remaining equity still owed
    post_recap_lp_at_recap = recap_dividend * 0.95    # most goes to LPs
    post_recap_gp_at_recap = recap_dividend * 0.05
    # Final distribution (exit) of remaining equity value
    remaining_equity = max(0, entry_equity * 2.5 - recap_dividend)
    post_recap_gp_final = max(0, remaining_equity * carry_rate)
    post_recap_lp_final = remaining_equity - post_recap_gp_final

    return [
        CarryImpact(
            item="LP Distributions",
            pre_recap_mm=round(pre_recap_lp, 1),
            post_recap_mm=round(post_recap_lp_at_recap + post_recap_lp_final, 1),
            delta_mm=round(post_recap_lp_at_recap + post_recap_lp_final - pre_recap_lp, 1),
            notes="LPs receive dividend at recap; rest at exit",
        ),
        CarryImpact(
            item="GP Carry",
            pre_recap_mm=round(pre_recap_gp, 1),
            post_recap_mm=round(post_recap_gp_at_recap + post_recap_gp_final, 1),
            delta_mm=round(post_recap_gp_at_recap + post_recap_gp_final - pre_recap_gp, 1),
            notes="Marginal carry change; time-value of GP take",
        ),
        CarryImpact(
            item="Net IRR to LPs",
            pre_recap_mm=0.224,
            post_recap_mm=0.268,
            delta_mm=0.044,
            notes="Earlier cash = higher IRR even if MOIC flat",
        ),
        CarryImpact(
            item="MOIC to LPs",
            pre_recap_mm=2.15,
            post_recap_mm=2.12,
            delta_mm=-0.03,
            notes="Slight MOIC drag from interim carry crystallization",
        ),
    ]


def _build_market_context() -> List[MarketContext]:
    return [
        MarketContext("Leveraged Loan Index Yield", "9.8%", "rising", "Recap pricing tightening; act soon"),
        MarketContext("B-Rated Spread (vs LIBOR)", "+410 bps", "stable", "Premium for healthcare services deals"),
        MarketContext("Unitranche Availability", "Selective", "tightening", "Best for >$500M tranches"),
        MarketContext("PIK Flex / Holdco Notes", "Available", "selective", "For stretch tranches"),
        MarketContext("Second-Lien Market Reopens", "Partial", "improving", "For 5.5-6.0x deals"),
        MarketContext("Public HY / Loan Index Correl.", "+0.72", "elevated", "Market volatility risk"),
        MarketContext("Recent Healthcare Recap Comps",
                      "8 deals in last 12 mo", "active",
                      "Avg dividend 65-80% of original equity"),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_dividend_recap(
    ev_mm: float = 300.0,
    entry_ebitda_mm: float = 25.0,
    entry_leverage: float = 5.0,
    current_year: int = 3,
    ebitda_growth_pct: float = 0.07,
    hold_years: int = 5,
) -> DividendRecapResult:
    corpus = _load_corpus()

    entry_debt = entry_ebitda_mm * entry_leverage
    entry_equity = ev_mm - entry_debt
    # Current state
    current_ebitda = entry_ebitda_mm * ((1 + ebitda_growth_pct) ** current_year)
    current_debt = entry_debt * (1 - 0.08 * current_year)
    current_leverage = current_debt / current_ebitda if current_ebitda else 0

    # Current equity value (implied)
    current_ev = current_ebitda * (ev_mm / entry_ebitda_mm * 1.05)
    current_equity = current_ev - current_debt

    scenarios = _build_scenarios(current_ebitda, current_debt, entry_equity, current_year)
    timing = _build_timing_analysis(entry_ebitda_mm, ebitda_growth_pct, entry_debt, hold_years)

    # Recommended: market scenario (5.5x)
    recommended = scenarios[1] if len(scenarios) > 1 else scenarios[0]
    max_recap = recommended.net_dividend_mm

    carry_impact = _build_carry_impact(max_recap, entry_equity)
    market = _build_market_context()

    cash_mult = max_recap / entry_equity if entry_equity else 0

    return DividendRecapResult(
        ev_mm=round(ev_mm, 1),
        entry_ebitda_mm=round(entry_ebitda_mm, 2),
        current_ebitda_mm=round(current_ebitda, 2),
        entry_leverage=round(entry_leverage, 2),
        current_leverage=round(current_leverage, 2),
        current_equity_value_mm=round(current_equity, 1),
        total_invested_equity_mm=round(entry_equity, 1),
        recommended_scenario=recommended.scenario,
        max_recap_dividend_mm=round(max_recap, 1),
        scenarios=scenarios,
        timing_analysis=timing,
        carry_impact=carry_impact,
        market_context=market,
        cash_multiple_from_recap=round(cash_mult, 2),
        corpus_deal_count=len(corpus),
    )
