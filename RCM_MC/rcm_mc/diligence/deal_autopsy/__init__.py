"""Deal Autopsy — "You're about to do Steward again."

A library of historical PE healthcare deals (bankruptcies, distressed
sales, and strong exits) with each deal reduced to a 9-dimension
risk signature. Given a target's signature (built from the CCD +
metadata), rank the historical library by similarity and surface
the closest matches with their outcomes + partner lessons.

Why this is a moat:
    Chartis/VMG/A&M produce descriptive diligence reports. They do
    not say "this looks 74% like Steward Health Care 2016". Nobody
    maintains a curated, signature-matched library of healthcare PE
    failures because they don't have a consistent 9-dimensional
    lens. We do (built from CCD + counterfactual + Steward Score +
    V28 + cyber outputs).

The MD demo moment: dragging a target through the tool surfaces
"74% signature match to Steward (Cerberus, 2010). That deal went
bankrupt in 2024. Here are the three features where your target
matches Steward and the two where it diverges." Then a named
risk section flows straight into the IC Packet walkaway memo.

Public API::

    from rcm_mc.diligence.deal_autopsy import (
        DealAutopsy, DealSignature, HistoricalDeal, MatchResult,
        OUTCOME_BANKRUPTCY, OUTCOME_STRONG_EXIT,
        historical_library, match_target, signature_from_ccd,
    )
"""
from __future__ import annotations

from .library import (
    DealAutopsy, HistoricalDeal, OUTCOMES,
    OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE, OUTCOME_DELISTED,
    OUTCOME_STRONG_EXIT, OUTCOME_STRONG_PUBLIC,
    historical_library,
)
from .matcher import (
    DealSignature, FEATURE_NAMES, MatchResult,
    match_target, signature_distance, signature_from_ccd,
)

__all__ = [
    "DealAutopsy",
    "DealSignature",
    "FEATURE_NAMES",
    "HistoricalDeal",
    "MatchResult",
    "OUTCOMES",
    "OUTCOME_BANKRUPTCY",
    "OUTCOME_CHAPTER_11",
    "OUTCOME_DELISTED",
    "OUTCOME_DISTRESSED_SALE",
    "OUTCOME_STRONG_EXIT",
    "OUTCOME_STRONG_PUBLIC",
    "historical_library",
    "match_target",
    "signature_distance",
    "signature_from_ccd",
]
