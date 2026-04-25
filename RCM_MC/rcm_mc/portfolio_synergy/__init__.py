"""PortfolioSynergyPredictor — cross-portfolio synthetic-DiD.

When a sponsor implements a best practice (e.g., a new RCM
workflow) at one portfolio company, the question for every
LP-grade fund is: how much of the resulting EBITDA lift is
operational alpha vs general market beta? And: how fast will
that practice diffuse to the rest of the portfolio + the next
add-on?

Three modules:

  • sdid       — Synthetic Difference-in-Differences (Arkhangelsky
                 et al. 2021) treatment-effect estimator. Closed-
                 form unit + time weights via ridge-regularized
                 L2 problem. Pure numpy.

  • diffusion  — best-practice diffusion model. Logistic adoption
                 curve fits the historical "% portfolio adopted by
                 month" series; forecasts adoption + EBITDA-lift
                 timing for the next add-on.

  • alpha      — operational_alpha_attribution. Splits realized
                 EBITDA growth into operational alpha (the SDID
                 estimate) + market beta (peer-group baseline).
                 LP-grade attribution.

Public API::

    from rcm_mc.portfolio_synergy import (
        sdid_estimate, SDIDResult,
        fit_diffusion_curve, predict_synergy_timing,
        DiffusionCurve, SynergyTiming,
        operational_alpha_attribution,
        AlphaAttribution,
    )
"""
from .sdid import sdid_estimate, SDIDResult
from .diffusion import (
    fit_diffusion_curve,
    predict_synergy_timing,
    DiffusionCurve,
    SynergyTiming,
)
from .alpha import (
    operational_alpha_attribution,
    AlphaAttribution,
)

__all__ = [
    "sdid_estimate", "SDIDResult",
    "fit_diffusion_curve", "predict_synergy_timing",
    "DiffusionCurve", "SynergyTiming",
    "operational_alpha_attribution", "AlphaAttribution",
]
