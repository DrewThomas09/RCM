"""Causal Inference Engine — shared substrate for treatment-
effect estimation.

Three estimators, in increasing sophistication, share the same
panel-data input shape Y: (N units × T periods) with a designated
treated_unit and treated_period:

  • DiD                 standard 2×2 difference-in-differences.
                        Closed form. The textbook starting point.
                        Doesn't model unit heterogeneity — every
                        control unit weighs equally.
  • Synthetic Control   Abadie-Gardeazabal (2003). Solves for
                        non-negative simplex weights ω (Σω = 1,
                        ω ≥ 0) that make the weighted control's
                        pre-treatment outcomes match the treated
                        unit's. Projected gradient descent —
                        pure numpy.
  • SDID                Arkhangelsky et al. (2021). Synthetic
                        Difference-in-Differences. Solves L2-
                        regularized closed-form for both unit
                        AND time weights, then computes the DiD
                        on the doubly-weighted panel. The most
                        flexible estimator — partner-defensible
                        when match quality is good.

All three return a comparable Result shape so downstream packets
(PortfolioSynergyPredictor, the regulatory-impact tracker, etc.)
can swap estimators without rewriting their pipelines.

Public API::

    from rcm_mc.causal import (
        did_estimate, DiDResult,
        synthetic_control_estimate, SyntheticControlResult,
        sdid_estimate, SDIDResult,
    )
"""
from .did import did_estimate, DiDResult
from .synthetic_control import (
    synthetic_control_estimate,
    SyntheticControlResult,
)
from .sdid import sdid_estimate, SDIDResult

__all__ = [
    "did_estimate", "DiDResult",
    "synthetic_control_estimate",
    "SyntheticControlResult",
    "sdid_estimate", "SDIDResult",
]
