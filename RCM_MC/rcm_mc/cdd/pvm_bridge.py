"""NEW-02 Growth bridge: price-volume-mix waterfall.

Symmetric (Bennet-indicator) decomposition of a two-period revenue change for
revenue = sum over lines of volume times price. The decomposition is exactly
additive (volume + price + mix + new/lost == total change) and reversal
consistent (swapping period 1 and 2 negates every component). Both properties
hold to machine precision, not approximately.

Math, for lines present in both periods (continuing lines):
    price  = sum_i  (p2_i - p1_i) * (q1_i + q2_i)/2
    volume = dQ     * sum_i (p1_i+p2_i)/2 * (s1_i+s2_i)/2
    mix    = Qavg   * sum_i (p1_i+p2_i)/2 * (s2_i - s1_i)
where s_i is line i's share of total volume, dQ = Q2 - Q1, Qavg = (Q1+Q2)/2.
Lines present in only one period go to a new/lost bucket at full revenue, so the
continuing-line PVM never has to invent a missing price.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-02"
TOL = 1e-6

# IBCS-style waterfall convention.
COLOR_POS = "green"
COLOR_NEG = "red"
COLOR_TOTAL = "blue"


def _index_period(rows: Sequence[Dict[str, Any]], period: Any) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for r in rows:
        if r["period"] != period:
            continue
        line = str(r["line"])
        vol = float(r["volume"])
        price = float(r["price"])
        if line in out:
            raise ValueError(f"duplicate line {line} in period {period}")
        out[line] = (vol, price)
    return out


def pvm_bridge(
    rows: Sequence[Dict[str, Any]],
    *,
    period1: Any,
    period2: Any,
    source: str = "Target P&L by line",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Decompose revenue change between two periods into price, volume, mix.

    ``rows``: records of {period, line, volume, price}. ``period1`` is the base
    period, ``period2`` the comparison period.
    """
    p1 = _index_period(rows, period1)
    p2 = _index_period(rows, period2)
    if not p1 and not p2:
        raise ValueError("no rows for either period")

    lines = sorted(set(p1) | set(p2))
    continuing = [ln for ln in lines if ln in p1 and ln in p2]

    r1_total = sum(v * pr for v, pr in p1.values())
    r2_total = sum(v * pr for v, pr in p2.values())
    total_change = r2_total - r1_total

    # New / lost bucket: lines present in only one period, at full revenue.
    new_lost = 0.0
    for ln in lines:
        if ln in p2 and ln not in p1:
            new_lost += p2[ln][0] * p2[ln][1]
        elif ln in p1 and ln not in p2:
            new_lost -= p1[ln][0] * p1[ln][1]

    q1 = sum(p1[ln][0] for ln in continuing)
    q2 = sum(p2[ln][0] for ln in continuing)
    dq = q2 - q1
    q_avg = (q1 + q2) / 2.0

    price = 0.0
    volume = 0.0
    mix = 0.0
    for ln in continuing:
        v1, pr1 = p1[ln]
        v2, pr2 = p2[ln]
        qa = (v1 + v2) / 2.0
        pa = (pr1 + pr2) / 2.0
        s1 = safe_div(v1, q1)
        s2 = safe_div(v2, q2)
        s_avg = (s1 + s2) / 2.0
        price += (pr2 - pr1) * qa
        volume += dq * pa * s_avg
        mix += q_avg * pa * (s2 - s1)

    components = {"volume": volume, "price": price, "mix": mix, "new_lost": new_lost}
    recomposed = price + volume + mix + new_lost

    reconciliations = [
        Reconciliation(
            identity="volume + price + mix + new_lost == total_change",
            lhs=recomposed,
            rhs=total_change,
            tolerance=TOL,
        )
    ]

    flags: List[Flag] = []
    if not reconciliations[0].ok:
        flags.append(
            Flag(
                code="bridge_not_additive",
                severity="risk",
                message="PVM components did not sum to the total change. Check inputs.",
            )
        )

    # Waterfall ordered by magnitude, largest driver first. Drop a zero bucket.
    drivers = [(k, v) for k, v in components.items() if abs(v) > TOL]
    drivers.sort(key=lambda kv: abs(kv[1]), reverse=True)
    wf_points: List[Dict[str, Any]] = [
        {"label": "Period 1 revenue", "value": r1_total, "kind": "start", "color": COLOR_TOTAL}
    ]
    label_map = {"volume": "Volume", "price": "Price", "mix": "Mix", "new_lost": "New / lost lines"}
    for k, v in drivers:
        wf_points.append(
            {
                "label": label_map[k],
                "value": v,
                "kind": "delta",
                "color": COLOR_POS if v >= 0 else COLOR_NEG,
            }
        )
    wf_points.append(
        {"label": "Period 2 revenue", "value": r2_total, "kind": "end", "color": COLOR_TOTAL}
    )

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Symmetric Bennet decomposition: additive and reversal consistent to 1e-6.",
            "Lines present in only one period are bucketed as new or lost at full revenue.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Revenue bridge: price, volume, mix",
        audience=audience,
        series=[Series(name="PVM waterfall", kind="waterfall", points=wf_points)],
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Revenue moved {total_change:,.1f} from {r1_total:,.1f} to "
            f"{r2_total:,.1f}. Volume {volume:,.1f}, price {price:,.1f}, "
            f"mix {mix:,.1f}, new or lost {new_lost:,.1f}."
        ),
        meta={
            "r1": r1_total,
            "r2": r2_total,
            "total_change": total_change,
            "volume": volume,
            "price": price,
            "mix": mix,
            "new_lost": new_lost,
            "recomposed": recomposed,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    rows = [
        {"period": "FY24", "line": "A", "volume": 100, "price": 10.0},
        {"period": "FY24", "line": "B", "volume": 200, "price": 5.0},
        {"period": "FY24", "line": "C", "volume": 50, "price": 20.0},
        {"period": "FY25", "line": "A", "volume": 120, "price": 11.0},
        {"period": "FY25", "line": "B", "volume": 180, "price": 5.0},
        {"period": "FY25", "line": "C", "volume": 60, "price": 22.0},
    ]
    return pvm_bridge(rows, period1="FY24", period2="FY25",
                      source="Demo P&L", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Growth bridge / price-volume-mix waterfall",
        audience="both",
        demo=_demo,
    )
)
