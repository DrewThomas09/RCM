"""Cross-Dataset Analysis — correlate any two state-grain public datasets.

The Further Analysis explorer charts one dataset at a time. This adds the
analytical layer on top: pick a measure from dataset X and a measure from
dataset Y, join them on the US state they share, and get a real correlation
read — Pearson r, R², a least-squares fit, the scatter, and the joined table.
That turns the platform's 14 state-grain datasets into pairwise hypotheses a
partner actually asks ("does MA penetration track SNF quality? does the
uninsured rate track provider exclusions?").

Pure logic, no UI, no network. Joins on the state label both datasets already
carry, scales each measure into its display unit (reusing
``further_analysis._scale``), and is None/NaN-safe — a state missing either
value is dropped from the pair, never zero-filled.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from . import further_analysis as fa


def state_grain_datasets() -> List[fa.Dataset]:
    """Datasets keyed one-row-per-state — the joinable universe."""
    return [d for d in fa.list_datasets() if d.grain == "state"]


def _value_map(dataset: fa.Dataset, measure_key: str) -> Dict[str, float]:
    """``{state_label: scaled_value}`` for one dataset+measure, None/NaN-safe."""
    measure = dataset.measure(measure_key)
    if measure is None:
        return {}
    out: Dict[str, float] = {}
    for row in dataset.loader(None):
        label = row.get(dataset.dim_key)
        if label is None:
            continue
        scaled = fa._scale(row.get(measure_key), measure.fmt)
        if scaled is None:
            continue
        try:
            v = float(scaled)
        except (TypeError, ValueError):
            continue
        if math.isnan(v) or math.isinf(v):
            continue
        out[str(label)] = v
    return out


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Pearson correlation coefficient, or None when undefined (n<3 or a
    constant series — a flat axis has no meaningful correlation)."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def _linfit(xs: List[float], ys: List[float]) -> Optional[Tuple[float, float]]:
    """Least-squares (slope, intercept), or None when x has no variance."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return b, my - b * mx


def _strength(r: float) -> str:
    a = abs(r)
    band = ("negligible" if a < 0.1 else "weak" if a < 0.3
            else "moderate" if a < 0.5 else "strong" if a < 0.7
            else "very strong")
    return f"{'positive' if r >= 0 else 'negative'} · {band}"


def correlate(
    x_id: str, x_measure: str, y_id: str, y_measure: str,
) -> Dict[str, Any]:
    """Join two state-grain datasets and compute the correlation.

    Returns a dict with the scatter ``table`` (rows ``(state, [x, y])`` for
    ``render_cdd_chart("scatter", …, {"trendline": True})``), the joined data
    table, and stats (n, pearson_r, r2, slope, intercept, strength).
    """
    dx = fa.DATASETS.get(x_id)
    dy = fa.DATASETS.get(y_id)
    if dx is None or dy is None or dx.grain != "state" or dy.grain != "state":
        return {"ok": False, "reason": "both datasets must be state-grain"}

    mx = dx.measure(x_measure) or dx.measures[0]
    my = dy.measure(y_measure) or dy.measures[0]
    xmap = _value_map(dx, mx.key)
    ymap = _value_map(dy, my.key)
    states = sorted(set(xmap) & set(ymap))

    rows: List[Tuple[str, List[Optional[float]]]] = []
    xs: List[float] = []
    ys: List[float] = []
    for st in states:
        xv, yv = xmap[st], ymap[st]
        rows.append((st, [xv, yv]))
        xs.append(xv)
        ys.append(yv)

    r = _pearson(xs, ys)
    fit = _linfit(xs, ys)
    x_suffix = fa.measure_suffix(mx.fmt)
    y_suffix = fa.measure_suffix(my.fmt)

    stats: Dict[str, Any] = {
        "n": len(states),
        "pearson_r": r,
        "r2": (r * r) if r is not None else None,
        "slope": fit[0] if fit else None,
        "intercept": fit[1] if fit else None,
        "strength": _strength(r) if r is not None else None,
    }
    x_label = f"{dx.label} · {mx.label}"
    y_label = f"{dy.label} · {my.label}"
    return {
        "ok": True,
        "x": {"dataset": dx.id, "measure": mx.key, "label": x_label,
              "suffix": x_suffix},
        "y": {"dataset": dy.id, "measure": my.key, "label": y_label,
              "suffix": y_suffix},
        "table": {"headers": ["State", mx.label, my.label], "rows": rows},
        "stats": stats,
    }


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def resolve_query(qs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Clamp query params to valid state-grain datasets/measures, defaulting to
    a sensible, populated pair so the page renders something on first load."""
    sgs = state_grain_datasets()
    by_id = {d.id: d for d in sgs}
    # Defaults: MA penetration vs hospital operating margin — a real question.
    x_id = _qs1(qs, "x", "ma_penetration")
    y_id = _qs1(qs, "y", "hcris_state")
    if x_id not in by_id:
        x_id = sgs[0].id
    if y_id not in by_id:
        y_id = sgs[min(1, len(sgs) - 1)].id
    dx, dy = by_id[x_id], by_id[y_id]
    x_measure = _qs1(qs, "xm", dx.measures[0].key)
    if dx.measure(x_measure) is None:
        x_measure = dx.measures[0].key
    y_measure = _qs1(qs, "ym", dy.measures[0].key)
    if dy.measure(y_measure) is None:
        y_measure = dy.measures[0].key
    result = correlate(x_id, x_measure, y_id, y_measure)
    return {
        "x_id": x_id, "y_id": y_id,
        "x_measure": x_measure, "y_measure": y_measure,
        "result": result,
    }


def build_cross_analysis(qs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """JSON-API payload: the resolved pair + stats + the joinable catalog."""
    spec = resolve_query(qs)
    res = spec["result"]
    catalog = [{
        "id": d.id, "label": d.label, "category": d.category,
        "measures": [{"key": m.key, "label": m.label, "fmt": m.fmt}
                     for m in d.measures],
    } for d in state_grain_datasets()]
    table = res.get("table", {"headers": [], "rows": []})
    return {
        "selected": {
            "x": spec["x_id"], "xm": spec["x_measure"],
            "y": spec["y_id"], "ym": spec["y_measure"],
        },
        "stats": res.get("stats", {}),
        "ok": res.get("ok", False),
        "joined": [{"state": lbl, "x": vals[0], "y": vals[1]}
                   for lbl, vals in table["rows"]],
        "catalog": catalog,
    }
