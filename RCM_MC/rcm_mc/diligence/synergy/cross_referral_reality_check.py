"""Cross-referral reality check.

Sellers often claim cross-referral synergy between sister
practices. This module uses the referral-leakage data (Gap 5) to
reality-check the claim — how much cross-referral is actually
happening before the deal?
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class CrossReferralRealityCheck:
    claimed_cross_referral_usd: float
    actual_pre_close_cross_referral_usd: float
    realization_ratio: float            # actual / claimed
    credibility: str                    # HIGH | MEDIUM | LOW
    narrative: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def check_cross_referral_claim(
    *,
    claimed_cross_referral_usd: float,
    pre_close_referral_pairs: Iterable[Dict[str, Any]],
    sister_practice_ids: Iterable[str],
) -> CrossReferralRealityCheck:
    """Compare claimed cross-referral synergy to the actual pre-
    close flow between sister practices.

    Each ``pre_close_referral_pairs`` dict: {from, to, dollars_usd}.
    """
    sisters = {str(x) for x in sister_practice_ids}
    actual = 0.0
    for row in pre_close_referral_pairs:
        if (str(row.get("from")) in sisters
                and str(row.get("to")) in sisters):
            actual += float(row.get("dollars_usd", 0.0) or 0.0)
    claimed = float(claimed_cross_referral_usd or 0.0)
    ratio = (actual / claimed) if claimed > 0 else 0.0
    if ratio >= 0.75:
        credibility = "HIGH"
    elif ratio >= 0.30:
        credibility = "MEDIUM"
    else:
        credibility = "LOW"
    return CrossReferralRealityCheck(
        claimed_cross_referral_usd=claimed,
        actual_pre_close_cross_referral_usd=actual,
        realization_ratio=ratio,
        credibility=credibility,
        narrative=(
            f"Seller claims ${claimed:,.0f} cross-referral synergy. "
            f"Pre-close actual flow between sister practices: "
            f"${actual:,.0f} ({ratio:.0%} of claim). "
            f"Credibility: {credibility}."
        ),
    )
