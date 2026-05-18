"""Phase-6 buyability model — final phase of the regression rebuild.

The user's original rebuild plan ended with:

    A hospital can have high revenue and low buyability.
    So your system should eventually produce two scores:
      - Financial profile score
      - Acquisition likelihood / buyability score
    Academic hospitals may be extremely informative for the first
    score but near-zero for the second.

This module is the second score. It answers \"is this hospital
realistically acquirable by a PE healthcare fund?\" — not \"is
this hospital financially interesting?\"

The two scores combine multiplicatively in
``target_attractiveness``:

    attractiveness = financial_opportunity × P(buyable) × strategic_fit

The buyability score is intentionally a **rule-based heuristic**
in v1, not a learned model. Why:
  - We have no labeled buyability data (\"this hospital was
    actually acquired vs declined\").
  - The dominant signals are categorical (ownership, system
    affiliation, segment label) and small in number — a learned
    model would overfit on a few hundred examples.
  - Partners need the score to be EXPLAINABLE — every score
    carries the reasons that drove it, not just a number.

When labeled data becomes available, swap this rule-based scorer
for a small classifier (logistic / GBT). The dataclass + scorer
signature is the boundary; the rest of the platform reads
``BuyabilityScore.score`` and doesn't care how it was computed.

DIAGNOSTIC SCOPE: this is the final phase of the rebuild but the
score is heuristic v1 — treat the *ordering* (academic centre vs
community hospital) as the reliable signal, and the *absolute
percentages* as a partner-friendly summary, not a precision claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ── Buyability priors by rule-based segment ─────────────────────
# Numbers reflect partner-articulated PE healthcare experience:
# Flagship Specialty / Academic / Children's are essentially
# never PE-acquirable (they're nonprofit, system-affiliated,
# politically sensitive). Community + CAH + Rehab + LTACH are the
# sweet spot. Public safety-net hospitals are mostly off the table.
# Numbers are NOT calibrated against a real label set — they're
# the partner's prior, encoded.
_SEGMENT_BUYABILITY: Dict[str, float] = {
    "Flagship Specialty":       0.02,
    "Academic":                 0.04,
    "Teaching":                 0.12,
    "Children's":               0.03,
    "Safety-Net Community":     0.18,
    "Critical Access":          0.35,
    "Psychiatric / Behavioral": 0.45,
    "LTACH":                    0.55,
    "Rehab":                    0.60,
    "Small Community":          0.65,
    "Large Community":          0.55,
    "Other":                    0.30,
}

# Curated list of large nonprofit / catholic / academic systems
# whose member hospitals are effectively unbuyable. Substring
# match against the hospital name. Penalty applied when matched.
_UNBUYABLE_SYSTEM_KEYWORDS: tuple[str, ...] = (
    "ASCENSION",
    "PROVIDENCE",
    "COMMONSPIRIT",
    "CHRISTUS",
    "DIGNITY HEALTH",
    "TRINITY HEALTH",
    "MERCY HEALTH",
    "SSM HEALTH",
    "KAISER",
    "VETERANS AFFAIRS",
    "VA MEDICAL CENTER",
    "U.S. DEPARTMENT OF",
    "DEPARTMENT OF DEFENSE",
    "INDIAN HEALTH SERVICE",
    "MILITARY HOSPITAL",
    "ARMY MEDICAL",
    "NAVAL HOSPITAL",
    "AIR FORCE",
    "CHILDREN'S HOSPITAL OF",  # large children's systems
    "MAYO CLINIC",
    "CLEVELAND CLINIC",
    "STANFORD",
    "JOHNS HOPKINS",
    "MD ANDERSON",
)


@dataclass(frozen=True)
class BuyabilityScore:
    """Per-hospital buyability classification.

    ``score`` is in ``[0, 1]``; partner-facing percentage.
    ``tier`` maps score to one of: very_low / low / medium / high.
    ``reasons`` is the human-readable list of signals that drove
    the score — partners can read \"Academic hospital + member of
    a large nonprofit system + 800 beds\" and immediately
    understand why the model says 4% rather than 60%.
    """
    score: float
    tier: str
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "tier": self.tier,
            "reasons": list(self.reasons),
        }


def _tier_from_score(s: float) -> str:
    if s >= 0.55:
        return "high"
    if s >= 0.30:
        return "medium"
    if s >= 0.15:
        return "low"
    return "very_low"


def score_buyability(row: Dict[str, Any]) -> BuyabilityScore:
    """Score a single hospital. ``row`` is a dict-like with the
    taxonomy columns from ``hospital_taxonomy.derive_taxonomy``
    (segment_label, safety_net_proxy_flag, etc.) plus the standard
    HCRIS columns (name, beds).

    Algorithm:
      1. Start with the segment-level prior.
      2. Penalize for unbuyable-system name matches.
      3. Adjust for bed-size sweet spot (50-400 beds favored).
      4. Apply per-flag adjustments (safety-net penalty,
         flagship-specialty penalty already in segment).
      5. Clamp to [0, 1], build the reason list, return.
    """
    segment = str(row.get("segment_label", "Other"))
    base = _SEGMENT_BUYABILITY.get(segment, 0.30)
    score = base
    reasons: List[str] = [
        f"Base prior for '{segment}': {base * 100:.0f}%"
    ]

    # Bed-size adjustment — PE sweet spot is mid-sized community
    # (50-400 beds). Very small CAHs and very large flagships
    # get an additional penalty.
    beds_raw = row.get("beds")
    try:
        beds = float(beds_raw) if beds_raw is not None else None
    except (TypeError, ValueError):
        beds = None
    if beds is not None and beds == beds:  # NaN check
        if beds < 25:
            score *= 0.75
            reasons.append("Very small bed count (<25) — limited "
                           "PE scale, -25%")
        elif beds > 600:
            score *= 0.50
            reasons.append("Flagship-scale bed count (>600) — "
                           "rarely PE-acquirable, -50%")
        elif 50 <= beds <= 400:
            score = min(1.0, score * 1.10)
            reasons.append("Mid-size sweet spot (50-400 beds), +10%")

    # Unbuyable-system name match
    name = str(row.get("name") or "").upper()
    matched_systems = [k for k in _UNBUYABLE_SYSTEM_KEYWORDS if k in name]
    if matched_systems:
        score *= 0.20
        reasons.append(
            f"Member of an unacquirable system "
            f"({matched_systems[0].title()}), -80%"
        )

    # Safety-net penalty (often government / public, hard to
    # acquire even when nominally community)
    if bool(row.get("safety_net_proxy_flag", False)):
        score *= 0.65
        reasons.append("Safety-net hospital (high Medicaid share) — "
                       "often public / government-owned, -35%")

    # Children's hospitals — almost never PE acquirable; the
    # segment label already captures this but reinforce
    if bool(row.get("children_flag", False)):
        score = min(score, 0.05)
        reasons.append("Children's hospital — almost never PE-"
                       "acquirable, capped at 5%")

    score = max(0.0, min(1.0, score))
    return BuyabilityScore(
        score=score,
        tier=_tier_from_score(score),
        reasons=reasons,
    )


def score_buyability_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ``score_buyability`` row-wise and return a new
    DataFrame with ``buyability_score`` and ``buyability_tier``
    columns appended. Original frame not mutated.

    ``df`` must carry the taxonomy columns (call
    ``hospital_taxonomy.derive_taxonomy`` first).
    """
    if "segment_label" not in df.columns:
        raise ValueError(
            "df is missing taxonomy columns. Call "
            "hospital_taxonomy.derive_taxonomy(df) first."
        )
    scores: List[float] = []
    tiers: List[str] = []
    for _, row in df.iterrows():
        result = score_buyability(row.to_dict())
        scores.append(result.score)
        tiers.append(result.tier)
    out = df.copy()
    out["buyability_score"] = scores
    out["buyability_tier"] = tiers
    return out


