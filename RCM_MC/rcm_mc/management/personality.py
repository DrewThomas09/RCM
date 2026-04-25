"""Big Five (OCEAN) personality assessment.

The Big Five is the standard psychometric framework with
established healthcare-leadership performance correlations:

  Conscientiousness        strongest predictor of CEO performance
                            (financial discipline, follow-through)
  Emotional stability       predicts retention + team cohesion
  Openness                  predicts innovation + transformation
                            success (matters most for VBC pivots,
                            tech-enabled platforms)
  Extraversion              predicts external-facing role
                            effectiveness (payer negotiation, LP
                            relations)
  Agreeableness             predicts team retention but inverse
                            to negotiation outcomes — too high is
                            actually a yellow flag for a CEO

Inputs are 0-5 scores per trait (assessment via Hogan, Korn
Ferry, etc.). We compute a role-specific "investable signal"
score that weights the traits per the published correlations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BigFiveProfile:
    """One executive's Big Five profile + investability score."""
    person_id: str
    role: str
    openness: float = 3.0
    conscientiousness: float = 3.0
    extraversion: float = 3.0
    agreeableness: float = 3.0
    emotional_stability: float = 3.0
    investability_score: float = 0.0
    notes: str = ""


# Role-specific OCEAN weights. C and ES dominate everywhere;
# E matters more for external-facing roles (CEO, CRO).
# Agreeableness is INVERSELY weighted for CEO/CRO (too agreeable
# loses on payer negotiations).
_TRAIT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "CEO": {
        "openness": 0.20, "conscientiousness": 0.25,
        "extraversion": 0.20, "agreeableness": -0.05,
        "emotional_stability": 0.25,
    },
    "CFO": {
        "openness": 0.05, "conscientiousness": 0.40,
        "extraversion": 0.05, "agreeableness": 0.10,
        "emotional_stability": 0.30,
    },
    "COO": {
        "openness": 0.10, "conscientiousness": 0.35,
        "extraversion": 0.15, "agreeableness": 0.10,
        "emotional_stability": 0.30,
    },
    "CRO": {
        "openness": 0.10, "conscientiousness": 0.20,
        "extraversion": 0.30, "agreeableness": -0.05,
        "emotional_stability": 0.25,
    },
    "DEFAULT": {
        "openness": 0.15, "conscientiousness": 0.30,
        "extraversion": 0.15, "agreeableness": 0.10,
        "emotional_stability": 0.30,
    },
}


def assess_big_five(
    person_id: str,
    role: str,
    *,
    openness: float = 3.0,
    conscientiousness: float = 3.0,
    extraversion: float = 3.0,
    agreeableness: float = 3.0,
    emotional_stability: float = 3.0,
) -> BigFiveProfile:
    """Compute the role-weighted investability score.

    Score ranges:
      ≥ 4.5  exceptional (top decile)
      4.0-4.5  strong
      3.5-4.0  acceptable
      < 3.5  concerning
    """
    weights = _TRAIT_WEIGHTS.get(role, _TRAIT_WEIGHTS["DEFAULT"])

    score = (
        openness * weights["openness"]
        + conscientiousness * weights["conscientiousness"]
        + extraversion * weights["extraversion"]
        + agreeableness * weights["agreeableness"]
        + emotional_stability * weights["emotional_stability"]
    )
    # Negative-weighted agreeableness can make the score go below
    # zero in extreme cases. Clamp to 0 and rescale so the typical
    # all-3.0 baseline produces ~3.0 score.
    # Sum of |weights| can be > 1 due to the negative agreeableness
    # weight; normalize by sum of weights to keep score on the
    # 0-5 scale.
    total_weight = sum(weights.values())
    if total_weight > 0:
        score = score / total_weight
    score = max(0.0, min(5.0, score))

    notes = ""
    if conscientiousness < 3.0 and role in ("CEO", "CFO", "COO"):
        notes = "Low conscientiousness on a senior role — concerning."
    elif role in ("CEO", "CRO") and agreeableness > 4.5:
        notes = (
            "Very high agreeableness — yellow flag for negotiation-"
            "intensive role.")
    elif emotional_stability < 2.5:
        notes = (
            "Low emotional stability — flight-risk + team-cohesion "
            "concern.")

    return BigFiveProfile(
        person_id=person_id,
        role=role,
        openness=openness,
        conscientiousness=conscientiousness,
        extraversion=extraversion,
        agreeableness=agreeableness,
        emotional_stability=emotional_stability,
        investability_score=round(score, 3),
        notes=notes,
    )
