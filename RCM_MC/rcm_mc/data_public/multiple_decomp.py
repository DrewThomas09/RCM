"""Acquisition Multiple Decomposition — entry EV/EBITDA explained vs. premium.

Decomposes an entry EV/EBITDA multiple into:
  - Sector baseline (corpus median for the sector)
  - Size premium/discount (EV-size adjustment)
  - Payer mix premium (commercial-heavy premium)
  - Unexplained premium (what the buyer paid above fundamentals)

Uses corpus regression on realized MOIC to calibrate whether paying premium
has historically been justified.
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
    for i in range(2, 44):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


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


def _comm_pct(d: Dict[str, Any]) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        for k in ("commercial", "comm"):
            v = pm.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return None


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


def _linear_fit(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    """Return (slope, intercept) via OLS."""
    n = len(xs)
    if n < 3:
        return 0.0, sum(ys) / len(ys) if ys else 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    ss_xx = sum((x - mx) ** 2 for x in xs)
    if ss_xx < 1e-10:
        return 0.0, my
    slope = ss_xy / ss_xx
    return round(slope, 4), round(my - slope * mx, 4)


@dataclass
class MultipleComponent:
    label: str
    value: float      # the multiple component (turns)
    pct_of_total: float  # % of entry EV/EBITDA
    description: str


@dataclass
class SectorBenchmark:
    sector: str
    n: int
    median_ev_ebitda: Optional[float]
    p25_ev_ebitda: Optional[float]
    p75_ev_ebitda: Optional[float]
    median_moic: Optional[float]
    # Slope of EV/EBITDA vs MOIC
    premium_moic_slope: float  # +ve = high multiple → higher MOIC
    premium_moic_slope_r2: float


@dataclass
class MultipleDecompResult:
    input_sector: str
    input_ev_mm: Optional[float]
    input_ev_ebitda: float
    input_comm_pct: Optional[float]

    sector_baseline: float
    size_adjustment: float
    payer_adjustment: float
    unexplained_premium: float
    components: List[MultipleComponent]

    corpus_median_ev_ebitda: float
    sector_median_ev_ebitda: Optional[float]
    sector_n: int

    # Historical precedent: what MOIC do deals at similar premium earn?
    similar_premium_moic_p50: Optional[float]
    high_premium_moic_p50: Optional[float]   # entry > sector median + 3×
    low_premium_moic_p50: Optional[float]    # entry < sector median

    sector_benchmarks: List[SectorBenchmark] = field(default_factory=list)
    peer_deals: List[Dict[str, Any]] = field(default_factory=list)


def compute_multiple_decomp(
    sector: str = "",
    ev_mm: Optional[float] = None,
    ev_ebitda: float = 12.0,
    comm_pct: Optional[float] = None,
) -> MultipleDecompResult:
    corpus = _load_corpus()

    # Corpus-wide EV/EBITDA stats
    all_ee = sorted([v for d in corpus for v in [_ev_ebitda(d)] if v is not None])
    corpus_median = _percentile(all_ee, 0.50) or 10.0

    # Sector-filtered peers
    sector_peers = []
    if sector:
        for d in corpus:
            dsec = (d.get("sector") or "").lower()
            q = sector.lower()
            words = set(q.split())
            dsec_words = set(dsec.split())
            if q in dsec or (words & dsec_words):
                sector_peers.append(d)

    if len(sector_peers) < 5:
        sector_peers = corpus  # fallback

    sector_ee = sorted([v for d in sector_peers for v in [_ev_ebitda(d)] if v is not None])
    sector_median = _percentile(sector_ee, 0.50)
    sector_p25 = _percentile(sector_ee, 0.25)
    sector_p75 = _percentile(sector_ee, 0.75)

    baseline = sector_median or corpus_median

    # Size adjustment: large deals (EV > $500M) vs small (<$100M) carry different multiples
    size_adj = 0.0
    if ev_mm is not None:
        # Regression of log(EV) vs EV/EBITDA in sector peers
        ev_ee_pairs = [
            (math.log(float(d["ev_mm"])), _ev_ebitda(d))
            for d in sector_peers
            if d.get("ev_mm") and float(d.get("ev_mm", 0)) > 0 and _ev_ebitda(d) is not None
        ]
        if len(ev_ee_pairs) >= 5:
            xs, ys = zip(*ev_ee_pairs)
            slope, intercept = _linear_fit(list(xs), list(ys))
            # Predicted EV/EBITDA at this size
            predicted_for_size = slope * math.log(float(ev_mm)) + intercept
            # Size adjustment = (predicted_for_size - baseline)
            size_adj = round(predicted_for_size - baseline, 2)

    # Payer mix adjustment: commercial % premium
    payer_adj = 0.0
    if comm_pct is not None:
        # Regression of comm% vs EV/EBITDA
        pay_ee_pairs = [
            (_comm_pct(d), _ev_ebitda(d))
            for d in sector_peers
            if _comm_pct(d) is not None and _ev_ebitda(d) is not None
        ]
        if len(pay_ee_pairs) >= 5:
            xs, ys = zip(*pay_ee_pairs)
            slope, intercept = _linear_fit(list(xs), list(ys))
            corpus_avg_comm = sum(xs) / len(xs)
            payer_adj = round(slope * (comm_pct - corpus_avg_comm), 2)

    # Unexplained premium
    explained = baseline + size_adj + payer_adj
    unexplained = round(ev_ebitda - explained, 2)

    total = ev_ebitda
    def _pct(v: float) -> float:
        return round(v / total * 100, 1) if total > 0 else 0.0

    components = [
        MultipleComponent(
            "Sector Baseline",
            round(baseline, 2),
            _pct(baseline),
            f"Corpus median EV/EBITDA for {sector or 'all sectors'}",
        ),
        MultipleComponent(
            "Size Adjustment",
            round(size_adj, 2),
            _pct(size_adj),
            f"Adjustment for {'$' + str(int(ev_mm)) + 'M EV' if ev_mm else 'unknown EV'} vs. sector average",
        ),
        MultipleComponent(
            "Payer Mix Adjustment",
            round(payer_adj, 2),
            _pct(payer_adj),
            f"Commercial-payer premium at {comm_pct*100:.0f}%" if comm_pct else "N/A (no payer data)",
        ),
        MultipleComponent(
            "Unexplained Premium",
            round(unexplained, 2),
            _pct(unexplained),
            "Entry multiple above fundamental drivers (growth, scarcity, competitive auction)",
        ),
    ]

    # Historical MOIC at different premium levels
    def _peer_moic_at_premium(premium_lo: float, premium_hi: float) -> Optional[float]:
        ms = []
        for d in sector_peers:
            ee = _ev_ebitda(d)
            m = _moic(d)
            if ee is None or m is None:
                continue
            prem = ee - (sector_median or corpus_median)
            if premium_lo <= prem < premium_hi:
                ms.append(m)
        return _percentile(sorted(ms), 0.50) if ms else None

    similar_prem_lo = max(-2.0, unexplained - 2.0)
    similar_prem_hi = unexplained + 2.0
    similar_moic = _peer_moic_at_premium(similar_prem_lo, similar_prem_hi)
    high_moic = _peer_moic_at_premium(3.0, 999)
    low_moic = _peer_moic_at_premium(-999, 0)

    # Sector benchmarks for top sectors
    from collections import defaultdict
    sector_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in corpus:
        s = (d.get("sector") or "Unknown").strip()
        sector_map[s].append(d)

    # Top 12 sectors by deal count with EV/EBITDA data
    benchmarks = []
    for s, deals in sorted(sector_map.items(), key=lambda x: -len(x[1]))[:12]:
        ees = sorted([v for d in deals for v in [_ev_ebitda(d)] if v is not None])
        moics = sorted([v for d in deals for v in [_moic(d)] if v is not None])
        if len(ees) < 2:
            continue
        # Premium vs MOIC regression for this sector
        pairs = [
            (_ev_ebitda(d), _moic(d))
            for d in deals
            if _ev_ebitda(d) is not None and _moic(d) is not None
        ]
        sl, r2 = 0.0, 0.0
        if len(pairs) >= 3:
            xs, ys = zip(*pairs)
            sl2, _ = _linear_fit(list(xs), list(ys))
            sl = sl2
            my = sum(ys) / len(ys)
            ss_res = sum((y - (sl * x + _)) ** 2 for x, y in zip(xs, ys))
            ss_tot = sum((y - my) ** 2 for y in ys)
            r2 = round(1 - ss_res / ss_tot, 3) if ss_tot > 1e-10 else 0.0
        benchmarks.append(SectorBenchmark(
            sector=s,
            n=len(deals),
            median_ev_ebitda=_percentile(ees, 0.50),
            p25_ev_ebitda=_percentile(ees, 0.25),
            p75_ev_ebitda=_percentile(ees, 0.75),
            median_moic=_percentile(moics, 0.50),
            premium_moic_slope=round(sl, 4),
            premium_moic_slope_r2=round(abs(r2), 3),
        ))

    # Top 10 peer deals by similarity
    scored = []
    for d in sector_peers:
        if _ev_ebitda(d) is None:
            continue
        sim = 0.0
        ee_diff = abs(_ev_ebitda(d) - ev_ebitda)
        sim += max(0, 30 - ee_diff * 5)
        if ev_mm and d.get("ev_mm"):
            r = float(d["ev_mm"]) / float(ev_mm)
            if 0.5 <= r <= 2.0:
                sim += 20.0 * (1 - abs(math.log(r)) / math.log(2))
        if comm_pct is not None and _comm_pct(d) is not None:
            sim += max(0, 10 - abs(comm_pct - _comm_pct(d)) * 50)
        scored.append((sim, d))
    scored.sort(key=lambda x: -x[0])
    peer_deals = [d for _, d in scored[:15]]

    return MultipleDecompResult(
        input_sector=sector,
        input_ev_mm=ev_mm,
        input_ev_ebitda=ev_ebitda,
        input_comm_pct=comm_pct,
        sector_baseline=round(baseline, 2),
        size_adjustment=round(size_adj, 2),
        payer_adjustment=round(payer_adj, 2),
        unexplained_premium=round(unexplained, 2),
        components=components,
        corpus_median_ev_ebitda=round(corpus_median, 2),
        sector_median_ev_ebitda=sector_median,
        sector_n=len(sector_peers) if sector else len(corpus),
        similar_premium_moic_p50=similar_moic,
        high_premium_moic_p50=high_moic,
        low_premium_moic_p50=low_moic,
        sector_benchmarks=benchmarks,
        peer_deals=peer_deals,
    )
