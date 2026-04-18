"""Hold period optimizer — identifies the MOIC-maximizing exit year.

Given entry assumptions and a model of how multiples compress over time,
computes MOIC for each possible hold year from 2 to 10 and returns
the optimal exit window. Also integrates corpus data on actual hold
periods by sector to calibrate the optimal range.

The multiple-compression model is grounded in corpus observation:
  - Healthcare PE multiples compress ~0.3-0.5x/year on average after year 5
  - Peak exits historically cluster at years 3-6
  - Sponsor-level holding past 7 years is typically sub-optimal except
    in platform build contexts

Public API:
    HoldResult                                       dataclass
    OptimalExitWindow                                dataclass
    compute_hold_curve(entry_assumptions, max_years) -> List[HoldResult]
    find_optimal_exit(hold_curve)                    -> OptimalExitWindow
    corpus_hold_benchmarks(deals, sector)            -> Dict[str, Any]
    hold_optimizer_report(curve, optimal, benchmarks) -> str
    hold_curve_table(curve)                          -> str
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HoldResult:
    """MOIC / IRR at a specific exit year."""
    hold_years: float
    exit_ebitda_mm: float
    exit_multiple: float        # Projected EV/EBITDA at this exit year
    exit_ev_mm: float
    exit_debt_mm: float
    exit_equity_mm: float
    gross_moic: float
    gross_irr: float
    net_moic: float
    moic_per_year: float        # Gross MOIC / hold years (MOIC velocity)
    leverage_at_exit: float     # Turns of debt / exit EBITDA
    notes: str = ""


@dataclass
class OptimalExitWindow:
    """Summary of the best exit window."""
    moic_maximizing_year: float       # Year that maximizes gross MOIC
    irr_maximizing_year: float        # Year that maximizes IRR (usually earlier)
    sweet_spot_start: float           # First year above 75% of max MOIC
    sweet_spot_end: float             # Last year above 75% of max MOIC
    peak_gross_moic: float
    peak_gross_irr: float
    moic_at_irr_optimal: float
    cliff_year: Optional[float]       # Year MOIC starts declining (multiple compression > EBITDA growth)


# ---------------------------------------------------------------------------
# Multiple-compression models
# ---------------------------------------------------------------------------

_SECTOR_MULTIPLE_COMPRESSION: Dict[str, float] = {
    "behavioral_health": -0.25,    # per year after year 3
    "home_health": -0.20,
    "hospice": -0.15,
    "dialysis": -0.25,
    "physician_group": -0.35,
    "asc": -0.20,
    "snf": -0.30,
    "hospital": -0.35,
    "health_it": -0.40,
    "managed_care": -0.20,
    "dental": -0.25,
    "physical_therapy": -0.35,
    "dme_home_health": -0.30,
    "oncology": -0.20,
}

_DEFAULT_COMPRESSION = -0.25  # per year after year 3


def _multiple_at_exit(
    entry_multiple: float,
    hold_years: float,
    sector: Optional[str] = None,
    multiple_expansion_years: float = 3.0,
) -> float:
    """Project exit EV/EBITDA at a given hold year.

    Assumes multiple holds flat through year `multiple_expansion_years`,
    then compresses at the sector-specific rate.
    """
    if sector:
        compression = _SECTOR_MULTIPLE_COMPRESSION.get(
            sector.lower().replace(" ", "_"), _DEFAULT_COMPRESSION
        )
    else:
        compression = _DEFAULT_COMPRESSION

    years_beyond_peak = max(0.0, hold_years - multiple_expansion_years)
    exit_multiple = entry_multiple + compression * years_beyond_peak
    return max(exit_multiple, entry_multiple * 0.60)  # floor at 60% of entry


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_hold_curve(
    entry_ebitda_mm: float,
    entry_multiple: float,
    ebitda_cagr: float,
    leverage_pct: float = 0.55,
    debt_amortization_pct: float = 0.03,
    management_fee_drag: float = 0.02,
    sector: Optional[str] = None,
    max_years: int = 10,
    step: float = 1.0,
) -> List[HoldResult]:
    """Compute MOIC/IRR for each hold year from 1 to max_years.

    Args:
        entry_ebitda_mm:     Entry EBITDA
        entry_multiple:      Entry EV/EBITDA
        ebitda_cagr:         Annual EBITDA growth rate
        leverage_pct:        Debt as % of entry EV
        debt_amortization_pct: Annual debt paydown as % of initial debt
        management_fee_drag: Annual fee drag on equity
        sector:              Optional sector for multiple-compression model
        max_years:           Maximum hold years to evaluate
        step:                Year increment

    Returns:
        List of HoldResult, one per hold year
    """
    entry_ev = entry_ebitda_mm * entry_multiple
    entry_debt = entry_ev * leverage_pct
    entry_equity = entry_ev - entry_debt

    results = []
    year = step
    while year <= max_years + 0.001:
        hy = round(year, 1)

        exit_ebitda = entry_ebitda_mm * (1 + ebitda_cagr) ** hy
        exit_multiple = _multiple_at_exit(entry_multiple, hy, sector)
        exit_ev = exit_ebitda * exit_multiple

        annual_paydown = entry_debt * debt_amortization_pct
        total_paydown = min(annual_paydown * hy, entry_debt)
        exit_debt = max(0.0, entry_debt - total_paydown)
        exit_equity = max(0.0, exit_ev - exit_debt)

        gross_moic = exit_equity / entry_equity if entry_equity > 0 else 0.0
        gross_irr = (gross_moic ** (1.0 / hy) - 1.0) if hy > 0 and gross_moic > 0 else 0.0

        # Net MOIC approximation
        fee_haircut = (1 - management_fee_drag) ** hy
        gross_gain = gross_moic - 1.0
        carry = max(0.0, gross_gain * 0.20)
        net_moic = (gross_moic - carry) * fee_haircut

        lev_at_exit = exit_debt / exit_ebitda if exit_ebitda > 0 else 0.0
        moic_per_year = gross_moic / hy if hy > 0 else 0.0

        notes = ""
        if exit_multiple < entry_multiple * 0.80:
            notes = "multiple compression >20%"

        results.append(HoldResult(
            hold_years=hy,
            exit_ebitda_mm=round(exit_ebitda, 1),
            exit_multiple=round(exit_multiple, 2),
            exit_ev_mm=round(exit_ev, 1),
            exit_debt_mm=round(exit_debt, 1),
            exit_equity_mm=round(exit_equity, 1),
            gross_moic=round(gross_moic, 3),
            gross_irr=round(gross_irr, 4),
            net_moic=round(net_moic, 3),
            moic_per_year=round(moic_per_year, 3),
            leverage_at_exit=round(lev_at_exit, 2),
            notes=notes,
        ))
        year += step

    return results


def find_optimal_exit(hold_curve: List[HoldResult]) -> OptimalExitWindow:
    """Find the optimal exit window from a hold curve."""
    if not hold_curve:
        return OptimalExitWindow(
            moic_maximizing_year=5.0, irr_maximizing_year=4.0,
            sweet_spot_start=3.0, sweet_spot_end=6.0,
            peak_gross_moic=0.0, peak_gross_irr=0.0,
            moic_at_irr_optimal=0.0, cliff_year=None,
        )

    max_moic_result = max(hold_curve, key=lambda r: r.gross_moic)
    max_irr_result = max(hold_curve, key=lambda r: r.gross_irr)

    peak_moic = max_moic_result.gross_moic
    threshold = peak_moic * 0.75

    sweet_spot = [r for r in hold_curve if r.gross_moic >= threshold]
    sweet_start = sweet_spot[0].hold_years if sweet_spot else max_moic_result.hold_years
    sweet_end = sweet_spot[-1].hold_years if sweet_spot else max_moic_result.hold_years

    # Find cliff year: first year where MOIC starts declining
    cliff_year = None
    for i in range(1, len(hold_curve)):
        if hold_curve[i].gross_moic < hold_curve[i-1].gross_moic - 0.05:
            cliff_year = hold_curve[i].hold_years
            break

    return OptimalExitWindow(
        moic_maximizing_year=max_moic_result.hold_years,
        irr_maximizing_year=max_irr_result.hold_years,
        sweet_spot_start=sweet_start,
        sweet_spot_end=sweet_end,
        peak_gross_moic=peak_moic,
        peak_gross_irr=max_irr_result.gross_irr,
        moic_at_irr_optimal=hold_curve[hold_curve.index(max_irr_result)].gross_moic,
        cliff_year=cliff_year,
    )


def corpus_hold_benchmarks(
    deals: List[Dict[str, Any]],
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute P25/P50/P75 hold years and MOIC from corpus for a sector."""
    filtered = [d for d in deals if d.get("hold_years") is not None and d.get("realized_moic") is not None]

    if sector:
        from .subsector_benchmarks import _canonical_sector
        canonical = _canonical_sector(sector)
        sector_deals = [d for d in filtered if _canonical_sector(d.get("sector")) == canonical]
        if len(sector_deals) >= 3:
            filtered = sector_deals

    holds = sorted([float(d["hold_years"]) for d in filtered])
    moics = sorted([float(d["realized_moic"]) for d in filtered])

    def pct(vals, p):
        if not vals:
            return None
        idx = max(0, min(len(vals)-1, int(p * (len(vals)-1))))
        return round(vals[idx], 2)

    return {
        "n": len(filtered),
        "sector": sector,
        "hold_p25": pct(holds, 0.25),
        "hold_p50": pct(holds, 0.50),
        "hold_p75": pct(holds, 0.75),
        "moic_p25": pct(moics, 0.25),
        "moic_p50": pct(moics, 0.50),
        "moic_p75": pct(moics, 0.75),
        "mean_hold": round(sum(holds)/len(holds), 2) if holds else None,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def hold_curve_table(curve: List[HoldResult]) -> str:
    """Formatted hold-year sensitivity table."""
    lines = [
        f"{'Year':>5} {'Exit EBITDA':>12} {'Exit Mult':>10} {'Exit EV':>9} "
        f"{'Gross MOIC':>11} {'Gross IRR':>10} {'Net MOIC':>9} {'MOIC/yr':>8}",
        "-" * 82,
    ]
    for r in curve:
        lines.append(
            f"{r.hold_years:>5.0f} ${r.exit_ebitda_mm:>10,.1f}M {r.exit_multiple:>9.1f}x "
            f"${r.exit_ev_mm:>8,.0f}M {r.gross_moic:>10.2f}x {r.gross_irr:>9.1%} "
            f"{r.net_moic:>8.2f}x {r.moic_per_year:>7.3f}"
            + (f"  [{r.notes}]" if r.notes else "")
        )
    return "\n".join(lines) + "\n"


def hold_optimizer_report(
    curve: List[HoldResult],
    optimal: OptimalExitWindow,
    benchmarks: Optional[Dict[str, Any]] = None,
) -> str:
    """Narrative report for IC packet."""
    lines = [
        "Hold Period Optimization Report",
        "=" * 50,
        f"  MOIC-maximizing exit:  Year {optimal.moic_maximizing_year:.0f} ({optimal.peak_gross_moic:.2f}x)",
        f"  IRR-maximizing exit:   Year {optimal.irr_maximizing_year:.0f} ({optimal.peak_gross_irr:.1%})",
        f"  Sweet spot window:     Years {optimal.sweet_spot_start:.0f}–{optimal.sweet_spot_end:.0f}",
        f"  MOIC at IRR-optimal:   {optimal.moic_at_irr_optimal:.2f}x",
    ]
    if optimal.cliff_year:
        lines.append(f"  Multiple compression cliff: Year {optimal.cliff_year:.0f}")

    if benchmarks and benchmarks.get("n", 0) >= 3:
        lines += [
            "",
            f"  Corpus comparables (n={benchmarks['n']}, sector={benchmarks.get('sector','all')})",
            f"    Hold P25/P50/P75:  {benchmarks['hold_p25']} / {benchmarks['hold_p50']} / {benchmarks['hold_p75']} yrs",
            f"    MOIC P25/P50/P75:  {benchmarks['moic_p25']}x / {benchmarks['moic_p50']}x / {benchmarks['moic_p75']}x",
        ]

    return "\n".join(lines) + "\n"
