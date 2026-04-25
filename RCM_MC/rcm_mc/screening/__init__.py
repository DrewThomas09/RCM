"""Deal Screening Engine — Bloomberg-like filterable deal universe.

Sourcing deals is a partner's daily problem. The killer feature
is a single screen showing:

  • Universe of candidate targets (fed by the corpus or a custom
    target list)
  • Per-target predicted EBITDA uplift the sponsor could deliver
  • Confidence band on that prediction
  • Top risk factors flagged
  • Filter chips: sector, size, confidence floor, exclude topics

Backed by the existing causal substrate + comparable_outcomes +
regulatory risk + qoe-flagger so predictions land on real model
output rather than vibes.

Public API::

    from rcm_mc.screening import (
        DealCandidate, ScreeningResult,
        predict_deal_metrics,
        DealFilter, apply_filter,
        render_screening_dashboard,
    )
"""
from .predict import (
    DealCandidate,
    ScreeningResult,
    predict_deal_metrics,
    score_universe,
)
from .filter import DealFilter, apply_filter
from .dashboard import render_screening_dashboard

__all__ = [
    "DealCandidate",
    "ScreeningResult",
    "predict_deal_metrics",
    "score_universe",
    "DealFilter",
    "apply_filter",
    "render_screening_dashboard",
]
