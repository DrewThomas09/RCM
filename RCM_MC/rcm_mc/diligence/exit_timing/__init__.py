"""Exit Timing + Buyer-Type Fit Analyzer.

Answers the two questions PE partners face at year 3–5 of every
deal: **when** should we exit, and **to whom**.

Composes three existing data sources into a new predictive layer:

    1. Deal MC ``YearBand`` — per-year EBITDA + revenue distribution
       across the 5-year hold
    2. Market Intel — category EV/EBITDA bands, sector sentiment,
       analyst consensus
    3. Deal Autopsy — historical exit-outcome patterns by sponsor
       + buyer type

Produces:

    - An IRR-by-exit-year curve across years 2–7 with MOIC + $ proceeds
    - Buyer-type fit scores for STRATEGIC / PE_SECONDARY / IPO, each
      with expected multiple premium/discount, expected time-to-close,
      and close-certainty
    - A recommended exit year + buyer type with partner-readable
      narrative ("Exit year 4 to a strategic acquirer: 28% IRR
      vs 22% at year 5. The extra year of hold costs 6 pp of IRR
      — fund-level math should prefer year 4.")

Public API::

    from rcm_mc.diligence.exit_timing import (
        BuyerFitScore, BuyerType, ExitCurvePoint,
        ExitRecommendation, ExitTimingReport,
        analyze_exit_timing,
    )
"""
from __future__ import annotations

from .playbook import (
    BUYER_PLAYBOOKS, BuyerPlaybook, BuyerType,
)
from .curves import (
    DEFAULT_CANDIDATE_HOLDS, ExitCurvePoint, build_exit_curve,
)
from .buyer_fit import (
    BuyerFitScore, score_buyer_fit, score_all_buyers,
)
from .analyzer import (
    ExitRecommendation, ExitTimingReport, analyze_exit_timing,
)

__all__ = [
    "BUYER_PLAYBOOKS",
    "BuyerFitScore",
    "BuyerPlaybook",
    "BuyerType",
    "DEFAULT_CANDIDATE_HOLDS",
    "ExitCurvePoint",
    "ExitRecommendation",
    "ExitTimingReport",
    "analyze_exit_timing",
    "build_exit_curve",
    "score_all_buyers",
    "score_buyer_fit",
]
