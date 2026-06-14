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

import functools
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


_NUMERIC_FMTS = {"num", "usd", "usd_m", "usd_b", "pct", "pct100", "x", "weeks"}
# Range ratio above which a "num" measure is treated as a raw count/scale that
# trivially tracks state size (population, bed/facility counts) rather than a
# bounded rate or score — excluded from the scan so it surfaces real signal.
_SCALE_RANGE_RATIO = 50.0


def _is_scale_measure(measure: fa.Measure, values: Dict[str, float]) -> bool:
    """True if a measure is a raw count/scale (vs a normalized rate/score)."""
    if measure.fmt != "num":
        return False
    vs = [abs(v) for v in values.values() if v not in (None, 0)]
    if len(vs) < 2:
        return False
    lo, hi = min(vs), max(vs)
    return lo > 0 and (hi / lo) > _SCALE_RANGE_RATIO


def _same_metric(a: fa.Measure, b: fa.Measure) -> bool:
    """Heuristic: two measures are 'the same metric reused' when one label is a
    substring of the other (e.g. 'SNF overall' vs 'SNF avg star rating')."""
    la, lb = a.label.lower(), b.label.lower()
    return la in lb or lb in la


@functools.lru_cache(maxsize=16)
def scan_correlations(
    *, min_n: int = 30, top: int = 20, min_abs_r: float = 0.0,
    max_abs_r: float = 0.985,
    include_scale: bool = False, include_derived: bool = False,
) -> List[Dict[str, Any]]:
    """Scan every measure pair across *different* state-grain datasets and
    return the strongest *substantive* correlations — a discovery engine for
    "what moves with what" in the public-data universe.

    Filtered for signal by default: derived composite indices are skipped
    (they tautologically track their own inputs), raw count/scale measures are
    skipped (they just track state size), and same-metric pairs (one label a
    substring of the other) are dropped. Only pairs with at least ``min_n``
    jointly-present states are scored. Returns up to ``top`` rows by ``|r|``.
    """
    sgs = [d for d in state_grain_datasets()
           if include_derived or d.category != "Derived"]
    maps: List[Tuple[fa.Dataset, fa.Measure, Dict[str, float]]] = []
    for d in sgs:
        for m in d.measures:
            if m.fmt not in _NUMERIC_FMTS:
                continue
            vm = _value_map(d, m.key)
            if len(vm) < min_n:
                continue
            if not include_scale and _is_scale_measure(m, vm):
                continue
            maps.append((d, m, vm))

    out: List[Dict[str, Any]] = []
    for i in range(len(maps)):
        di, mi, vi = maps[i]
        for j in range(i + 1, len(maps)):
            dj, mj, vj = maps[j]
            if di.id == dj.id:          # same dataset — not a cross relationship
                continue
            if _same_metric(mi, mj):    # same metric reused across datasets
                continue
            states = set(vi) & set(vj)
            if len(states) < min_n:
                continue
            xs = [vi[s] for s in states]
            ys = [vj[s] for s in states]
            r = _pearson(xs, ys)
            # A near-perfect r across many states almost always means the same
            # underlying series loaded into two datasets — drop as a duplicate.
            if r is None or abs(r) < min_abs_r or abs(r) > max_abs_r:
                continue
            out.append({
                "x_id": di.id, "x_measure": mi.key,
                "x_label": f"{di.label} · {mi.label}",
                "y_id": dj.id, "y_measure": mj.key,
                "y_label": f"{dj.label} · {mj.label}",
                "r": r, "abs_r": abs(r), "n": len(states),
                "strength": _strength(r),
            })
    out.sort(key=lambda d: d["abs_r"], reverse=True)
    return out[:max(1, int(top))]


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
        "top_relationships": list(scan_correlations(min_n=30, top=15,
                                                    min_abs_r=0.3)),
        "catalog": catalog,
    }
