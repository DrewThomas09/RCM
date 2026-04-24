"""Earnout advisor — provider-retention structure recommendation.

Extends the existing earnout advisor with provider-retention logic.
When top-5 provider concentration crosses thresholds, specific
earnout structures align the seller's personal incentive with the
acquisition thesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .comp_ingester import Provider


@dataclass
class EarnoutRecommendation:
    top5_concentration_pct: float
    recommended_structure: str      # RETENTION_BOND | WRVU_BASED |
                                     # COLLECTIONS_BASED | HYBRID
    rationale: str
    attach_to_top_n: int
    hold_period_years: int
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top5_concentration_pct": self.top5_concentration_pct,
            "recommended_structure": self.recommended_structure,
            "rationale": self.rationale,
            "attach_to_top_n": self.attach_to_top_n,
            "hold_period_years": self.hold_period_years,
            "notes": list(self.notes),
        }


def recommend_earnout_structure(
    providers: Iterable[Provider],
    *,
    hold_period_years: int = 3,
) -> EarnoutRecommendation:
    """Recommend an earnout structure based on concentration risk.

    Thresholds:
        top5 > 40% of collections → RETENTION_BOND (pay-to-stay)
        top5 25-40%                → HYBRID (retention + wRVU)
        top5 < 25%                 → WRVU_BASED (standard)

    Rationale: when a handful of providers carry the platform's
    collections, the earnout's downside risk is concentrated in
    their decision to stay. A retention-bond structure pays them
    to stay post-close regardless of the comp model friction;
    wRVU-based earnouts only reward volume, which doesn't
    compensate for departure-risk."""
    plist = list(providers)
    collections = sorted(
        (float(p.collections_annual_usd or 0.0) for p in plist),
        reverse=True,
    )
    total = sum(collections) or 1.0
    top5 = sum(collections[:5]) / total

    notes: List[str] = []
    if top5 >= 0.40:
        structure = "RETENTION_BOND"
        rationale = (
            f"Top-5 providers control {top5*100:.1f}% of collections. "
            f"Earnout structures based on wRVU or collections fail "
            f"when the key providers depart — a retention-bond "
            f"payout keyed to their post-close tenure is the only "
            f"instrument that aligns sellers with the thesis."
        )
        n = 5
        notes.append(
            "Pair with non-compete (state-law-permitting) + restrictive "
            "covenant carve-outs in the BLAs."
        )
    elif top5 >= 0.25:
        structure = "HYBRID"
        rationale = (
            f"Top-5 concentration {top5*100:.1f}% — material but not "
            f"extreme. Hybrid: 60% retention-bond on top 3 + 40% wRVU-"
            f"based on the rest."
        )
        n = 3
    else:
        structure = "WRVU_BASED"
        rationale = (
            f"Top-5 concentration {top5*100:.1f}% — well-diversified "
            f"roster. Standard wRVU-based earnout aligns incentives "
            f"without retention-bond overhead."
        )
        n = 0
        notes.append(
            "Quality-gate scalar recommended on the wRVU formula to "
            "prevent post-close volume-gaming (see Gap 6 quality "
            "module)."
        )

    return EarnoutRecommendation(
        top5_concentration_pct=top5,
        recommended_structure=structure,
        rationale=rationale,
        attach_to_top_n=n,
        hold_period_years=hold_period_years,
        notes=notes,
    )
