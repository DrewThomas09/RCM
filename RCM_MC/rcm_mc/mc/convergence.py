"""Running-P50 convergence check for Monte Carlo output.

The convention we advertise: a packet's MC section is trustworthy only
if the running P50 over the last ``window`` simulations changes by less
than ``tolerance`` (as a fraction of the overall P50). Below that bar
we tell the partner to re-run with higher N, rather than silently
publishing a number that could shift next run.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

import numpy as np


@dataclass
class ConvergenceReport:
    converged: bool = False
    n_simulations: int = 0
    window: int = 0
    tolerance: float = 0.0
    last_window_range: float = 0.0    # |max - min| of last-window running P50
    recommended_n: int = 0
    p50_final: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _rolling_p50(values: np.ndarray) -> np.ndarray:
    """Cumulative P50 at each step. Not a true rolling window — each
    point is the median of everything seen up to that sim.

    Critical property: once enough sims accumulate the value stabilizes.
    We use this to detect "extra simulations stop moving the needle".
    """
    n = len(values)
    out = np.empty(n, dtype=float)
    # np.median across a growing prefix. n*log(n) overall; fine for
    # n=10k which is our upper bound.
    sorted_buf = []
    for i, v in enumerate(values):
        # Maintain a sorted buffer for O(log n) insertion + O(1) median.
        from bisect import insort
        insort(sorted_buf, float(v))
        mid = len(sorted_buf) // 2
        if len(sorted_buf) % 2 == 1:
            out[i] = sorted_buf[mid]
        else:
            out[i] = 0.5 * (sorted_buf[mid - 1] + sorted_buf[mid])
    return out


def check_convergence(
    results: np.ndarray,
    *,
    window: int = 1000,
    tolerance: float = 0.01,
) -> ConvergenceReport:
    """Check if the running P50 has stabilized.

    Parameters
    ----------
    results
        1-D numpy array of per-simulation outputs (e.g., ebitda_impact).
    window
        Size of the tail window we check for stability. Partners typical
        check the last 1000 of 10000 sims.
    tolerance
        Max allowed ``|max - min|`` of the running P50 in the window,
        as a fraction of the overall P50. Default 1% is what the
        diligence team considers "same number to two decimal places".

    Returns
    -------
    ConvergenceReport. ``converged`` is True iff the last-window range
    is within tolerance. ``recommended_n`` is a doubling heuristic —
    not a tight bound, just a hint to the partner.
    """
    arr = np.asarray(results, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n == 0:
        return ConvergenceReport(converged=False, n_simulations=0,
                                  window=window, tolerance=tolerance,
                                  recommended_n=max(1000, window))

    p50_final = float(np.median(arr))
    if n < window:
        # Not enough simulations to judge — return not-converged with a
        # recommendation to run at least one window's worth.
        return ConvergenceReport(
            converged=False, n_simulations=n, window=window,
            tolerance=tolerance, last_window_range=0.0,
            recommended_n=max(n * 2, window), p50_final=p50_final,
        )

    running = _rolling_p50(arr)
    tail = running[-window:]
    span = float(np.max(tail) - np.min(tail))
    scale = max(abs(p50_final), 1e-9)
    rel_span = span / scale
    converged = rel_span <= tolerance
    rec_n = n if converged else int(n * 2)
    return ConvergenceReport(
        converged=bool(converged),
        n_simulations=int(n),
        window=int(window),
        tolerance=float(tolerance),
        last_window_range=float(span),
        recommended_n=int(rec_n),
        p50_final=p50_final,
    )
