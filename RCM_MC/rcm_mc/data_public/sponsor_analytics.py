"""Sponsor league table analytics.

Aggregates corpus deals by PE sponsor (buyer), computes:
- deal count, total EV deployed
- MOIC P25/P50/P75, IRR P50
- win rate (MOIC >= 2.0x), loss rate (MOIC < 1.5x)
- sectors covered, hold year median
- rank by composite score (weighted MOIC + deal count)
"""
from __future__ import annotations

import importlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


def _load_corpus() -> List[Dict[str, Any]]:
    from .deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 35):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


def _normalize_sponsor(buyer: str) -> str:
    """Collapse fund-number suffixes and consortium splits to canonical name."""
    if not buyer:
        return "Unknown"
    # take first named entity before / or ;
    primary = re.split(r"[/;]", buyer)[0].strip()
    # remove fund numbers: "KKR Fund XII", "Warburg Pincus Private Equity XIV"
    primary = re.sub(r"\s+(Fund|PE|Partners|Capital|Growth)?\s*(X{0,3})(I{0,3}|IV|VI{0,3}|IX|X{0,3})\b", "", primary, flags=re.I).strip()
    # remove trailing roman numerals standalone
    primary = re.sub(r"\s+[IVXLC]+$", "", primary).strip()
    return primary or buyer


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


@dataclass
class SponsorStats:
    name: str
    deal_count: int
    total_ev_mm: Optional[float]
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    irr_p50: Optional[float]
    win_rate: Optional[float]   # pct deals with MOIC >= 2.0
    loss_rate: Optional[float]  # pct deals with MOIC < 1.5
    hold_p50: Optional[float]
    sectors: List[str]
    top_deals: List[str]        # top 3 by MOIC
    composite_score: float      # for ranking

    @property
    def tier(self) -> str:
        if self.deal_count >= 8 and (self.moic_p50 or 0) >= 3.0:
            return "Elite"
        if self.deal_count >= 5 or (self.moic_p50 or 0) >= 2.5:
            return "Tier 1"
        if self.deal_count >= 3:
            return "Active"
        return "Emerging"


def compute_sponsor_league(corpus: Optional[List[Dict]] = None) -> List[SponsorStats]:
    if corpus is None:
        corpus = _load_corpus()

    groups: Dict[str, List[Dict]] = defaultdict(list)
    for d in corpus:
        buyer = d.get("buyer") or ""
        name = _normalize_sponsor(buyer)
        groups[name].append(d)

    results: List[SponsorStats] = []
    for name, deals in groups.items():
        if len(deals) < 2:
            continue

        moics = [d["realized_moic"] for d in deals if d.get("realized_moic") is not None]
        irrs  = [d["realized_irr"]  for d in deals if d.get("realized_irr")  is not None]
        holds = [d["hold_years"]    for d in deals if d.get("hold_years")     is not None]
        evs   = [d["ev_mm"]         for d in deals if d.get("ev_mm")          is not None]

        win_rate  = (sum(1 for m in moics if m >= 2.0) / len(moics)) if moics else None
        loss_rate = (sum(1 for m in moics if m < 1.5)  / len(moics)) if moics else None

        sectors: List[str] = []
        seen_sec: Set[str] = set()
        for d in deals:
            s = d.get("sector")
            if s and s not in seen_sec:
                sectors.append(s)
                seen_sec.add(s)

        # top 3 deals by MOIC
        ranked = sorted(
            [(d.get("realized_moic") or 0, d.get("deal_name", "")) for d in deals],
            reverse=True,
        )
        top_deals = [name for _, name in ranked[:3]]

        moic_p50 = _percentile(moics, 50) or 0
        composite = (moic_p50 * 40) + (len(deals) * 4) + ((win_rate or 0) * 20)

        results.append(SponsorStats(
            name=name,
            deal_count=len(deals),
            total_ev_mm=sum(evs) if evs else None,
            moic_p25=_percentile(moics, 25),
            moic_p50=_percentile(moics, 50),
            moic_p75=_percentile(moics, 75),
            irr_p50=_percentile(irrs, 50),
            win_rate=win_rate,
            loss_rate=loss_rate,
            hold_p50=_percentile(holds, 50),
            sectors=sectors[:5],
            top_deals=top_deals,
            composite_score=composite,
        ))

    results.sort(key=lambda s: -s.composite_score)
    return results
