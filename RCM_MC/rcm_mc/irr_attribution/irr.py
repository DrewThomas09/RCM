"""IRR + MOIC computation on a list of (year, amount) cash flows.

IRR is the discount rate that makes NPV(cashflows) = 0. Solved
by Newton-Raphson with bisection fallback for robustness.
Convention: negative amounts are LP outflows (calls), positive
amounts are LP inflows (distributions).
"""
from __future__ import annotations

from typing import List, Tuple


def _npv(rate: float, cashflows: List[Tuple[float, float]]) -> float:
    return sum(amount / ((1.0 + rate) ** year)
               for year, amount in cashflows)


def _npv_derivative(
    rate: float, cashflows: List[Tuple[float, float]]
) -> float:
    return sum(-year * amount / ((1.0 + rate) ** (year + 1))
               for year, amount in cashflows)


def compute_irr(
    cashflows: List[Tuple[float, float]],
    *,
    initial_guess: float = 0.15,
    max_iter: int = 100,
    tol: float = 1e-7,
) -> float:
    """Compute IRR for a stream of (year_from_close, amount) tuples.

    Returns the rate at which NPV = 0. Uses Newton-Raphson with
    a bisection fallback when the derivative is too small.

    Returns 0.0 on degenerate inputs (no negative or no positive
    cashflows — IRR undefined).
    """
    if not cashflows or len(cashflows) < 2:
        return 0.0
    has_outflow = any(a < 0 for _, a in cashflows)
    has_inflow = any(a > 0 for _, a in cashflows)
    if not (has_outflow and has_inflow):
        return 0.0

    # Newton-Raphson
    rate = initial_guess
    for _ in range(max_iter):
        npv = _npv(rate, cashflows)
        if abs(npv) < tol:
            return float(rate)
        deriv = _npv_derivative(rate, cashflows)
        if abs(deriv) < 1e-12:
            break
        new_rate = rate - npv / deriv
        if abs(new_rate - rate) < tol:
            return float(new_rate)
        rate = new_rate
        # Sanity bound
        if rate < -0.99 or rate > 10.0:
            break

    # Fallback: bisection over a wide bracket
    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        v = _npv(mid, cashflows)
        if abs(v) < tol:
            return float(mid)
        # NPV is monotone-decreasing in rate for typical PE flows
        # (early outflows, late inflows). Use the sign at lo.
        if v * _npv(lo, cashflows) < 0:
            hi = mid
        else:
            lo = mid
    return float(0.5 * (lo + hi))


def compute_moic(cashflows: List[Tuple[float, float]]) -> float:
    """Multiple of invested capital — total inflows / total outflows."""
    inflows = sum(a for _, a in cashflows if a > 0)
    outflows = -sum(a for _, a in cashflows if a < 0)
    if outflows <= 0:
        return 0.0
    return float(inflows / outflows)
