"""Month-precision hold-period overlay for marquee corpus deals.

PEDESK Phase 3 (Week 3, Model Retraining) — Hold Analysis fix.

The shipped deal corpus stores ``hold_years`` as integer years
(e.g., HCA = 5.0, Steward = 14.0). At percentile-aggregation time
this produces clusters of identical values that collide on the
quartile grid — the partner-visible symptom is P25 = P50 = 4.0y,
which looks like a calculation error to anyone who knows hold
periods don't actually round to whole years.

This module overlays month-precision hold values, sourced from each
deal's public closing-date / exit-date pair (announcements,
SEC filings, and bankruptcy-court filings for restructured deals).
The overlay only covers the marquee transactions that are
publicly-anchored; the rest of the corpus retains its integer-year
precision and is flagged as such so the UI can show a "precision"
column without misrepresenting confidence.

When sub-month dates were not publicly disclosed, we picked
mid-month for the announcement / close / exit and rounded to one
decimal — the partner-visible precision is "tenth of a year"
(~37 days), which is appropriate given the source-document
granularity.
"""
from __future__ import annotations

from typing import Any, Dict, List


# source_id → (month-precision hold years, brief provenance)
HOLD_PRECISION_OVERLAY: Dict[str, Dict[str, Any]] = {
    "seed_001": {
        "hold_years": 4.4,
        "rationale": "KKR/Bain closed Nov 2006; re-IPO Mar 10 2011.",
    },
    "seed_002": {
        "hold_years": 9.1,
        "rationale": "Blackstone closed Sep 2004; sold to Tenet Oct 2013.",
    },
    "seed_003": {
        "hold_years": 13.3,
        "rationale": "TPG closed Jun 2004; sold to Steward Sep 29 2017.",
    },
    "seed_004": {
        "hold_years": 4.6,
        "rationale": "Warburg closed Feb 2005; re-IPO Sep 25 2009.",
    },
    "seed_007": {
        "hold_years": 4.6,
        "rationale": (
            "KKR closed Oct 11 2018; equity zero'd at Chapter 11 "
            "filing May 15 2023 — partner-visible hold ends at CH11."
        ),
    },
    "seed_013": {
        "hold_years": 13.5,
        "rationale": (
            "Cerberus closed Nov 2010 (Caritas Christi); 2020 SPAC "
            "IPO did not return capital; Chapter 11 filed May 6 2024."
        ),
    },
    "seed_014": {
        "hold_years": 5.4,
        "rationale": (
            "Apollo / GTCR closed Apr 2015 (RegionalCare + Capella "
            "merger); rolled into LifePoint merger Sep 2018."
        ),
    },
}


def apply_hold_precision(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a new list with ``hold_years`` overridden where overlay exists.

    Every deal also gets a ``hold_precision`` field — ``"month"`` when
    the overlay applied, ``"year"`` otherwise — so downstream renderers
    can label the precision honestly. The input list is not mutated.
    """
    out: List[Dict[str, Any]] = []
    for d in deals:
        sid = d.get("source_id")
        copy = dict(d)
        if sid and sid in HOLD_PRECISION_OVERLAY:
            entry = HOLD_PRECISION_OVERLAY[sid]
            copy["hold_years"] = float(entry["hold_years"])
            copy["hold_precision"] = "month"
            copy["hold_provenance"] = entry.get("rationale", "")
        else:
            copy.setdefault("hold_precision", "year")
        out.append(copy)
    return out


def hold_precision_summary(deals: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count how many deals carry month-precision vs year-precision hold.

    Used by the Hold Analysis page footer to put an honest precision
    figure in front of the partner ("X of Y deals carry month-precision
    hold; remainder are integer-year approximations").
    """
    summary = {"month": 0, "year": 0, "missing": 0}
    for d in deals:
        if d.get("hold_years") is None:
            summary["missing"] += 1
            continue
        prec = d.get("hold_precision") or "year"
        if prec == "month":
            summary["month"] += 1
        else:
            summary["year"] += 1
    return summary
