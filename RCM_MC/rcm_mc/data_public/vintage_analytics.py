"""Vintage analytics — corpus performance by deal entry year.

Computes P25/P50/P75 MOIC, IRR, deal count, hold period, and loss rate
per vintage year, enabling macro-timing analysis at IC.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _pct(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


@dataclass
class VintageStats:
    year: int
    n_deals: int
    moic_p25: float
    moic_p50: float
    moic_p75: float
    irr_p50: float
    avg_hold: float
    loss_rate: float       # fraction with MOIC < 1.0
    avg_ev_mm: float
    top_sectors: List[str] = field(default_factory=list)

    @property
    def moic_color_tier(self) -> str:
        if self.moic_p50 >= 3.0: return "green"
        if self.moic_p50 >= 2.0: return "blue"
        if self.moic_p50 >= 1.5: return "amber"
        return "red"


def compute_vintage_stats(corpus: List[Dict[str, Any]]) -> List[VintageStats]:
    by_year: Dict[int, List[Dict[str, Any]]] = collections.defaultdict(list)
    for d in corpus:
        yr = d.get("year") or d.get("entry_year")
        if yr:
            try:
                by_year[int(yr)].append(d)
            except (TypeError, ValueError):
                pass

    results = []
    for year in sorted(by_year.keys()):
        deals = by_year[year]
        moics = [float(d["realized_moic"]) for d in deals if d.get("realized_moic") is not None]
        irrs  = [float(d["realized_irr"])  for d in deals if d.get("realized_irr")  is not None]
        holds = [float(d["hold_years"])    for d in deals if d.get("hold_years")     is not None]
        evs   = [float(d["ev_mm"])         for d in deals if d.get("ev_mm")          is not None]

        if not moics:
            continue

        sector_counts = collections.Counter(d.get("sector") for d in deals if d.get("sector"))
        top_sectors = [s for s, _ in sector_counts.most_common(3)]

        results.append(VintageStats(
            year=year,
            n_deals=len(deals),
            moic_p25=_pct(moics, 25),
            moic_p50=_pct(moics, 50),
            moic_p75=_pct(moics, 75),
            irr_p50=_pct(irrs, 50) if irrs else 0.0,
            avg_hold=sum(holds) / len(holds) if holds else 0.0,
            loss_rate=sum(1 for m in moics if m < 1.0) / len(moics),
            avg_ev_mm=sum(evs) / len(evs) if evs else 0.0,
            top_sectors=top_sectors,
        ))

    return results
