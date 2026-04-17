"""Concentration analytics — HHI, CR3/CR5, and diversification metrics.

Computes market/portfolio concentration across dimensions:
- Sector HHI (deal count-weighted and EV-weighted)
- Sponsor HHI
- Payer regime HHI
- Vintage HHI
- Geographic HHI

HHI = sum of squared market shares (0–10,000 scale).
"""
from __future__ import annotations

import importlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from .deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 37):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


def _hhi(shares: List[float]) -> float:
    """HHI on 0–10000 scale from market share fractions 0–1."""
    return sum((s * 100) ** 2 for s in shares)


def _cr(shares: List[float], n: int) -> float:
    """CR-n: sum of top n market shares as percent."""
    return sum(sorted(shares, reverse=True)[:n]) * 100


@dataclass
class ConcentrationDimension:
    name: str
    hhi: float
    cr3: float
    cr5: float
    top_5: List[Tuple[str, int, float]]  # (label, count, share_pct)
    total_n: int
    interpretation: str  # Competitive / Moderate / Concentrated / Highly Concentrated


def _interpret_hhi(hhi: float) -> str:
    if hhi < 1000:
        return "Competitive"
    if hhi < 1800:
        return "Moderate"
    if hhi < 2500:
        return "Concentrated"
    return "Highly Concentrated"


def _normalize_sponsor(buyer: str) -> str:
    import re
    if not buyer:
        return "Unknown"
    primary = re.split(r"[/;]", buyer)[0].strip()
    primary = re.sub(r"\s+(Fund|PE|Partners|Capital|Growth)?\s*(X{0,3})(I{0,3}|IV|VI{0,3}|IX|X{0,3})\b", "", primary, flags=re.I).strip()
    primary = re.sub(r"\s+[IVXLC]+$", "", primary).strip()
    return primary or buyer


def _payer_regime(d: Dict[str, Any]) -> str:
    pm = d.get("payer_mix")
    if not isinstance(pm, dict):
        return "Unknown"
    comm  = pm.get("commercial", 0)
    mc    = pm.get("medicare", 0)
    mcaid = pm.get("medicaid", 0)
    if comm  >= 0.55: return "Commercial"
    if mc    >= 0.50: return "Medicare-Heavy"
    if mcaid >= 0.40: return "Medicaid-Heavy"
    if mc + mcaid >= 0.60: return "Gov-Mix"
    return "Balanced"


def _build_dim(name: str, counts: Counter) -> ConcentrationDimension:
    total = sum(counts.values())
    if total == 0:
        return ConcentrationDimension(name=name, hhi=0, cr3=0, cr5=0, top_5=[], total_n=0, interpretation="N/A")
    shares = [c / total for c in counts.values()]
    hhi = _hhi(shares)
    cr3 = _cr(shares, 3)
    cr5 = _cr(shares, 5)
    top_5 = [
        (label, cnt, cnt / total * 100)
        for label, cnt in counts.most_common(5)
    ]
    return ConcentrationDimension(
        name=name,
        hhi=round(hhi, 0),
        cr3=round(cr3, 1),
        cr5=round(cr5, 1),
        top_5=top_5,
        total_n=total,
        interpretation=_interpret_hhi(hhi),
    )


@dataclass
class ConcentrationReport:
    corpus_size: int
    sector: ConcentrationDimension
    sponsor: ConcentrationDimension
    payer_regime: ConcentrationDimension
    vintage: ConcentrationDimension
    region: ConcentrationDimension
    size_bucket: ConcentrationDimension
    # EV-weighted sector
    sector_ev: ConcentrationDimension


def _size_bucket(ev_mm: Optional[float]) -> str:
    if ev_mm is None: return "Unknown"
    if ev_mm < 100:   return "Small"
    if ev_mm < 300:   return "Mid"
    if ev_mm < 1000:  return "Large"
    return "Mega"


def _vintage_bucket(year: Optional[int]) -> str:
    if year is None:    return "Unknown"
    if year < 2005:     return "Pre-2005"
    if year < 2010:     return "2005–2009"
    if year < 2015:     return "2010–2014"
    if year < 2020:     return "2015–2019"
    return "2020+"


def compute_concentration(corpus: Optional[List[Dict]] = None) -> ConcentrationReport:
    if corpus is None:
        corpus = _load_corpus()

    sector_cnt: Counter = Counter()
    sponsor_cnt: Counter = Counter()
    payer_cnt: Counter = Counter()
    vintage_cnt: Counter = Counter()
    region_cnt: Counter = Counter()
    size_cnt: Counter = Counter()

    sector_ev: Dict[str, float] = defaultdict(float)

    for d in corpus:
        sector_cnt[d.get("sector") or "Unknown"] += 1
        sponsor_cnt[_normalize_sponsor(d.get("buyer") or "")] += 1
        payer_cnt[_payer_regime(d)] += 1
        vintage_cnt[_vintage_bucket(d.get("year"))] += 1
        region_cnt[d.get("region") or "Unknown"] += 1
        size_cnt[_size_bucket(d.get("ev_mm"))] += 1
        sec = d.get("sector") or "Unknown"
        if d.get("ev_mm"):
            sector_ev[sec] += d["ev_mm"]

    # EV-weighted sector HHI
    total_ev = sum(sector_ev.values())
    sector_ev_shares = {k: v / total_ev for k, v in sector_ev.items()} if total_ev > 0 else {}
    sector_ev_counter = Counter({k: int(v * 1000) for k, v in sector_ev_shares.items()})

    return ConcentrationReport(
        corpus_size=len(corpus),
        sector=_build_dim("Sector (deal count)", sector_cnt),
        sponsor=_build_dim("Sponsor (deal count)", sponsor_cnt),
        payer_regime=_build_dim("Payer Regime", payer_cnt),
        vintage=_build_dim("Vintage Bucket", vintage_cnt),
        region=_build_dim("Region", region_cnt),
        size_bucket=_build_dim("Deal Size", size_cnt),
        sector_ev=_build_dim("Sector (EV-weighted)", sector_ev_counter),
    )
