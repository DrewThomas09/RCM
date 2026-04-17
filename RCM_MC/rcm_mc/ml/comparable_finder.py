"""Comparable-hospital finder.

Given a target hospital profile, return the most-similar peers from a
larger population. Similarity is a weighted blend of six dimensions
that analysts actually defend in an IC meeting:

- bed_count           (0.25) — size is the single strongest predictor of RCM posture
- region              (0.20) — payer mix + labor rates cluster regionally
- payer_mix_similarity (0.25) — cosine similarity of payer-pct vectors
- system_affiliation  (0.10) — independent vs. health-system
- teaching_status     (0.10) — teaching/non-teaching
- urban_rural         (0.10) — urban/suburban/rural

Missing fields are handled gracefully — the missing dimension contributes
0.5 (neutral) rather than propagating NaN. This matches how a partner
thinks: "we don't know their teaching status, so treat it as a wash."
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional


# Similarity weights must sum to 1.0; exposed so tests can sanity-check.
WEIGHTS = {
    "bed_count": 0.25,
    "region": 0.20,
    "payer_mix": 0.25,
    "system_affiliation": 0.10,
    "teaching_status": 0.10,
    "urban_rural": 0.10,
}


def _bed_similarity(a: Optional[float], b: Optional[float]) -> float:
    """1 - relative bed-count difference, clipped to [0,1].

    Two 500-bed hospitals score 1.0. A 500-bed vs. 1500-bed pair scores
    1 - 1000/1500 ≈ 0.33. Missing → 0.5 (neutral)."""
    if a is None or b is None:
        return 0.5
    try:
        af, bf = float(a), float(b)
    except (TypeError, ValueError):
        return 0.5
    if af < 0 or bf < 0:
        return 0.5
    denom = max(af, bf)
    if denom <= 0:
        return 1.0
    return max(0.0, 1.0 - abs(af - bf) / denom)


def _equal_similarity(a: Any, b: Any) -> float:
    """Binary equality on normalized strings. Missing → 0.5."""
    if a is None or b is None:
        return 0.5
    sa = str(a).strip().lower()
    sb = str(b).strip().lower()
    if not sa or not sb:
        return 0.5
    return 1.0 if sa == sb else 0.0


def _payer_mix_similarity(
    a: Optional[Dict[str, float]], b: Optional[Dict[str, float]],
) -> float:
    """Cosine similarity of payer-percentage vectors.

    Keys are unioned across both mixes so missing payers contribute 0.
    Vectors are not pre-normalized — payer_mix dicts should sum to ~1
    in caller data, but we don't enforce it; cosine handles scale.
    """
    if not a or not b:
        return 0.5
    keys = set(a) | set(b)
    dot = 0.0
    na = 0.0
    nb = 0.0
    for k in keys:
        try:
            va = float(a.get(k) or 0.0)
            vb = float(b.get(k) or 0.0)
        except (TypeError, ValueError):
            va, vb = 0.0, 0.0
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na <= 0 or nb <= 0:
        return 0.5
    return max(0.0, min(1.0, dot / (math.sqrt(na) * math.sqrt(nb))))


def similarity_score(
    target: Dict[str, Any], peer: Dict[str, Any],
) -> Dict[str, float]:
    """Return ``{"score": 0-1, "components": {dim: 0-1}}``.

    Exposed for tests + for downstream code that wants to show a partner
    *why* a peer was selected."""
    components = {
        "bed_count": _bed_similarity(
            target.get("bed_count"), peer.get("bed_count")),
        "region": _equal_similarity(
            target.get("region"), peer.get("region")),
        "payer_mix": _payer_mix_similarity(
            target.get("payer_mix"), peer.get("payer_mix")),
        "system_affiliation": _equal_similarity(
            target.get("system_affiliation"),
            peer.get("system_affiliation")),
        "teaching_status": _equal_similarity(
            target.get("teaching_status"),
            peer.get("teaching_status")),
        "urban_rural": _equal_similarity(
            target.get("urban_rural"), peer.get("urban_rural")),
    }
    score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    return {"score": float(score), "components": components}


def find_comparables(
    target_hospital: Dict[str, Any],
    all_hospitals: Iterable[Dict[str, Any]],
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """Rank ``all_hospitals`` against ``target_hospital`` and return the
    top ``max_results``.

    Each returned peer is a shallow copy of the original dict augmented
    with:

    - ``similarity_score`` — float in [0, 1]
    - ``similarity_components`` — per-dimension breakdown (for partner UI)

    The target itself is excluded from the candidate pool by identity
    match on ``ccn`` if present (otherwise on object identity).
    """
    if max_results <= 0:
        return []
    target_ccn = target_hospital.get("ccn")
    ranked: List[Dict[str, Any]] = []
    for peer in all_hospitals:
        if not isinstance(peer, dict):
            continue
        if peer is target_hospital:
            continue
        if target_ccn is not None and peer.get("ccn") == target_ccn:
            continue
        sim = similarity_score(target_hospital, peer)
        enriched = dict(peer)
        enriched["similarity_score"] = sim["score"]
        enriched["similarity_components"] = sim["components"]
        ranked.append(enriched)
    ranked.sort(key=lambda p: p["similarity_score"], reverse=True)
    return ranked[:max_results]
