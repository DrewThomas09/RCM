"""Simplified LBO underwriting model with corpus-calibrated guardrails.

Projects forward IRR and MOIC from entry assumptions, then compares
against corpus P25/P50/P75 benchmarks to flag outlier return expectations.

This is NOT a substitute for a full LBO model — it is a quick-screen
tool for reasonableness checking during initial diligence.

Public API:
    UnderwritingAssumptions            dataclass
    UnderwritingResult                 dataclass
    underwrite_deal(assumptions)       -> UnderwritingResult
    sensitivity_table(assumptions)     -> list[dict]  (exit multiple × hold year grid)
    benchmark_compare(result, benchmarks) -> dict
    underwriting_report(result, benchmarks) -> str
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class UnderwritingAssumptions:
    """Entry assumptions for a deal underwriting."""

    # Entry
    entry_ev_mm: float              # EV at entry ($M)
    entry_ebitda_mm: float          # EBITDA at entry ($M)
    equity_contribution_pct: float  # Equity as % of EV (e.g. 0.40)

    # Growth
    ebitda_cagr: float              # Projected EBITDA CAGR (e.g. 0.12 = 12%)
    hold_years: float               # Investment horizon in years (e.g. 5.0)

    # Exit
    exit_multiple: float            # Exit EV/EBITDA multiple (e.g. 10.0)

    # Debt
    entry_leverage_x: float = 5.0  # Entry leverage (debt / EBITDA)
    debt_amortization_pct: float = 0.03  # Annual % of debt repaid (3%)
    interest_rate: float = 0.075   # Debt interest rate

    # Fees
    transaction_fee_pct: float = 0.02   # % of EV
    management_fee_annual_mm: float = 2.0  # Annual management fee $M

    deal_name: str = ""


@dataclass
class UnderwritingResult:
    """Output of the underwriting model."""

    assumptions: UnderwritingAssumptions

    # Equity math
    entry_equity_mm: float = 0.0
    entry_debt_mm: float = 0.0
    entry_ev_ebitda: float = 0.0

    # Exit projections
    exit_ebitda_mm: float = 0.0
    exit_ev_mm: float = 0.0
    exit_debt_mm: float = 0.0
    exit_equity_mm: float = 0.0

    # Returns
    gross_moic: float = 0.0
    gross_irr: float = 0.0
    net_moic: float = 0.0
    net_irr: float = 0.0

    # Fees/costs
    total_fees_mm: float = 0.0
    annual_interest_mm: float = 0.0

    # Checks
    warnings: List[str] = field(default_factory=list)


def underwrite_deal(assumptions: UnderwritingAssumptions) -> UnderwritingResult:
    """Run the simplified LBO underwriting model.

    Returns UnderwritingResult with gross and net IRR/MOIC projections.
    All dollar figures in $M.
    """
    a = assumptions
    result = UnderwritingResult(assumptions=a)
    warnings: List[str] = []

    # Entry
    entry_debt = a.entry_ebitda_mm * a.entry_leverage_x
    entry_equity = a.entry_ev_mm * a.equity_contribution_pct
    txn_fee = a.entry_ev_mm * a.transaction_fee_pct

    result.entry_ev_ebitda = a.entry_ev_mm / a.entry_ebitda_mm if a.entry_ebitda_mm else 0.0
    result.entry_equity_mm = entry_equity
    result.entry_debt_mm = entry_debt

    # Check: equity + debt + fees should roughly equal EV
    implied_ev = entry_equity + entry_debt
    if abs(implied_ev - a.entry_ev_mm) / a.entry_ev_mm > 0.20:
        warnings.append(
            f"Equity ({entry_equity:.0f}) + debt ({entry_debt:.0f}) = {implied_ev:.0f} "
            f"differs from stated EV {a.entry_ev_mm:.0f} by >{20}% — check assumptions"
        )

    if a.entry_ebitda_mm <= 0:
        warnings.append("Negative EBITDA at entry — model not applicable; use revenue-based approach")
        result.warnings = warnings
        return result

    # Exit projections
    exit_ebitda = a.entry_ebitda_mm * ((1 + a.ebitda_cagr) ** a.hold_years)
    exit_ev = exit_ebitda * a.exit_multiple

    # Debt paydown (simple linear amortization)
    annual_amort = entry_debt * a.debt_amortization_pct
    exit_debt = max(0.0, entry_debt - annual_amort * a.hold_years)

    exit_equity = exit_ev - exit_debt
    if exit_equity < 0:
        warnings.append("Exit equity negative — deal is underwater at these assumptions")
        exit_equity = 0.0

    result.exit_ebitda_mm = round(exit_ebitda, 2)
    result.exit_ev_mm = round(exit_ev, 2)
    result.exit_debt_mm = round(exit_debt, 2)
    result.exit_equity_mm = round(exit_equity, 2)

    # Gross returns (before management fees)
    cost_basis = entry_equity + txn_fee
    result.total_fees_mm = txn_fee
    result.annual_interest_mm = round(entry_debt * a.interest_rate, 2)

    if cost_basis > 0:
        result.gross_moic = round(exit_equity / cost_basis, 3)
        if result.gross_moic > 0 and a.hold_years > 0:
            result.gross_irr = round(result.gross_moic ** (1 / a.hold_years) - 1, 4)

    # Net returns (after annual management fees)
    total_mgmt_fees = a.management_fee_annual_mm * a.hold_years
    net_exit_equity = max(0.0, exit_equity - total_mgmt_fees)
    result.total_fees_mm += total_mgmt_fees

    if cost_basis > 0:
        result.net_moic = round(net_exit_equity / cost_basis, 3)
        if result.net_moic > 0 and a.hold_years > 0:
            result.net_irr = round(result.net_moic ** (1 / a.hold_years) - 1, 4)

    # Sanity checks
    if result.gross_irr > 0.60:
        warnings.append(f"Gross IRR {result.gross_irr:.1%} > 60% — verify exit multiple or CAGR assumptions")
    if result.gross_moic > 10.0:
        warnings.append(f"Gross MOIC {result.gross_moic:.1f}x > 10x — very rare; stress-test")
    if a.exit_multiple > a.entry_ev_mm / a.entry_ebitda_mm + 3:
        warnings.append(
            f"Exit multiple {a.exit_multiple:.1f}x > entry {result.entry_ev_ebitda:.1f}x + 3 "
            f"— multiple expansion assumption is aggressive"
        )

    result.warnings = warnings
    return result


# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------

def sensitivity_table(
    assumptions: UnderwritingAssumptions,
    exit_multiples: Optional[List[float]] = None,
    hold_years_list: Optional[List[float]] = None,
    metric: str = "net_irr",
) -> List[Dict[str, Any]]:
    """Grid of returns across exit-multiple × hold-year combinations.

    Returns list of dicts: {exit_multiple, hold_years, <metric>}.
    metric: 'net_irr' | 'gross_irr' | 'net_moic' | 'gross_moic'
    """
    em = exit_multiples or [
        assumptions.exit_multiple - 2,
        assumptions.exit_multiple - 1,
        assumptions.exit_multiple,
        assumptions.exit_multiple + 1,
        assumptions.exit_multiple + 2,
    ]
    holds = hold_years_list or [
        max(1.0, assumptions.hold_years - 2),
        max(1.0, assumptions.hold_years - 1),
        assumptions.hold_years,
        assumptions.hold_years + 1,
        assumptions.hold_years + 2,
    ]

    rows = []
    for hy in holds:
        for mul in em:
            if mul <= 0:
                continue
            a = UnderwritingAssumptions(
                entry_ev_mm=assumptions.entry_ev_mm,
                entry_ebitda_mm=assumptions.entry_ebitda_mm,
                equity_contribution_pct=assumptions.equity_contribution_pct,
                ebitda_cagr=assumptions.ebitda_cagr,
                hold_years=hy,
                exit_multiple=mul,
                entry_leverage_x=assumptions.entry_leverage_x,
                debt_amortization_pct=assumptions.debt_amortization_pct,
                interest_rate=assumptions.interest_rate,
                transaction_fee_pct=assumptions.transaction_fee_pct,
                management_fee_annual_mm=assumptions.management_fee_annual_mm,
            )
            res = underwrite_deal(a)
            rows.append({
                "exit_multiple": mul,
                "hold_years": hy,
                metric: getattr(res, metric, None),
            })
    return rows


# ---------------------------------------------------------------------------
# Benchmark comparison
# ---------------------------------------------------------------------------

def benchmark_compare(
    result: UnderwritingResult,
    benchmarks: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare underwriting result against corpus benchmarks.

    benchmarks: dict with moic_p25/p50/p75 keys (from base_rates or portfolio_analytics).
    Returns assessment dict with positioning and recommendation.
    """
    moic = result.net_moic
    irr = result.net_irr

    out: Dict[str, Any] = {
        "net_moic": moic,
        "net_irr": irr,
        "moic_p25": benchmarks.get("moic_p25"),
        "moic_p50": benchmarks.get("moic_p50"),
        "moic_p75": benchmarks.get("moic_p75"),
    }

    if moic and benchmarks.get("moic_p50"):
        p25 = benchmarks.get("moic_p25", 0)
        p50 = benchmarks.get("moic_p50", 0)
        p75 = benchmarks.get("moic_p75", 0)
        if moic >= p75:
            out["corpus_positioning"] = "top_quartile"
            out["recommendation"] = "Return expectations in top quartile vs corpus — validate assumptions"
        elif moic >= p50:
            out["corpus_positioning"] = "above_median"
            out["recommendation"] = "Above-median expected returns — reasonable hurdle rate"
        elif moic >= p25:
            out["corpus_positioning"] = "below_median"
            out["recommendation"] = "Below-median returns — stress exit multiple or improve EBITDA assumptions"
        else:
            out["corpus_positioning"] = "bottom_quartile"
            out["recommendation"] = "Bottom-quartile expected returns — reconsider entry price or thesis"
    else:
        out["corpus_positioning"] = "unknown"
        out["recommendation"] = "Insufficient benchmark data for comparison"

    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def underwriting_report(
    result: UnderwritingResult,
    benchmarks: Optional[Dict[str, Any]] = None,
) -> str:
    """Formatted underwriting report."""
    a = result.assumptions

    def _p(v: Any, fmt: str = ".2f") -> str:
        if v is None:
            return "N/A"
        try:
            return format(float(v), fmt)
        except (TypeError, ValueError):
            return str(v)

    lines = [
        f"LBO Underwriting Summary — {a.deal_name or 'Deal'}",
        "=" * 64,
        "  ENTRY",
        f"    EV           : ${_p(a.entry_ev_mm, ',.0f')}M",
        f"    EBITDA       : ${_p(a.entry_ebitda_mm, ',.0f')}M",
        f"    EV/EBITDA    : {_p(result.entry_ev_ebitda, '.1f')}x",
        f"    Equity       : ${_p(result.entry_equity_mm, ',.0f')}M "
        f"({a.equity_contribution_pct:.0%})",
        f"    Debt         : ${_p(result.entry_debt_mm, ',.0f')}M "
        f"({a.entry_leverage_x:.1f}x EBITDA)",
        "",
        "  EXIT PROJECTIONS",
        f"    Hold years   : {a.hold_years:.1f}y",
        f"    EBITDA CAGR  : {a.ebitda_cagr:.1%}",
        f"    Exit EBITDA  : ${_p(result.exit_ebitda_mm, ',.0f')}M",
        f"    Exit EV      : ${_p(result.exit_ev_mm, ',.0f')}M  "
        f"({a.exit_multiple:.1f}x EBITDA)",
        f"    Exit equity  : ${_p(result.exit_equity_mm, ',.0f')}M",
        "",
        "  RETURNS",
        f"    Gross MOIC   : {_p(result.gross_moic)}x",
        f"    Gross IRR    : {_p(result.gross_irr, '.1%')}",
        f"    Net MOIC     : {_p(result.net_moic)}x",
        f"    Net IRR      : {_p(result.net_irr, '.1%')}",
        f"    Total fees   : ${_p(result.total_fees_mm, ',.1f')}M",
    ]

    if benchmarks:
        comp = benchmark_compare(result, benchmarks)
        lines += [
            "",
            "  CORPUS BENCHMARK",
            f"    P25/P50/P75  : {_p(comp.get('moic_p25'))}x / "
            f"{_p(comp.get('moic_p50'))}x / {_p(comp.get('moic_p75'))}x",
            f"    Positioning  : {comp.get('corpus_positioning', 'N/A')}",
            f"    → {comp.get('recommendation', '')}",
        ]

    if result.warnings:
        lines += ["", "  WARNINGS:"]
        for w in result.warnings:
            lines.append(f"    ⚠ {w}")

    lines.append("=" * 64)
    return "\n".join(lines) + "\n"
