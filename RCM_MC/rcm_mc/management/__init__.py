"""Management Assessment Packet — team scorecard for diligence.

A structured assessment surface for the management team a partner
is acquiring. Six modules:

  • scorecard      — competency scorecard with weighted scoring
                     across 8 healthcare-PE-relevant dimensions
                     (financial discipline, payer relationships,
                     M&A integration, talent retention, etc.).
  • personality    — Big Five (OCEAN) distilled into investable
                     signals correlated with CEO/CFO performance
                     in healthcare-PE realizations.
  • org_design     — span-of-control + layers + role-clarity
                     scoring; flags healthcare-specific
                     anti-patterns (clinical leader as COO,
                     dual-hat CFO/CRO, etc.).
  • feedback       — 360-feedback aggregation with rater-weighted
                     means (boss > peer > direct report >
                     external).
  • succession     — key-person-risk register: per-role
                     concentration, departure-impact $-estimate,
                     bench-strength score.
  • optimize       — team-optimization recommendations: hire,
                     promote, restructure, sunset.

Public API::

    from rcm_mc.management import (
        Executive, ManagementTeam,
        score_competencies, CompetencyScorecard,
        assess_big_five, BigFiveProfile,
        score_org_design, OrgDesignScore,
        aggregate_360_feedback, FeedbackAggregate,
        build_succession_register, SuccessionRegister,
        recommend_team_actions, TeamRecommendations,
    )
"""
from .executive import Executive, ManagementTeam, RaterRole
from .scorecard import (
    score_competencies,
    CompetencyScorecard,
    CompetencyScore,
)
from .personality import assess_big_five, BigFiveProfile
from .org_design import score_org_design, OrgDesignScore
from .feedback import (
    aggregate_360_feedback,
    FeedbackAggregate,
    RaterFeedback,
)
from .succession import (
    build_succession_register,
    SuccessionRegister,
    KeyPersonRisk,
)
from .optimize import (
    recommend_team_actions,
    TeamRecommendations,
    TeamAction,
)

__all__ = [
    "Executive", "ManagementTeam", "RaterRole",
    "score_competencies", "CompetencyScorecard", "CompetencyScore",
    "assess_big_five", "BigFiveProfile",
    "score_org_design", "OrgDesignScore",
    "aggregate_360_feedback", "FeedbackAggregate",
    "RaterFeedback",
    "build_succession_register", "SuccessionRegister",
    "KeyPersonRisk",
    "recommend_team_actions", "TeamRecommendations", "TeamAction",
]
