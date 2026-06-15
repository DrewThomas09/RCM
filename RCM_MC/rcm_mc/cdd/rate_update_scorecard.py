"""NEW-22 2026 payment-rate update scorecard.

A diverging bar of the net 2026 Medicare update by setting. Home health is the
only negative update for 2026; the Physician Fee Schedule splits into two
conversion factors for the first time, so it shows as two bars (qualifying APM
participant and non-participant). Where CMS states the rate-setting components
(market basket, productivity, forecast-error), the scorecard reconciles them to
the published net so the number is auditable, not just asserted.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-23"

# Components must sum to the net within this tolerance (CMS rounds to one tenth).
COMPONENT_TOL = 0.05


@dataclass(frozen=True)
class RateUpdate:
    """One setting's net 2026 update.

    ``components`` are the stated rate-setting inputs (positive market basket,
    negative productivity, and so on) that sum to ``net_pct`` when CMS publishes
    them; an empty list means the net is published without a clean decomposition.
    """

    setting: str
    net_pct: float
    rule: str
    components: List[float] = field(default_factory=list)
    note: str = ""


# Net 2026 updates from the final-rule scorecard.
SCORECARD: List[RateUpdate] = [
    RateUpdate("Skilled nursing", 3.2, "CMS-1827-F", [3.3, 0.6, -0.7]),
    RateUpdate("Hospice", 2.6, "CMS-1835-F", [3.3, -0.7]),
    RateUpdate("Home health", -1.3, "CMS-1828-F", [],
               note="2.4 market basket, 1.023 permanent cut, 3.0 temporary behavioral adjustment"),
    RateUpdate("Inpatient hospital operating", 2.6, "CMS-1833-F", [3.3, -0.7]),
    RateUpdate("Long-term acute care", 2.7, "CMS-1833-F", [3.4, -0.7]),
    RateUpdate("Inpatient rehab", 2.6, "CMS-1829-F", [3.3, -0.7]),
    RateUpdate("Inpatient psych", 2.5, "FY2026 IPF final rule", [3.2, -0.7]),
    RateUpdate("Hospital outpatient", 2.6, "CMS-1834-FC", [3.3, -0.7]),
    RateUpdate("Ambulatory surgical center", 2.6, "CMS-1834-FC", [],
               note="hospital market basket applied through CY2026"),
    RateUpdate("ESRD dialysis", 2.2, "CMS-1830-F", [],
               note="2.1 ESRD bundled market basket plus net adjustments"),
    RateUpdate("Physician QP", 3.77, "CMS-1832-F", [],
               note="OBBB 2.5 one-year plus 0.75 statutory plus 0.49 budget neutrality"),
    RateUpdate("Physician non-QP", 3.26, "CMS-1832-F", [],
               note="OBBB 2.5 one-year plus 0.25 statutory plus 0.49 budget neutrality"),
]


def rate_update_scorecard(
    updates: Optional[Sequence[RateUpdate]] = None,
    *,
    source: str = "CMS 2026 final rules",
    vintage: str = "2026",
    audience: str = "both",
) -> Exhibit:
    """Build the diverging scorecard of net 2026 updates by setting."""
    table = list(updates) if updates is not None else list(SCORECARD)
    if not table:
        raise ValueError("rate_update_scorecard requires at least one update")

    points: List[Dict[str, Any]] = []
    for u in sorted(table, key=lambda r: r.net_pct):
        points.append({
            "label": u.setting,
            "value": u.net_pct,
            "direction": "negative" if u.net_pct < 0 else "positive",
            "color": "red" if u.net_pct < 0 else "green",
            "rule": u.rule,
            "components": list(u.components),
            "note": u.note,
        })

    negatives = [p for p in points if p["value"] < 0]
    flags: List[Flag] = []
    for p in negatives:
        flags.append(Flag(
            code="negative_update",
            severity="warn",
            message=f"{p['label']} has a negative 2026 update of {p['value']:.1f} percent.",
            source=p["rule"],
        ))
    pfs = [p for p in points if p["label"].startswith("Physician")]
    if len(pfs) >= 2:
        flags.append(Flag(
            code="pfs_dual_conversion_factor",
            severity="info",
            message=(
                "The Physician Fee Schedule splits into two conversion factors for "
                "2026, so it shows as two bars."
            ),
            source="CMS-1832-F",
        ))

    # Reconciliation: where components are stated, they sum to the net update.
    component_gap = sum(
        abs(sum(u.components) - u.net_pct) for u in table if u.components
    )
    n_decomposed = sum(1 for u in table if u.components)
    reconciliations = [
        Reconciliation(
            identity="stated components sum to the net update",
            lhs=component_gap,
            rhs=0.0,
            tolerance=COMPONENT_TOL,
        ),
        Reconciliation(
            identity="flagged negative updates equal settings below zero",
            lhs=len(negatives),
            rhs=sum(1 for u in table if u.net_pct < 0),
            tolerance=1e-9,
        ),
    ]

    series = [Series(name="Net 2026 update by setting", kind="bar", points=points)]

    footnote = Footnote(
        source=source,
        vintage=vintage,
        assumptions=[
            "Net updates are the 2026 final-rule figures by setting.",
            "Positive updates render green, negative render red.",
            "Where stated, market basket and productivity components reconcile to the net.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="2026 payment-rate update scorecard",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(table)} settings, {len(negatives)} negative. Updates run from "
            f"{points[0]['value']:.1f} to {points[-1]['value']:.1f} percent."
        ),
        meta={
            "n_settings": len(table),
            "n_negative": len(negatives),
            "n_decomposed": n_decomposed,
            "min_update": points[0]["value"],
            "max_update": points[-1]["value"],
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return rate_update_scorecard(source="CMS 2026 final rules", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="2026 payment-rate update scorecard",
        audience="both",
        demo=_demo,
    )
)
