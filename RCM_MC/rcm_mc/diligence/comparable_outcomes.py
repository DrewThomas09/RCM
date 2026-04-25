"""Comparable-deal outcome benchmarking — the "what would this trade
for?" capability for healthcare PE diligence.

The classic PE diligence ask: "I'm looking at a hospital this size,
this region, this payer mix. What did similar deals trade at? What
was their realized MOIC?" Currently the tool has corpus search and
HCRIS peer X-ray, but no first-class "for THIS deal, here are N
realized comparables with their outcome distribution."

This module computes:

  1. **Match score** for every realized PE deal in the corpus,
     ranking by similarity to the input deal across:
       - Sector
       - EV size (log-scaled distance)
       - Year (favors recency)
       - Payer mix (Medicare / Medicaid pct distance)
       - Buyer overlap (same sponsor type)

  2. **Outcome distribution** across the top-N matches:
       - Realized MOIC: median, p25, p75
       - Realized IRR: median, p25, p75
       - Hold years: median
       - Win rate (% with MOIC ≥ 2.5x — the partner's "good deal" bar)

  3. **Comparable list** — top-N deals with their full row so the
     UI can render details (name, year, buyer, MOIC, IRR).

Public API::

    score_match(target, candidate) -> float
    find_comparables(corpus, target, *, top_n=5) -> List[Comparable]
    summarize_outcomes(comparables) -> Dict
    benchmark_deal(corpus, target, *, top_n=10) -> Dict   # the one-shot

Used by the new ``/diligence/comparable-outcomes?ccn=X`` page and
the ``/api/diligence/comparable-outcomes`` JSON endpoint.

Design choice: pure stdlib + already-bundled corpus. No external
data calls, no LLM, no commercial license. The corpus is what
makes this fast — 635 realized deals already on disk.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Match scoring ──────────────────────────────────────────────────

# Per-feature weights — tuned so sector mismatch alone ≈ kills the
# match (a hospital deal compared against a managed-care deal isn't
# a comparable). Recency tied for the second-largest weight because
# 2010 vintage outcomes don't predict 2024 vintage outcomes.
_W_SECTOR     = 35.0
_W_SIZE       = 20.0
_W_YEAR       = 20.0
_W_PAYER_MIX  = 15.0
_W_BUYER_TYPE = 10.0


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _sector_match(target_sector: str, candidate_sector: str) -> float:
    """1.0 for exact match, 0.5 for related-sector, 0.0 otherwise."""
    a = (target_sector or "").strip().lower()
    b = (candidate_sector or "").strip().lower()
    if not a or not b:
        return 0.5  # unknown — generous neutral
    if a == b:
        return 1.0
    # Loose adjacency map — hospitals + post_acute share margin
    # dynamics; managed_care + risk_bearing share regulatory exposure.
    related = [
        {"hospital", "post_acute", "rehabilitation"},
        {"managed_care", "risk_bearing", "insurance"},
        {"physician_practice", "specialty_group"},
    ]
    for group in related:
        if a in group and b in group:
            return 0.5
    return 0.0


def _size_distance(target_ev_mm: Optional[float],
                   candidate_ev_mm: Optional[float]) -> float:
    """1.0 when EVs are within 25% of each other on a log scale,
    decaying to 0 at 5x. None on either side → 0.5 neutral."""
    if not target_ev_mm or not candidate_ev_mm:
        return 0.5
    if target_ev_mm <= 0 or candidate_ev_mm <= 0:
        return 0.5
    ratio = max(target_ev_mm, candidate_ev_mm) / min(
        target_ev_mm, candidate_ev_mm)
    # ratio=1 → 1.0, ratio=2 → ~0.7, ratio=5 → ~0.0
    return max(0.0, 1.0 - math.log(ratio) / math.log(5.0))


def _year_recency(target_year: Optional[int],
                  candidate_year: Optional[int]) -> float:
    """Linear decay: same year = 1.0, 5y apart = 0.5, 10y+ apart = 0."""
    if target_year is None or candidate_year is None:
        return 0.5
    delta = abs(int(target_year) - int(candidate_year))
    return max(0.0, 1.0 - delta / 10.0)


def _payer_mix_match(target_mix: Optional[Dict[str, float]],
                     candidate_mix: Optional[Dict[str, float]]) -> float:
    """1.0 when Medicare + Medicaid percentages are within 5pp;
    decays linearly to 0 at 30pp+ apart. Skips when either side
    lacks payer data."""
    if not target_mix or not candidate_mix:
        return 0.5
    t_gov = (_safe_float(target_mix.get("medicare")) or 0) + \
            (_safe_float(target_mix.get("medicaid")) or 0)
    c_gov = (_safe_float(candidate_mix.get("medicare")) or 0) + \
            (_safe_float(candidate_mix.get("medicaid")) or 0)
    delta = abs(t_gov - c_gov)
    return max(0.0, 1.0 - delta / 0.30)


def _buyer_type_match(target_buyer: str, candidate_buyer: str) -> float:
    """Coarse: same buyer string = 1.0, otherwise 0.0. Real
    sponsor-tier classification is future work; for now, exact
    matches are a strong signal (NMC, KKR, Apollo, etc.) and
    everything else is neutral."""
    a = (target_buyer or "").strip().lower()
    b = (candidate_buyer or "").strip().lower()
    if not a or not b:
        return 0.5
    if a == b:
        return 1.0
    return 0.0


def score_breakdown(
    target: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, float]:
    """Return per-feature contribution to the composite match score.

    Lets the UI show a partner WHY a comparable scored 70 vs 50:
    "70 because sector + payer matched, but size is 3× off". The
    sum of the values equals what `score_match` returns.
    """
    s_sector = _sector_match(target.get("sector", ""),
                             candidate.get("sector", ""))
    s_size   = _size_distance(_safe_float(target.get("ev_mm")),
                              _safe_float(candidate.get("ev_mm")))
    s_year   = _year_recency(target.get("year"),
                             candidate.get("year"))
    s_payer  = _payer_mix_match(target.get("payer_mix"),
                                candidate.get("payer_mix"))
    s_buyer  = _buyer_type_match(target.get("buyer", ""),
                                 candidate.get("buyer", ""))
    return {
        "sector":     round(_W_SECTOR     * s_sector,     1),
        "size":       round(_W_SIZE       * s_size,       1),
        "year":       round(_W_YEAR       * s_year,       1),
        "payer_mix":  round(_W_PAYER_MIX  * s_payer,      1),
        "buyer_type": round(_W_BUYER_TYPE * s_buyer,      1),
    }


def score_match(
    target: Dict[str, Any],
    candidate: Dict[str, Any],
) -> float:
    """Return a 0–100 similarity score across the five dimensions.

    Sum of `score_breakdown(target, candidate).values()`. Inputs
    are dicts with optional keys: sector, ev_mm, year, payer_mix,
    buyer. Missing fields fall through to 0.5 neutrals so partial
    information doesn't penalize.
    """
    return round(sum(score_breakdown(target, candidate).values()), 1)


# ── Comparable record + outcome summary ────────────────────────────

@dataclass
class Comparable:
    """One realized corpus deal annotated with its match score."""
    deal: Dict[str, Any]
    score: float
    match_reasons: List[str] = field(default_factory=list)
    score_breakdown: Dict[str, float] = field(default_factory=dict)


def _explain_reasons(target: Dict[str, Any],
                     candidate: Dict[str, Any]) -> List[str]:
    """Plain-English reasons this candidate was picked. Used by the
    UI so partners see WHY each comparable is in the list."""
    reasons: List[str] = []
    if _sector_match(target.get("sector", ""),
                     candidate.get("sector", "")) >= 1.0:
        reasons.append(f"same sector ({target.get('sector')})")
    if (target.get("year") and candidate.get("year")
            and abs(target["year"] - candidate["year"]) <= 2):
        reasons.append(f"vintage within 2y of {target['year']}")
    t_ev = _safe_float(target.get("ev_mm"))
    c_ev = _safe_float(candidate.get("ev_mm"))
    if t_ev and c_ev and 0.5 <= (c_ev / t_ev) <= 2.0:
        reasons.append(f"EV within 2× ({c_ev:.0f} vs {t_ev:.0f}M)")
    if _payer_mix_match(target.get("payer_mix"),
                        candidate.get("payer_mix")) >= 0.85:
        reasons.append("similar payer mix")
    if _buyer_type_match(target.get("buyer", ""),
                         candidate.get("buyer", "")) >= 1.0:
        reasons.append(f"same sponsor ({target.get('buyer')})")
    return reasons


def find_comparables(
    corpus: Any,
    target: Dict[str, Any],
    *, top_n: int = 5,
    require_realized: bool = True,
) -> List[Comparable]:
    """Score every corpus deal and return the top-N by match score.

    ``require_realized`` filters to deals with realized_moic, since
    benchmarking is about outcome distribution; a partner doesn't
    learn from a still-held comparable.
    """
    candidates = corpus.list(
        with_moic=require_realized,
        with_irr=False,
        limit=2000,
    )
    scored: List[Comparable] = []
    for c in candidates:
        if c.get("source_id") == target.get("source_id"):
            continue  # don't compare a deal to itself
        breakdown = score_breakdown(target, c)
        sc = round(sum(breakdown.values()), 1)
        scored.append(Comparable(
            deal=c, score=sc,
            match_reasons=_explain_reasons(target, c),
            score_breakdown=breakdown,
        ))
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_n]


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * pct
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def summarize_outcomes(
    comparables: List[Comparable],
) -> Dict[str, Any]:
    """Distribution stats across a comparable set.

    Win rate: % of comparables with realized MOIC ≥ 2.5x. Standard
    "good outcome" PE bar — anything ≤ 1.5x is sub-cost-of-capital.
    """
    moics = [_safe_float(c.deal.get("realized_moic"))
             for c in comparables]
    irrs = [_safe_float(c.deal.get("realized_irr"))
            for c in comparables]
    holds = [_safe_float(c.deal.get("hold_years"))
             for c in comparables]

    moics = [m for m in moics if m is not None]
    irrs = [i for i in irrs if i is not None]
    holds = [h for h in holds if h is not None]

    win_rate = (
        sum(1 for m in moics if m >= 2.5) / len(moics)
        if moics else None
    )

    return {
        "n_comparables": len(comparables),
        "moic": {
            "median": _percentile(moics, 0.50),
            "p25":    _percentile(moics, 0.25),
            "p75":    _percentile(moics, 0.75),
        },
        "irr": {
            "median": _percentile(irrs, 0.50),
            "p25":    _percentile(irrs, 0.25),
            "p75":    _percentile(irrs, 0.75),
        },
        "hold_years_median": _percentile(holds, 0.50),
        "win_rate_2_5x":     win_rate,
        "min_score":         min((c.score for c in comparables), default=0),
        "max_score":         max((c.score for c in comparables), default=0),
    }


def benchmark_deal(
    corpus: Any,
    target: Dict[str, Any],
    *, top_n: int = 10,
) -> Dict[str, Any]:
    """One-shot: run find_comparables + summarize_outcomes and
    return both as a single dict. Caller can serialize to JSON or
    template into HTML."""
    comps = find_comparables(corpus, target, top_n=top_n)
    return {
        "target": {
            "sector": target.get("sector"),
            "ev_mm": _safe_float(target.get("ev_mm")),
            "year": target.get("year"),
            "buyer": target.get("buyer"),
        },
        "comparables": [
            {
                "deal_id": c.deal.get("source_id"),
                "deal_name": c.deal.get("deal_name"),
                "year": c.deal.get("year"),
                "buyer": c.deal.get("buyer"),
                "ev_mm": _safe_float(c.deal.get("ev_mm")),
                "realized_moic": _safe_float(c.deal.get("realized_moic")),
                "realized_irr": _safe_float(c.deal.get("realized_irr")),
                "hold_years": _safe_float(c.deal.get("hold_years")),
                "match_score": c.score,
                "match_reasons": c.match_reasons,
                "score_breakdown": c.score_breakdown,
            }
            for c in comps
        ],
        "outcome_distribution": summarize_outcomes(comps),
    }