def target_attractiveness(
    financial_score: float,
    buyability_score: float,
    strategic_fit: float = 1.0,
) -> float:
    """Multiplicative combiner. Returns 0 if any input is 0.

    The default ``strategic_fit=1.0`` lets callers skip the third
    factor when there's no sector / fund-mandate signal. When the
    fund has a mandate (e.g. \"only PE acquisitions in the
    Northeast\"), the caller can plug in a 0-1 strategic_fit score.

    All inputs are clamped to ``[0, 1]`` before multiplication so
    a buggy financial_score doesn't blow the composite up.
    """
    f = max(0.0, min(1.0, float(financial_score)))
    b = max(0.0, min(1.0, float(buyability_score)))
    s = max(0.0, min(1.0, float(strategic_fit)))
    return f * b * s


def attractiveness_tier(att: float) -> str:
    """Map attractiveness score to a partner-readable tier."""
    if att >= 0.30:
        return "pursue"
    if att >= 0.15:
        return "investigate"
    if att >= 0.05:
        return "monitor"
    return "skip"


# ── Distribution summary helpers used by the UI panel ──────────


@dataclass(frozen=True)
class BuyabilityDistribution:
    """Aggregate distribution of buyability scores across a frame —
    used by the UI Buyability Lens panel to show partners the
    rough shape of the corpus.

    ``tier_counts``: { tier_name: count_of_hospitals }
    ``mean_score``: arithmetic mean across all rows
    ``median_score``: median across all rows
    ``segment_means``: { segment_label: mean buyability for that
      segment } — confirms academic segments score near zero,
      community/CAH near the top.
    """
    n: int
    mean_score: float
    median_score: float
    tier_counts: Dict[str, int]
    segment_means: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "mean_score": round(self.mean_score, 4),
            "median_score": round(self.median_score, 4),
            "tier_counts": dict(self.tier_counts),
            "segment_means": {
                k: round(v, 4) for k, v in self.segment_means.items()
            },
        }


def summarize_distribution(df: pd.DataFrame) -> BuyabilityDistribution:
    """Build a buyability distribution summary from a frame that
    already has ``buyability_score`` and ``buyability_tier``
    columns (call ``score_buyability_batch`` first).
    """
    if "buyability_score" not in df.columns:
        raise ValueError(
            "frame missing buyability_score. Call "
            "score_buyability_batch(df) first."
        )
    n = len(df)
    if n == 0:
        return BuyabilityDistribution(
            n=0, mean_score=0.0, median_score=0.0,
            tier_counts={}, segment_means={},
        )
    scores = df["buyability_score"].astype(float)
    tier_counts = (
        df["buyability_tier"].value_counts().to_dict()
    )
    # Segment means (rounded for partner display)
    segment_means: Dict[str, float] = {}
    if "segment_label" in df.columns:
        grouped = df.groupby("segment_label")["buyability_score"]
        segment_means = {
            str(seg): float(mean)
            for seg, mean in grouped.mean().items()
        }
    return BuyabilityDistribution(
        n=n,
        mean_score=float(scores.mean()),
        median_score=float(scores.median()),
        tier_counts={str(k): int(v) for k, v in tier_counts.items()},
        segment_means=segment_means,
    )
