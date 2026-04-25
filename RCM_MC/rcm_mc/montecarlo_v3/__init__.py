"""MonteCarloPacket v3 — copulas, Sobol, importance sampling.

Upgrades the existing Monte Carlo machinery with the variance-
reduction + tail-modeling tools that move diligence-grade risk
analysis from "vibes" to "defensible numbers":

  • Joint copulas (Gaussian, Student-t, Archimedean Clayton /
    Gumbel / Frank) — model risk-factor dependence beyond the
    naive independent-marginals assumption that under-estimates
    joint tail events.
  • Glasserman-Li importance sampling — exponential tilting that
    drives more samples into rare-event regions (CMS payment cut
    + commercial compression + labor inflation hitting at the
    same time).
  • Sobol quasi-MC sequences — better convergence than pseudo-
    random for low-dimensional integrals.
  • Control variates — variance reduction using a correlated
    proxy with known expectation.
  • Nested simulation — outer + inner MC for real-options
    pricing where each outer state needs its own option value.
  • Healthcare-specific joint tail model wiring CMS payment cuts,
    commercial rate compression, and labor inflation as a
    correlated three-factor system.

All pure numpy. No scipy.

Public API::

    from rcm_mc.montecarlo_v3 import (
        gaussian_copula_sample, t_copula_sample,
        clayton_copula_sample, gumbel_copula_sample,
        sobol_sequence,
        importance_sample_tail,
        control_variate_estimate,
        nested_mc_real_option,
        joint_tail_healthcare_shock,
    )
"""
from .copula import (
    gaussian_copula_sample,
    t_copula_sample,
    clayton_copula_sample,
    gumbel_copula_sample,
    frank_copula_sample,
)
from .sobol import sobol_sequence
from .importance import (
    importance_sample_tail,
    glasserman_li_tilt,
)
from .control_variates import control_variate_estimate
from .nested import nested_mc_real_option
from .healthcare import joint_tail_healthcare_shock

__all__ = [
    "gaussian_copula_sample",
    "t_copula_sample",
    "clayton_copula_sample",
    "gumbel_copula_sample",
    "frank_copula_sample",
    "sobol_sequence",
    "importance_sample_tail",
    "glasserman_li_tilt",
    "control_variate_estimate",
    "nested_mc_real_option",
    "joint_tail_healthcare_shock",
]
