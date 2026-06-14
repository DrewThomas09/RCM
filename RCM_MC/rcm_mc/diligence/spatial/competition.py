"""Spatial competition: Huff gravity model + Moran's I — numpy + stdlib.

The rigorous version of "service area." A radius circle around a
facility is a lie — it ignores that patients flow to bigger, closer,
more attractive competitors and that a competitor across the street
guts your capture. The **Huff gravity model** estimates patient-capture
*probability* as attractiveness / distance^β, normalized across all
competitors, so TAM and white-space stop being circles. **Moran's I**
then tests whether utilization actually clusters in space (a real
catchment) or is just noise.

What's here (all numpy + stdlib — distances via haversine, no geo deps):

* :func:`huff_capture` — per-facility expected patient capture and
  market share from demand-point populations and facility
  attractiveness, with a tunable distance-decay β.
* :func:`morans_i` — global spatial autocorrelation of a variable over
  locations (inverse-distance, row-standardized weights), with a
  normal-approximation z/p and a clustered/dispersed/random verdict.

Honesty about the method:
    * Straight-line (great-circle) distance, not drive time. Drive-time
      isochrones need a routing engine (an optional geo extra); β can be
      raised to proxy for travel friction in the meantime.
    * Huff attractiveness is whatever proxy you pass (beds, providers,
      service breadth) — the model is only as good as that proxy, so it
      is an explicit input, not hidden.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

CITATION_KEY = "SP1"
SOURCE_MODULE = "diligence.spatial"

_EARTH_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return 2 * _EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True)
class Facility:
    facility_id: str
    lat: float
    lon: float
    attractiveness: float            # beds / providers / service breadth proxy


@dataclass(frozen=True)
class DemandPoint:
    point_id: str
    lat: float
    lon: float
    demand: float                    # population / expected volume


@dataclass
class HuffResult:
    facility_capture: Dict[str, float]
    market_share: Dict[str, float]
    total_demand: float
    beta: float
    target_facility_id: Optional[str]
    target_capture: Optional[float]
    target_share: Optional[float]
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facility_capture": {
                k: round(v, 2) for k, v in self.facility_capture.items()
            },
            "market_share": {
                k: round(v, 6) for k, v in self.market_share.items()
            },
            "total_demand": round(self.total_demand, 2),
            "beta": self.beta,
            "target_facility_id": self.target_facility_id,
            "target_capture": (
                None if self.target_capture is None
                else round(self.target_capture, 2)
            ),
            "target_share": (
                None if self.target_share is None
                else round(self.target_share, 6)
            ),
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def huff_capture(
    demand_points: Sequence[DemandPoint],
    facilities: Sequence[Facility],
    beta: float = 2.0,
    min_distance_km: float = 0.5,
    target_facility_id: Optional[str] = None,
) -> HuffResult:
    """Huff gravity-model capture.

    For each demand point, P(choose facility j) ∝ A_j / d_ij^β,
    normalized across all facilities; expected capture for j is the
    demand-weighted sum of those probabilities. ``min_distance_km``
    floors distance so a facility sitting on a demand centroid doesn't
    blow up to infinite utility."""
    if not facilities:
        raise ValueError("need at least one facility")
    fac = list(facilities)
    capture = {f.facility_id: 0.0 for f in fac}
    total_demand = 0.0
    for dp in demand_points:
        total_demand += dp.demand
        utils = []
        for f in fac:
            d = max(haversine_km(dp.lat, dp.lon, f.lat, f.lon), min_distance_km)
            utils.append(f.attractiveness / (d ** beta))
        s = sum(utils)
        if s <= 0:
            continue
        for f, u in zip(fac, utils):
            capture[f.facility_id] += dp.demand * (u / s)

    share = {
        k: (v / total_demand if total_demand > 0 else 0.0)
        for k, v in capture.items()
    }
    tcap = capture.get(target_facility_id) if target_facility_id else None
    tshare = share.get(target_facility_id) if target_facility_id else None
    res = HuffResult(
        facility_capture=capture, market_share=share,
        total_demand=total_demand, beta=beta,
        target_facility_id=target_facility_id,
        target_capture=tcap, target_share=tshare,
    )
    res.headline = _huff_headline(res)
    return res


def _huff_headline(res: HuffResult) -> str:
    if not res.market_share:
        return "Huff model: no capture computed."
    leader = max(res.market_share, key=res.market_share.get)
    base = (
        f"Huff (β={res.beta}): leader {leader} captures "
        f"{res.market_share[leader] * 100:.1f}% of {res.total_demand:,.0f} "
        f"demand units."
    )
    if res.target_facility_id is not None and res.target_share is not None:
        base += (
            f" Target {res.target_facility_id}: {res.target_share * 100:.1f}% "
            f"share ({res.target_capture:,.0f} captured)."
        )
    return base


# ────────────────────────────────────────────────────────────────────
# Moran's I
# ────────────────────────────────────────────────────────────────────

class SpatialVerdict(str, Enum):
    CLUSTERED = "CLUSTERED"          # positive autocorrelation (real catchment)
    DISPERSED = "DISPERSED"          # negative autocorrelation (checkerboard)
    RANDOM = "RANDOM"                # no significant spatial structure


@dataclass
class MoranResult:
    morans_i: float
    expected_i: float
    z_score: float
    p_value: float
    n: int
    verdict: SpatialVerdict
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "morans_i": round(self.morans_i, 6),
            "expected_i": round(self.expected_i, 6),
            "z_score": round(self.z_score, 4),
            "p_value": round(self.p_value, 6),
            "n": self.n,
            "verdict": self.verdict.value,
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def morans_i(
    lats: Sequence[float],
    lons: Sequence[float],
    values: Sequence[float],
    min_distance_km: float = 0.5,
) -> MoranResult:
    """Global Moran's I with inverse-distance, row-standardized weights.

    Tests whether ``values`` (e.g. utilization, cost) cluster in space.
    Significance uses the normality-assumption variance and a normal
    z-approximation (dependency-free). Verdict: CLUSTERED if I is
    significantly above its expectation, DISPERSED if significantly
    below, else RANDOM."""
    lat = np.asarray(lats, dtype=float)
    lon = np.asarray(lons, dtype=float)
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 3:
        return MoranResult(0.0, 0.0, 0.0, 1.0, n, SpatialVerdict.RANDOM,
                           "Too few locations for Moran's I (need ≥3).")

    # Inverse-distance weights, zero diagonal.
    W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = max(haversine_km(lat[i], lon[i], lat[j], lon[j]), min_distance_km)
            W[i, j] = 1.0 / d
    # Row-standardize.
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    W = W / row_sums

    xbar = x.mean()
    z = x - xbar
    S0 = W.sum()
    denom = float((z ** 2).sum())
    if denom == 0 or S0 == 0:
        return MoranResult(0.0, -1.0 / (n - 1), 0.0, 1.0, n,
                           SpatialVerdict.RANDOM,
                           "Zero variance in values — Moran's I undefined.")
    num = float(z @ W @ z)
    i_stat = (n / S0) * (num / denom)
    E_I = -1.0 / (n - 1)

    # Normality-assumption variance.
    S1 = 0.5 * float(((W + W.T) ** 2).sum())
    row = W.sum(axis=1)
    col = W.sum(axis=0)
    S2 = float(((row + col) ** 2).sum())
    var = (
        (n ** 2 * S1 - n * S2 + 3 * S0 ** 2)
        / ((n ** 2 - 1) * S0 ** 2)
    ) - E_I ** 2
    z_score = (i_stat - E_I) / math.sqrt(var) if var > 0 else 0.0
    p = 2.0 * (1.0 - _phi(abs(z_score)))

    if p < 0.05 and i_stat > E_I:
        verdict = SpatialVerdict.CLUSTERED
    elif p < 0.05 and i_stat < E_I:
        verdict = SpatialVerdict.DISPERSED
    else:
        verdict = SpatialVerdict.RANDOM

    res = MoranResult(
        morans_i=i_stat, expected_i=E_I, z_score=z_score, p_value=p,
        n=n, verdict=verdict,
    )
    res.headline = (
        f"Moran's I = {i_stat:.3f} (E[I]={E_I:.3f}, z={z_score:.2f}, p={p:.3f}): "
        f"utilization is spatially {verdict.value.lower()}."
    )
    return res


# ────────────────────────────────────────────────────────────────────
# Local Moran's I (LISA) — where the hot/cold spots are
# ────────────────────────────────────────────────────────────────────

@dataclass
class LisaPoint:
    """Local indicator of spatial association for one location."""
    index: int
    local_i: float
    spatial_lag: float
    quadrant: str                    # HH / LL / HL / LH
    p_value: float
    significant: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "local_i": round(self.local_i, 6),
            "spatial_lag": round(self.spatial_lag, 6),
            "quadrant": self.quadrant,
            "p_value": round(self.p_value, 4),
            "significant": self.significant,
        }


@dataclass
class LisaResult:
    points: List[LisaPoint]
    n: int
    n_hot: int                       # significant High-High
    n_cold: int                      # significant Low-Low
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "n": self.n, "n_hot": self.n_hot, "n_cold": self.n_cold,
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def local_morans_i(
    lats: Sequence[float],
    lons: Sequence[float],
    values: Sequence[float],
    min_distance_km: float = 0.5,
    permutations: int = 199,
    seed: int = 0,
) -> LisaResult:
    """Local Moran's I (LISA) — classifies each location as a hot spot
    (High-High), cold spot (Low-Low), or spatial outlier (High-Low /
    Low-High), with a conditional-permutation pseudo p-value.

    Global Moran's I says *whether* utilization clusters; LISA says
    *where* — which facilities sit in a high-utilization neighborhood
    (a real catchment) vs which are isolated outliers. The permutation
    test (hold location i fixed, shuffle the rest) is dependency-free
    and the standard LISA inference."""
    lat = np.asarray(lats, dtype=float)
    lon = np.asarray(lons, dtype=float)
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 3:
        return LisaResult([], n, 0, 0, "Too few locations for LISA (need ≥3).")

    W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = max(haversine_km(lat[i], lon[i], lat[j], lon[j]), min_distance_km)
            W[i, j] = 1.0 / d
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    W = W / row_sums

    z = x - x.mean()
    m2 = float((z ** 2).sum()) / n
    if m2 == 0:
        return LisaResult([], n, 0, 0, "Zero variance — LISA undefined.")

    rng = np.random.default_rng(seed)
    points: List[LisaPoint] = []
    n_hot = n_cold = 0
    for i in range(n):
        lag = float(W[i] @ z)
        ii = (z[i] / m2) * lag
        # Conditional permutation: shuffle the other n-1 z's into j≠i.
        others = np.delete(z, i)
        w_i = np.delete(W[i], i)
        perm_i = np.empty(permutations)
        for p in range(permutations):
            shuffled = rng.permutation(others)
            perm_i[p] = (z[i] / m2) * float(w_i @ shuffled)
        ge = int(np.sum(np.abs(perm_i) >= abs(ii)))
        pval = (ge + 1) / (permutations + 1)
        if z[i] > 0 and lag > 0:
            quad = "HH"
        elif z[i] < 0 and lag < 0:
            quad = "LL"
        elif z[i] > 0 and lag < 0:
            quad = "HL"
        else:
            quad = "LH"
        sig = pval < 0.05
        if sig and quad == "HH":
            n_hot += 1
        elif sig and quad == "LL":
            n_cold += 1
        points.append(LisaPoint(i, ii, lag, quad, pval, sig))

    res = LisaResult(points=points, n=n, n_hot=n_hot, n_cold=n_cold)
    res.headline = (
        f"LISA over {n} locations: {n_hot} hot spot(s) (High-High), "
        f"{n_cold} cold spot(s) (Low-Low) at p<0.05."
    )
    return res


# ────────────────────────────────────────────────────────────────────
# New-entrant competitive impact
# ────────────────────────────────────────────────────────────────────

@dataclass
class EntrantImpactResult:
    target_facility_id: str
    capture_before: float
    capture_after: float
    volume_at_risk: float            # before − after (≥0 when entrant hurts)
    pct_volume_lost: float
    new_entrant_capture: float
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_facility_id": self.target_facility_id,
            "capture_before": round(self.capture_before, 2),
            "capture_after": round(self.capture_after, 2),
            "volume_at_risk": round(self.volume_at_risk, 2),
            "pct_volume_lost": round(self.pct_volume_lost, 6),
            "new_entrant_capture": round(self.new_entrant_capture, 2),
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def competitor_impact(
    demand_points: Sequence[DemandPoint],
    existing_facilities: Sequence[Facility],
    new_entrant: Facility,
    target_facility_id: str,
    beta: float = 2.0,
    min_distance_km: float = 0.5,
) -> EntrantImpactResult:
    """Volume-at-risk to a target facility from a new competitor opening.

    Runs the Huff model with and without ``new_entrant`` and returns the
    target's capture before/after, the absolute volume at risk, and the
    new entrant's own capture — the rigorous answer to "how much does
    the clinic opening down the road actually take from us?\""""
    before = huff_capture(
        demand_points, existing_facilities, beta=beta,
        min_distance_km=min_distance_km, target_facility_id=target_facility_id,
    )
    after = huff_capture(
        demand_points, list(existing_facilities) + [new_entrant], beta=beta,
        min_distance_km=min_distance_km, target_facility_id=target_facility_id,
    )
    cap_before = before.target_capture or 0.0
    cap_after = after.target_capture or 0.0
    var = cap_before - cap_after
    pct = (var / cap_before) if cap_before > 0 else 0.0
    res = EntrantImpactResult(
        target_facility_id=target_facility_id,
        capture_before=cap_before, capture_after=cap_after,
        volume_at_risk=var, pct_volume_lost=pct,
        new_entrant_capture=after.facility_capture.get(new_entrant.facility_id, 0.0),
    )
    res.headline = (
        f"New entrant {new_entrant.facility_id} puts {var:,.0f} units "
        f"({pct * 100:.1f}% of capture) at risk for {target_facility_id} "
        f"(capture {cap_before:,.0f} → {cap_after:,.0f})."
    )
    return res
