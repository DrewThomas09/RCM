"""Hold Period Optimizer — corpus-calibrated optimal hold analysis.

Given an entry profile (EV, EV/EBITDA, sector, payer mix), finds the hold
period bucket with the highest P50 MOIC among corpus peers and computes
confidence intervals from the peer distribution.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 42):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


def _ev_ebitda(d: Dict[str, Any]) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm")
    if ev and eb and float(eb) > 0:
        return round(float(ev) / float(eb), 2)
    stored = d.get("ev_ebitda")
    if stored:
        try:
            return float(stored)
        except (TypeError, ValueError):
            pass
    return None


def _moic(d: Dict[str, Any]) -> Optional[float]:
    for k in ("moic", "realized_moic"):
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _hold(d: Dict[str, Any]) -> Optional[float]:
    v = d.get("hold_years")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    return None


def _comm_pct(d: Dict[str, Any]) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        v = pm.get("commercial") or pm.get("comm")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


# Hold buckets in years
HOLD_BUCKETS: List[Tuple[str, float, float]] = [
    ("2–3 yr",  2.0, 3.5),
    ("3–4 yr",  3.5, 4.5),
    ("4–5 yr",  4.5, 5.5),
    ("5–6 yr",  5.5, 6.5),
    ("6–7 yr",  6.5, 7.5),
    ("7+ yr",   7.5, 99.0),
]


@dataclass
class HoldBucketStats:
    label: str
    hold_lo: float
    hold_hi: float
    n: int
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    moic_mean: Optional[float]
    irr_p50: Optional[float]
    loss_rate: float   # fraction with MOIC < 1.0
    home_run_rate: float  # fraction with MOIC > 3.0
    is_optimal: bool = False


@dataclass
class HoldOptimizerResult:
    n_peers: int
    sector_filter: str
    ev_mm_lo: float
    ev_mm_hi: float
    ev_ebitda_lo: float
    ev_ebitda_hi: float
    comm_pct_filter: Optional[float]
    buckets: List[HoldBucketStats]
    optimal_bucket: Optional[str]
    optimal_moic_p50: Optional[float]
    corpus_p50: Optional[float]
    corpus_n: int
    peer_deals: List[Dict[str, Any]] = field(default_factory=list)


def _score_peer(
    deal: Dict[str, Any],
    sector: str,
    ev_mm: Optional[float],
    ev_ebitda: Optional[float],
    comm_pct: Optional[float],
) -> float:
    score = 0.0
    # Sector match (40 pts)
    if sector and deal.get("sector"):
        if sector.lower() in (deal.get("sector") or "").lower():
            score += 40.0
        else:
            # Partial word match
            words_query = set(sector.lower().split())
            words_deal = set((deal.get("sector") or "").lower().split())
            overlap = words_query & words_deal
            if overlap:
                score += 20.0
    # EV proximity (30 pts, decaying with distance)
    if ev_mm and deal.get("ev_mm"):
        ratio = float(deal["ev_mm"]) / float(ev_mm)
        if 0.5 <= ratio <= 2.0:
            score += 30.0 * (1 - abs(math.log(ratio)) / math.log(2))
    # EV/EBITDA proximity (20 pts)
    peer_ee = _ev_ebitda(deal)
    if ev_ebitda and peer_ee:
        diff = abs(float(ev_ebitda) - peer_ee)
        score += max(0.0, 20.0 - diff * 4)
    # Payer mix (10 pts)
    if comm_pct is not None:
        peer_comm = _comm_pct(deal)
        if peer_comm is not None:
            diff = abs(comm_pct - peer_comm)
            score += max(0.0, 10.0 * (1 - diff * 5))
    return score


def compute_hold_optimizer(
    sector: str = "",
    ev_mm: Optional[float] = None,
    ev_ebitda_entry: Optional[float] = None,
    comm_pct: Optional[float] = None,
    min_peers: int = 5,
    top_n_peers: int = 60,
) -> HoldOptimizerResult:
    """Find the optimal hold period from corpus peers matching entry profile.

    Ranks corpus deals by similarity to the input profile, takes top_n_peers,
    then buckets by hold period and computes P50 MOIC per bucket.
    """
    corpus = _load_corpus()

    # Determine EV range filter (±50%)
    ev_lo, ev_hi = 0.0, 1e9
    if ev_mm:
        ev_lo = float(ev_mm) * 0.4
        ev_hi = float(ev_mm) * 2.5

    # EV/EBITDA filter (±4×)
    ee_lo, ee_hi = 5.0, 25.0
    if ev_ebitda_entry:
        ee_lo = max(5.0, float(ev_ebitda_entry) - 4.0)
        ee_hi = float(ev_ebitda_entry) + 4.0

    # Score all peers
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for d in corpus:
        m = _moic(d)
        h = _hold(d)
        if m is None or h is None:
            continue
        score = _score_peer(d, sector, ev_mm, ev_ebitda_entry, comm_pct)
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: -x[0])
    peers = [d for _, d in scored[:top_n_peers]]

    # Corpus-wide P50 for context
    all_moics = sorted([_moic(d) for d in corpus if _moic(d) is not None])
    corpus_p50 = _percentile(all_moics, 0.50)

    # Bucket peers
    buckets: List[HoldBucketStats] = []
    for label, lo, hi in HOLD_BUCKETS:
        bucket_deals = [d for d in peers if lo <= (_hold(d) or 0) < hi]
        moics = sorted([_moic(d) for d in bucket_deals if _moic(d) is not None])
        irrs = sorted([
            float(d["irr"]) if d.get("irr") else float(d["realized_irr"])
            for d in bucket_deals
            if d.get("irr") is not None or d.get("realized_irr") is not None
        ])
        bs = HoldBucketStats(
            label=label,
            hold_lo=lo,
            hold_hi=hi,
            n=len(bucket_deals),
            moic_p25=_percentile(moics, 0.25),
            moic_p50=_percentile(moics, 0.50),
            moic_p75=_percentile(moics, 0.75),
            moic_mean=round(sum(moics) / len(moics), 3) if moics else None,
            irr_p50=_percentile(irrs, 0.50),
            loss_rate=sum(1 for m in moics if m < 1.0) / len(moics) if moics else 0.0,
            home_run_rate=sum(1 for m in moics if m >= 3.0) / len(moics) if moics else 0.0,
        )
        buckets.append(bs)

    # Find optimal bucket (highest P50 MOIC with n >= min_peers)
    eligible = [b for b in buckets if b.n >= min_peers and b.moic_p50 is not None]
    optimal = max(eligible, key=lambda b: b.moic_p50, default=None)
    if optimal:
        optimal.is_optimal = True

    return HoldOptimizerResult(
        n_peers=len(peers),
        sector_filter=sector,
        ev_mm_lo=ev_lo,
        ev_mm_hi=ev_hi,
        ev_ebitda_lo=ee_lo,
        ev_ebitda_hi=ee_hi,
        comm_pct_filter=comm_pct,
        buckets=buckets,
        optimal_bucket=optimal.label if optimal else None,
        optimal_moic_p50=optimal.moic_p50 if optimal else None,
        corpus_p50=corpus_p50,
        corpus_n=len(corpus),
        peer_deals=peers[:20],
    )
