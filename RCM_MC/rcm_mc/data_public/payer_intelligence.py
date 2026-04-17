"""Payer mix intelligence — corpus performance segmented by payer regime.

Buckets deals by commercial %, computes P25/P50/P75 MOIC and IRR per bucket,
and computes overall corpus payer concentration metrics.
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


# Payer regime buckets by commercial %
REGIME_BUCKETS = [
    ("Gov-heavy",      0.00, 0.30),   # <30% commercial
    ("Balanced",       0.30, 0.50),   # 30-50%
    ("Commercial-mix", 0.50, 0.70),   # 50-70%
    ("Commercial",     0.70, 1.01),   # >70%
]


@dataclass
class PayerRegimeStats:
    regime: str
    commercial_range: Tuple[float, float]
    n_deals: int
    moic_p25: float
    moic_p50: float
    moic_p75: float
    irr_p50: float
    avg_commercial_pct: float
    avg_medicare_pct: float
    avg_medicaid_pct: float
    loss_rate: float


@dataclass
class CorpusPayerProfile:
    avg_commercial: float
    avg_medicare: float
    avg_medicaid: float
    avg_self_pay: float
    # correlation proxies
    commercial_moic_corr: float   # simple rank correlation approximation
    medicaid_moic_corr: float
    regime_stats: List[PayerRegimeStats] = field(default_factory=list)


def _rank_corr(xs: List[float], ys: List[float]) -> float:
    """Spearman rank correlation approximation."""
    if len(xs) < 3:
        return 0.0
    n = len(xs)
    rank_x = {v: i for i, v in enumerate(sorted(xs))}
    rank_y = {v: i for i, v in enumerate(sorted(ys))}
    rx = [rank_x[v] for v in xs]
    ry = [rank_y[v] for v in ys]
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def compute_payer_intelligence(corpus: List[Dict[str, Any]]) -> CorpusPayerProfile:
    deals_with_payer = [
        d for d in corpus
        if isinstance(d.get("payer_mix"), dict) and d.get("realized_moic") is not None
    ]

    def _pm(d: Dict[str, Any], k: str) -> float:
        return float(d["payer_mix"].get(k, 0) or 0)

    comm_vals  = [_pm(d, "commercial")  for d in deals_with_payer]
    med_vals   = [_pm(d, "medicare")    for d in deals_with_payer]
    maid_vals  = [_pm(d, "medicaid")    for d in deals_with_payer]
    self_vals  = [_pm(d, "self_pay")    for d in deals_with_payer]
    moic_vals  = [float(d["realized_moic"]) for d in deals_with_payer]

    n = len(deals_with_payer)
    avg_comm = sum(comm_vals) / n if n else 0
    avg_med  = sum(med_vals)  / n if n else 0
    avg_maid = sum(maid_vals) / n if n else 0
    avg_self = sum(self_vals) / n if n else 0

    # regime buckets
    regime_stats: List[PayerRegimeStats] = []
    for regime, lo, hi in REGIME_BUCKETS:
        bucket = [
            (d, comm, moic)
            for d, comm, moic in zip(deals_with_payer, comm_vals, moic_vals)
            if lo <= comm < hi
        ]
        if not bucket:
            continue
        bmoics = [m for _, _, m in bucket]
        bcomm  = [c for _, c, _ in bucket]
        bmed   = [_pm(d, "medicare")  for d, _, _ in bucket]
        bmaid  = [_pm(d, "medicaid")  for d, _, _ in bucket]
        birrs  = [float(d["realized_irr"]) for d, _, _ in bucket if d.get("realized_irr") is not None]
        regime_stats.append(PayerRegimeStats(
            regime=regime,
            commercial_range=(lo, hi),
            n_deals=len(bucket),
            moic_p25=_pct(bmoics, 25),
            moic_p50=_pct(bmoics, 50),
            moic_p75=_pct(bmoics, 75),
            irr_p50=_pct(birrs, 50) if birrs else 0.0,
            avg_commercial_pct=sum(bcomm) / len(bcomm),
            avg_medicare_pct=sum(bmed) / len(bmed),
            avg_medicaid_pct=sum(bmaid) / len(bmaid),
            loss_rate=sum(1 for m in bmoics if m < 1.0) / len(bmoics),
        ))

    return CorpusPayerProfile(
        avg_commercial=avg_comm,
        avg_medicare=avg_med,
        avg_medicaid=avg_maid,
        avg_self_pay=avg_self,
        commercial_moic_corr=_rank_corr(comm_vals, moic_vals),
        medicaid_moic_corr=_rank_corr(maid_vals, moic_vals),
        regime_stats=regime_stats,
    )
