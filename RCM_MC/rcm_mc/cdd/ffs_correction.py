"""NEW-13 FFS-to-all-population correction.

Many CMS metrics are fee-for-service only. Where Medicare Advantage penetration
is high, an FFS-only count understates true all-population activity. This module
grosses FFS activity up to the whole Medicare population using each county's MA
penetration: the per-county weight is 1 / (1 - MA_penetration), made explicit on
every row. Counties where FFS materially understates activity are flagged.
National MA penetration anchor: roughly 55 percent in 2026, far higher in some
counties.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-13"
NATIONAL_MA_PENETRATION_2026 = 0.55
HIGH_MA_THRESHOLD = 0.40


def ffs_to_all_population(
    counties: Sequence[Mapping[str, Any]],
    *,
    high_ma_threshold: float = HIGH_MA_THRESHOLD,
    source: str = "CMS FFS metric plus MA penetration",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Gross FFS-only activity up to all-population using MA penetration.

    ``counties``: records of {fips, ffs_activity, ma_penetration}.
    """
    if not counties:
        raise ValueError("ffs_to_all_population requires at least one county")

    flags: List[Flag] = []
    rows: List[Dict[str, Any]] = []
    total_ffs = 0.0
    total_corrected = 0.0
    high_ma_counties: List[str] = []

    for c in counties:
        fips = str(c["fips"])
        ffs = float(c["ffs_activity"])
        ma = float(c["ma_penetration"])
        if not (0.0 <= ma < 1.0):
            if ma >= 1.0:
                flags.append(Flag(
                    code="ma_penetration_at_100pct",
                    severity="warn",
                    message=f"County {fips} reports 100 percent MA penetration; correction is undefined.",
                ))
                rows.append({"fips": fips, "ffs_activity": ffs, "ma_penetration": ma,
                             "weight": None, "corrected_activity": None, "uncomputable": True})
                continue
            raise ValueError(f"county {fips}: ma_penetration must be in [0, 1)")

        ffs_share = 1.0 - ma
        weight = safe_div(1.0, ffs_share, default=0.0)
        corrected = ffs * weight
        understatement = corrected - ffs
        rows.append({
            "fips": fips,
            "ffs_activity": ffs,
            "ma_penetration": ma,
            "ffs_share": ffs_share,
            "weight": weight,
            "corrected_activity": corrected,
            "understatement": understatement,
        })
        total_ffs += ffs
        total_corrected += corrected
        if ma >= high_ma_threshold:
            high_ma_counties.append(fips)

    if high_ma_counties:
        flags.append(Flag(
            code="high_ma_understatement",
            severity="warn",
            message=(
                f"{len(high_ma_counties)} county(ies) above {high_ma_threshold*100:.0f} "
                "percent MA penetration where FFS-only materially understates activity."
            ),
            source=source,
        ))

    # Reconcile: total corrected equals sum of per-county corrected estimates.
    recomputed = sum(r["corrected_activity"] for r in rows if r.get("corrected_activity") is not None)
    reconciliations = [
        Reconciliation(
            identity="total corrected equals sum of per-county corrected",
            lhs=total_corrected,
            rhs=recomputed,
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="FFS vs all-population activity", kind="bar", points=[
            {"label": r["fips"], "ffs": r["ffs_activity"], "value": r.get("corrected_activity")}
            for r in rows
        ]),
        Series(name="Per-county correction weight", kind="bar", internal_only=True, points=[
            {"label": r["fips"], "value": r.get("weight")} for r in rows
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "All-population activity = FFS activity divided by FFS share, where FFS share is 1 minus MA penetration.",
            "Assumes MA beneficiaries have a similar per-capita rate to FFS beneficiaries.",
            f"National MA penetration anchor is about {NATIONAL_MA_PENETRATION_2026*100:.0f} percent in 2026.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="FFS to all-population correction",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(rows)} county(ies). FFS total {total_ffs:,.0f} corrects to "
            f"{total_corrected:,.0f} all-population."
        ),
        meta={
            "rows": rows,
            "total_ffs": total_ffs,
            "total_corrected": total_corrected,
            "high_ma_counties": high_ma_counties,
            "national_ma_anchor": NATIONAL_MA_PENETRATION_2026,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    counties = [
        {"fips": "06037", "ffs_activity": 1000, "ma_penetration": 0.50},
        {"fips": "48201", "ffs_activity": 1000, "ma_penetration": 0.20},
    ]
    return ffs_to_all_population(counties, source="Demo FFS metric", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="FFS-to-all-population correction",
        audience="both",
        demo=_demo,
    )
)
