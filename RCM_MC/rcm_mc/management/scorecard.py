"""Competency scorecard — 8 healthcare-PE-relevant dimensions.

Each executive scores 0-5 on each dimension; the dimensions
weight differently by role (a CFO's financial-discipline
weight dominates; a COO's operational-execution weight does).
The result is a per-executive composite + a team-wide composite
that benchmarks against typical realized-deal performance bars.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .executive import Executive, ManagementTeam


# ── Dimensions + role-specific weights ──────────────────────────

DIMENSIONS = (
    "financial_discipline",
    "payer_relationships",
    "ma_integration",
    "talent_retention",
    "regulatory_compliance",
    "operational_execution",
    "strategic_clarity",
    "external_credibility",
)


# Per-role weight matrix. Rows must sum to 1.0.
_ROLE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "CEO": {
        "financial_discipline": 0.10,
        "payer_relationships": 0.10,
        "ma_integration": 0.15,
        "talent_retention": 0.15,
        "regulatory_compliance": 0.05,
        "operational_execution": 0.10,
        "strategic_clarity": 0.20,
        "external_credibility": 0.15,
    },
    "CFO": {
        "financial_discipline": 0.30,
        "payer_relationships": 0.05,
        "ma_integration": 0.15,
        "talent_retention": 0.10,
        "regulatory_compliance": 0.15,
        "operational_execution": 0.10,
        "strategic_clarity": 0.10,
        "external_credibility": 0.05,
    },
    "COO": {
        "financial_discipline": 0.10,
        "payer_relationships": 0.10,
        "ma_integration": 0.20,
        "talent_retention": 0.15,
        "regulatory_compliance": 0.10,
        "operational_execution": 0.25,
        "strategic_clarity": 0.05,
        "external_credibility": 0.05,
    },
    "CRO": {     # Chief Revenue / Compliance — for RCM platforms
        "financial_discipline": 0.15,
        "payer_relationships": 0.30,
        "ma_integration": 0.05,
        "talent_retention": 0.10,
        "regulatory_compliance": 0.20,
        "operational_execution": 0.10,
        "strategic_clarity": 0.05,
        "external_credibility": 0.05,
    },
    "DEFAULT": {
        "financial_discipline": 0.15,
        "payer_relationships": 0.10,
        "ma_integration": 0.10,
        "talent_retention": 0.15,
        "regulatory_compliance": 0.10,
        "operational_execution": 0.15,
        "strategic_clarity": 0.15,
        "external_credibility": 0.10,
    },
}


@dataclass
class CompetencyScore:
    """Per-executive composite + per-dimension scores."""
    person_id: str
    role: str
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    composite: float = 0.0
    band: str = "average"      # standout / above_avg / average /
                               # below_avg / concerning


@dataclass
class CompetencyScorecard:
    """Team-level scorecard."""
    team_composite: float
    team_band: str
    per_executive: List[CompetencyScore] = field(default_factory=list)
    weakest_dimension: str = ""
    strongest_dimension: str = ""


def _band_for_score(score: float) -> str:
    if score >= 4.5:
        return "standout"
    if score >= 4.0:
        return "above_avg"
    if score >= 3.0:
        return "average"
    if score >= 2.0:
        return "below_avg"
    return "concerning"


def score_competencies(
    team: ManagementTeam,
    raw_scores: Dict[str, Dict[str, float]],
) -> CompetencyScorecard:
    """Score the team's competencies.

    Args:
      raw_scores: {person_id → {dimension → score (0-5)}}.
        Missing dimensions default to 3.0 (average); missing
        executives skip.

    Returns CompetencyScorecard with per-exec composites,
    team-wide composite, and team-wide weakest/strongest
    dimension across executives.
    """
    per_exec: List[CompetencyScore] = []
    team_dim_totals: Dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    team_dim_counts: Dict[str, int] = {d: 0 for d in DIMENSIONS}

    for ex in team.executives:
        scores = raw_scores.get(ex.person_id, {})
        weights = _ROLE_WEIGHTS.get(ex.role, _ROLE_WEIGHTS["DEFAULT"])
        dim_scores: Dict[str, float] = {}
        composite = 0.0
        for d in DIMENSIONS:
            v = float(scores.get(d, 3.0))
            dim_scores[d] = round(v, 3)
            composite += v * weights[d]
            team_dim_totals[d] += v
            team_dim_counts[d] += 1
        per_exec.append(CompetencyScore(
            person_id=ex.person_id,
            role=ex.role,
            dimension_scores=dim_scores,
            composite=round(composite, 3),
            band=_band_for_score(composite),
        ))

    if not per_exec:
        return CompetencyScorecard(
            team_composite=0.0, team_band="average")

    team_composite = sum(p.composite for p in per_exec) / len(per_exec)
    team_dim_means = {
        d: (team_dim_totals[d] / team_dim_counts[d]
            if team_dim_counts[d] else 0.0)
        for d in DIMENSIONS
    }
    weakest = min(team_dim_means, key=team_dim_means.get)
    strongest = max(team_dim_means, key=team_dim_means.get)

    return CompetencyScorecard(
        team_composite=round(team_composite, 3),
        team_band=_band_for_score(team_composite),
        per_executive=per_exec,
        weakest_dimension=weakest,
        strongest_dimension=strongest,
    )
