"""Signature extraction + similarity matching for Deal Autopsy.

The signature is a 9-vector in [0.0, 1.0]. Similarity uses squared
Euclidean distance normalised to the maximum theoretical distance
(sqrt(9) == 3.0). Each dimension's squared deviation is surfaced
so the UI can show "this match is driven by lease_intensity +
ebitdar_stress + medicare_mix" — the partner-facing "why" behind
the similarity score.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .library import HistoricalDeal


# Names are ordered to match the signature tuple. Keep in sync with
# :class:`HistoricalDeal.signature`.
FEATURE_NAMES: Tuple[str, ...] = (
    "lease_intensity",
    "ebitdar_stress",
    "medicare_mix",
    "payer_concentration",
    "denial_rate",
    "dar_stress",
    "regulatory_exposure",
    "physician_concentration",
    "oon_revenue_share",
)

# User-facing labels for the UI.
FEATURE_LABELS: Dict[str, str] = {
    "lease_intensity": "Lease intensity",
    "ebitdar_stress": "EBITDAR coverage stress",
    "medicare_mix": "Medicare / MA mix",
    "payer_concentration": "Top-payer concentration",
    "denial_rate": "Baseline denial rate",
    "dar_stress": "Days-in-AR stress",
    "regulatory_exposure": "Regulatory exposure",
    "physician_concentration": "Physician RVU concentration",
    "oon_revenue_share": "Out-of-network revenue share",
}

# Maximum possible Euclidean distance in a 9-D unit cube is sqrt(9).
_MAX_DISTANCE = math.sqrt(len(FEATURE_NAMES))


# ────────────────────────────────────────────────────────────────────
# DealSignature — named wrapper around the 9-tuple
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DealSignature:
    """A 9-dimension risk signature.  All fields in [0.0, 1.0]."""

    lease_intensity: float = 0.0
    ebitdar_stress: float = 0.0
    medicare_mix: float = 0.0
    payer_concentration: float = 0.0
    denial_rate: float = 0.0
    dar_stress: float = 0.0
    regulatory_exposure: float = 0.0
    physician_concentration: float = 0.0
    oon_revenue_share: float = 0.0

    # Provenance — free-form dict of (feature → source string) so the
    # UI can show "lease_intensity came from metadata.lease_pct".
    provenance: Dict[str, str] = field(default_factory=dict)

    def as_tuple(self) -> Tuple[float, ...]:
        return tuple(getattr(self, name) for name in FEATURE_NAMES)

    def to_dict(self) -> Dict[str, Any]:
        d = {name: getattr(self, name) for name in FEATURE_NAMES}
        d["provenance"] = dict(self.provenance)
        return d


# ────────────────────────────────────────────────────────────────────
# Signature extraction from CCD + metadata
# ────────────────────────────────────────────────────────────────────

def _clip01(x: float) -> float:
    if x is None or math.isnan(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _claim_amount(claim: Any) -> float:
    """Best-effort $ amount for concentration calculations."""
    for attr in ("allowed_amount", "paid_amount", "charge_amount"):
        v = getattr(claim, attr, None)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _is_denied(claim: Any) -> bool:
    status = getattr(claim, "status", None)
    v = status.value if hasattr(status, "value") else str(status or "")
    return v.upper() in ("DENIED", "WRITTEN_OFF")


def _payer_key(claim: Any) -> str:
    canonical = getattr(claim, "payer_canonical", None)
    if canonical:
        return str(canonical).upper()
    raw = getattr(claim, "payer_raw", None)
    if raw:
        return str(raw).upper()
    pc = getattr(claim, "payer_class", None)
    return str(pc.value if hasattr(pc, "value") else (pc or "UNKNOWN"))


def _payer_class(claim: Any) -> str:
    pc = getattr(claim, "payer_class", None)
    if hasattr(pc, "value"):
        return pc.value
    return str(pc or "UNKNOWN").upper()


def _network_status(claim: Any) -> str:
    ns = getattr(claim, "network_status", None)
    if ns is None:
        return "UNKNOWN"
    return str(ns).upper()


def signature_from_ccd(
    ccd: Any,
    *,
    metadata: Optional[Dict[str, float]] = None,
) -> DealSignature:
    """Build a 9-dim signature from an ingested CCD + optional
    deal metadata.

    CCD-derivable dimensions:
        denial_rate, medicare_mix, payer_concentration,
        oon_revenue_share

    Metadata-only dimensions (supply via ``metadata`` dict):
        lease_intensity, ebitdar_stress, dar_stress,
        regulatory_exposure, physician_concentration

    Metadata may also override CCD-derived dimensions — useful when
    the partner has authoritative numbers for one of them.

    Missing dimensions default to 0.0 (interpreted as "no stress").
    """
    metadata = dict(metadata or {})
    claims = list(getattr(ccd, "claims", []) or [])
    provenance: Dict[str, str] = {}

    # ---- CCD-derived ---------------------------------------------
    if claims:
        n_denied = sum(1 for c in claims if _is_denied(c))
        denial_rate = n_denied / len(claims)
        provenance["denial_rate"] = "ccd.status=DENIED"

        by_payer: Dict[str, float] = {}
        total_amount = 0.0
        medicare_amount = 0.0
        oon_amount = 0.0

        for c in claims:
            amt = _claim_amount(c)
            if amt <= 0:
                continue
            total_amount += amt
            key = _payer_key(c)
            by_payer[key] = by_payer.get(key, 0) + amt

            cls = _payer_class(c)
            if cls in ("MEDICARE", "MEDICARE_ADVANTAGE"):
                medicare_amount += amt

            if _network_status(c) == "OON":
                oon_amount += amt

        if total_amount > 0:
            top_payer_share = max(by_payer.values()) / total_amount
            medicare_mix = medicare_amount / total_amount
            oon_revenue_share = oon_amount / total_amount
            provenance["payer_concentration"] = (
                "ccd.payer_canonical top-1 share"
            )
            provenance["medicare_mix"] = (
                "ccd.payer_class in (MEDICARE, MEDICARE_ADVANTAGE)"
            )
            provenance["oon_revenue_share"] = (
                "ccd.network_status == OON"
            )
        else:
            top_payer_share = 0.0
            medicare_mix = 0.0
            oon_revenue_share = 0.0
    else:
        denial_rate = 0.0
        top_payer_share = 0.0
        medicare_mix = 0.0
        oon_revenue_share = 0.0

    # Metadata overrides + supplies the ones the CCD doesn't have.
    def _md(key: str, default: float) -> float:
        if key in metadata:
            provenance[key] = f"metadata.{key}"
            return _clip01(float(metadata[key]))
        return _clip01(default)

    sig = DealSignature(
        lease_intensity=_md("lease_intensity", 0.0),
        ebitdar_stress=_md("ebitdar_stress", 0.0),
        medicare_mix=_md("medicare_mix", medicare_mix),
        payer_concentration=_md(
            "payer_concentration", top_payer_share,
        ),
        denial_rate=_md("denial_rate", denial_rate),
        dar_stress=_md("dar_stress", 0.0),
        regulatory_exposure=_md("regulatory_exposure", 0.0),
        physician_concentration=_md("physician_concentration", 0.0),
        oon_revenue_share=_md("oon_revenue_share", oon_revenue_share),
        provenance=provenance,
    )
    return sig


# ────────────────────────────────────────────────────────────────────
# Match result + similarity scoring
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FeatureDelta:
    """One feature's contribution to the similarity score."""
    feature: str
    target_value: float
    historical_value: float
    squared_deviation: float
    # Share of the target-vs-historical squared distance. Sums to 1.0
    # across all nine features in a single MatchResult (with the
    # all-identical degenerate case returning share=0 for each).
    share_of_distance: float

    @property
    def label(self) -> str:
        return FEATURE_LABELS.get(self.feature, self.feature)

    def to_dict(self) -> Dict[str, Any]:
        return {**self.__dict__, "label": self.label}


