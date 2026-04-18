"""Return attribution analytics — MOIC decomposition by deal characteristic dimensions.

For each dimension (sector, vintage, payer regime, size bucket, hold bucket),
computes P25/P50/P75/mean MOIC and deal count. Used for IC-level attribution
and portfolio construction analysis.
"""
from __future__ import annotations

import importlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from .deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 36):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _mean(vals: List[float]) -> Optional[float]:
    return sum(vals) / len(vals) if vals else None


@dataclass
class DimSlice:
    label: str
    deal_count: int
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    moic_mean: Optional[float]
    irr_p50: Optional[float]
    win_rate: Optional[float]
    total_ev_mm: Optional[float]

    @property
    def moic_spread(self) -> Optional[float]:
        if self.moic_p25 is not None and self.moic_p75 is not None:
            return round(self.moic_p75 - self.moic_p25, 2)
        return None


@dataclass
class ReturnAttribution:
    corpus_size: int
    corpus_moic_p50: Optional[float]
    corpus_irr_p50: Optional[float]

    by_sector: List[DimSlice]
    by_vintage: List[DimSlice]       # 5-year buckets
    by_payer_regime: List[DimSlice]
    by_size_bucket: List[DimSlice]
    by_hold_bucket: List[DimSlice]
    by_ev_ebitda_bucket: List[DimSlice]


def _ev_ebitda(d: Dict[str, Any]) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
    if ev and eb and eb > 0:
        return ev / eb
    stored = d.get("ev_ebitda")
    return stored if stored and stored > 0 else None


def _payer_regime(d: Dict[str, Any]) -> str:
    pm = d.get("payer_mix")
    if not isinstance(pm, dict):
        return "Unknown"
    comm = pm.get("commercial", 0)
    mc   = pm.get("medicare", 0)
    mcaid = pm.get("medicaid", 0)
    if comm >= 0.55:
        return "Commercial"
    if mc >= 0.50:
        return "Medicare-Heavy"
    if mcaid >= 0.40:
        return "Medicaid-Heavy"
    if mc + mcaid >= 0.60:
        return "Gov-Mix"
    return "Balanced"


def _size_bucket(ev_mm: Optional[float]) -> str:
    if ev_mm is None:
        return "Unknown"
    if ev_mm < 100:
        return "Small (<$100M)"
    if ev_mm < 300:
        return "Mid ($100–300M)"
    if ev_mm < 1000:
        return "Large ($300M–1B)"
    return "Mega (>$1B)"


def _hold_bucket(hold: Optional[float]) -> str:
    if hold is None:
        return "Unknown"
    if hold < 3:
        return "Short (<3y)"
    if hold < 5:
        return "Medium (3–5y)"
    if hold < 7:
        return "Long (5–7y)"
    return "Extended (7y+)"


def _ev_ebitda_bucket(mult: Optional[float]) -> str:
    if mult is None:
        return "Unknown"
    if mult < 8:
        return "Discount (<8×)"
    if mult < 11:
        return "Fair (8–11×)"
    if mult < 14:
        return "Premium (11–14×)"
    return "Rich (14×+)"


def _vintage_bucket(year: Optional[int]) -> str:
    if year is None:
        return "Unknown"
    if year < 2005:
        return "Pre-2005"
    if year < 2010:
        return "2005–2009"
    if year < 2015:
        return "2010–2014"
    if year < 2020:
        return "2015–2019"
    return "2020+"


def _build_slices(
    groups: Dict[str, List[Dict]],
    min_n: int = 3,
    sort_by_p50: bool = True,
) -> List[DimSlice]:
    slices: List[DimSlice] = []
    for label, deals in groups.items():
        moics = [d["realized_moic"] for d in deals if d.get("realized_moic") is not None]
        irrs  = [d["realized_irr"]  for d in deals if d.get("realized_irr")  is not None]
        evs   = [d["ev_mm"]         for d in deals if d.get("ev_mm")          is not None]
        win   = (sum(1 for m in moics if m >= 2.0) / len(moics)) if moics else None
        slices.append(DimSlice(
            label=label,
            deal_count=len(deals),
            moic_p25=_percentile(moics, 25),
            moic_p50=_percentile(moics, 50),
            moic_p75=_percentile(moics, 75),
            moic_mean=_mean(moics),
            irr_p50=_percentile(irrs, 50),
            win_rate=win,
            total_ev_mm=sum(evs) if evs else None,
        ))
    if sort_by_p50:
        slices.sort(key=lambda s: -(s.moic_p50 or 0))
    return slices


def compute_return_attribution(corpus: Optional[List[Dict]] = None) -> ReturnAttribution:
    if corpus is None:
        corpus = _load_corpus()

    all_moics = [d["realized_moic"] for d in corpus if d.get("realized_moic") is not None]
    all_irrs  = [d["realized_irr"]  for d in corpus if d.get("realized_irr")  is not None]

    by_sector: Dict[str, List[Dict]] = defaultdict(list)
    by_vintage: Dict[str, List[Dict]] = defaultdict(list)
    by_payer: Dict[str, List[Dict]] = defaultdict(list)
    by_size: Dict[str, List[Dict]] = defaultdict(list)
    by_hold: Dict[str, List[Dict]] = defaultdict(list)
    by_mult: Dict[str, List[Dict]] = defaultdict(list)

    for d in corpus:
        sec = d.get("sector") or "Unknown"
        by_sector[sec].append(d)
        by_vintage[_vintage_bucket(d.get("year"))].append(d)
        by_payer[_payer_regime(d)].append(d)
        by_size[_size_bucket(d.get("ev_mm"))].append(d)
        by_hold[_hold_bucket(d.get("hold_years"))].append(d)
        by_mult[_ev_ebitda_bucket(_ev_ebitda(d))].append(d)

    # vintage sorted chronologically
    vintage_order = ["Pre-2005", "2005–2009", "2010–2014", "2015–2019", "2020+", "Unknown"]
    by_vintage_slices = [
        s for label in vintage_order
        if (s := next((x for x in _build_slices({label: by_vintage[label]}, sort_by_p50=False) if x.deal_count >= 1), None))
    ]

    return ReturnAttribution(
        corpus_size=len(corpus),
        corpus_moic_p50=_percentile(all_moics, 50),
        corpus_irr_p50=_percentile(all_irrs, 50),
        by_sector=_build_slices(dict(by_sector)),
        by_vintage=by_vintage_slices,
        by_payer_regime=_build_slices(dict(by_payer), sort_by_p50=True),
        by_size_bucket=_build_slices(dict(by_size), sort_by_p50=False),
        by_hold_bucket=_build_slices(dict(by_hold), sort_by_p50=False),
        by_ev_ebitda_bucket=_build_slices(dict(by_mult), sort_by_p50=False),
    )
