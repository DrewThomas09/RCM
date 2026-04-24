"""IRR / MOIC / proceeds curves across candidate exit years.

Given Deal MC output (year-by-year EBITDA trajectory), compute a
curve of (year, moic, irr, proceeds) for each candidate hold
year. Includes a per-year "sharpe-like" reward / hold-risk ratio
that partners use to pick the sweet spot.

Math:

    Terminal value at year N = EBITDA(N) × exit_multiple(N)
    Equity proceeds at year N = terminal_value - remaining_debt
                                (+ cumulative distributed cash, if any)
    MOIC = equity_proceeds / equity_check
    IRR  = MOIC^(1/N) - 1         (approximation — no cash flow
                                    timing beyond terminal)
    Reward = MOIC
    Hold penalty = year × fund_opportunity_cost_pp
    Sharpe-like ratio = IRR − hurdle_rate

Candidates default to years 2–7. Years outside a plausible range
(< 2 or > 8) aren't supported — PE fund typical lives are 7-10yrs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Year-2 through year-7 is the realistic PE exit window. Earlier
# exits look like quick flips (regulatory / multiple-compression
# driven); later exits break fund-level IRR math.
DEFAULT_CANDIDATE_HOLDS: Tuple[int, ...] = (2, 3, 4, 5, 6, 7)


# Assumed annual debt paydown rate (fraction of outstanding debt).
# Real LBO schedules vary; 8% aggregate is a typical acute-hospital
# deal's assumed paydown through operating cash flow.
_DEFAULT_DEBT_PAYDOWN_RATE: float = 0.08

# Assumed partner hurdle rate used to compute Sharpe-like excess
# return. Typical LP hurdle 8%; funds quote their own.
_DEFAULT_HURDLE_RATE: float = 0.08


@dataclass
class ExitCurvePoint:
    """One candidate hold year with its exit math."""
    year: int
    ebitda_median_usd: float
    exit_multiple_assumed: float
    terminal_enterprise_value_usd: float
    remaining_debt_usd: float
    equity_proceeds_usd: float
    moic: float
    irr: float                          # Year-over-year IRR estimate
    excess_over_hurdle_pct: float       # IRR - hurdle_rate

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _amortize_debt(
    debt_year0_usd: float, years_elapsed: int,
    paydown_rate: float = _DEFAULT_DEBT_PAYDOWN_RATE,
) -> float:
    """Straight-line-ish paydown: outstanding debt decays by
    ``paydown_rate`` per year.  Floor at 0."""
    remaining = debt_year0_usd
    for _ in range(years_elapsed):
        remaining = max(0.0, remaining * (1.0 - paydown_rate))
    return remaining


def _estimate_moic_irr(
    equity_check_usd: float,
    ebitda_year_n_usd: float,
    exit_multiple: float,
    debt_year0_usd: float,
    years_elapsed: int,
    paydown_rate: float = _DEFAULT_DEBT_PAYDOWN_RATE,
) -> Tuple[float, float, float, float]:
    """Return (moic, irr, terminal_ev, equity_proceeds)."""
    terminal_ev = ebitda_year_n_usd * exit_multiple
    remaining_debt = _amortize_debt(
        debt_year0_usd, years_elapsed, paydown_rate=paydown_rate,
    )
    equity_proceeds = max(0.0, terminal_ev - remaining_debt)
    moic = (
        equity_proceeds / equity_check_usd
        if equity_check_usd > 0 else 0.0
    )
    # IRR = MOIC^(1/N) - 1, assuming single terminal cash flow
    if years_elapsed <= 0 or moic <= 0:
        irr = 0.0
    else:
        irr = moic ** (1.0 / years_elapsed) - 1.0
    return moic, irr, terminal_ev, equity_proceeds


def build_exit_curve(
    *,
    equity_check_usd: float,
    debt_year0_usd: float,
    ebitda_median_by_year: Sequence[float],
    exit_multiple_by_year: Sequence[float],
    candidate_holds: Sequence[int] = DEFAULT_CANDIDATE_HOLDS,
    debt_paydown_rate: float = _DEFAULT_DEBT_PAYDOWN_RATE,
    hurdle_rate: float = _DEFAULT_HURDLE_RATE,
) -> List[ExitCurvePoint]:
    """Compute the per-candidate-year exit curve.

    ``ebitda_median_by_year`` is a sequence indexed by year
    (index 0 = year 0, index 1 = year 1, ...). Typically passed in
    from Deal MC's ``YearBand.median`` values.
    ``exit_multiple_by_year`` aligns with the same indexing — pass
    in peer-median multiple(s) or a sector-rotation-adjusted
    projection. Values in turns (e.g., 9.0 = 9x EV/EBITDA).
    """
    points: List[ExitCurvePoint] = []
    for year in candidate_holds:
        # Bounds check — if the caller didn't supply far enough out,
        # skip.  Year index into the arrays.
        if year >= len(ebitda_median_by_year):
            continue
        if year >= len(exit_multiple_by_year):
            continue
        ebitda = float(ebitda_median_by_year[year])
        mult = float(exit_multiple_by_year[year])
        if ebitda <= 0 or mult <= 0:
            continue
        moic, irr, terminal_ev, equity_proceeds = _estimate_moic_irr(
            equity_check_usd=equity_check_usd,
            ebitda_year_n_usd=ebitda,
            exit_multiple=mult,
            debt_year0_usd=debt_year0_usd,
            years_elapsed=year,
            paydown_rate=debt_paydown_rate,
        )
        remaining_debt = _amortize_debt(
            debt_year0_usd, year, paydown_rate=debt_paydown_rate,
        )
        points.append(ExitCurvePoint(
            year=year,
            ebitda_median_usd=ebitda,
            exit_multiple_assumed=mult,
            terminal_enterprise_value_usd=terminal_ev,
            remaining_debt_usd=remaining_debt,
            equity_proceeds_usd=equity_proceeds,
            moic=moic,
            irr=irr,
            excess_over_hurdle_pct=irr - hurdle_rate,
        ))
    return points


def peak_irr_year(points: Sequence[ExitCurvePoint]) -> Optional[ExitCurvePoint]:
    """Return the curve point with the highest IRR."""
    if not points:
        return None
    return max(points, key=lambda p: p.irr)


def moic_hurdle_year(
    points: Sequence[ExitCurvePoint], hurdle: float = 2.0,
) -> Optional[ExitCurvePoint]:
    """First year where MOIC clears a partner-chosen hurdle
    (default 2.0x). Returns None if never cleared."""
    for p in points:
        if p.moic >= hurdle:
            return p
    return None
