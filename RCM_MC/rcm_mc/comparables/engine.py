"""Top-level entry: run_comparables_engine.

Combines feature extraction + PSM + Mahalanobis into a single
result with weight matrix, multiple distribution, and margin-
expansion benchmarks across the matched comp set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .features import FeatureVector, extract_features
from .mahalanobis import mahalanobis_match
from .psm import PSMConfig, psm_match


@dataclass
class ComparablesResult:
    target_id: str
    method: str                   # "psm" | "mahalanobis"
    matches: List[Dict[str, Any]] = field(default_factory=list)
    weight_matrix: Dict[str, float] = field(default_factory=dict)
    entry_multiple_distribution: Dict[str, float] = field(
        default_factory=dict)
    exit_multiple_distribution: Dict[str, float] = field(
        default_factory=dict)
    margin_expansion_distribution: Dict[str, float] = field(
        default_factory=dict)
    n_matches: int = 0


def _percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    arr = np.array(values, dtype=float)
    return {
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "mean": float(arr.mean()),
        "n": int(arr.size),
    }


def _entry_multiple(deal: Dict[str, Any]) -> Optional[float]:
    ev = deal.get("ev_mm")
    eb = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")
    try:
        if ev and eb:
            return float(ev) / float(eb)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return None


def _exit_multiple(deal: Dict[str, Any]) -> Optional[float]:
    moic = deal.get("realized_moic")
    if moic is None:
        moic = deal.get("moic")
    if moic is None:
        return None
    entry = _entry_multiple(deal)
    if entry is None:
        return None
    try:
        return float(entry) * float(moic)
    except (TypeError, ValueError):
        return None


def _margin_expansion(deal: Dict[str, Any]) -> Optional[float]:
    """Margin expansion in pp (entry → exit)."""
    entry_margin = deal.get("ebitda_margin_at_entry")
    exit_margin = deal.get("ebitda_margin_at_exit")
    try:
        if entry_margin is not None and exit_margin is not None:
            return float(exit_margin) - float(entry_margin)
    except (TypeError, ValueError):
        return None
    return None


def run_comparables_engine(
    corpus: List[Dict[str, Any]],
    target: Dict[str, Any],
    *,
    method: str = "psm",
    k_matches: int = 15,
    psm_config: Optional[PSMConfig] = None,
) -> ComparablesResult:
    """Run the comparables engine end-to-end.

    Steps:
      1. Extract features from corpus + target.
      2. Run PSM (default) or Mahalanobis matching.
      3. Build the weight matrix + multiple/margin distributions.

    Returns a ComparablesResult with everything the partner needs
    to defend the comp set.
    """
    corpus_fvs, target_fv = extract_features(corpus, target)

    if method == "psm":
        config = psm_config or PSMConfig(k_matches=k_matches)
        psm_result = psm_match(corpus_fvs, target_fv, config=config)
        match_tuples = psm_result.matches
        used_method = "psm"
    elif method == "mahalanobis":
        match_tuples = mahalanobis_match(
            corpus_fvs, target_fv, k_matches=k_matches)
        used_method = "mahalanobis"
    else:
        raise ValueError(
            f"method must be 'psm' or 'mahalanobis', got {method!r}")

    matches: List[Dict[str, Any]] = []
    weight_matrix: Dict[str, float] = {}
    entry_mults: List[float] = []
    exit_mults: List[float] = []
    margin_expansions: List[float] = []
    for fv, distance, weight in match_tuples:
        deal = fv.raw
        em = _entry_multiple(deal)
        xm = _exit_multiple(deal)
        me = _margin_expansion(deal)
        matches.append({
            "deal_id": fv.deal_id,
            "deal_name": deal.get("deal_name"
                                  ) or deal.get("company_name"),
            "year": deal.get("year"),
            "buyer": deal.get("buyer"),
            "ev_mm": deal.get("ev_mm"),
            "realized_moic": (deal.get("realized_moic")
                              or deal.get("moic")),
            "distance": round(distance, 4),
            "weight": round(weight, 4),
            "entry_multiple": (round(em, 2) if em else None),
            "exit_multiple": (round(xm, 2) if xm else None),
            "margin_expansion_pp": (round(me, 4) if me is not None
                                    else None),
        })
        weight_matrix[fv.deal_id] = round(weight, 4)
        if em is not None:
            entry_mults.append(em)
        if xm is not None:
            exit_mults.append(xm)
        if me is not None:
            margin_expansions.append(me)

    return ComparablesResult(
        target_id=target_fv.deal_id,
        method=used_method,
        matches=matches,
        weight_matrix=weight_matrix,
        entry_multiple_distribution=_percentiles(entry_mults),
        exit_multiple_distribution=_percentiles(exit_mults),
        margin_expansion_distribution=_percentiles(margin_expansions),
        n_matches=len(matches),
    )
