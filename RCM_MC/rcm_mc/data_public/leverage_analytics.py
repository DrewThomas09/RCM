"""Leverage analytics — corpus performance by debt/equity structure.

Uses explicit leverage_pct where available; proxies from EV/EBITDA
(assuming ~60% LTV at 8-12x EV/EBITDA) for deals without direct leverage data.

Buckets: Low <45%, Mid 45-60%, High 60-70%, Very High >70%.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _pct(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _implied_leverage(ev_ebitda: float) -> Optional[float]:
    """Rough leverage proxy: healthcare PE typically 5-7x debt at given EV/EBITDA."""
    if ev_ebitda <= 0:
        return None
    typical_debt_ebitda = min(6.0, ev_ebitda * 0.55)
    return typical_debt_ebitda / ev_ebitda


LEVERAGE_BUCKETS = [
    ("Low",       0.00, 0.45, "#22c55e"),
    ("Mid",       0.45, 0.60, "#3b82f6"),
    ("High",      0.60, 0.70, "#f59e0b"),
    ("Very High", 0.70, 1.01, "#ef4444"),
]


@dataclass
class LeverageBucketStats:
    label: str
    lev_range: Tuple[float, float]
    color: str
    n_deals: int
    moic_p25: float
    moic_p50: float
    moic_p75: float
    irr_p50: float
    avg_leverage: float
    loss_rate: float
    is_direct: bool  # True if from leverage_pct; False if proxied


@dataclass
class LeveragePoint:
    source_id: str
    deal_name: str
    leverage_pct: float
    moic: float
    irr: float
    ev_mm: float
    is_direct: bool  # True = explicit field; False = EV/EBITDA proxy


@dataclass
class LeverageProfile:
    n_direct: int
    n_proxied: int
    avg_leverage_direct: float
    lev_moic_corr: float       # Spearman rank correlation
    optimal_bucket: str        # bucket with highest P50 MOIC
    points: List[LeveragePoint] = field(default_factory=list)
    buckets: List[LeverageBucketStats] = field(default_factory=list)


def _rank_corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 3:
        return 0.0
    n = len(xs)
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    d2 = sum((rx[x] - ry[y]) ** 2 for x, y in zip(xs, ys))
    return 1 - 6 * d2 / (n * (n * n - 1))


def compute_leverage_analytics(corpus: List[Dict[str, Any]]) -> LeverageProfile:
    points: List[LeveragePoint] = []

    for d in corpus:
        moic = d.get("realized_moic")
        irr  = d.get("realized_irr")
        ev   = d.get("ev_mm")
        if moic is None:
            continue
        try:
            moic_f = float(moic)
            irr_f  = float(irr) if irr is not None else 0.0
            ev_f   = float(ev)  if ev  is not None else 0.0
        except (TypeError, ValueError):
            continue

        lev = d.get("leverage_pct")
        is_direct = lev is not None
        if is_direct:
            try:
                lev_f = float(lev)
            except (TypeError, ValueError):
                continue
        else:
            ev_ebitda = d.get("ev_ebitda")
            if ev_ebitda is None:
                continue
            try:
                lev_f = _implied_leverage(float(ev_ebitda))
                if lev_f is None:
                    continue
            except (TypeError, ValueError):
                continue

        points.append(LeveragePoint(
            source_id=d.get("source_id", ""),
            deal_name=d.get("deal_name", ""),
            leverage_pct=lev_f,
            moic=moic_f,
            irr=irr_f,
            ev_mm=ev_f,
            is_direct=is_direct,
        ))

    n_direct  = sum(1 for p in points if p.is_direct)
    n_proxied = sum(1 for p in points if not p.is_direct)
    direct_levs = [p.leverage_pct for p in points if p.is_direct]
    avg_lev_direct = sum(direct_levs) / len(direct_levs) if direct_levs else 0.0

    levs  = [p.leverage_pct for p in points]
    moics = [p.moic for p in points]
    corr  = _rank_corr(levs, moics)

    # Build bucket stats
    buckets: List[LeverageBucketStats] = []
    best_p50 = -1.0
    best_bucket = "Mid"
    for label, lo, hi, color in LEVERAGE_BUCKETS:
        bp = [p for p in points if lo <= p.leverage_pct < hi]
        if not bp:
            continue
        bmoics = [p.moic for p in bp]
        birrs  = [p.irr  for p in bp]
        blevs  = [p.leverage_pct for p in bp]
        p50 = _pct(bmoics, 50)
        is_direct_bucket = any(p.is_direct for p in bp)
        buckets.append(LeverageBucketStats(
            label=label,
            lev_range=(lo, hi),
            color=color,
            n_deals=len(bp),
            moic_p25=_pct(bmoics, 25),
            moic_p50=p50,
            moic_p75=_pct(bmoics, 75),
            irr_p50=_pct(birrs, 50),
            avg_leverage=sum(blevs) / len(blevs),
            loss_rate=sum(1 for m in bmoics if m < 1.0) / len(bmoics),
            is_direct=is_direct_bucket,
        ))
        if p50 > best_p50:
            best_p50 = p50
            best_bucket = label

    return LeverageProfile(
        n_direct=n_direct,
        n_proxied=n_proxied,
        avg_leverage_direct=avg_lev_direct,
        lev_moic_corr=corr,
        optimal_bucket=best_bucket,
        points=points,
        buckets=buckets,
    )
