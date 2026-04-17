"""Enhanced comparables engine for the public deals corpus.

Improves on the base comparables.py by adding:
  - Multi-dimensional similarity scoring (EV, payer mix, leverage, vintage)
  - Payer-mix cosine similarity for nuanced Medicare/Medicaid matching
  - Leverage-adjusted return normalization
  - Peer group percentile ranking
  - Human-readable comp tables

Public API:
    similarity_score(deal_a, deal_b)       -> float (0-1)
    find_enhanced_comps(target, corpus, n) -> list[dict]
    peer_group_percentiles(target, comps)  -> dict
    comp_table_enhanced(comps)             -> str
    leverage_adj_moic(deal)                -> Optional[float]
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _payer_vec(deal: Dict) -> Optional[List[float]]:
    """Return [medicare, medicaid, commercial, selfpay] float vector or None."""
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            return None
    if not isinstance(pm, dict):
        return None
    keys = ["medicare", "medicaid", "commercial", "selfpay"]
    vals = [float(pm.get(k, 0.0) or 0.0) for k in keys]
    return vals


def _cosine_sim(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _log_size_sim(ev_a: float, ev_b: float) -> float:
    """Similarity on log EV scale; returns 0-1 where 1 = identical."""
    if ev_a <= 0 or ev_b <= 0:
        return 0.0
    diff = abs(math.log(ev_a) - math.log(ev_b))
    return math.exp(-diff)


def _vintage_sim(yr_a: int, yr_b: int) -> float:
    """Vintage year similarity; decays with |yr_a - yr_b|."""
    gap = abs(yr_a - yr_b)
    return math.exp(-gap / 3.0)


def _keyword_overlap(a: str, b: str) -> float:
    """Jaccard overlap on deal-name tokens for deal-type signal."""
    _STOPWORDS = {"the", "a", "an", "of", "and", "&", "-", "/", "–"}
    def _tokens(s: str) -> set:
        return {t.lower() for t in s.split() if t.lower() not in _STOPWORDS and len(t) > 2}
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------------------------------------------------------------------------
# Leverage-adjusted MOIC
# ---------------------------------------------------------------------------

def leverage_adj_moic(deal: Dict[str, Any]) -> Optional[float]:
    """Normalize realized MOIC to a notional 5x leverage deal.

    A rough de-levering: if leverage < 5x the deal had less risk and
    we scale moic down; if > 5x scale up.  Uses simplified equity
    contribution ratio adjustment.  Returns None if data is missing.
    """
    moic = _safe_float(deal.get("realized_moic"))
    lev = _safe_float(deal.get("leverage_x"))
    ebitda = _safe_float(deal.get("ebitda_at_entry_mm"))
    ev = _safe_float(deal.get("ev_mm"))

    if moic is None:
        return None
    if lev is None or ev is None or ebitda is None or ev <= 0:
        return moic  # can't adjust; return as-is

    equity_pct = max(0.1, 1.0 - (lev * ebitda / ev))
    ref_equity_pct = max(0.1, 1.0 - (5.0 * ebitda / ev))
    if ref_equity_pct == 0 or equity_pct == 0:
        return moic
    # Scale moic proportionally to equity contribution ratio
    adj = moic * (equity_pct / ref_equity_pct)
    return round(adj, 3)


# ---------------------------------------------------------------------------
# Core similarity
# ---------------------------------------------------------------------------

_WEIGHTS = {
    "ev_size": 0.30,
    "payer_mix": 0.30,
    "vintage": 0.20,
    "deal_type": 0.20,
}


def similarity_score(
    deal_a: Dict[str, Any],
    deal_b: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Multi-dimensional similarity score between two deals (0–1).

    Dimensions: EV log-scale (30%), payer mix cosine (30%),
    vintage proximity (20%), deal-name keyword Jaccard (20%).
    """
    w = weights or _WEIGHTS

    scores: Dict[str, float] = {}

    # EV size
    ev_a = _safe_float(deal_a.get("ev_mm"))
    ev_b = _safe_float(deal_b.get("ev_mm"))
    if ev_a and ev_b:
        scores["ev_size"] = _log_size_sim(ev_a, ev_b)
    else:
        scores["ev_size"] = 0.5  # neutral when data missing

    # Payer mix
    pv_a = _payer_vec(deal_a)
    pv_b = _payer_vec(deal_b)
    if pv_a and pv_b:
        scores["payer_mix"] = _cosine_sim(pv_a, pv_b)
    else:
        scores["payer_mix"] = 0.5

    # Vintage
    yr_a = deal_a.get("year")
    yr_b = deal_b.get("year")
    if yr_a and yr_b:
        scores["vintage"] = _vintage_sim(int(yr_a), int(yr_b))
    else:
        scores["vintage"] = 0.5

    # Deal type via name keywords
    name_a = str(deal_a.get("deal_name") or "")
    name_b = str(deal_b.get("deal_name") or "")
    scores["deal_type"] = _keyword_overlap(name_a, name_b)

    total = sum(w.get(dim, 0) * s for dim, s in scores.items())
    total_w = sum(w.values())
    return round(total / total_w if total_w > 0 else 0.0, 4)


