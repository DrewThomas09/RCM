"""Comparable deal finder for the public corpus.

Given a deal dict (or a set of key metrics), finds the N most similar
closed transactions in the corpus using Euclidean distance across
normalised numeric features.

Features used for similarity (all log-scaled where appropriate):
    - ev_mm          (log2 scale)
    - ebitda_at_entry_mm (log2 scale, if present)
    - ev_ebitda_mult  (derived, if both present)
    - hold_years
    - payer_mix fractions (medicare, medicaid, commercial, self_pay)

Year is used as a soft tie-breaker but NOT as a distance dimension
(different eras have different multiples; mixing freely would penalise
recent deals vs a 2006 vintage unnecessarily).

Public API:
    ComparableDeal  dataclass
    find_comparables(query_deal, corpus_db_path, n, min_score) -> List[ComparableDeal]
    comparables_table(query_deal, corpus_db_path, n)            -> str (ASCII table)
    find_by_metrics(ev_mm, ebitda_mm, payer_mix, corpus_db_path, n) -> List[ComparableDeal]
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ComparableDeal:
    source_id: str
    deal_name: str
    year: Optional[int]
    ev_mm: Optional[float]
    ebitda_at_entry_mm: Optional[float]
    realized_moic: Optional[float]
    realized_irr: Optional[float]
    buyer: Optional[str]
    similarity_score: float        # 0-100 (100 = identical on all dimensions)
    distance: float                # raw Euclidean distance in normalised space
    matched_dimensions: List[str]  # which features were actually compared

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "deal_name": self.deal_name,
            "year": self.year,
            "ev_mm": self.ev_mm,
            "ebitda_at_entry_mm": self.ebitda_at_entry_mm,
            "realized_moic": self.realized_moic,
            "realized_irr": self.realized_irr,
            "buyer": self.buyer,
            "similarity_score": round(self.similarity_score, 1),
            "distance": round(self.distance, 4),
            "matched_dimensions": self.matched_dimensions,
        }


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

_PAYER_KEYS = ("medicare", "medicaid", "commercial", "self_pay")

_FEATURE_WEIGHTS: Dict[str, float] = {
    "log_ev":         2.0,   # size matters most
    "log_ebitda":     1.5,
    "ev_ebitda_mult": 1.5,   # valuation multiple is strongly predictive
    "hold_years":     0.8,
    "medicare":       1.0,
    "medicaid":       1.0,
    "commercial":     1.0,
    "self_pay":       0.5,
}


def _extract_features(deal: Dict[str, Any]) -> Dict[str, float]:
    feats: Dict[str, float] = {}

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    hold = deal.get("hold_years")

    if ev and ev > 0:
        feats["log_ev"] = math.log2(ev)
    if ebitda and ebitda > 0:
        feats["log_ebitda"] = math.log2(ebitda)
    if ev and ebitda and ebitda > 0:
        feats["ev_ebitda_mult"] = ev / ebitda
    if hold and hold > 0:
        feats["hold_years"] = float(hold)

    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = None
    if pm and isinstance(pm, dict):
        for key in _PAYER_KEYS:
            val = pm.get(key) or pm.get(key.replace("_", ""))
            if val is not None:
                feats[key] = float(val)

    return feats


def _weighted_distance(
    a: Dict[str, float],
    b: Dict[str, float],
    weights: Dict[str, float],
) -> Tuple[float, List[str]]:
    """Weighted Euclidean distance; returns (distance, matched_dims)."""
    shared = set(a) & set(b) & set(weights)
    if not shared:
        return float("inf"), []

    dist_sq = 0.0
    for dim in shared:
        diff = a[dim] - b[dim]
        dist_sq += weights[dim] * diff * diff

    return math.sqrt(dist_sq), sorted(shared)


def _distance_to_score(dist: float, max_dist: float = 10.0) -> float:
    """Convert distance to 0-100 similarity score (100 = identical)."""
    if dist == float("inf"):
        return 0.0
    return max(0.0, 100.0 * (1.0 - dist / max_dist))


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def _load_corpus(corpus_db_path: str) -> List[Dict[str, Any]]:
    con = sqlite3.connect(corpus_db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM public_deals").fetchall()
    con.close()
    deals = []
    for row in rows:
        d = dict(row)
        pm = d.get("payer_mix")
        if pm and isinstance(pm, str):
            try:
                d["payer_mix"] = json.loads(pm)
            except Exception:
                pass
        deals.append(d)
    return deals


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_comparables(
    query_deal: Dict[str, Any],
    corpus_db_path: str,
    n: int = 5,
    min_score: float = 0.0,
    exclude_self: bool = True,
) -> List[ComparableDeal]:
    """Find the N most similar closed deals from the corpus.

    Args:
        query_deal:       deal dict (must have at least ev_mm or payer_mix)
        corpus_db_path:   path to corpus SQLite file
        n:                number of comparables to return
        min_score:        minimum similarity score (0-100) to include
        exclude_self:     exclude the query deal itself if it is in the corpus

    Returns:
        List of ComparableDeal sorted by similarity_score descending.
    """
    query_feats = _extract_features(query_deal)
    if not query_feats:
        return []

    query_source_id = str(query_deal.get("source_id", ""))
    corpus = _load_corpus(corpus_db_path)

    results: List[ComparableDeal] = []
    for deal in corpus:
        if exclude_self and str(deal.get("source_id", "")) == query_source_id:
            continue

        corp_feats = _extract_features(deal)
        dist, matched = _weighted_distance(query_feats, corp_feats, _FEATURE_WEIGHTS)
        if not matched:
            continue

        score = _distance_to_score(dist)
        if score < min_score:
            continue

        pm = deal.get("payer_mix")
        if isinstance(pm, str):
            try:
                pm = json.loads(pm)
            except Exception:
                pm = {}

        results.append(ComparableDeal(
            source_id=str(deal.get("source_id", "")),
            deal_name=str(deal.get("deal_name", "")),
            year=deal.get("year"),
            ev_mm=deal.get("ev_mm"),
            ebitda_at_entry_mm=deal.get("ebitda_at_entry_mm"),
            realized_moic=deal.get("realized_moic"),
            realized_irr=deal.get("realized_irr"),
            buyer=deal.get("buyer"),
            similarity_score=score,
            distance=dist,
            matched_dimensions=matched,
        ))

    results.sort(key=lambda c: c.similarity_score, reverse=True)
    return results[:n]


def find_by_metrics(
    ev_mm: Optional[float] = None,
    ebitda_mm: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
    hold_years: Optional[float] = None,
    corpus_db_path: str = "corpus.db",
    n: int = 5,
) -> List[ComparableDeal]:
    """Convenience wrapper — build a query deal from raw metrics."""
    query = {}
    if ev_mm:
        query["ev_mm"] = ev_mm
    if ebitda_mm:
        query["ebitda_at_entry_mm"] = ebitda_mm
    if payer_mix:
        query["payer_mix"] = payer_mix
    if hold_years:
        query["hold_years"] = hold_years
    return find_comparables(query, corpus_db_path, n=n, exclude_self=False)


def comparables_table(
    query_deal: Dict[str, Any],
    corpus_db_path: str,
    n: int = 5,
) -> str:
    """Return an ASCII table of the N most comparable deals."""
    comps = find_comparables(query_deal, corpus_db_path, n=n)
    q_name = query_deal.get("deal_name", "Query")

    lines = [
        f"Comparable Deals for: {q_name}",
        "-" * 110,
        f"{'Score':>5}  {'Deal':<50} {'Year':>4} {'EV $M':>8} {'MOIC':>6} {'IRR':>7}  Dimensions",
        "-" * 110,
    ]
    for c in comps:
        moic = f"{c.realized_moic:.2f}x" if c.realized_moic is not None else "   —  "
        irr  = f"{c.realized_irr:.1%}"   if c.realized_irr  is not None else "    —  "
        ev   = f"${c.ev_mm:,.0f}"         if c.ev_mm         is not None else "      —"
        year = str(c.year) if c.year else "  —"
        dims = ",".join(c.matched_dimensions[:4])
        lines.append(
            f"{c.similarity_score:5.1f}  {c.deal_name[:49]:<50} {year:>4} {ev:>8} "
            f"{moic:>6} {irr:>7}  {dims}"
        )
    if not comps:
        lines.append("  (no comparable deals found — check corpus is seeded)")
    return "\n".join(lines)
