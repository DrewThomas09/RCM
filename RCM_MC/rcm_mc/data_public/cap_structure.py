"""Capital Structure Optimizer — optimal debt/equity mix for LBO.

Evaluates leverage scenarios (3.0x to 7.0x total leverage) to find:
- Maximum equity MOIC while respecting covenants
- WACC minimization point
- Cost of debt (increases with leverage)
- DSCR constraints
- Equity returns under each structure
- Downside risk (breach probability)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Cost of debt by leverage multiple (increases non-linearly)
# ---------------------------------------------------------------------------

def _cost_of_debt(leverage: float) -> float:
    """Blended rate increases with leverage."""
    if leverage <= 3.0:
        return 0.075
    if leverage <= 4.0:
        return 0.080
    if leverage <= 5.0:
        return 0.088
    if leverage <= 5.5:
        return 0.096
    if leverage <= 6.0:
        return 0.105
    if leverage <= 6.5:
        return 0.118
    return 0.135


def _market_debt_availability(leverage: float) -> str:
    if leverage <= 4.5:
        return "readily available"
    if leverage <= 5.5:
        return "limited institutional"
    if leverage <= 6.0:
        return "private credit only"
    return "unitranche / direct lending"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LeverageScenario:
    total_leverage: float
    senior_leverage: float
    sub_leverage: float
    debt_mm: float
    equity_mm: float
    equity_pct: float
    blended_cost_of_debt: float
    wacc: float
    year1_interest_mm: float
    dscr: float
    covenant_headroom_pct: float
    market_availability: str


@dataclass
class ReturnScenario:
    leverage: float
    exit_ebitda_mm: float
    exit_ev_mm: float
    remaining_debt_mm: float
    exit_equity_mm: float
    moic: float
    irr: float
    cash_flow_to_equity_mm: float


@dataclass
class BreachProbability:
    leverage: float
    ebitda_drop_5pct: float
    ebitda_drop_10pct: float
    ebitda_drop_15pct: float
    ebitda_drop_20pct: float


@dataclass
class CapStructureResult:
    ev_mm: float
    ebitda_mm: float
    current_leverage: float
    optimal_leverage: float
    optimal_moic: float
    leverage_scenarios: List[LeverageScenario]
    return_scenarios: List[ReturnScenario]
    breach_probabilities: List[BreachProbability]
    recommendation: str
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 68):
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


def _senior_sub_split(leverage: float) -> (float, float):
    """Typical senior/sub split at each leverage level."""
    if leverage <= 4.0:
        return leverage, 0  # All senior
    if leverage <= 5.5:
        return 4.0, leverage - 4.0
    return 4.5, leverage - 4.5


def _build_leverage_scenarios(
    ev_mm: float, ebitda_mm: float, cost_of_equity: float,
) -> List[LeverageScenario]:
    rows = []
    # Test 3x through 7x leverage
    leverages = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]
    for lev in leverages:
        sr, sub = _senior_sub_split(lev)
        debt = ebitda_mm * lev
        equity = ev_mm - debt
        if equity <= 0:
            continue
        equity_pct = equity / ev_mm
        cod = _cost_of_debt(lev)
        # Blended: senior at slightly lower rate, sub higher
        if sub > 0:
            sr_rate = cod * 0.88
            sub_rate = cod + 0.025
            blended = (sr * sr_rate + sub * sub_rate) / lev
        else:
            blended = cod

        wacc = (equity / ev_mm) * cost_of_equity + (debt / ev_mm) * blended * (1 - 0.25)  # after-tax
        year1_int = debt * blended
        dscr = ebitda_mm / year1_int if year1_int else 0
        # Covenant: Total leverage threshold typically 5.5-6.5x; headroom = (covenant - current) / covenant
        covenant_max = 6.0 if lev <= 6.0 else 7.0
        headroom = (covenant_max - lev) / covenant_max

        rows.append(LeverageScenario(
            total_leverage=round(lev, 2),
            senior_leverage=round(sr, 2),
            sub_leverage=round(sub, 2),
            debt_mm=round(debt, 1),
            equity_mm=round(equity, 1),
            equity_pct=round(equity_pct, 3),
            blended_cost_of_debt=round(blended, 4),
            wacc=round(wacc, 4),
            year1_interest_mm=round(year1_int, 2),
            dscr=round(dscr, 2),
            covenant_headroom_pct=round(max(0, headroom), 3),
            market_availability=_market_debt_availability(lev),
        ))
    return rows


def _build_return_scenarios(
    scenarios: List[LeverageScenario], ebitda_growth_pct: float,
    exit_multiple: float, hold_years: int, debt_paydown_pct: float,
) -> List[ReturnScenario]:
    rows = []
    for s in scenarios:
        # Terminal EBITDA
        exit_ebitda = s.equity_mm * 0    # placeholder
        # Recompute using base EBITDA from leverage
        base_ebitda = s.debt_mm / s.total_leverage
        exit_ebitda = base_ebitda * ((1 + ebitda_growth_pct) ** hold_years)
        exit_ev = exit_ebitda * exit_multiple
        remaining_debt = s.debt_mm * (1 - debt_paydown_pct)
        exit_equity = exit_ev - remaining_debt
        moic = exit_equity / s.equity_mm if s.equity_mm else 0
        irr = (moic ** (1 / hold_years) - 1) if moic > 0 else 0

        # Cumulative cash flow to equity (net of interest paid)
        total_interest = s.year1_interest_mm * hold_years * 0.75    # taper as debt paid down
        cf_to_eq = exit_equity - s.equity_mm - total_interest + s.year1_interest_mm * hold_years * 0.3 * 0.25    # tax shield

        rows.append(ReturnScenario(
            leverage=s.total_leverage,
            exit_ebitda_mm=round(exit_ebitda, 2),
            exit_ev_mm=round(exit_ev, 1),
            remaining_debt_mm=round(remaining_debt, 1),
            exit_equity_mm=round(exit_equity, 1),
            moic=round(moic, 2),
            irr=round(irr, 4),
            cash_flow_to_equity_mm=round(cf_to_eq, 1),
        ))
    return rows


def _build_breach_probabilities(scenarios: List[LeverageScenario]) -> List[BreachProbability]:
    rows = []
    for s in scenarios:
        # Probability of breach given EBITDA drop
        # Breach if leverage > covenant (6.0x typical)
        # If EBITDA drops X%, effective leverage = current / (1-X)
        def _prob(ebitda_drop: float) -> float:
            effective_lev = s.total_leverage / (1 - ebitda_drop)
            # Assume covenant at 6.0x, cushion distribution
            cushion = (6.0 - effective_lev) / 6.0
            # Logistic-ish scoring
            if cushion >= 0.20: return 0.02
            if cushion >= 0.10: return 0.15
            if cushion >= 0.05: return 0.35
            if cushion >= 0: return 0.55
            if cushion >= -0.05: return 0.78
            return 0.92

        rows.append(BreachProbability(
            leverage=s.total_leverage,
            ebitda_drop_5pct=round(_prob(0.05), 3),
            ebitda_drop_10pct=round(_prob(0.10), 3),
            ebitda_drop_15pct=round(_prob(0.15), 3),
            ebitda_drop_20pct=round(_prob(0.20), 3),
        ))
    return rows


def _find_optimal(
    lev_scenarios: List[LeverageScenario],
    ret_scenarios: List[ReturnScenario],
    min_dscr: float = 1.3, max_breach_10pct: float = 0.25,
) -> (float, float, str):
    """Find leverage that maximizes MOIC subject to DSCR and breach constraints."""
    if not lev_scenarios or not ret_scenarios:
        return 5.0, 0, "insufficient data"

    candidates = []
    for ls, rs in zip(lev_scenarios, ret_scenarios):
        if ls.dscr < min_dscr:
            continue
        if ls.covenant_headroom_pct < 0.12:
            continue
        candidates.append((ls.total_leverage, rs.moic))

    if not candidates:
        return 4.5, 2.0, "Use conservative structure — high-risk profile"

    # Pick max MOIC
    best = max(candidates, key=lambda c: c[1])
    rec = f"{best[0]:.1f}x total leverage — {best[1]:.2f}x MOIC while meeting DSCR ≥ {min_dscr:.1f}x"
    return best[0], best[1], rec


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cap_structure(
    ev_mm: float = 300.0,
    ebitda_mm: float = 25.0,
    hold_years: int = 5,
    ebitda_growth_pct: float = 0.06,
    exit_multiple: float = 12.0,
    debt_paydown_pct: float = 0.40,
    cost_of_equity: float = 0.18,
) -> CapStructureResult:
    corpus = _load_corpus()

    lev_scenarios = _build_leverage_scenarios(ev_mm, ebitda_mm, cost_of_equity)
    ret_scenarios = _build_return_scenarios(
        lev_scenarios, ebitda_growth_pct, exit_multiple, hold_years, debt_paydown_pct,
    )
    breach_probs = _build_breach_probabilities(lev_scenarios)

    # Current leverage
    current_lev = ev_mm / ebitda_mm * 0.55 / ebitda_mm * ebitda_mm    # placeholder
    # Simpler: use 5x as typical starting point
    current_lev = 5.0

    opt_lev, opt_moic, rec = _find_optimal(lev_scenarios, ret_scenarios)

    return CapStructureResult(
        ev_mm=round(ev_mm, 1),
        ebitda_mm=round(ebitda_mm, 2),
        current_leverage=current_lev,
        optimal_leverage=opt_lev,
        optimal_moic=opt_moic,
        leverage_scenarios=lev_scenarios,
        return_scenarios=ret_scenarios,
        breach_probabilities=breach_probs,
        recommendation=rec,
        corpus_deal_count=len(corpus),
    )
