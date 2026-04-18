"""Acquisition Timing Analytics — vintage cycle analysis.

Maps entry EV/EBITDA multiples and MOIC by year to identify:
  - Cycle peaks (high multiples → lower MOIC)
  - Buying opportunities (low multiples → higher MOIC)
  - Timing premium: MOIC penalty for buying at peak vs. trough multiples
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
    for i in range(2, 48):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _moic(d: Dict[str, Any]) -> Optional[float]:
    for k in ("moic", "realized_moic"):
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


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


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


@dataclass
class YearStats:
    year: int
    n: int
    n_with_moic: int
    ee_p25: Optional[float]
    ee_p50: Optional[float]
    ee_p75: Optional[float]
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    avg_hold: Optional[float]
    cycle_label: str   # Peak / Trough / Neutral


# Known cycle labels based on PE market dynamics
_CYCLE_LABELS = {
    2007: "Peak",
    2008: "Peak",
    2009: "Trough",
    2010: "Recovery",
    2011: "Recovery",
    2012: "Mid-Cycle",
    2013: "Mid-Cycle",
    2014: "Expansion",
    2015: "Expansion",
    2016: "Late Cycle",
    2017: "Late Cycle",
    2018: "Late Cycle",
    2019: "Peak",
    2020: "Trough",
    2021: "ZIRP Peak",
    2022: "Peak",
}


@dataclass
class TimingQuintile:
    quintile: int     # 1 = lowest EE, 5 = highest
    ee_range: str
    n: int
    moic_p50: Optional[float]
    moic_p25: Optional[float]
    moic_p75: Optional[float]
    loss_rate: float


@dataclass
class AcqTimingResult:
    by_year: List[YearStats]
    quintiles: List[TimingQuintile]
    # Timing premium: MOIC(quintile 1) - MOIC(quintile 5)
    timing_premium_moic: Optional[float]
    # Peak vs. trough years
    peak_years: List[int]
    trough_years: List[int]
    peak_moic_p50: Optional[float]
    trough_moic_p50: Optional[float]
    # Full corpus stats
    corpus_ee_p50: Optional[float]
    corpus_moic_p50: Optional[float]
    n_total: int


def compute_acq_timing() -> AcqTimingResult:
    corpus = _load_corpus()

    from collections import defaultdict
    by_year: Dict[int, Dict[str, List[float]]] = defaultdict(lambda: {"ees": [], "moics": [], "holds": []})

    for d in corpus:
        yr = d.get("year")
        if not yr:
            continue
        try:
            yr = int(yr)
        except (TypeError, ValueError):
            continue
        ee = _ev_ebitda(d)
        m = _moic(d)
        h = d.get("hold_years")
        if ee:
            by_year[yr]["ees"].append(ee)
        if m:
            by_year[yr]["moics"].append(m)
        if h:
            try:
                by_year[yr]["holds"].append(float(h))
            except (TypeError, ValueError):
                pass

    year_stats: List[YearStats] = []
    for yr in sorted(by_year.keys()):
        ees = sorted(by_year[yr]["ees"])
        moics = sorted(by_year[yr]["moics"])
        holds = sorted(by_year[yr]["holds"])
        label = _CYCLE_LABELS.get(yr, "Neutral")
        year_stats.append(YearStats(
            year=yr,
            n=len(by_year[yr]["ees"]) or len(by_year[yr]["moics"]),
            n_with_moic=len(moics),
            ee_p25=_percentile(ees, 0.25),
            ee_p50=_percentile(ees, 0.50),
            ee_p75=_percentile(ees, 0.75),
            moic_p25=_percentile(moics, 0.25),
            moic_p50=_percentile(moics, 0.50),
            moic_p75=_percentile(moics, 0.75),
            avg_hold=round(sum(holds) / len(holds), 2) if holds else None,
            cycle_label=label,
        ))

    # All corpus EE and MOIC
    all_ee = sorted([_ev_ebitda(d) for d in corpus if _ev_ebitda(d) is not None])
    all_moic = sorted([_moic(d) for d in corpus if _moic(d) is not None])

    # Quintile analysis of EV/EBITDA vs MOIC
    pairs = [
        (_ev_ebitda(d), _moic(d))
        for d in corpus
        if _ev_ebitda(d) is not None and _moic(d) is not None
    ]
    pairs.sort(key=lambda x: x[0])
    q_size = max(1, len(pairs) // 5)
    quintiles: List[TimingQuintile] = []
    for q in range(5):
        lo = q * q_size
        hi = lo + q_size if q < 4 else len(pairs)
        q_pairs = pairs[lo:hi]
        q_ees = sorted([p[0] for p in q_pairs])
        q_moics = sorted([p[1] for p in q_pairs])
        ee_lo = q_ees[0] if q_ees else 0
        ee_hi = q_ees[-1] if q_ees else 0
        quintiles.append(TimingQuintile(
            quintile=q + 1,
            ee_range=f"{ee_lo:.1f}× – {ee_hi:.1f}×",
            n=len(q_pairs),
            moic_p50=_percentile(q_moics, 0.50),
            moic_p25=_percentile(q_moics, 0.25),
            moic_p75=_percentile(q_moics, 0.75),
            loss_rate=round(sum(1 for m in q_moics if m < 1.0) / len(q_moics), 3) if q_moics else 0.0,
        ))

    # Timing premium
    q1_moic = quintiles[0].moic_p50 if quintiles else None
    q5_moic = quintiles[-1].moic_p50 if quintiles else None
    timing_premium = round(q1_moic - q5_moic, 3) if q1_moic and q5_moic else None

    # Peak vs. trough MOIC
    peak_yrs = [yr for yr, lbl in _CYCLE_LABELS.items() if "Peak" in lbl]
    trough_yrs = [yr for yr, lbl in _CYCLE_LABELS.items() if "Trough" in lbl or "Recovery" in lbl]
    peak_moics = sorted([m for d in corpus if _moic(d) and int(d.get("year", 0) or 0) in peak_yrs for m in [_moic(d)]])
    trough_moics = sorted([m for d in corpus if _moic(d) and int(d.get("year", 0) or 0) in trough_yrs for m in [_moic(d)]])

    return AcqTimingResult(
        by_year=year_stats,
        quintiles=quintiles,
        timing_premium_moic=timing_premium,
        peak_years=sorted(peak_yrs),
        trough_years=sorted(trough_yrs),
        peak_moic_p50=_percentile(peak_moics, 0.50),
        trough_moic_p50=_percentile(trough_moics, 0.50),
        corpus_ee_p50=_percentile(all_ee, 0.50),
        corpus_moic_p50=_percentile(all_moic, 0.50),
        n_total=len(corpus),
    )
