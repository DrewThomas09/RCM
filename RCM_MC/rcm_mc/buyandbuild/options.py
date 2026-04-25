"""Black-Scholes + binomial-lattice option valuation in pure numpy.

We need three flavours:

  1. ``black_scholes_call`` — closed-form European call. Used to
     value the optionality of *not* exercising an add-on right.

  2. ``binomial_lattice_call`` — Cox-Ross-Rubinstein lattice for
     American options (early exercise allowed at every node). Used
     when the add-on right has discrete decision points.

  3. ``binomial_lattice_compound`` — compound option (option on
     an option). Each add-on creates the *option* to acquire the
     next one; without explicit compounding the partner under-
     values the sequence dramatically.

All three are pure numpy — no scipy.
"""
from __future__ import annotations

from math import erf, exp, log, sqrt
from typing import Optional

import numpy as np


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2)))


def black_scholes_call(
    S: float,        # current asset value (e.g. add-on standalone EV)
    K: float,        # strike (purchase price)
    T: float,        # time to exercise in years
    r: float,        # risk-free rate
    sigma: float,    # volatility (annualized)
) -> float:
    """Closed-form European call value."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return max(0.0, S - K * exp(-r * T))
    d1 = (log(S / K) + (r + sigma * sigma / 2.0) * T) / (
        sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return S * _norm_cdf(d1) - K * exp(-r * T) * _norm_cdf(d2)


def binomial_lattice_call(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    *,
    steps: int = 50,
    american: bool = True,
) -> float:
    """Cox-Ross-Rubinstein binomial lattice call valuation.

    With ``american=True`` (default) the holder may exercise at
    every node — appropriate for an add-on right where the
    partner can pull the trigger at any LOI deadline. European
    valuation matches Black-Scholes in the limit.
    """
    if T <= 0 or sigma <= 0 or steps < 1:
        return max(0.0, S - K * exp(-r * T))
    dt = T / steps
    u = exp(sigma * sqrt(dt))
    d = 1.0 / u
    p = (exp(r * dt) - d) / (u - d)
    if not (0.0 <= p <= 1.0):
        # Numerical issue — fall back to Black-Scholes
        return black_scholes_call(S, K, T, r, sigma)

    # Asset prices at terminal nodes
    j = np.arange(steps + 1)
    asset = S * (u ** (steps - j)) * (d ** j)
    value = np.maximum(asset - K, 0.0)

    disc = exp(-r * dt)
    for step in range(steps - 1, -1, -1):
        # Roll back
        asset = asset[: step + 1] / u
        value = disc * (p * value[: step + 1] + (1 - p) * value[1: step + 2])
        if american:
            # Early-exercise check at this layer
            value = np.maximum(value, asset - K)
    return float(value[0])


def binomial_lattice_compound(
    S: float,
    K_inner: float,
    T_inner: float,
    K_outer: float,
    T_outer: float,
    r: float,
    sigma: float,
    *,
    steps_outer: int = 30,
    steps_inner: int = 30,
) -> float:
    """Compound call (option on an option). The outer holder pays
    K_outer at T_outer to acquire an inner European call with
    strike K_inner expiring at T_inner > T_outer.

    Used when the partner buys the platform PLATFORM (outer) which
    confers the right to acquire add-on (inner) at a later
    decision point.
    """
    if T_outer >= T_inner:
        # Compound only makes sense if outer expires first
        return black_scholes_call(S, K_inner, T_inner, r, sigma)

    # Inner option value at the outer expiry, evaluated across the
    # outer-step asset distribution.
    dt_outer = T_outer / steps_outer
    u = exp(sigma * sqrt(dt_outer))
    d = 1.0 / u
    p = (exp(r * dt_outer) - d) / (u - d)

    # Asset values at outer expiry
    j = np.arange(steps_outer + 1)
    asset_at_outer = S * (u ** (steps_outer - j)) * (d ** j)

    # Inner option value at each outer-expiry asset price
    inner_T = T_inner - T_outer
    inner_values = np.array([
        binomial_lattice_call(
            float(a), K_inner, inner_T, r, sigma,
            steps=steps_inner, american=True,
        )
        for a in asset_at_outer
    ])

    # Outer payoff: max(inner_value − K_outer, 0)
    payoff = np.maximum(inner_values - K_outer, 0.0)

    # Roll the outer lattice back to t=0
    disc = exp(-r * dt_outer)
    value = payoff
    for step in range(steps_outer - 1, -1, -1):
        value = disc * (p * value[: step + 1]
                        + (1 - p) * value[1: step + 2])
    return float(value[0])
