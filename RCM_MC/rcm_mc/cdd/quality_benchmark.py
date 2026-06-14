"""NEW-14 Quality / outcomes benchmarking.

Benchmarks a target hospital against a peer set and the national value across
Care Compare measures (mortality, readmission, PSI-90, HAIs, HCAHPS, star
rating), joined on CCN. Computes a directional percentile rank where 100 is best
regardless of whether higher or lower is better, and flags bottom-quartile
measures as operational risk. Measures suppressed for small hospitals are
excluded and flagged.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-14"
BOTTOM_QUARTILE = 25.0


def _percentile_rank(target: float, peers: Sequence[float], higher_is_better: bool) -> float:
    """Fraction of peers the target beats, in percent. 100 means best."""
    n = len(peers)
    if n == 0:
        return float("nan")
    if higher_is_better:
        beaten = sum(1 for p in peers if p < target)
    else:
        beaten = sum(1 for p in peers if p > target)
    return safe_div(beaten, n) * 100.0


def quality_benchmark(
    target_ccn: str,
    measures: Sequence[Mapping[str, Any]],
    *,
    source: str = "CMS Care Compare / Provider Data Catalog",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Percentile-rank a target across measures vs peers and national.

    ``measures``: records of {measure, target, peers:[...], direction:
    'higher'|'lower', national (optional), suppressed (optional bool)}.
    """
    if not measures:
        raise ValueError("quality_benchmark requires at least one measure")

    flags: List[Flag] = []
    rows: List[Dict[str, Any]] = []
    suppressed: List[str] = []

    for m in measures:
        name = str(m["measure"])
        direction = str(m.get("direction", "higher")).lower()
        if direction not in {"higher", "lower"}:
            raise ValueError(f"measure {name}: direction must be 'higher' or 'lower'")
        higher = direction == "higher"
        if m.get("suppressed"):
            suppressed.append(name)
            rows.append({"measure": name, "suppressed": True, "percentile": None})
            continue
        target = float(m["target"])
        peers = [float(p) for p in m["peers"]]
        pct = _percentile_rank(target, peers, higher)
        national = m.get("national")
        vs_national = None
        if national is not None:
            national = float(national)
            better_than_national = (target > national) if higher else (target < national)
            vs_national = "above" if better_than_national else "below"
        row = {
            "measure": name,
            "direction": direction,
            "target": target,
            "percentile": pct,
            "national": national,
            "vs_national": vs_national,
            "bottom_quartile": pct < BOTTOM_QUARTILE,
            "suppressed": False,
        }
        rows.append(row)
        if pct < BOTTOM_QUARTILE:
            flags.append(Flag(
                code="bottom_quartile_measure",
                severity="risk",
                message=(
                    f"{name} is at the {pct:.0f}th percentile versus peers, "
                    "bottom quartile and an operational risk."
                ),
                source=source,
            ))

    if suppressed:
        flags.append(Flag(
            code="measures_suppressed",
            severity="info",
            message=f"{len(suppressed)} measure(s) suppressed for a small hospital and excluded.",
        ))

    scored = [r for r in rows if not r["suppressed"]]
    in_range = all(0.0 <= r["percentile"] <= 100.0 for r in scored)
    reconciliations = [
        Reconciliation(identity="all percentiles in [0, 100]",
                       lhs=1.0 if in_range else 0.0, rhs=1.0, tolerance=1e-9),
    ]

    series = [
        Series(name="Percentile rank by measure", kind="bar", points=[
            {"label": r["measure"], "value": r["percentile"]} for r in scored
        ]),
        Series(name="Target vs national detail", kind="bar", internal_only=True, points=[
            {"label": r["measure"], "target": r["target"], "national": r["national"],
             "vs_national": r["vs_national"]} for r in scored
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Percentile rank is the share of peers the target beats, where 100 is best.",
            "Direction per measure sets whether higher or lower is better.",
            "Measures suppressed for small hospitals are excluded.",
        ],
    )

    bottom = [r["measure"] for r in scored if r["bottom_quartile"]]
    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Quality and outcomes benchmarking",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"CCN {target_ccn}: {len(scored)} measure(s) scored, "
            f"{len(bottom)} in the bottom quartile."
        ),
        meta={
            "target_ccn": target_ccn,
            "rows": rows,
            "bottom_quartile_measures": bottom,
            "suppressed_measures": suppressed,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    measures = [
        {"measure": "Readmission", "direction": "lower", "target": 15, "peers": [10, 12, 14, 16, 18], "national": 14},
        {"measure": "Mortality", "direction": "lower", "target": 20, "peers": [5, 8, 10, 12, 15], "national": 10},
        {"measure": "HCAHPS", "direction": "higher", "target": 90, "peers": [70, 75, 80, 85, 88], "national": 82},
        {"measure": "PSI-90", "direction": "lower", "suppressed": True},
    ]
    return quality_benchmark("123456", measures, source="Demo Care Compare", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Quality / outcomes benchmarking",
        audience="both",
        demo=_demo,
    )
)
