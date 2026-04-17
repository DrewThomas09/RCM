"""SeekingChartis Composite Score: 0-100 rating for any hospital.

Combines market position (35%), financial health (25%), operational
quality (20%), and competitive moat (20%) into a single investability
score. Every hospital in HCRIS gets a score.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class ChartisScore:
    ccn: str
    name: str
    score: int
    grade: str
    components: Dict[str, float]
    breakdown: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "name": self.name,
            "score": self.score,
            "grade": self.grade,
            "components": {k: round(v, 1) for k, v in self.components.items()},
            "breakdown": self.breakdown,
        }


def _grade(score: int) -> str:
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 80: return "A-"
    if score >= 75: return "B+"
    if score >= 70: return "B"
    if score >= 65: return "B-"
    if score >= 60: return "C+"
    if score >= 55: return "C"
    if score >= 50: return "C-"
    if score >= 40: return "D"
    return "F"


def compute_caduceus_score(
    profile: Dict[str, Any],
    market_data: Optional[Dict[str, Any]] = None,
) -> ChartisScore:
    """Compute the SeekingChartis score for a hospital."""
    ccn = str(profile.get("ccn") or profile.get("deal_id") or "")
    name = str(profile.get("name") or "")

    # Market Position (35 points max)
    market_score = 15.0
    breakdown = {}
    beds = float(profile.get("beds") or profile.get("bed_count") or 0)
    npr = float(profile.get("net_patient_revenue") or profile.get("net_revenue") or 0)

    if beds > 300:
        market_score += 10
        breakdown["beds"] = f"{int(beds)} beds (large, +10)"
    elif beds > 150:
        market_score += 5
        breakdown["beds"] = f"{int(beds)} beds (mid-size, +5)"
    else:
        breakdown["beds"] = f"{int(beds)} beds (small, +0)"

    if npr > 500e6:
        market_score += 10
        breakdown["revenue"] = f"${npr/1e6:.0f}M NPR (large, +10)"
    elif npr > 200e6:
        market_score += 5
        breakdown["revenue"] = f"${npr/1e6:.0f}M NPR (mid, +5)"
    else:
        breakdown["revenue"] = f"${npr/1e6:.0f}M NPR (small, +0)"

    market_score = min(market_score, 35)

    # Financial Health (25 points max)
    fin_score = 10.0
    opex = float(profile.get("operating_expenses") or 0)
    ni = float(profile.get("net_income") or 0)
    margin = (npr - opex) / npr if npr > 1e5 and opex > 0 else 0
    margin = max(-1.0, min(1.0, margin))

    if margin > 0.10:
        fin_score += 15
        breakdown["margin"] = f"{margin:.1%} margin (strong, +15)"
    elif margin > 0.05:
        fin_score += 8
        breakdown["margin"] = f"{margin:.1%} margin (moderate, +8)"
    elif margin > 0:
        fin_score += 3
        breakdown["margin"] = f"{margin:.1%} margin (thin, +3)"
    else:
        breakdown["margin"] = f"{margin:.1%} margin (negative, +0)"

    fin_score = min(fin_score, 25)

    # Operational Quality (20 points max)
    ops_score = 8.0
    denial_rate = float(profile.get("denial_rate") or 12)
    ar_days = float(profile.get("days_in_ar") or 50)

    if denial_rate < 8:
        ops_score += 8
        breakdown["denial"] = f"{denial_rate:.1f}% denial (excellent, +8)"
    elif denial_rate < 12:
        ops_score += 4
        breakdown["denial"] = f"{denial_rate:.1f}% denial (good, +4)"
    else:
        breakdown["denial"] = f"{denial_rate:.1f}% denial (high, +0)"

    if ar_days < 42:
        ops_score += 4
        breakdown["ar_days"] = f"{ar_days:.0f} AR days (excellent, +4)"
    elif ar_days < 50:
        ops_score += 2
        breakdown["ar_days"] = f"{ar_days:.0f} AR days (good, +2)"
    else:
        breakdown["ar_days"] = f"{ar_days:.0f} AR days (slow, +0)"

    ops_score = min(ops_score, 20)

    # Moat (20 points max)
    moat_score = 8.0
    if beds > 250:
        moat_score += 4
    if market_data and market_data.get("hhi_index", 0) < 2500:
        moat_score += 4
    if margin > 0.08:
        moat_score += 4
    moat_score = min(moat_score, 20)
    breakdown["moat"] = f"Moat score: {moat_score:.0f}/20"

    total = int(round(market_score + fin_score + ops_score + moat_score))
    total = max(0, min(100, total))

    return ChartisScore(
        ccn=ccn, name=name, score=total, grade=_grade(total),
        components={
            "market_position": market_score,
            "financial_health": fin_score,
            "operational_quality": ops_score,
            "competitive_moat": moat_score,
        },
        breakdown=breakdown,
    )


CaduceusScore = ChartisScore
