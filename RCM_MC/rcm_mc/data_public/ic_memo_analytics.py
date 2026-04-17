"""IC Memo benchmarking analytics — corpus-driven peer comparison and percentile ranks.

Given a deal's inputs (EV, EBITDA, sector, hold_years, payer mix),
computes corpus benchmarks: percentile ranks, peer comps, flag summary.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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


def _pct_rank(val: float, values: List[float]) -> float:
    """Return 0–100 percentile rank of val in values (higher = better)."""
    if not values:
        return 50.0
    below = sum(1 for v in values if v < val)
    return round(below / len(values) * 100, 1)


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


@dataclass
class PeerDeal:
    deal_name: str
    year: Optional[int]
    buyer: Optional[str]
    sector: Optional[str]
    ev_mm: Optional[float]
    ev_ebitda: Optional[float]
    moic: Optional[float]
    irr: Optional[float]
    hold_years: Optional[float]
    similarity_score: float


@dataclass
class CorpusBenchmark:
    # corpus summary
    corpus_size: int
    sector_size: int
    sector_label: str

    # percentile ranks (0–100, higher = better)
    moic_pct: Optional[float]        # vs full corpus
    irr_pct: Optional[float]
    ev_ebitda_pct: Optional[float]   # lower EV/EBITDA = more attractive entry

    # corpus P25/P50/P75 for MOIC
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]

    # sector P25/P50/P75
    sector_moic_p25: Optional[float]
    sector_moic_p50: Optional[float]
    sector_moic_p75: Optional[float]

    # EV/EBITDA corpus benchmarks
    ev_ebitda_p25: Optional[float]
    ev_ebitda_p50: Optional[float]
    ev_ebitda_p75: Optional[float]

    # hold years
    hold_p50: Optional[float]

    # peer comps
    peers: List[PeerDeal]

    # red flags
    flags: List[str]

    # deal inputs echoed back
    deal_ev_mm: Optional[float]
    deal_ebitda_mm: Optional[float]
    deal_ev_ebitda: Optional[float]
    deal_moic: Optional[float]
    deal_irr: Optional[float]
    deal_hold: Optional[float]
    deal_sector: Optional[str]


def _ev_ebitda(d: Dict[str, Any]) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
    if ev and eb and eb > 0:
        return ev / eb
    stored = d.get("ev_ebitda")
    return stored if stored and stored > 0 else None


def _similarity(
    d: Dict[str, Any],
    sector: Optional[str],
    ev_mm: Optional[float],
    ev_ebitda_val: Optional[float],
) -> float:
    score = 0.0
    d_sector = d.get("sector")
    if sector and d_sector and sector.lower() == d_sector.lower():
        score += 40
    elif sector and d_sector and (
        sector.lower() in d_sector.lower() or d_sector.lower() in sector.lower()
    ):
        score += 20

    d_ev = d.get("ev_mm")
    if ev_mm and d_ev:
        ratio = min(ev_mm, d_ev) / max(ev_mm, d_ev)
        score += 30 * ratio

    d_mult = _ev_ebitda(d)
    if ev_ebitda_val and d_mult:
        diff = abs(ev_ebitda_val - d_mult)
        score += max(0, 30 - diff * 3)

    return score


def compute_ic_benchmarks(
    deal_name: str,
    ev_mm: Optional[float],
    ebitda_mm: Optional[float],
    hold_years: Optional[float],
    sector: Optional[str],
    target_moic: Optional[float] = None,
    target_irr: Optional[float] = None,
    payer_comm_pct: Optional[float] = None,
    max_peers: int = 8,
) -> CorpusBenchmark:
    corpus = _load_corpus()

    ev_ebitda_val: Optional[float] = None
    if ev_mm and ebitda_mm and ebitda_mm > 0:
        ev_ebitda_val = ev_mm / ebitda_mm

    # collect corpus vectors
    all_moics = [d["realized_moic"] for d in corpus if d.get("realized_moic") is not None]
    all_irrs  = [d["realized_irr"]  for d in corpus if d.get("realized_irr")  is not None]
    all_ev_ebitdas = [x for d in corpus if (x := _ev_ebitda(d)) is not None]
    all_holds = [d["hold_years"] for d in corpus if d.get("hold_years") is not None]

    # sector subset
    sector_deals = [
        d for d in corpus
        if sector and d.get("sector") and sector.lower() in d["sector"].lower()
    ]
    sector_moics = [d["realized_moic"] for d in sector_deals if d.get("realized_moic") is not None]

    # percentile ranks
    moic_pct = _pct_rank(target_moic, all_moics) if target_moic is not None else None
    irr_pct  = _pct_rank(target_irr,  all_irrs)  if target_irr  is not None else None
    # lower EV/EBITDA = more attractive entry → invert rank
    ev_ebitda_pct: Optional[float] = None
    if ev_ebitda_val is not None:
        raw = _pct_rank(ev_ebitda_val, all_ev_ebitdas)
        ev_ebitda_pct = round(100 - raw, 1)

    # peers
    scored: List[Tuple[float, Dict]] = []
    for d in corpus:
        if d.get("deal_name", "") == deal_name:
            continue
        sim = _similarity(d, sector, ev_mm, ev_ebitda_val)
        if sim > 0:
            scored.append((sim, d))
    scored.sort(key=lambda x: -x[0])
    peers: List[PeerDeal] = []
    for sim_score, d in scored[:max_peers]:
        mult = _ev_ebitda(d)
        peers.append(PeerDeal(
            deal_name=d.get("deal_name", ""),
            year=d.get("year"),
            buyer=d.get("buyer"),
            sector=d.get("sector"),
            ev_mm=d.get("ev_mm"),
            ev_ebitda=mult,
            moic=d.get("realized_moic"),
            irr=d.get("realized_irr"),
            hold_years=d.get("hold_years"),
            similarity_score=round(sim_score, 1),
        ))

    # flags
    flags: List[str] = []
    if target_moic is not None and target_moic < 2.0:
        flags.append(f"Target MOIC {target_moic:.2f}× below PE convention floor of 2.0×")
    if target_irr is not None and target_irr < 0.20:
        flags.append(f"Target IRR {target_irr*100:.1f}% below typical PE hurdle of 20%")
    if ev_ebitda_val is not None and ev_ebitda_val > 18:
        flags.append(f"Entry EV/EBITDA {ev_ebitda_val:.1f}× is elevated (corpus P75 = {_percentile(all_ev_ebitdas,75) or 0:.1f}×)")
    if ev_ebitda_val is not None and ev_ebitda_val < 4:
        flags.append(f"Entry EV/EBITDA {ev_ebitda_val:.1f}× is unusually low — verify EBITDA quality")
    if hold_years is not None and hold_years > 7:
        flags.append(f"Planned hold of {hold_years:.1f} years exceeds typical fund cycle")
    if payer_comm_pct is not None and payer_comm_pct < 0.25:
        flags.append(f"Commercial payer mix {payer_comm_pct*100:.0f}% is low — revenue exposed to rate risk")
    if moic_pct is not None and moic_pct < 25:
        flags.append(f"Target MOIC ranks {moic_pct:.0f}th percentile vs corpus — below-median return profile")

    return CorpusBenchmark(
        corpus_size=len(corpus),
        sector_size=len(sector_deals),
        sector_label=sector or "All",
        moic_pct=moic_pct,
        irr_pct=irr_pct,
        ev_ebitda_pct=ev_ebitda_pct,
        moic_p25=_percentile(all_moics, 25),
        moic_p50=_percentile(all_moics, 50),
        moic_p75=_percentile(all_moics, 75),
        sector_moic_p25=_percentile(sector_moics, 25),
        sector_moic_p50=_percentile(sector_moics, 50),
        sector_moic_p75=_percentile(sector_moics, 75),
        ev_ebitda_p25=_percentile(all_ev_ebitdas, 25),
        ev_ebitda_p50=_percentile(all_ev_ebitdas, 50),
        ev_ebitda_p75=_percentile(all_ev_ebitdas, 75),
        hold_p50=_percentile(all_holds, 50),
        peers=peers,
        flags=flags,
        deal_ev_mm=ev_mm,
        deal_ebitda_mm=ebitda_mm,
        deal_ev_ebitda=ev_ebitda_val,
        deal_moic=target_moic,
        deal_irr=target_irr,
        deal_hold=hold_years,
        deal_sector=sector,
    )
