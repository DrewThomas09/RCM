"""LBO entry optimizer — finds the maximum entry multiple that hits a target MOIC.

Given a deal's EBITDA, expected growth, hold period, and target exit multiple,
this module solves backward for the maximum tenable entry EV/EBITDA that still
achieves a target gross MOIC. It also checks the proposed entry against corpus
sector bands.

Validated approach:
  Exit equity = Entry equity × MOIC
  Entry equity = Entry EV × (1 - leverage_pct)
  Exit EV = Exit EBITDA × exit_multiple
  Exit equity = Exit EV - remaining debt

  Solve for entry_multiple given moic target + assumptions.

Public API:
    LBOAssumptions                                    dataclass
    LBOResult                                         dataclass
    solve_entry_multiple(assumptions, target_moic)    -> LBOResult
    sweep_moic_vs_entry(assumptions, entry_range)     -> List[LBOResult]
    entry_vs_corpus(deal, assumptions, deals, sector) -> Dict[str, Any]
    entry_optimizer_table(results)                    -> str
    entry_optimizer_report(result, corpus_check)      -> str
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LBOAssumptions:
    """Inputs for LBO entry optimization."""
    entry_ebitda_mm: float          # EBITDA at entry ($M)
    ebitda_cagr: float              # Expected EBITDA CAGR over hold (e.g. 0.10)
    hold_years: float               # Hold period (years)
    exit_multiple: float            # Expected exit EV/EBITDA
    leverage_pct: float = 0.55      # Debt as % of entry EV (typical: 50-60%)
    debt_interest_rate: float = 0.07  # Interest rate on debt
    debt_amortization_pct: float = 0.03  # Annual principal paydown as % of entry debt
    management_fee_drag: float = 0.02  # Annual fee drag on equity (typical 2%)
    # Optional: target IRR instead of MOIC (used for validation)
    target_irr: Optional[float] = None


@dataclass
class LBOResult:
    """Output of LBO entry optimization."""
    entry_multiple: float           # Solved entry EV/EBITDA
    entry_ev_mm: float              # Entry enterprise value ($M)
    entry_equity_mm: float          # Equity check ($M)
    entry_debt_mm: float            # Debt at entry ($M)
    exit_ebitda_mm: float           # Projected exit EBITDA
    exit_ev_mm: float               # Projected exit EV
    exit_debt_mm: float             # Remaining debt at exit
    exit_equity_mm: float           # Equity at exit
    gross_moic: float               # Gross MOIC
    gross_irr: float                # Gross IRR (annualized)
    net_moic: float                 # Net MOIC (after 20% carry, 2% fee drag)
    debt_paydown_mm: float          # Total debt repaid over hold
    ebitda_at_exit_mm: float        # Same as exit_ebitda_mm (alias for clarity)
    leverage_turn_entry: float      # Debt / Entry EBITDA
    leverage_turn_exit: float       # Exit Debt / Exit EBITDA
    feasible: bool                  # True if debt can be serviced (DSCR > 1.0)
    warnings: List[str] = field(default_factory=list)


def _irr_from_moic(moic: float, years: float) -> float:
    """Simple IRR approximation from MOIC and hold years."""
    if years <= 0 or moic <= 0:
        return 0.0
    return round(moic ** (1.0 / years) - 1.0, 4)


def _net_moic(gross_moic: float, carry: float = 0.20, fee_drag: float = 0.02,
              hold_years: float = 5.0) -> float:
    """Approximate net MOIC after carry and fee drag."""
    gross_gain = gross_moic - 1.0
    carry_payment = max(0.0, gross_gain * carry)
    fee_haircut = (1 - fee_drag) ** hold_years
    return round((gross_moic - carry_payment) * fee_haircut, 3)


def solve_entry_multiple(
    assumptions: LBOAssumptions,
    target_moic: float = 2.5,
    max_multiple: float = 25.0,
    tolerance: float = 0.01,
) -> LBOResult:
    """Binary-search for the maximum entry multiple that achieves target_moic.

    Args:
        assumptions:  LBOAssumptions dataclass
        target_moic:  Gross MOIC to achieve (e.g. 2.5x)
        max_multiple: Upper bound for binary search
        tolerance:    MOIC convergence tolerance

    Returns:
        LBOResult at the solved entry multiple
    """
    a = assumptions
    warnings: List[str] = []

    # Project exit EBITDA
    exit_ebitda = a.entry_ebitda_mm * (1 + a.ebitda_cagr) ** a.hold_years

    def compute_moic(entry_multiple: float) -> float:
        entry_ev = a.entry_ebitda_mm * entry_multiple
        entry_debt = entry_ev * a.leverage_pct
        entry_equity = entry_ev - entry_debt

        # Debt paydown: simple annual amortization
        annual_paydown = entry_debt * a.debt_amortization_pct
        total_paydown = min(annual_paydown * a.hold_years, entry_debt)
        exit_debt = max(0.0, entry_debt - total_paydown)

        exit_ev = exit_ebitda * a.exit_multiple
        exit_equity = max(0.0, exit_ev - exit_debt)

        if entry_equity <= 0:
            return 0.0
        return exit_equity / entry_equity

    # Binary search
    lo, hi = 1.0, max_multiple
    best_multiple = lo

    for _ in range(60):
        mid = (lo + hi) / 2.0
        moic = compute_moic(mid)
        if moic >= target_moic:
            best_multiple = mid
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.001:
            break

    # Compute final result at best_multiple
    entry_ev = a.entry_ebitda_mm * best_multiple
    entry_debt = entry_ev * a.leverage_pct
    entry_equity = entry_ev - entry_debt
    annual_paydown = entry_debt * a.debt_amortization_pct
    total_paydown = min(annual_paydown * a.hold_years, entry_debt)
    exit_debt = max(0.0, entry_debt - total_paydown)
    exit_ev = exit_ebitda * a.exit_multiple
    exit_equity = max(0.0, exit_ev - exit_debt)

    gross_moic = exit_equity / entry_equity if entry_equity > 0 else 0.0
    gross_irr = _irr_from_moic(gross_moic, a.hold_years)
    net = _net_moic(gross_moic, hold_years=a.hold_years)

    leverage_entry = entry_debt / a.entry_ebitda_mm if a.entry_ebitda_mm > 0 else 0
    leverage_exit = exit_debt / exit_ebitda if exit_ebitda > 0 else 0

    # DSCR check: EBITDA / annual interest
    annual_interest = entry_debt * a.debt_interest_rate
    dscr = a.entry_ebitda_mm / annual_interest if annual_interest > 0 else 99.0
    feasible = dscr >= 1.2

    if not feasible:
        warnings.append(f"Entry DSCR {dscr:.1f}x below 1.2x minimum — debt may be unsustainable")
    if leverage_entry > 7.0:
        warnings.append(f"Entry leverage {leverage_entry:.1f}x exceeds 7.0x LBO market norm")
    if best_multiple > 18.0:
        warnings.append(f"Entry multiple {best_multiple:.1f}x is above historical healthcare PE norms")
    if gross_moic < target_moic - tolerance:
        warnings.append(f"Could not achieve {target_moic:.1f}x MOIC — max feasible was {gross_moic:.2f}x")

    return LBOResult(
        entry_multiple=round(best_multiple, 2),
        entry_ev_mm=round(entry_ev, 1),
        entry_equity_mm=round(entry_equity, 1),
        entry_debt_mm=round(entry_debt, 1),
        exit_ebitda_mm=round(exit_ebitda, 1),
        exit_ev_mm=round(exit_ev, 1),
        exit_debt_mm=round(exit_debt, 1),
        exit_equity_mm=round(exit_equity, 1),
        gross_moic=round(gross_moic, 3),
        gross_irr=gross_irr,
        net_moic=net,
        debt_paydown_mm=round(total_paydown, 1),
        ebitda_at_exit_mm=round(exit_ebitda, 1),
        leverage_turn_entry=round(leverage_entry, 2),
        leverage_turn_exit=round(leverage_exit, 2),
        feasible=feasible,
        warnings=warnings,
    )


def sweep_moic_vs_entry(
    assumptions: LBOAssumptions,
    entry_range: Optional[List[float]] = None,
) -> List[LBOResult]:
    """Compute MOIC at each entry multiple in the range.

    Returns list of LBOResult, one per entry multiple tested.
    """
    if entry_range is None:
        entry_range = [round(x * 0.5, 1) for x in range(16, 36)]  # 8x–18x in 0.5x steps

    results = []
    for multiple in entry_range:
        # Use solve_entry_multiple with very high target so it doesn't cap
        res = solve_entry_multiple(assumptions, target_moic=0.001, max_multiple=multiple + 0.001)
        # Recalculate at exactly this multiple (not the solved one)
        a = assumptions
        exit_ebitda = a.entry_ebitda_mm * (1 + a.ebitda_cagr) ** a.hold_years
        entry_ev = a.entry_ebitda_mm * multiple
        entry_debt = entry_ev * a.leverage_pct
        entry_equity = entry_ev - entry_debt
        annual_paydown = entry_debt * a.debt_amortization_pct
        total_paydown = min(annual_paydown * a.hold_years, entry_debt)
        exit_debt = max(0.0, entry_debt - total_paydown)
        exit_ev = exit_ebitda * a.exit_multiple
        exit_equity = max(0.0, exit_ev - exit_debt)
        gross_moic = exit_equity / entry_equity if entry_equity > 0 else 0.0
        gross_irr = _irr_from_moic(gross_moic, a.hold_years)
        net = _net_moic(gross_moic, hold_years=a.hold_years)
        annual_interest = entry_debt * a.debt_interest_rate
        dscr = a.entry_ebitda_mm / annual_interest if annual_interest > 0 else 99.0
        lev_entry = entry_debt / a.entry_ebitda_mm if a.entry_ebitda_mm > 0 else 0
        lev_exit = exit_debt / exit_ebitda if exit_ebitda > 0 else 0

        results.append(LBOResult(
            entry_multiple=multiple,
            entry_ev_mm=round(entry_ev, 1),
            entry_equity_mm=round(entry_equity, 1),
            entry_debt_mm=round(entry_debt, 1),
            exit_ebitda_mm=round(exit_ebitda, 1),
            exit_ev_mm=round(exit_ev, 1),
            exit_debt_mm=round(exit_debt, 1),
            exit_equity_mm=round(exit_equity, 1),
            gross_moic=round(gross_moic, 3),
            gross_irr=gross_irr,
            net_moic=net,
            debt_paydown_mm=round(total_paydown, 1),
            ebitda_at_exit_mm=round(exit_ebitda, 1),
            leverage_turn_entry=round(lev_entry, 2),
            leverage_turn_exit=round(lev_exit, 2),
            feasible=dscr >= 1.2,
        ))

    return results


def entry_vs_corpus(
    deal: Dict[str, Any],
    assumptions: LBOAssumptions,
    corpus_deals: List[Dict[str, Any]],
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """Check whether the proposed entry multiple is inside corpus sector bands.

    Uses subsector_benchmarks to get P25/P75 EV/EBITDA for the sector,
    then flags whether the proposed entry is aggressive, normal, or conservative.
    """
    from .subsector_benchmarks import compute_subsector_benchmarks, _canonical_sector

    sector = sector or deal.get("sector") or "unknown"
    canonical = _canonical_sector(sector)

    # Compute corpus EV/EBITDA by sector
    ev_ebitda_by_sector: Dict[str, List[float]] = {}
    for d in corpus_deals:
        s = _canonical_sector(d.get("sector"))
        ev_e = d.get("ev_ebitda")
        if ev_e is not None:
            ev_ebitda_by_sector.setdefault(s, []).append(float(ev_e))

    sector_multiples = ev_ebitda_by_sector.get(canonical, [])

    result: Dict[str, Any] = {
        "sector": canonical,
        "proposed_entry_multiple": assumptions.entry_ebitda_mm and (
            deal.get("ev_mm", 0) / assumptions.entry_ebitda_mm
            if assumptions.entry_ebitda_mm else None
        ),
        "corpus_peer_count": len(sector_multiples),
    }

    if not sector_multiples:
        result["signal"] = "no_sector_data"
        return result

    sorted_m = sorted(sector_multiples)
    n = len(sorted_m)
    p25 = sorted_m[max(0, int(0.25 * n))]
    p50 = sorted_m[max(0, int(0.50 * n))]
    p75 = sorted_m[max(0, int(0.75 * n))]

    entry_multiple = deal.get("ev_ebitda") or (
        deal.get("ev_mm", 0) / assumptions.entry_ebitda_mm
        if assumptions.entry_ebitda_mm else None
    )

    result.update({
        "corpus_p25_multiple": round(p25, 1),
        "corpus_p50_multiple": round(p50, 1),
        "corpus_p75_multiple": round(p75, 1),
        "proposed_ev_ebitda": round(entry_multiple, 1) if entry_multiple else None,
    })

    if entry_multiple is not None:
        if entry_multiple <= p25:
            result["signal"] = "conservative"
        elif entry_multiple <= p50:
            result["signal"] = "below_median"
        elif entry_multiple <= p75:
            result["signal"] = "above_median"
        else:
            result["signal"] = "aggressive"
    else:
        result["signal"] = "unknown"

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def entry_optimizer_table(results: List[LBOResult]) -> str:
    """Sensitivity table: entry multiple vs. MOIC / IRR / leverage."""
    lines = [
        f"{'Entry EV/EBITDA':>15} {'Entry EV':>10} {'Gross MOIC':>11} {'Gross IRR':>10} "
        f"{'Net MOIC':>9} {'Lev (entry)':>12} {'Feasible':>9}",
        "-" * 82,
    ]
    for r in results:
        feas = "Yes" if r.feasible else "No"
        lines.append(
            f"{r.entry_multiple:>15.1f}x {r.entry_ev_mm:>9,.0f}M {r.gross_moic:>10.2f}x "
            f"{r.gross_irr:>9.1%} {r.net_moic:>8.2f}x {r.leverage_turn_entry:>11.1f}x {feas:>9}"
        )
    return "\n".join(lines) + "\n"


def entry_optimizer_report(result: LBOResult, corpus_check: Optional[Dict[str, Any]] = None) -> str:
    """Full text report for IC memo."""
    lines = [
        "LBO Entry Optimization Report",
        "=" * 50,
        f"  Max entry multiple:   {result.entry_multiple:.1f}x EV/EBITDA",
        f"  Entry EV:             ${result.entry_ev_mm:,.1f}M",
        f"  Entry equity:         ${result.entry_equity_mm:,.1f}M  ({result.leverage_turn_entry:.1f}x levered)",
        f"  Exit EBITDA:          ${result.exit_ebitda_mm:,.1f}M",
        f"  Exit EV:              ${result.exit_ev_mm:,.1f}M",
        f"  Gross MOIC:           {result.gross_moic:.2f}x",
        f"  Gross IRR:            {result.gross_irr:.1%}",
        f"  Net MOIC:             {result.net_moic:.2f}x (after carry/fees)",
        f"  Leverage at entry:    {result.leverage_turn_entry:.1f}x",
        f"  Leverage at exit:     {result.leverage_turn_exit:.1f}x",
        f"  Debt paydown:         ${result.debt_paydown_mm:,.1f}M",
        f"  Feasible (DSCR≥1.2): {'Yes' if result.feasible else 'No'}",
    ]
    if result.warnings:
        lines.append("")
        lines.append("  Warnings:")
        for w in result.warnings:
            lines.append(f"    ! {w}")
    if corpus_check:
        lines.append("")
        lines.append(f"  Corpus check ({corpus_check.get('sector', '?')}):")
        lines.append(f"    Sector P50 entry:  {corpus_check.get('corpus_p50_multiple', '—')}x")
        lines.append(f"    Signal:            {corpus_check.get('signal', '—')}")
    return "\n".join(lines) + "\n"
