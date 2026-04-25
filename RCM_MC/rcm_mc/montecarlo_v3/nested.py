"""Nested Monte Carlo for real-options valuation.

Outer simulation: N_outer paths of the underlying state to a
decision date. Inner simulation: at each outer state, run
N_inner paths to estimate the option's continuation value.
The decision (exercise or continue) is the max of immediate
exercise vs. expected continuation.

This is the textbook approach for path-dependent American-style
real options where the closed-form binomial lattice doesn't fit
(e.g. when the underlying has stochastic volatility or jumps).
"""
from __future__ import annotations

from typing import Callable

import numpy as np


def nested_mc_real_option(
    *,
    initial_state: float,
    decision_time: float,
    horizon: float,
    drift: float,
    volatility: float,
    payoff: Callable[[np.ndarray], np.ndarray],
    n_outer: int = 200,
    n_inner: int = 100,
    seed: int = 0,
) -> dict:
    """Two-level Monte Carlo for an American-style real option.

    Inputs model a geometric Brownian motion underlying:
      dS = drift × S dt + volatility × S dW

    At ``decision_time`` the holder chooses exercise (apply
    payoff to current state) vs. continue to ``horizon`` (mean
    payoff of inner paths).

    Returns a dict with: option_value, exercise_probability,
    se_outer (standard error across outer paths).
    """
    if decision_time <= 0 or horizon <= decision_time:
        raise ValueError(
            "Need 0 < decision_time < horizon")

    rng = np.random.default_rng(seed)
    # Outer: simulate to decision_time
    Z_outer = rng.standard_normal(n_outer)
    drift_dec = (drift - 0.5 * volatility * volatility) * decision_time
    diffuse_dec = volatility * np.sqrt(decision_time)
    S_dec = initial_state * np.exp(drift_dec + diffuse_dec * Z_outer)

    # For each outer state, simulate inner paths to horizon
    inner_dt = horizon - decision_time
    drift_inner = (drift - 0.5 * volatility * volatility) * inner_dt
    diffuse_inner = volatility * np.sqrt(inner_dt)

    Z_inner = rng.standard_normal((n_outer, n_inner))
    S_term = S_dec[:, np.newaxis] * np.exp(
        drift_inner + diffuse_inner * Z_inner)
    inner_payoffs = payoff(S_term.flatten()).reshape(
        n_outer, n_inner)
    continuation_values = inner_payoffs.mean(axis=1)

    # Exercise decision
    immediate = payoff(S_dec)
    decision_values = np.maximum(immediate, continuation_values)
    exercise_now = (immediate > continuation_values)

    return {
        "option_value": float(decision_values.mean()),
        "exercise_probability": float(exercise_now.mean()),
        "se_outer": float(
            decision_values.std(ddof=1) / np.sqrt(n_outer)),
        "n_outer": int(n_outer),
        "n_inner": int(n_inner),
    }
