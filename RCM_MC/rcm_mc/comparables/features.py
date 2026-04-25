"""Feature extraction — corpus deal dict → standardized vector.

The full feature space:

    sector       — categorical, one-hot encoded across a fixed taxonomy
    size         — log(EV + 1) so a $50M deal and a $5B deal sit on
                   comparable scales
    vintage      — calendar year, demeaned
    geography    — categorical (US census region) one-hot
    payer_mix    — Medicare / Medicaid / commercial / self-pay shares
    growth       — observed growth rate (defaults to sector median if
                   missing)

All numeric features are z-score standardized using the corpus
distribution; categoricals are one-hot encoded so distance metrics
treat sector mismatches consistently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# Canonical sector taxonomy — same set the rest of the codebase uses
_SECTORS: Tuple[str, ...] = (
    "hospital", "physician_group", "mso", "asc",
    "behavioral_health", "skilled_nursing", "home_health",
    "dialysis", "managed_care", "imaging", "lab", "dental",
    "dermatology", "ophthalmology", "other",
)

# US census regions
_REGIONS: Dict[str, str] = {
    # Northeast
    "CT": "northeast", "ME": "northeast", "MA": "northeast",
    "NH": "northeast", "RI": "northeast", "VT": "northeast",
    "NJ": "northeast", "NY": "northeast", "PA": "northeast",
    # Midwest
    "IL": "midwest", "IN": "midwest", "MI": "midwest",
    "OH": "midwest", "WI": "midwest", "IA": "midwest",
    "KS": "midwest", "MN": "midwest", "MO": "midwest",
    "NE": "midwest", "ND": "midwest", "SD": "midwest",
    # South
    "DE": "south", "FL": "south", "GA": "south", "MD": "south",
    "NC": "south", "SC": "south", "VA": "south", "WV": "south",
    "AL": "south", "KY": "south", "MS": "south", "TN": "south",
    "AR": "south", "LA": "south", "OK": "south", "TX": "south",
    "DC": "south",
    # West
    "AZ": "west", "CO": "west", "ID": "west", "MT": "west",
    "NV": "west", "NM": "west", "UT": "west", "WY": "west",
    "AK": "west", "CA": "west", "HI": "west",
    "OR": "west", "WA": "west",
}
_REGION_NAMES: Tuple[str, ...] = ("northeast", "midwest",
                                  "south", "west", "unknown")


@dataclass
class FeatureVector:
    """A single deal's feature vector + provenance."""
    deal_id: str
    raw: Dict[str, Any] = field(default_factory=dict)
    vector: np.ndarray = field(default_factory=lambda: np.zeros(0))
    feature_names: List[str] = field(default_factory=list)


def _normalize_sector(s: Any) -> str:
    if not s:
        return "other"
    s_low = str(s).strip().lower().replace(" ", "_")
    return s_low if s_low in _SECTORS else "other"


def _state_to_region(state: Any) -> str:
    if not state:
        return "unknown"
    return _REGIONS.get(str(state).upper(), "unknown")


def _payer_share(payer_mix: Any, key: str) -> float:
    if isinstance(payer_mix, dict):
        return float(payer_mix.get(key, 0.0) or 0.0)
    return 0.0


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def extract_features(
    deals: List[Dict[str, Any]],
    target: Dict[str, Any],
) -> Tuple[List[FeatureVector], FeatureVector]:
    """Extract (corpus_features, target_features).

    Returns:
      (List[FeatureVector] for corpus deals, FeatureVector for target)
    Both sets share the same feature_names + the same standardization
    scheme so distances are comparable.
    """
    if not deals:
        raise ValueError("Empty corpus")

    # Build raw feature blocks
    raw_blocks: List[Dict[str, Any]] = []
    all_targets = list(deals) + [target]
    for d in all_targets:
        raw_blocks.append({
            "sector": _normalize_sector(
                d.get("sector") or d.get("subsector")),
            "log_ev": log(_safe_float(d.get("ev_mm"), 50.0) + 1),
            "year": _safe_float(d.get("year"), 2020),
            "region": _state_to_region(d.get("state")),
            "medicare_share": _payer_share(
                d.get("payer_mix"), "medicare"),
            "medicaid_share": _payer_share(
                d.get("payer_mix"), "medicaid"),
            "commercial_share": _payer_share(
                d.get("payer_mix"), "commercial"),
            "selfpay_share": _payer_share(
                d.get("payer_mix"), "self_pay"),
            "growth_rate": _safe_float(
                d.get("growth_rate"), 0.08),
        })

    # Compute z-score parameters from CORPUS only (target is the
    # deal we're matching to, so we don't want it in the moments)
    corpus_blocks = raw_blocks[:-1]
    log_evs = np.array([b["log_ev"] for b in corpus_blocks])
    years = np.array([b["year"] for b in corpus_blocks])
    growths = np.array([b["growth_rate"] for b in corpus_blocks])

    log_ev_mean = float(log_evs.mean())
    log_ev_std = float(log_evs.std() or 1.0)
    year_mean = float(years.mean())
    year_std = float(years.std() or 1.0)
    growth_mean = float(growths.mean())
    growth_std = float(growths.std() or 0.05)

    # Build feature names
    feature_names: List[str] = []
    feature_names += [f"sector_{s}" for s in _SECTORS]
    feature_names += [f"region_{r}" for r in _REGION_NAMES]
    feature_names += [
        "log_ev_z", "year_z", "growth_z",
        "medicare_share", "medicaid_share",
        "commercial_share", "selfpay_share",
    ]

    def _vec(block: Dict[str, Any]) -> np.ndarray:
        v: List[float] = []
        # sector one-hot
        for s in _SECTORS:
            v.append(1.0 if block["sector"] == s else 0.0)
        # region one-hot
        for r in _REGION_NAMES:
            v.append(1.0 if block["region"] == r else 0.0)
        # numeric z-scores
        v.append((block["log_ev"] - log_ev_mean) / log_ev_std)
        v.append((block["year"] - year_mean) / year_std)
        v.append((block["growth_rate"] - growth_mean) / growth_std)
        # payer shares (already on [0, 1])
        v.append(block["medicare_share"])
        v.append(block["medicaid_share"])
        v.append(block["commercial_share"])
        v.append(block["selfpay_share"])
        return np.array(v, dtype=float)

    corpus_features: List[FeatureVector] = []
    for d, b in zip(deals, corpus_blocks):
        corpus_features.append(FeatureVector(
            deal_id=str(d.get("source_id")
                        or d.get("deal_id") or "unknown"),
            raw=d,
            vector=_vec(b),
            feature_names=feature_names,
        ))

    target_block = raw_blocks[-1]
    target_features = FeatureVector(
        deal_id=str(target.get("source_id")
                    or target.get("deal_id") or "TARGET"),
        raw=target,
        vector=_vec(target_block),
        feature_names=feature_names,
    )

    return corpus_features, target_features
