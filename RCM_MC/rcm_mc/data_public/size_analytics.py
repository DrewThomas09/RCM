"""Deal size analytics — corpus performance by EV size bucket.

Buckets: Small (<$100M), Mid ($100-300M), Large ($300-1B), Mega (>$1B).
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


def _pct(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


SIZE_BUCKETS = [
    ("Small",  0,     100,   "#64748b"),
    ("Mid",    100,   300,   "#3b82f6"),
    ("Large",  300,   1000,  "#f59e0b"),
    ("Mega",   1000,  1e9,   "#ef4444"),
]


@dataclass
class SizeBucketStats:
    label: str
    ev_range: Tuple[float, float]
    color: str
    n_deals: int
    moic_p25: float
    moic_p50: float
    moic_p75: float
    irr_p50: float
    avg_ev_mm: float
    loss_rate: float
    avg_hold: float


@dataclass
class SizeProfile:
    n_total: int
    ev_p25: float
    ev_p50: float
    ev_p75: float
    size_moic_corr: float
    buckets: List[SizeBucketStats] = field(default_factory=list)
    ev_moic_points: List[Tuple[float, float, str]] = field(default_factory=list)  # (ev, moic, deal_name)


def _rank_corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 3:
        return 0.0
    n = len(xs)
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    d2 = sum((rx[x] - ry[y]) ** 2 for x, y in zip(xs, ys))
    return 1 - 6 * d2 / (n * (n * n - 1))


def compute_size_analytics(corpus: List[Dict[str, Any]]) -> SizeProfile:
    valid = [
        d for d in corpus
        if d.get("ev_mm") is not None and d.get("realized_moic") is not None
    ]

    evs   = []
    moics = []
    points = []
    for d in valid:
        try:
            ev   = float(d["ev_mm"])
            moic = float(d["realized_moic"])
            if ev > 0:
                evs.append(ev)
                moics.append(moic)
                points.append((ev, moic, d.get("deal_name", "")))
        except (TypeError, ValueError):
            pass

    buckets: List[SizeBucketStats] = []
    for label, lo, hi, color in SIZE_BUCKETS:
        bp_evs   = []
        bp_moics = []
        bp_irrs  = []
        bp_holds = []
        for d in valid:
            try:
                ev = float(d["ev_mm"])
                if lo <= ev < hi:
                    bp_evs.append(ev)
                    bp_moics.append(float(d["realized_moic"]))
                    if d.get("realized_irr") is not None:
                        bp_irrs.append(float(d["realized_irr"]))
                    if d.get("hold_years") is not None:
                        bp_holds.append(float(d["hold_years"]))
            except (TypeError, ValueError):
                pass
        if not bp_moics:
            continue
        buckets.append(SizeBucketStats(
            label=label,
            ev_range=(lo, hi),
            color=color,
            n_deals=len(bp_moics),
            moic_p25=_pct(bp_moics, 25),
            moic_p50=_pct(bp_moics, 50),
            moic_p75=_pct(bp_moics, 75),
            irr_p50=_pct(bp_irrs, 50) if bp_irrs else 0.0,
            avg_ev_mm=sum(bp_evs) / len(bp_evs),
            loss_rate=sum(1 for m in bp_moics if m < 1.0) / len(bp_moics),
            avg_hold=sum(bp_holds) / len(bp_holds) if bp_holds else 0.0,
        ))

    return SizeProfile(
        n_total=len(points),
        ev_p25=_pct(evs, 25),
        ev_p50=_pct(evs, 50),
        ev_p75=_pct(evs, 75),
        size_moic_corr=_rank_corr(evs, moics),
        buckets=buckets,
        ev_moic_points=points,
    )
