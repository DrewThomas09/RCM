"""NEW-09 Site-of-care shift analysis.

Use-per-1,000 by care setting (inpatient, hospital outpatient, ASC, office,
home) across two periods, with named migration metrics: hospital outpatient to
ASC, inpatient to outpatient, and facility to home. An optional changepoint
overlay (ruptures, see BOLSTER-03) flags an inflection in a per-setting trend.
The CY2026 OPPS and ASC payment context ships as an internal-only note.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-09"

SETTINGS = ["IP", "HOPD", "ASC", "Office", "Home"]
OUTPATIENT = {"HOPD", "ASC", "Office"}
FACILITY = {"IP", "HOPD"}

CY2026_NOTE = (
    "CY2026 OPPS and ASC final rule continues the outpatient and ASC payment "
    "updates and the inpatient-only list reductions that push volume from "
    "inpatient and hospital outpatient toward ASC and the home."
)


def _rate(value: float, population: Optional[float]) -> float:
    if population:
        return safe_div(value, population) * 1000.0
    return float(value)


def site_of_care_shift(
    period1: Mapping[str, float],
    period2: Mapping[str, float],
    *,
    population1: Optional[float] = None,
    population2: Optional[float] = None,
    trend_by_setting: Optional[Mapping[str, Sequence[float]]] = None,
    source: str = "Medicare Geographic Variation",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Two-period use-per-1,000 by setting plus named migration metrics."""
    if not period1 or not period2:
        raise ValueError("site_of_care_shift requires two non-empty periods")

    settings = [s for s in SETTINGS if s in period1 or s in period2]
    r1 = {s: _rate(float(period1.get(s, 0.0)), population1) for s in settings}
    r2 = {s: _rate(float(period2.get(s, 0.0)), population2) for s in settings}
    deltas = {s: r2[s] - r1[s] for s in settings}

    d = lambda s: deltas.get(s, 0.0)  # noqa: E731
    migrations = {
        "hopd_to_asc": min(max(-d("HOPD"), 0.0), max(d("ASC"), 0.0)),
        "ip_to_outpatient": max(-d("IP"), 0.0),
        "facility_to_home": max(d("Home"), 0.0),
        "outpatient_net": sum(d(s) for s in OUTPATIENT if s in settings),
        "facility_net": sum(d(s) for s in FACILITY if s in settings),
    }

    flags: List[Flag] = []
    if migrations["hopd_to_asc"] > 0:
        flags.append(Flag(
            code="hopd_to_asc_migration",
            severity="info",
            message=(
                f"Volume migrated from hospital outpatient to ASC: "
                f"{migrations['hopd_to_asc']:.1f} per 1,000."
            ),
            source=source,
        ))
    if migrations["facility_to_home"] > 0:
        flags.append(Flag(
            code="facility_to_home_migration",
            severity="info",
            message=f"Home-setting use rose {migrations['facility_to_home']:.1f} per 1,000.",
            source=source,
        ))

    # Optional changepoint overlay via the BOLSTER-03 detector if a trend is given.
    changepoints: Dict[str, Any] = {}
    if trend_by_setting:
        try:
            from .changepoint import detect_changepoints
            for s, vals in trend_by_setting.items():
                cps = detect_changepoints(list(vals), source=source, vintage=vintage)
                changepoints[s] = cps.meta.get("changepoints", [])
        except Exception:  # noqa: BLE001 - overlay is best-effort
            changepoints = {}

    reconciliations = [
        Reconciliation(
            identity="per-setting deltas equal period2 rate minus period1 rate",
            lhs=sum(deltas.values()),
            rhs=sum(r2.values()) - sum(r1.values()),
            tolerance=1e-9,
        )
    ]

    series = [
        Series(name="Use per 1,000 by setting", kind="line",
               points=[{"label": s, "period1": r1[s], "period2": r2[s]} for s in settings]),
        Series(name="Setting shift (delta per 1,000)", kind="bar",
               points=[{"label": s, "value": deltas[s]} for s in settings]),
        Series(name="CY2026 OPPS/ASC context", kind="bar", internal_only=True,
               points=[{"label": "context", "note": CY2026_NOTE}]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Rates are use per 1,000 beneficiaries by care setting.",
            "Migration metrics are derived from the period-over-period rate deltas.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Site-of-care shift",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Outpatient net {migrations['outpatient_net']:+.1f}, facility net "
            f"{migrations['facility_net']:+.1f} per 1,000."
        ),
        meta={
            "rate1": r1,
            "rate2": r2,
            "deltas": deltas,
            "migrations": migrations,
            "changepoints": changepoints,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    p1 = {"IP": 100, "HOPD": 200, "ASC": 50, "Office": 300, "Home": 20}
    p2 = {"IP": 90, "HOPD": 170, "ASC": 90, "Office": 300, "Home": 30}
    return site_of_care_shift(p1, p2, source="Demo GV PUF", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Site-of-care shift analysis",
        audience="both",
        demo=_demo,
    )
)