@dataclass
class MatchResult:
    """One historical deal's match score against a target signature.

    ``similarity`` is in [0.0, 1.0] — 1.0 means identical signatures.
    ``aligning`` are the features where target and historical are
    closest (small squared deviation — they share the pattern);
    ``diverging`` are the features where they differ most (they
    share little on these).
    """
    deal: HistoricalDeal
    similarity: float
    distance: float
    feature_deltas: List[FeatureDelta]

    @property
    def aligning(self) -> List[FeatureDelta]:
        """Up to 3 features with the smallest deviation."""
        ordered = sorted(
            self.feature_deltas,
            key=lambda d: d.squared_deviation,
        )
        return ordered[:3]

    @property
    def diverging(self) -> List[FeatureDelta]:
        """Up to 3 features with the largest deviation."""
        ordered = sorted(
            self.feature_deltas,
            key=lambda d: d.squared_deviation,
            reverse=True,
        )
        return ordered[:3]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal.deal_id,
            "name": self.deal.name,
            "sponsor": self.deal.sponsor,
            "sector": self.deal.sector,
            "entry_year": self.deal.entry_year,
            "outcome": self.deal.autopsy.outcome,
            "outcome_year": self.deal.autopsy.outcome_year,
            "is_negative": self.deal.autopsy.is_negative,
            "primary_killer": self.deal.autopsy.primary_killer,
            "partner_lesson": self.deal.autopsy.partner_lesson,
            "partner_quote": self.deal.autopsy.partner_quote,
            "similarity": self.similarity,
            "distance": self.distance,
            "feature_deltas":
                [d.to_dict() for d in self.feature_deltas],
            "aligning": [d.to_dict() for d in self.aligning],
            "diverging": [d.to_dict() for d in self.diverging],
        }


