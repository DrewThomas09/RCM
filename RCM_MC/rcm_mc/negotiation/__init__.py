"""Payer–provider negotiation simulator.

Agent-based simulator that consumes the TiC/MRF/NPPES foundation
and predicts negotiated-rate outcomes under counterfactual market
structures (post-merger consolidation, payer-network rebuild,
add-on acquisition).

Three levels of model:

  1. **Outside-options dispersion** — For each (NPI × code), look up
     every observed negotiated rate across payers in the corpus.
     The DISPERSION is the surplus available to negotiate over;
     each side's outside option anchors the bargaining range.

  2. **Nash bargaining** — Single-round split of the bargaining
     surplus weighted by relative bargaining power. Default
     equal-power Nash, parametrized by an asymmetric power
     coefficient that the partner can override.

  3. **Repeated-game adjustment** — Multi-round dynamics with
     reputation-driven concession; provider's "next-period leverage"
     depends on whether the payer can plausibly steer volume to an
     alternative provider (consumed from rcm_mc.referral.payer_leverage).

Public API::

    from rcm_mc.negotiation import (
        BargainingState,
        compute_outside_options,
        nash_bargaining,
        repeated_game_rate,
        simulate_post_merger_rate,
        antitrust_risk_score,
    )

The math is intentionally interpretable — every output rate can
be traced back to a specific outside-option distribution and a
specific bargaining-power assumption. No black-box ML.
"""
from .outside_options import compute_outside_options, OutsideOptions
from .bargaining import (
    BargainingState,
    nash_bargaining,
    repeated_game_rate,
)
from .counterfactual import (
    simulate_post_merger_rate,
    antitrust_risk_score,
)
from .distributions import (
    RateDistribution,
    aggregate_rate_distributions,
    cross_payer_dispersion,
)

__all__ = [
    "OutsideOptions",
    "compute_outside_options",
    "BargainingState",
    "nash_bargaining",
    "repeated_game_rate",
    "simulate_post_merger_rate",
    "antitrust_risk_score",
    "RateDistribution",
    "aggregate_rate_distributions",
    "cross_payer_dispersion",
]
