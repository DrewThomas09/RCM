"""Management Scorecard — systematic quality-of-management diligence.

Answers the question partners ask every deal: "will this team hit
the forecast they're giving us?" Today that's ad-hoc reference
calls + LinkedIn skimming. This module turns it into a
structured, partner-readable score per executive plus a roster-
level EBITDA-bridge haircut recommendation.

Four scored dimensions per executive (0–100, higher = better):

    1. ForecastReliability — |guide - actual| / guide, averaged
       over prior reporting periods. 0% miss → 100, ≥20% → 0.
    2. CompStructure       — base vs FMV p50/p90, equity alignment,
       clawbacks, performance-weighted bonus.
    3. Tenure              — years in role + years at facility.
       5+ years → 100, <1 year → 0.
    4. PriorRoleReputation — outcome at prior employer (strong
       exit → 100; Ch. 11 → 0). Cross-referenced against the
       Deal Autopsy failure library when a prior employer matches.

Output:
    - Per-executive ``ExecutiveScore`` with named reasons for each
      dimension's score
    - Roster-level aggregate + haircut recommendation (e.g.,
      "Apply 15% haircut to FY1 EBITDA guidance based on CEO's
      23% historical miss rate")
    - EBITDA-bridge-ready ``BridgeHaircutInput`` that feeds the
      Deal MC ``organic_growth_mean`` or a new reliability-discount
      driver

Why this is unique:
    Chartis / VMG do partner-interview frameworks. Nobody scores
    management systematically using public-data + reported history.
    Every output is a named executive with a specific dollar delta
    (haircut × guidance = expected miss in $).

Public API::

    from rcm_mc.diligence.management_scorecard import (
        BridgeHaircutInput, Executive, ExecutiveScore,
        ForecastHistory, ManagementReport, analyze_team,
        score_executive,
    )
"""
from __future__ import annotations

from .profile import (
    ComplevelBand, Executive, ForecastHistory, PriorRole,
    Role,
)
from .scorer import (
    DEFAULT_WEIGHTS, ExecutiveScore, RedFlag,
    score_executive, score_comp_structure,
    score_forecast_reliability, score_prior_role,
    score_tenure,
)
from .analyzer import (
    BridgeHaircutInput, ManagementReport, analyze_team,
)

__all__ = [
    "BridgeHaircutInput",
    "ComplevelBand",
    "DEFAULT_WEIGHTS",
    "Executive",
    "ExecutiveScore",
    "ForecastHistory",
    "ManagementReport",
    "PriorRole",
    "RedFlag",
    "Role",
    "analyze_team",
    "score_comp_structure",
    "score_executive",
    "score_forecast_reliability",
    "score_prior_role",
    "score_tenure",
]
