"""NEW-24 Commercial-to-Medicare pricing multiplier.

The single most powerful cross-vertical benchmarking lever: apply RAND Round 5.1
relative-price ratios to any Medicare anchor to get a defensible commercial
estimate. Inpatient facility runs about 254 percent of Medicare, outpatient
facility 279 percent, professional services 184 percent, and ASC outpatient
procedures 171 percent. Each charted commercial estimate is the Medicare anchor
times the ratio, and the exhibit reconciles that product so the benchmark is
auditable.

RAND uses 2020 to 2022 claims and the AHA disputes its representativeness, so
the multiplier travels as a directional benchmark, not a settled price.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-24"

# RAND Round 5.1 commercial price as a percent of Medicare, by service type.
RAND_RATIOS: Dict[str, float] = {
    "inpatient facility": 254.0,
    "outpatient facility": 279.0,
    "professional": 184.0,
    "asc outpatient": 171.0,
    "hospital-administered drugs": 205.0,  # of ASP
}

# State spread of the all-service ratio.
STATE_LOW = ("Arkansas", 162.0)
STATE_HIGH = ("Florida", 346.0)
STATE_MEDIAN = 254.0


def commercial_multiplier(
    anchors: Sequence[Mapping[str, Any]],
    *,
    ratios: Optional[Mapping[str, float]] = None,
    source: str = "RAND Round 5.1 (RRA1144-2-v2), 2020 to 2022 claims",
    vintage: str = "2022",
    audience: str = "both",
) -> Exhibit:
    """Apply RAND ratios to Medicare anchors to estimate commercial prices.

    ``anchors``: records of {label, service_type, medicare_amount}. The service
    type keys into ``ratios`` (defaults to :data:`RAND_RATIOS`).
    """
    if not anchors:
        raise ValueError("commercial_multiplier requires at least one anchor")
    rate_table = dict(ratios) if ratios is not None else dict(RAND_RATIOS)

    points: List[Dict[str, Any]] = []
    flags: List[Flag] = []
    for a in anchors:
        label = str(a["label"])
        service = str(a["service_type"]).lower()
        medicare = float(a["medicare_amount"])
        ratio = rate_table.get(service)
        if ratio is None:
            flags.append(Flag(
                code="unknown_service_type",
                severity="warn",
                message=f"No RAND ratio for service type {service}. {label} not benchmarked.",
                source=source,
            ))
            continue
        commercial = medicare * ratio / 100.0
        points.append({
            "label": label,
            "service_type": service,
            "medicare": medicare,
            "ratio_pct": ratio,
            "commercial_estimate": commercial,
        })

    if not points:
        raise ValueError("no anchor matched a known service type")

    flags.append(Flag(
        code="benchmark_not_price",
        severity="info",
        message=(
            "RAND uses 2020 to 2022 claims and the AHA disputes representativeness. "
            "Use the multiplier as a directional benchmark."
        ),
        source=source,
    ))

    # Reconciliation: every commercial estimate is the Medicare anchor times the
    # ratio (aggregate gap is zero within floating tolerance).
    product_gap = sum(
        abs(p["commercial_estimate"] - p["medicare"] * p["ratio_pct"] / 100.0)
        for p in points
    )
    reconciliations = [
        Reconciliation(
            identity="commercial estimate equals Medicare times ratio",
            lhs=product_gap,
            rhs=0.0,
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="Commercial estimate by anchor", kind="bar", points=[
            {"label": p["label"], "value": p["commercial_estimate"],
             "medicare": p["medicare"], "ratio_pct": p["ratio_pct"]}
            for p in points
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage,
        assumptions=[
            "Commercial price is the Medicare anchor times the RAND relative-price ratio.",
            "Ratios: inpatient 254, outpatient 279, professional 184, ASC 171 percent.",
            f"State spread runs {STATE_LOW[1]:.0f} to {STATE_HIGH[1]:.0f} percent.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Commercial-to-Medicare pricing multiplier",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(points)} Medicare anchors repriced to commercial using RAND "
            "relative-price ratios."
        ),
        meta={
            "ratios": rate_table,
            "state_low": {"state": STATE_LOW[0], "pct": STATE_LOW[1]},
            "state_high": {"state": STATE_HIGH[0], "pct": STATE_HIGH[1]},
            "state_median": STATE_MEDIAN,
            "anchors": points,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Apply the ratios to four verified 2026 Medicare anchors from the spine.
    anchors = [
        {"label": "Inpatient hospital discharge", "service_type": "inpatient facility",
         "medicare_amount": 6752.61},
        {"label": "Hospital outpatient service", "service_type": "outpatient facility",
         "medicare_amount": 91.415},
        {"label": "Physician RVU", "service_type": "professional",
         "medicare_amount": 33.5675},
        {"label": "Ambulatory surgical center case", "service_type": "asc outpatient",
         "medicare_amount": 56.322},
    ]
    return commercial_multiplier(
        anchors,
        source="RAND Round 5.1 applied to CMS 2026 anchors",
        vintage="2022",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Commercial-to-Medicare pricing multiplier",
        audience="both",
        demo=_demo,
    )
)
