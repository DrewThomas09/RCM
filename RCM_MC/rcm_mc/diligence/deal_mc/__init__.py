"""Deal-level Monte Carlo — the EBITDA + MOIC + IRR distribution
engine that integrates every risk-module's output.

What this does that existing MC modules don't:

    - Models the FULL hold-period EBITDA path, not just Phase-1
      RCM KPIs. Year-by-year revenue, EBITDA, free cash flow,
      debt paydown, exit multiple.

    - Stochastic over EVERY lever: organic growth, denials, payer
      mix shift, reg headwind realization, lease escalator,
      physician attrition, cyber incidents, V28 compression,
      exit-multiple dispersion.

    - Produces what partners actually ask for: P(MOIC < 1.0x),
      P(MOIC < 2.0x), P25/P75 EBITDA in each hold year,
      driver-attributed variance decomposition, one-at-a-time
      sensitivity tornado.

Integrates with:
    - CCD (baseline revenue, denial rate, OON share)
    - Risk modules: counterfactual, Steward Score, cyber, V28
    - Market intel: peer-median EV/EBITDA for exit multiple

Public API::

    from rcm_mc.diligence.deal_mc import (
        DealScenario, DealMCResult, DriverAttribution,
        run_deal_monte_carlo, stress_test_drivers,
    )
"""
from __future__ import annotations

from .engine import (
    DEFAULT_HOLD_YEARS, DEFAULT_N_RUNS,
    DealMCResult, DealScenario, DriverAttribution,
    DriverContribution, MOICBucket, YearBand,
    run_deal_monte_carlo, stress_test_drivers,
)

__all__ = [
    "DEFAULT_HOLD_YEARS",
    "DEFAULT_N_RUNS",
    "DealMCResult",
    "DealScenario",
    "DriverAttribution",
    "DriverContribution",
    "MOICBucket",
    "YearBand",
    "run_deal_monte_carlo",
    "stress_test_drivers",
]