def signature_distance(
    target: DealSignature, deal_sig: Tuple[float, ...],
) -> Tuple[float, List[FeatureDelta]]:
    """Compute Euclidean distance + per-feature contributions.

    Returns (distance, feature_deltas).
    Feature deltas' ``share_of_distance`` sums to 1.0 unless every
    deviation is zero (then each share is 0.0).
    """
    if len(deal_sig) != len(FEATURE_NAMES):
        raise ValueError(
            f"deal_sig must have {len(FEATURE_NAMES)} entries, "
            f"got {len(deal_sig)}",
        )
    tgt = target.as_tuple()
    sq_devs: List[float] = []
    for t_val, d_val in zip(tgt, deal_sig):
        sq = (t_val - d_val) ** 2
        sq_devs.append(sq)
    total_sq = sum(sq_devs)
    distance = math.sqrt(total_sq)
    deltas: List[FeatureDelta] = []
    for name, t_val, d_val, sq in zip(
        FEATURE_NAMES, tgt, deal_sig, sq_devs,
    ):
        share = sq / total_sq if total_sq > 0 else 0.0
        deltas.append(FeatureDelta(
            feature=name,
            target_value=float(t_val),
            historical_value=float(d_val),
            squared_deviation=float(sq),
            share_of_distance=float(share),
        ))
    return distance, deltas


def match_target(
    target: DealSignature,
    library: Tuple[HistoricalDeal, ...],
    *,
    top_k: int = 5,
    only_outcomes: Optional[Tuple[str, ...]] = None,
) -> List[MatchResult]:
    """Rank the library by similarity to ``target``.

    ``top_k`` bounds the return length (None / <=0 returns all).
    ``only_outcomes`` optionally filters to specific outcomes (e.g.,
    just the negative set when the partner wants failure-pattern
    hits).
    """
    pool = library
    if only_outcomes:
        want = set(only_outcomes)
        pool = tuple(d for d in library if d.autopsy.outcome in want)

    results: List[MatchResult] = []
    for deal in pool:
        distance, deltas = signature_distance(target, deal.signature)
        similarity = max(0.0, 1.0 - (distance / _MAX_DISTANCE))
        results.append(MatchResult(
            deal=deal,
            similarity=similarity,
            distance=distance,
            feature_deltas=deltas,
        ))

    results.sort(key=lambda r: r.similarity, reverse=True)
    if top_k and top_k > 0:
        return results[:top_k]
    return results
