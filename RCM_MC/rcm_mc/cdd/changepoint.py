"""BOLSTER-03 Changepoint detection (hardened).

Pins the changepoint spec: ruptures PELT with model l2 or rbf and a tuned
penalty. Applies to reimbursement-rate trends, site-of-care inflection, and
portfolio-KPI monitoring. Emits each changepoint's index (or mapped date),
magnitude (mean shift), and direction. A flat series yields zero changepoints; a
clear break is detected at the right index.

The default penalty is a BIC-style sigma^2 * log(n), with sigma estimated from
the median absolute first difference so a noisy series does not over-segment.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import ruptures as rpt

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "BOLSTER-03"


def _default_penalty(signal: np.ndarray) -> float:
    n = len(signal)
    if n < 2:
        return 1.0
    sigma = np.median(np.abs(np.diff(signal))) / 0.6745  # robust noise estimate
    sigma2 = float(sigma * sigma)
    return max(3.0 * sigma2 * np.log(n), 0.0)


def detect_changepoints(
    series: Sequence[float],
    *,
    dates: Optional[Sequence[Any]] = None,
    model: str = "l2",
    penalty: Optional[float] = None,
    min_size: int = 2,
    jump: int = 1,
    source: str = "KPI or reimbursement-rate series",
    vintage: str = "",
    audience: str = "internal",
) -> Exhibit:
    """Detect changepoints in a 1D series with ruptures PELT.

    Returns an exhibit whose meta['changepoints'] lists {index, date, magnitude,
    direction} for each detected break.
    """
    if model not in {"l2", "rbf"}:
        raise ValueError("model must be 'l2' or 'rbf'")
    values = np.asarray(series, dtype=float)
    n = len(values)
    if n < 2:
        raise ValueError("detect_changepoints needs at least 2 points")
    if dates is not None and len(dates) != n:
        raise ValueError("dates length must match series length")

    pen = _default_penalty(values) if penalty is None else float(penalty)
    signal = values.reshape(-1, 1)
    algo = rpt.Pelt(model=model, min_size=min_size, jump=jump).fit(signal)
    bkps = algo.predict(pen=pen)
    # ruptures includes n as the final breakpoint; internal changepoints drop it.
    cp_indices = [b for b in bkps if b < n]

    changepoints: List[Dict[str, Any]] = []
    prev = 0
    seg_bounds = cp_indices + [n]
    for k, idx in enumerate(cp_indices):
        before = values[prev:idx]
        nxt_end = seg_bounds[k + 1]
        after = values[idx:nxt_end]
        mag = float(np.mean(after) - np.mean(before)) if len(before) and len(after) else 0.0
        changepoints.append({
            "index": int(idx),
            "date": (dates[idx] if dates is not None else None),
            "magnitude": mag,
            "direction": "up" if mag >= 0 else "down",
        })
        prev = idx

    flags: List[Flag] = []
    if changepoints:
        flags.append(Flag(
            code="changepoint_detected",
            severity="warn",
            message=f"{len(changepoints)} changepoint(s) detected in the series.",
            source=source,
        ))

    indices_valid = all(0 < c["index"] < n for c in changepoints) and cp_indices == sorted(cp_indices)
    reconciliations = [
        Reconciliation(identity="changepoint indices strictly increasing and within range",
                       lhs=1.0 if indices_valid else 0.0, rhs=1.0, tolerance=1e-9),
    ]

    series_out = [
        Series(name="Series with changepoints", kind="line",
               points=[{"label": str(i), "value": float(v),
                        "changepoint": any(c["index"] == i for c in changepoints)}
                       for i, v in enumerate(values)]),
        Series(name="Changepoint detail", kind="bar", internal_only=True, points=changepoints),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            f"ruptures PELT, model {model}, penalty {pen:.3f}.",
            "Magnitude is the mean shift across the break; direction is its sign.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Changepoint detection",
        audience=audience,
        series=series_out,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{len(changepoints)} changepoint(s) at penalty {pen:.3f}.",
        meta={
            "changepoints": changepoints,
            "n": n,
            "penalty": pen,
            "model": model,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    series = [10.0] * 10 + [50.0] * 10
    return detect_changepoints(series, model="l2", source="Demo KPI series", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Changepoint detection (hardened)",
        audience="internal",
        demo=_demo,
    )
)
