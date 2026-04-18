"""Sector intelligence analytics — corpus-calibrated benchmarks by sector.

Computes P25/P50/P75 MOIC, IRR, loss rate, average hold, and deal count
for each sector in the corpus.  Exposes vintage trend data for sparklines.
"""
from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


@dataclass
class SectorStats:
    sector: str
    n_deals: int
    moic_p25: float
    moic_p50: float
    moic_p75: float
    irr_p50: float
    avg_hold: float
    loss_rate: float          # fraction with MOIC < 1.0
    avg_ev_mm: float
    # year → [moic, ...] for sparkline
    vintage_moic: Dict[int, List[float]] = field(default_factory=dict)

    @property
    def moic_spread(self) -> float:
        return self.moic_p75 - self.moic_p25

    @property
    def sharpe_proxy(self) -> float:
        """(P50 MOIC - 1) / spread — rough dispersion-adjusted return."""
        spread = max(0.01, self.moic_spread)
        return (self.moic_p50 - 1.0) / spread


def compute_sector_stats(corpus: List[Dict[str, Any]]) -> List[SectorStats]:
    by_sector: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for d in corpus:
        s = d.get("sector")
        if s:
            by_sector[s].append(d)

    results = []
    for sector, deals in by_sector.items():
        moics = [float(d["realized_moic"]) for d in deals if d.get("realized_moic") is not None]
        irrs  = [float(d["realized_irr"])  for d in deals if d.get("realized_irr")  is not None]
        holds = [float(d["hold_years"])    for d in deals if d.get("hold_years")     is not None]
        evs   = [float(d["ev_mm"])         for d in deals if d.get("ev_mm")          is not None]

        if not moics:
            continue

        vintage_moic: Dict[int, List[float]] = collections.defaultdict(list)
        for d in deals:
            yr = d.get("year") or d.get("entry_year")
            if yr and d.get("realized_moic") is not None:
                try:
                    vintage_moic[int(yr)].append(float(d["realized_moic"]))
                except (TypeError, ValueError):
                    pass

        results.append(SectorStats(
            sector=sector,
            n_deals=len(deals),
            moic_p25=_percentile(moics, 25),
            moic_p50=_percentile(moics, 50),
            moic_p75=_percentile(moics, 75),
            irr_p50=_percentile(irrs, 50) if irrs else 0.0,
            avg_hold=sum(holds) / len(holds) if holds else 0.0,
            loss_rate=sum(1 for m in moics if m < 1.0) / len(moics),
            avg_ev_mm=sum(evs) / len(evs) if evs else 0.0,
            vintage_moic=dict(vintage_moic),
        ))

    results.sort(key=lambda s: -s.moic_p50)
    return results
