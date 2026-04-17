"""Deal Risk Scorer — composite risk scoring for every deal in the corpus.

Scores each deal across 5 dimensions:
  1. Entry Multiple Risk   (EV/EBITDA vs sector median)
  2. Payer Concentration   (HHI of payer mix)
  3. Hold Duration Risk    (vs optimal hold for sector)
  4. Vintage Cycle Risk    (market cycle at entry year)
  5. Size Risk             (mega-deals and micro-deals carry extra risk)

Produces a composite 0–100 risk score and tier (Low/Medium/High/Critical).
Realized MOIC is used to validate: high-risk deals should underperform.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 46):
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


# Vintage cycle risk: years with elevated macro/credit risk
_VINTAGE_RISK = {
    2007: 25, 2008: 30, 2009: 20,  # GFC
    2020: 15, 2021: 20,            # COVID/ZIRP bubble
    2022: 15,                       # rate shock
}


def _hhi(d: Dict[str, Any]) -> float:
    """Compute payer HHI (0-10000 scale)."""
    pm = d.get("payer_mix")
    if not isinstance(pm, dict):
        return 5000.0  # unknown = assume concentrated
    shares = []
    for v in pm.values():
        try:
            shares.append(float(v))
        except (TypeError, ValueError):
            pass
    if not shares:
        return 5000.0
    return sum((s * 100) ** 2 for s in shares)


@dataclass
class DealRiskScore:
    source_id: str
    company_name: str
    sector: str
    year: int
    ev_mm: Optional[float]
    ev_ebitda: Optional[float]
    moic: Optional[float]

    # Component scores (0–100, higher = more risk)
    entry_multiple_score: float
    payer_concentration_score: float
    hold_duration_score: float
    vintage_cycle_score: float
    size_score: float

    composite_score: float
    tier: str   # Low / Medium / High / Critical

    # Weights applied
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class RiskDistribution:
    tier: str
    n: int
    pct: float
    avg_moic: Optional[float]
    moic_p50: Optional[float]


@dataclass
class DealRiskResult:
    total_deals: int
    scored_deals: List[DealRiskScore]
    distribution: List[RiskDistribution]
    # Validation: risk tier vs. realized MOIC
    tier_moic: Dict[str, Optional[float]]
    # By sector aggregates
    sector_avg_risk: List[Dict[str, Any]]
    corpus_avg_score: float
    pct_high_critical: float


_WEIGHTS = {
    "entry_multiple": 0.30,
    "payer_concentration": 0.20,
    "hold_duration": 0.20,
    "vintage_cycle": 0.15,
    "size": 0.15,
}


def _entry_multiple_score(ee: Optional[float], sector_median: float) -> float:
    """0–100 score based on EV/EBITDA vs sector median."""
    if ee is None:
        return 40.0  # neutral
    premium = ee - sector_median
    if premium <= -2:
        return 5.0
    if premium <= 0:
        return 15.0
    if premium <= 2:
        return 35.0
    if premium <= 4:
        return 55.0
    if premium <= 6:
        return 75.0
    return min(100.0, 75 + (premium - 6) * 5)


def _payer_concentration_score(hhi: float) -> float:
    """0–100 score based on payer HHI."""
    if hhi < 2500:
        return 10.0
    if hhi < 4000:
        return 25.0
    if hhi < 6000:
        return 45.0
    if hhi < 8000:
        return 65.0
    return 85.0


def _hold_duration_score(hold: Optional[float], sector_opt: float) -> float:
    """0–100 score: short holds (flips) and very long holds both carry risk."""
    if hold is None:
        return 40.0
    if hold < 2.0:
        return 80.0   # flip risk
    if hold < 3.0:
        return 50.0
    diff_from_opt = abs(hold - sector_opt)
    if diff_from_opt <= 1.0:
        return 10.0
    if diff_from_opt <= 2.5:
        return 30.0
    if diff_from_opt <= 4.0:
        return 55.0
    return 75.0


def _vintage_cycle_score(year: int) -> float:
    return float(_VINTAGE_RISK.get(year, 5))


def _size_score(ev_mm: Optional[float]) -> float:
    if ev_mm is None:
        return 30.0
    if ev_mm < 30:
        return 70.0   # micro-deal execution risk
    if ev_mm < 75:
        return 40.0
    if ev_mm < 500:
        return 10.0   # sweet spot
    if ev_mm < 1500:
        return 25.0
    if ev_mm < 3000:
        return 50.0
    return 70.0       # mega-deal


def _tier(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Medium"
    if score < 70:
        return "High"
    return "Critical"


def compute_deal_risk_scores() -> DealRiskResult:
    corpus = _load_corpus()

    # Build sector median EV/EBITDA and optimal hold
    from collections import defaultdict
    sector_ees: Dict[str, List[float]] = defaultdict(list)
    sector_holds: Dict[str, List[float]] = defaultdict(list)

    for d in corpus:
        sec = (d.get("sector") or "Unknown").strip()
        ee = _ev_ebitda(d)
        h = d.get("hold_years")
        if ee:
            sector_ees[sec].append(ee)
        if h:
            try:
                sector_holds[sec].append(float(h))
            except (TypeError, ValueError):
                pass

    sector_medians: Dict[str, float] = {}
    sector_opt_holds: Dict[str, float] = {}
    for sec, ees in sector_ees.items():
        sector_medians[sec] = _percentile(sorted(ees), 0.50) or 10.0
    for sec, holds in sector_holds.items():
        # Optimal hold = P50 of deals with above-median MOIC
        good_holds = [
            h for d, h in zip(
                [d for d in corpus if (d.get("sector") or "Unknown").strip() == sec],
                holds,
            )
            if (_moic(d) or 0) >= 2.5
        ]
        sector_opt_holds[sec] = _percentile(sorted(good_holds or holds), 0.50) or 4.5

    global_ee_median = _percentile(
        sorted([ee for ees in sector_ees.values() for ee in ees]),
        0.50,
    ) or 10.0
    global_opt_hold = 4.5

    # Score every deal
    scored: List[DealRiskScore] = []
    for d in corpus:
        sec = (d.get("sector") or "Unknown").strip()
        ee = _ev_ebitda(d)
        ev = d.get("ev_mm")
        try:
            ev_f = float(ev) if ev else None
        except (TypeError, ValueError):
            ev_f = None
        h = d.get("hold_years")
        try:
            h_f = float(h) if h else None
        except (TypeError, ValueError):
            h_f = None
        year = int(d["year"]) if d.get("year") else 2015
        hhi = _hhi(d)
        sec_med = sector_medians.get(sec, global_ee_median)
        sec_opt = sector_opt_holds.get(sec, global_opt_hold)

        em_s = _entry_multiple_score(ee, sec_med)
        pc_s = _payer_concentration_score(hhi)
        hd_s = _hold_duration_score(h_f, sec_opt)
        vc_s = _vintage_cycle_score(year)
        sz_s = _size_score(ev_f)

        composite = (
            em_s * _WEIGHTS["entry_multiple"]
            + pc_s * _WEIGHTS["payer_concentration"]
            + hd_s * _WEIGHTS["hold_duration"]
            + vc_s * _WEIGHTS["vintage_cycle"]
            + sz_s * _WEIGHTS["size"]
        )
        composite = round(composite, 1)

        scored.append(DealRiskScore(
            source_id=d.get("source_id", ""),
            company_name=d.get("company_name") or d.get("deal_name") or "",
            sector=sec,
            year=year,
            ev_mm=ev_f,
            ev_ebitda=ee,
            moic=_moic(d),
            entry_multiple_score=round(em_s, 1),
            payer_concentration_score=round(pc_s, 1),
            hold_duration_score=round(hd_s, 1),
            vintage_cycle_score=round(vc_s, 1),
            size_score=round(sz_s, 1),
            composite_score=composite,
            tier=_tier(composite),
            weights=dict(_WEIGHTS),
        ))

    # Distribution
    tiers = ["Low", "Medium", "High", "Critical"]
    dist = []
    total = len(scored)
    for t in tiers:
        t_deals = [d for d in scored if d.tier == t]
        moics = sorted([d.moic for d in t_deals if d.moic is not None])
        avg_m = round(sum(moics) / len(moics), 3) if moics else None
        dist.append(RiskDistribution(
            tier=t,
            n=len(t_deals),
            pct=round(len(t_deals) / total * 100, 1) if total else 0.0,
            avg_moic=avg_m,
            moic_p50=_percentile(moics, 0.50),
        ))

    # Tier vs realized MOIC
    tier_moic = {t: next((d.moic_p50 for d in dist if d.tier == t), None) for t in tiers}

    # By sector
    sec_groups: Dict[str, List[DealRiskScore]] = defaultdict(list)
    for ds in scored:
        sec_groups[ds.sector].append(ds)
    sector_risk = sorted(
        [
            {
                "sector": sec,
                "n": len(ds),
                "avg_score": round(sum(d.composite_score for d in ds) / len(ds), 1),
                "pct_high": round(sum(1 for d in ds if d.tier in ("High", "Critical")) / len(ds) * 100, 1),
                "moic_p50": _percentile(sorted([d.moic for d in ds if d.moic is not None]), 0.50),
            }
            for sec, ds in sec_groups.items()
            if len(ds) >= 3
        ],
        key=lambda x: -x["avg_score"],
    )[:15]

    avg_score = round(sum(d.composite_score for d in scored) / len(scored), 1) if scored else 0.0
    n_hc = sum(1 for d in scored if d.tier in ("High", "Critical"))
    pct_hc = round(n_hc / len(scored) * 100, 1) if scored else 0.0

    return DealRiskResult(
        total_deals=len(scored),
        scored_deals=scored,
        distribution=dist,
        tier_moic=tier_moic,
        sector_avg_risk=sector_risk,
        corpus_avg_score=avg_score,
        pct_high_critical=pct_hc,
    )
