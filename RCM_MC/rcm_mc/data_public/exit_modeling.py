"""Exit scenario modeling for hospital M&A deals.

Models four exit routes and decomposes returns into value-creation levers:
    1. Strategic sale         – exit to strategic buyer at EBITDA multiple
    2. Secondary buyout (SBO) – exit to another PE firm
    3. IPO                    – partial exit with equity overhang discount
    4. Dividend recapitalization – cash return pre-exit, reduces equity need

For each exit, computes:
    - Exit Enterprise Value
    - Net Equity Proceeds (EV - remaining debt)
    - MOIC and IRR
    - Attribution bridge: EBITDA growth / multiple expansion / debt paydown / dividends

Public API:
    ExitRoute        enum-like constants
    ExitAssumptions  dataclass
    ExitResult       dataclass
    ValueBridge      dataclass
    model_exit(deal, entry_debt_mm, exit_route, assumptions)  -> ExitResult
    model_all_exits(deal, entry_debt_mm, assumptions)          -> Dict[str, ExitResult]
    build_value_bridge(deal, exit_result, entry_debt_mm)       -> ValueBridge
    exit_table(results)                                        -> str (ASCII)
    irr_sensitivity(deal, entry_debt_mm, exit_multiples, holds) -> str (ASCII table)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exit routes
# ---------------------------------------------------------------------------

class ExitRoute:
    STRATEGIC     = "strategic_sale"
    SBO           = "secondary_buyout"
    IPO           = "ipo"
    DIVIDEND_RECAP = "dividend_recap"

    ALL = [STRATEGIC, SBO, IPO, DIVIDEND_RECAP]


# ---------------------------------------------------------------------------
# Defaults by exit route
# ---------------------------------------------------------------------------

_EXIT_MULTIPLE_HAIRCUTS: Dict[str, float] = {
    ExitRoute.STRATEGIC:     0.00,   # full strategic premium
    ExitRoute.SBO:          -0.50,   # SBO buyer typically pays 0.5x less
    ExitRoute.IPO:          -1.00,   # IPO at ~1x discount to strategic; partial exit
    ExitRoute.DIVIDEND_RECAP: 0.00,  # same EBITDA multiple; returns structured differently
}

_IPO_FLOAT_PCT: float = 0.35        # 35% of equity sold in IPO
_RECAP_LEVERAGE_ADD: float = 1.50   # additional turns of leverage in div recap


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExitAssumptions:
    exit_ebitda_growth_annual: float = 0.05     # EBITDA CAGR through hold
    exit_multiple: float = 9.0                  # base EV/EBITDA at exit
    hold_years: float = 5.0
    interest_rate: float = 0.075
    required_amort_pct: float = 0.010           # % of original debt / yr
    management_fee_pct: float = 0.015           # annual mgmt fee on equity ($)
    transaction_costs_pct: float = 0.020        # sell-side fees at exit
    ipo_float_pct: float = _IPO_FLOAT_PCT
    recap_leverage_add: float = _RECAP_LEVERAGE_ADD

    def as_dict(self) -> Dict[str, Any]:
        return {
            "exit_ebitda_growth_annual": self.exit_ebitda_growth_annual,
            "exit_multiple": self.exit_multiple,
            "hold_years": self.hold_years,
            "interest_rate": self.interest_rate,
            "required_amort_pct": self.required_amort_pct,
            "management_fee_pct": self.management_fee_pct,
            "transaction_costs_pct": self.transaction_costs_pct,
            "ipo_float_pct": self.ipo_float_pct,
            "recap_leverage_add": self.recap_leverage_add,
        }


@dataclass
class ExitResult:
    deal_name: str
    exit_route: str
    entry_ebitda_mm: float
    exit_ebitda_mm: float
    entry_ev_mm: float
    exit_ev_mm: float
    entry_debt_mm: float
    exit_debt_mm: float
    entry_equity_mm: float
    gross_equity_proceeds_mm: float     # before fees and mgmt fees
    net_equity_proceeds_mm: float       # after all costs
    interim_cash_distributions_mm: float  # dividend recaps, etc.
    total_return_mm: float              # net_equity + interim_cash
    moic: float
    irr: float
    assumptions: ExitAssumptions
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "exit_route": self.exit_route,
            "entry_ebitda_mm": round(self.entry_ebitda_mm, 2),
            "exit_ebitda_mm": round(self.exit_ebitda_mm, 2),
            "entry_ev_mm": round(self.entry_ev_mm, 2),
            "exit_ev_mm": round(self.exit_ev_mm, 2),
            "entry_debt_mm": round(self.entry_debt_mm, 2),
            "exit_debt_mm": round(self.exit_debt_mm, 2),
            "entry_equity_mm": round(self.entry_equity_mm, 2),
            "gross_equity_proceeds_mm": round(self.gross_equity_proceeds_mm, 2),
            "net_equity_proceeds_mm": round(self.net_equity_proceeds_mm, 2),
            "interim_cash_distributions_mm": round(self.interim_cash_distributions_mm, 2),
            "total_return_mm": round(self.total_return_mm, 2),
            "moic": round(self.moic, 3),
            "irr": round(self.irr, 4),
            "notes": self.notes,
            "assumptions": self.assumptions.as_dict(),
        }


@dataclass
class ValueBridge:
    """Attribution of MOIC into constituent value-creation levers."""
    deal_name: str
    exit_route: str
    entry_ev_mm: float
    exit_ev_mm: float
    moic: float
    # Attribution ($M)
    ebitda_growth_contribution_mm: float    # EV uplift from EBITDA growth
    multiple_expansion_mm: float            # EV uplift from multiple re-rating
    debt_paydown_mm: float                  # equity uplift from amortisation
    dividend_recap_mm: float                # direct cash returned pre-exit
    fees_drag_mm: float                     # negative: mgmt fees + tx costs

    def as_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "exit_route": self.exit_route,
            "entry_ev_mm": round(self.entry_ev_mm, 2),
            "exit_ev_mm": round(self.exit_ev_mm, 2),
            "moic": round(self.moic, 3),
            "attribution": {
                "ebitda_growth_contribution_mm": round(self.ebitda_growth_contribution_mm, 2),
                "multiple_expansion_mm": round(self.multiple_expansion_mm, 2),
                "debt_paydown_mm": round(self.debt_paydown_mm, 2),
                "dividend_recap_mm": round(self.dividend_recap_mm, 2),
                "fees_drag_mm": round(self.fees_drag_mm, 2),
            },
        }


# ---------------------------------------------------------------------------
# IRR solver (Newton-Raphson)
# ---------------------------------------------------------------------------

def _solve_irr(
    equity_invested: float,
    total_return: float,
    hold_years: float,
    interim_cash: float = 0.0,
) -> float:
    """Solve for IRR given entry equity, total exit proceeds, and hold years.

    Simplified: assumes interim_cash received at hold_years / 2 midpoint.
    Uses Newton-Raphson iteration.
    """
    if equity_invested <= 0 or hold_years <= 0:
        return 0.0

    mid = hold_years / 2.0

    def npv(r: float) -> float:
        if r <= -1:
            return float("inf")
        return (
            -equity_invested
            + interim_cash / (1 + r) ** mid
            + total_return / (1 + r) ** hold_years
        )

    def dnpv(r: float) -> float:
        if r <= -1:
            return 0.0
        return (
            -mid * interim_cash / (1 + r) ** (mid + 1)
            - hold_years * total_return / (1 + r) ** (hold_years + 1)
        )

    r = 0.15  # initial guess
    for _ in range(50):
        f = npv(r)
        df = dnpv(r)
        if abs(df) < 1e-12:
            break
        r_new = r - f / df
        r_new = max(-0.999, r_new)
        if abs(r_new - r) < 1e-8:
            r = r_new
            break
        r = r_new

    return r


# ---------------------------------------------------------------------------
# Core modelling
# ---------------------------------------------------------------------------

def _exit_ebitda(entry_ebitda: float, growth: float, years: float) -> float:
    return entry_ebitda * (1 + growth) ** years


def _exit_debt(entry_debt: float, amort_pct: float, years: float) -> float:
    paid = entry_debt * amort_pct * years
    return max(0.0, entry_debt - paid)


def model_exit(
    deal: Dict[str, Any],
    entry_debt_mm: Optional[float] = None,
    exit_route: str = ExitRoute.STRATEGIC,
    assumptions: Optional[ExitAssumptions] = None,
) -> ExitResult:
    """Model a single exit route.

    Args:
        deal:           deal dict (needs ev_mm, ebitda_at_entry_mm)
        entry_debt_mm:  override entry debt ($M); defaults to 60% of EV
        exit_route:     one of ExitRoute constants
        assumptions:    ExitAssumptions (or None for defaults)
    """
    a = assumptions or ExitAssumptions()

    ev = float(deal.get("ev_mm") or 0)
    ebitda = float(deal.get("ebitda_at_entry_mm") or 0)
    hold = a.hold_years

    if ev <= 0 or ebitda <= 0:
        raise ValueError("ev_mm and ebitda_at_entry_mm must be positive")

    debt = entry_debt_mm if entry_debt_mm is not None else ev * 0.60
    equity = ev - debt

    exit_ebitda = _exit_ebitda(ebitda, a.exit_ebitda_growth_annual, hold)
    exit_debt = _exit_debt(debt, a.required_amort_pct, hold)

    # Mgmt fees (annual, applied to entry equity)
    mgmt_fees_total = equity * a.management_fee_pct * hold

    # Exit-route specific adjustments
    interim_cash = 0.0
    notes: List[str] = []

    if exit_route == ExitRoute.STRATEGIC:
        exit_ev = exit_ebitda * a.exit_multiple
        gross_equity = exit_ev - exit_debt

    elif exit_route == ExitRoute.SBO:
        sbo_multiple = a.exit_multiple + _EXIT_MULTIPLE_HAIRCUTS[ExitRoute.SBO]
        exit_ev = exit_ebitda * sbo_multiple
        gross_equity = exit_ev - exit_debt
        notes.append(f"SBO: exit multiple discounted to {sbo_multiple:.1f}x (vs {a.exit_multiple:.1f}x strategic)")

    elif exit_route == ExitRoute.IPO:
        ipo_multiple = a.exit_multiple + _EXIT_MULTIPLE_HAIRCUTS[ExitRoute.IPO]
        exit_ev = exit_ebitda * ipo_multiple
        # Only float_pct of equity sold in IPO; remainder is residual stake
        float_proceeds = (exit_ev - exit_debt) * a.ipo_float_pct
        # Residual stake at end-of-hold assumed to be valued at full exit price
        residual = (exit_ev - exit_debt) * (1 - a.ipo_float_pct)
        gross_equity = float_proceeds + residual
        notes.append(
            f"IPO: {a.ipo_float_pct:.0%} floated at {ipo_multiple:.1f}x; "
            f"residual {1-a.ipo_float_pct:.0%} stake held"
        )

    elif exit_route == ExitRoute.DIVIDEND_RECAP:
        # Mid-hold recap: add leverage, distribute cash, exit at strategic multiple
        recap_debt_add = ebitda * a.recap_leverage_add
        interim_cash = recap_debt_add  # cash returned to PE mid-hold
        exit_debt_w_recap = min(exit_debt + recap_debt_add, exit_ebitda * 6.5)  # covenant cap
        exit_ev = exit_ebitda * a.exit_multiple
        gross_equity = exit_ev - exit_debt_w_recap
        notes.append(
            f"Div recap: +{recap_debt_add:.0f}M drawn mid-hold ({a.recap_leverage_add:.1f}x EBITDA); "
            f"exit debt {exit_debt_w_recap:.0f}M"
        )
        exit_debt = exit_debt_w_recap

    else:
        raise ValueError(f"Unknown exit_route: {exit_route}")

    # Transaction costs on exit
    tx_costs = max(0.0, gross_equity) * a.transaction_costs_pct
    net_equity = gross_equity - tx_costs - mgmt_fees_total
    total_return = net_equity + interim_cash

    moic = total_return / equity if equity > 0 else 0.0
    irr = _solve_irr(equity, net_equity, hold, interim_cash)

    return ExitResult(
        deal_name=str(deal.get("deal_name", "")),
        exit_route=exit_route,
        entry_ebitda_mm=ebitda,
        exit_ebitda_mm=exit_ebitda,
        entry_ev_mm=ev,
        exit_ev_mm=exit_ev,
        entry_debt_mm=debt,
        exit_debt_mm=exit_debt,
        entry_equity_mm=equity,
        gross_equity_proceeds_mm=max(0.0, gross_equity),
        net_equity_proceeds_mm=max(0.0, net_equity),
        interim_cash_distributions_mm=interim_cash,
        total_return_mm=max(0.0, total_return),
        moic=max(0.0, moic),
        irr=irr,
        assumptions=a,
        notes=notes,
    )


def model_all_exits(
    deal: Dict[str, Any],
    entry_debt_mm: Optional[float] = None,
    assumptions: Optional[ExitAssumptions] = None,
) -> Dict[str, ExitResult]:
    """Run all four exit routes and return a dict keyed by route name."""
    return {
        route: model_exit(deal, entry_debt_mm, route, assumptions)
        for route in ExitRoute.ALL
    }


def build_value_bridge(
    deal: Dict[str, Any],
    exit_result: ExitResult,
    entry_debt_mm: Optional[float] = None,
) -> ValueBridge:
    """Decompose MOIC into four value-creation levers.

    Attribution method (waterfall):
        1. EBITDA growth: entry_multiple × (exit_ebitda - entry_ebitda)
        2. Multiple expansion: (exit_multiple - entry_multiple) × exit_ebitda
        3. Debt paydown: entry_debt - exit_debt
        4. Dividend recap: interim_cash
        5. Fees drag: -(mgmt_fees + tx_costs)
    """
    ev = float(deal.get("ev_mm") or exit_result.entry_ev_mm)
    ebitda = float(deal.get("ebitda_at_entry_mm") or exit_result.entry_ebitda_mm)
    debt = entry_debt_mm if entry_debt_mm is not None else ev * 0.60
    equity = ev - debt

    entry_multiple = ev / ebitda if ebitda > 0 else 0.0
    exit_multiple = exit_result.exit_ev_mm / exit_result.exit_ebitda_mm if exit_result.exit_ebitda_mm > 0 else 0.0

    ebitda_growth_value = entry_multiple * (exit_result.exit_ebitda_mm - ebitda)
    multiple_expansion_value = (exit_multiple - entry_multiple) * exit_result.exit_ebitda_mm
    debt_paydown_value = exit_result.entry_debt_mm - exit_result.exit_debt_mm
    recap_value = exit_result.interim_cash_distributions_mm

    a = exit_result.assumptions
    fees_drag = -(equity * a.management_fee_pct * a.hold_years
                  + max(0.0, exit_result.gross_equity_proceeds_mm) * a.transaction_costs_pct)

    return ValueBridge(
        deal_name=exit_result.deal_name,
        exit_route=exit_result.exit_route,
        entry_ev_mm=ev,
        exit_ev_mm=exit_result.exit_ev_mm,
        moic=exit_result.moic,
        ebitda_growth_contribution_mm=ebitda_growth_value,
        multiple_expansion_mm=multiple_expansion_value,
        debt_paydown_mm=debt_paydown_value,
        dividend_recap_mm=recap_value,
        fees_drag_mm=fees_drag,
    )


def exit_table(results: Dict[str, ExitResult]) -> str:
    """ASCII table comparing exit routes."""
    lines = [
        "Exit Scenario Comparison",
        "-" * 95,
        f"{'Route':<22} {'Exit EV':>9} {'Equity Proc.':>13} {'Interim Cash':>13} "
        f"{'MOIC':>6} {'IRR':>7}",
        "-" * 95,
    ]
    for route, r in results.items():
        lines.append(
            f"{route:<22} ${r.exit_ev_mm:>7,.0f}M  ${r.net_equity_proceeds_mm:>10,.0f}M  "
            f"${r.interim_cash_distributions_mm:>10,.0f}M  "
            f"{r.moic:>5.2f}x  {r.irr:>6.1%}"
        )
        for note in r.notes:
            lines.append(f"  ↳ {note}")
    return "\n".join(lines)


def irr_sensitivity(
    deal: Dict[str, Any],
    entry_debt_mm: Optional[float] = None,
    exit_multiples: Optional[List[float]] = None,
    hold_years_list: Optional[List[float]] = None,
    exit_route: str = ExitRoute.STRATEGIC,
) -> str:
    """IRR sensitivity table: exit multiple × hold years."""
    if exit_multiples is None:
        exit_multiples = [6.0, 7.0, 8.0, 9.0, 10.0, 12.0]
    if hold_years_list is None:
        hold_years_list = [3.0, 4.0, 5.0, 6.0, 7.0]

    # Header
    col_hdrs = "  ".join(f"{h:.0f}yr" for h in hold_years_list)
    lines = [
        f"IRR Sensitivity — {deal.get('deal_name', 'Deal')} ({exit_route})",
        f"{'Exit Mult':<12}  {col_hdrs}",
        "-" * (12 + len(hold_years_list) * 8),
    ]

    for mult in exit_multiples:
        row = f"{mult:.1f}x EV/EBITDA  "
        for hold in hold_years_list:
            a = ExitAssumptions(exit_multiple=mult, hold_years=hold)
            try:
                result = model_exit(deal, entry_debt_mm, exit_route, a)
                row += f"{result.irr:>6.1%}  "
            except Exception:
                row += f"   —    "
        lines.append(row)

    return "\n".join(lines)