# ---------------------------------------------------------------------------
# Find comps
# ---------------------------------------------------------------------------

def find_enhanced_comps(
    target: Dict[str, Any],
    corpus: List[Dict[str, Any]],
    n: int = 5,
    min_similarity: float = 0.0,
) -> List[Dict[str, Any]]:
    """Find the n most similar deals in corpus to target.

    Excludes the target itself (matched by source_id or deal_name).
    Returns list of dicts with original deal fields plus 'similarity_score'.
    """
    target_id = target.get("source_id") or target.get("deal_name")

    scored = []
    for deal in corpus:
        deal_id = deal.get("source_id") or deal.get("deal_name")
        if deal_id == target_id:
            continue
        score = similarity_score(target, deal)
        if score >= min_similarity:
            row = dict(deal)
            row["similarity_score"] = score
            scored.append(row)

    scored.sort(key=lambda d: d["similarity_score"], reverse=True)
    return scored[:n]


# ---------------------------------------------------------------------------
# Peer-group percentiles
# ---------------------------------------------------------------------------

def peer_group_percentiles(
    target: Dict[str, Any],
    comps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """How does the target rank among its comps on MOIC, EV, IRR?

    Returns percentile ranks (0-100) and absolute position.
    """
    def _pct_rank(pool: List[float], val: float) -> float:
        if not pool:
            return 50.0
        below = sum(1 for v in pool if v < val)
        return round(100.0 * below / len(pool), 1)

    moic_t = _safe_float(target.get("realized_moic"))
    irr_t = _safe_float(target.get("realized_irr"))
    ev_t = _safe_float(target.get("ev_mm"))

    comp_moics = [v for c in comps if (v := _safe_float(c.get("realized_moic"))) is not None]
    comp_irrs = [v for c in comps if (v := _safe_float(c.get("realized_irr"))) is not None]
    comp_evs = [v for c in comps if (v := _safe_float(c.get("ev_mm"))) is not None]

    result: Dict[str, Any] = {"comp_count": len(comps)}
    if moic_t is not None and comp_moics:
        result["moic_percentile"] = _pct_rank(comp_moics, moic_t)
        result["moic_comp_median"] = sorted(comp_moics)[len(comp_moics) // 2]
    if irr_t is not None and comp_irrs:
        result["irr_percentile"] = _pct_rank(comp_irrs, irr_t)
    if ev_t is not None and comp_evs:
        result["ev_percentile"] = _pct_rank(comp_evs, ev_t)

    return result


# ---------------------------------------------------------------------------
# Table output
# ---------------------------------------------------------------------------

def comp_table_enhanced(comps: List[Dict[str, Any]], max_rows: int = 10) -> str:
    """Formatted enhanced comparables table."""
    if not comps:
        return "No comparable deals found.\n"

    lines = [
        "Enhanced Comparable Deals",
        "=" * 92,
        f"{'Deal':<42} {'Year':>5} {'EV ($M)':>9} {'MOIC':>6} {'IRR':>7} {'Sim':>6}",
        "-" * 92,
    ]
    for comp in comps[:max_rows]:
        name = str(comp.get("deal_name") or "")[:41]
        yr = str(comp.get("year") or "")
        ev = comp.get("ev_mm")
        ev_s = f"{ev:,.0f}" if ev is not None else "N/A"
        moic = comp.get("realized_moic")
        moic_s = f"{moic:.2f}x" if moic is not None else "N/A"
        irr = comp.get("realized_irr")
        irr_s = f"{irr:.1%}" if irr is not None else "N/A"
        sim = comp.get("similarity_score", 0.0)
        lines.append(
            f"{name:<42} {yr:>5} {ev_s:>9} {moic_s:>6} {irr_s:>7} {sim:>6.3f}"
        )
    lines.append("=" * 92)
    return "\n".join(lines) + "\n"
