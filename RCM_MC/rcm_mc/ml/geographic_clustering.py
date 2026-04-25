"""Geographic clustering — regional RCM hotspot detection.

The existing ``hospital_clustering.py`` clusters individual
hospitals into archetypes (Academic / Rural / Distressed). The
directive asks the *regional* version: aggregate hospitals to
states / MSAs / counties, cluster the regions, identify
underperformance hotspots — the geographic 'hunting grounds' a
PE partner walks into looking for asset opportunities.

Two outputs partners care about:

  1. **Regional clusters**: which states/MSAs share similar RCM
     profiles? Cluster labels — high-performing / mid-tier /
     underperforming — let the partner stratify their pipeline.
  2. **Hotspot scores**: per-region composite z-score across
     denial rate, days-in-AR, collection rate, operating margin.
     A hotspot is a region with materially worse RCM than peer
     regions — every hospital there is a candidate target.

Method:
  - Aggregate hospital metrics to regions (mean per region).
  - Standardize features (z-score across regions).
  - K-means clustering with k chosen by partner (default 4).
  - Composite hotspot score = mean of z-scores on cost/under-
    performance metrics, sign-aligned so larger = worse.

Pure numpy throughout — no sklearn.

Public API::

    from rcm_mc.ml.geographic_clustering import (
        RegionalAggregate,
        RegionalCluster,
        HotspotResult,
        aggregate_by_region,
        cluster_regions,
        score_hotspots,
        find_hunting_grounds,
    )
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


# Cluster archetype labels assigned post-hoc based on each
# cluster's mean composite hotspot score relative to others.
_CLUSTER_LABELS = [
    "high_performing",
    "above_average",
    "mid_tier",
    "below_average",
    "underperforming",
]

# Default RCM metrics for clustering. Higher denial rate / DSO
# = worse; higher collection rate / margin = better. The
# `direction` map is used to sign the composite hotspot score.
DEFAULT_FEATURES = [
    "denial_rate",
    "days_in_ar",
    "collection_rate",
    "operating_margin",
]
FEATURE_DIRECTION = {
    "denial_rate": "lower_is_better",
    "days_in_ar": "lower_is_better",
    "collection_rate": "higher_is_better",
    "operating_margin": "higher_is_better",
    "first_pass_resolution_rate": "higher_is_better",
    "cost_to_collect": "lower_is_better",
}


@dataclass
class RegionalAggregate:
    """One region's aggregated metrics."""
    region: str
    region_type: str          # 'state' / 'msa' / 'county'
    n_hospitals: int
    metrics: Dict[str, float] = field(default_factory=dict)
    population_weight: float = 0.0  # optional, for ranking


@dataclass
class RegionalCluster:
    """One cluster of similar regions."""
    cluster_id: int
    cluster_label: str
    regions: List[str]
    n_regions: int
    centroid_metrics: Dict[str, float] = field(
        default_factory=dict)
    mean_hotspot_score: float = 0.0


@dataclass
class HotspotResult:
    """One region's hotspot diagnostic."""
    region: str
    region_type: str
    n_hospitals: int
    composite_z: float        # composite hotspot score
    metric_z_scores: Dict[str, float] = field(
        default_factory=dict)
    rank: int = 0
    is_hotspot: bool = False     # composite_z > threshold
    cluster_label: Optional[str] = None


@dataclass
class HuntingGroundReport:
    """Geographic hunting-ground summary."""
    region_type: str
    n_regions: int
    n_hospitals_total: int
    clusters: List[RegionalCluster]
    hotspots: List[HotspotResult]
    notes: List[str] = field(default_factory=list)


# ── Regional aggregation ─────────────────────────────────────

def aggregate_by_region(
    hospital_records: Iterable[Dict[str, Any]],
    *,
    region_field: str = "state",
    region_type: str = "state",
    features: Optional[List[str]] = None,
    min_hospitals: int = 3,
) -> List[RegionalAggregate]:
    """Aggregate hospital RCM metrics to regions.

    Args:
      hospital_records: dicts with the region field + RCM metrics.
      region_field: key holding the region label (e.g., 'state',
        'msa', 'county_fips').
      region_type: human label threaded into outputs.
      features: list of metrics to aggregate. Default = the four
        canonical RCM metrics.
      min_hospitals: drop regions with fewer than N hospitals —
        otherwise a single distressed asset would dominate the
        aggregate. 3 is a defensible floor.

    Returns: list of RegionalAggregate, sorted by region name.
    """
    feats = features or DEFAULT_FEATURES
    bucket: Dict[str, Dict[str, List[float]]] = (
        defaultdict(lambda: {f: [] for f in feats}))
    counts: Dict[str, int] = defaultdict(int)
    for rec in hospital_records:
        region = str(rec.get(region_field) or "").strip()
        if not region:
            continue
        counts[region] += 1
        for f in feats:
            v = rec.get(f)
            if v is None:
                continue
            try:
                bucket[region][f].append(float(v))
            except (TypeError, ValueError):
                continue

    out: List[RegionalAggregate] = []
    for region, n in counts.items():
        if n < min_hospitals:
            continue
        metrics = {}
        for f in feats:
            vals = bucket[region][f]
            if vals:
                metrics[f] = float(np.mean(vals))
        out.append(RegionalAggregate(
            region=region,
            region_type=region_type,
            n_hospitals=n,
            metrics=metrics))
    out.sort(key=lambda r: r.region)
    return out


# ── K-means (pure numpy) ─────────────────────────────────────

def _kmeans(
    X: np.ndarray,
    k: int,
    *,
    max_iter: int = 100,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Run k-means; return (labels, centroids)."""
    rng = np.random.default_rng(seed)
    n, p = X.shape
    if n == 0 or k <= 0:
        return np.array([], dtype=int), np.zeros((0, p))
    if n <= k:
        # Each point is its own cluster
        labels = np.arange(n)
        return labels, X.copy()

    # k-means++ init: pick centroids spread out
    centroids = np.zeros((k, p))
    centroids[0] = X[rng.integers(0, n)]
    for i in range(1, k):
        d2 = np.min(
            np.linalg.norm(
                X[:, None, :] - centroids[:i, :],
                axis=2) ** 2,
            axis=1,
        )
        if d2.sum() > 0:
            probs = d2 / d2.sum()
            idx = rng.choice(n, p=probs)
        else:
            idx = rng.integers(0, n)
        centroids[i] = X[idx]

    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        dists = np.linalg.norm(
            X[:, None, :] - centroids[None, :, :],
            axis=2)
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels = new_labels
        for j in range(k):
            mask = labels == j
            if mask.any():
                centroids[j] = X[mask].mean(axis=0)
    return labels, centroids


# ── Hotspot scoring ──────────────────────────────────────────

def score_hotspots(
    aggregates: List[RegionalAggregate],
    *,
    features: Optional[List[str]] = None,
    hotspot_z_threshold: float = 1.0,
) -> List[HotspotResult]:
    """Compute composite hotspot z-score per region.

    Per-feature: standardize across regions (mean 0, std 1).
    Sign-align so 'worse' is positive (denial_rate higher = +,
    collection_rate higher = - because higher is better →
    we flip).

    Composite = mean of sign-aligned z-scores. > hotspot_z_threshold
    flags the region as a hotspot.

    Returns: HotspotResult per region, sorted by composite_z DESC
    (worst first — partner's hunting list).
    """
    feats = features or DEFAULT_FEATURES
    if not aggregates:
        return []

    # Build per-feature value array
    feature_arrays: Dict[str, np.ndarray] = {}
    feature_means: Dict[str, float] = {}
    feature_stds: Dict[str, float] = {}
    for f in feats:
        vals = [a.metrics.get(f) for a in aggregates]
        # Use only non-None for mean/std
        clean = [v for v in vals if v is not None]
        if not clean:
            continue
        m = float(np.mean(clean))
        s = float(np.std(clean))
        if s < 1e-9:
            s = 1.0
        feature_arrays[f] = np.array(
            [v if v is not None else m for v in vals],
            dtype=float)
        feature_means[f] = m
        feature_stds[f] = s

    # Per-feature z-scores; sign-align so worse = positive
    z_per_feature: Dict[str, np.ndarray] = {}
    for f, arr in feature_arrays.items():
        z = (arr - feature_means[f]) / feature_stds[f]
        if FEATURE_DIRECTION.get(
                f, "lower_is_better") == "higher_is_better":
            z = -z   # flip so worse = positive
        z_per_feature[f] = z

    # Composite = mean across features
    if z_per_feature:
        z_stack = np.array(list(z_per_feature.values()))
        composite = z_stack.mean(axis=0)
    else:
        composite = np.zeros(len(aggregates))

    out: List[HotspotResult] = []
    for i, agg in enumerate(aggregates):
        metric_z = {
            f: round(float(z_per_feature[f][i]), 4)
            for f in z_per_feature
        }
        comp = float(composite[i])
        out.append(HotspotResult(
            region=agg.region,
            region_type=agg.region_type,
            n_hospitals=agg.n_hospitals,
            composite_z=round(comp, 4),
            metric_z_scores=metric_z,
            is_hotspot=comp > hotspot_z_threshold,
        ))
    # Sort by composite z descending (worst first)
    out.sort(key=lambda h: -h.composite_z)
    for rank, h in enumerate(out, start=1):
        h.rank = rank
    return out


# ── Clustering ───────────────────────────────────────────────

def cluster_regions(
    aggregates: List[RegionalAggregate],
    *,
    features: Optional[List[str]] = None,
    n_clusters: int = 4,
    seed: int = 42,
) -> List[RegionalCluster]:
    """K-means cluster regions on RCM features.

    Returns clusters sorted by mean_hotspot_score ascending
    (best cluster first). Cluster labels assigned post-hoc from
    _CLUSTER_LABELS based on cluster rank.
    """
    feats = features or DEFAULT_FEATURES
    if not aggregates or n_clusters <= 0:
        return []

    # Build feature matrix; drop regions missing any feature
    rows = []
    for a in aggregates:
        if all(f in a.metrics for f in feats):
            rows.append(a)
    if not rows:
        return []
    X = np.array(
        [[a.metrics[f] for f in feats] for a in rows],
        dtype=float)
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds < 1e-9] = 1.0
    Xs = (X - means) / stds

    k = min(n_clusters, len(rows))
    labels, centroids = _kmeans(Xs, k, seed=seed)

    # Score each cluster by mean composite z (using
    # sign-aligned features — same logic as score_hotspots)
    cluster_hotspot: Dict[int, List[float]] = defaultdict(list)
    for i, a in enumerate(rows):
        z_signed = []
        for j, f in enumerate(feats):
            z = Xs[i, j]
            if FEATURE_DIRECTION.get(
                    f, "lower_is_better"
                    ) == "higher_is_better":
                z = -z
            z_signed.append(z)
        cluster_hotspot[int(labels[i])].append(
            float(np.mean(z_signed)))

    # Build clusters
    clusters: List[RegionalCluster] = []
    for cid in range(k):
        members = [a for i, a in enumerate(rows)
                   if int(labels[i]) == cid]
        centroid = centroids[cid]
        centroid_unscaled = (centroid * stds) + means
        centroid_dict = {
            f: round(float(centroid_unscaled[j]), 4)
            for j, f in enumerate(feats)
        }
        mean_hotspot = (
            float(np.mean(cluster_hotspot[cid]))
            if cluster_hotspot[cid] else 0.0)
        clusters.append(RegionalCluster(
            cluster_id=cid,
            cluster_label="",  # assigned below
            regions=[m.region for m in members],
            n_regions=len(members),
            centroid_metrics=centroid_dict,
            mean_hotspot_score=round(mean_hotspot, 4),
        ))

    # Sort clusters by hotspot score ascending (best first),
    # assign labels by rank
    clusters.sort(key=lambda c: c.mean_hotspot_score)
    for i, c in enumerate(clusters):
        if i < len(_CLUSTER_LABELS):
            c.cluster_label = _CLUSTER_LABELS[i]
        else:
            c.cluster_label = f"tier_{i}"
    return clusters


# ── End-to-end composer ─────────────────────────────────────

def find_hunting_grounds(
    hospital_records: Iterable[Dict[str, Any]],
    *,
    region_field: str = "state",
    region_type: str = "state",
    features: Optional[List[str]] = None,
    n_clusters: int = 4,
    min_hospitals_per_region: int = 3,
    hotspot_z_threshold: float = 1.0,
) -> HuntingGroundReport:
    """One-call composer: aggregate + cluster + score hotspots.

    Returns a HuntingGroundReport with both clusters and per-region
    hotspot scores. The hotspot list is the partner's hunting
    list — regions ranked by composite RCM underperformance.
    """
    records_list = list(hospital_records)
    aggregates = aggregate_by_region(
        records_list,
        region_field=region_field,
        region_type=region_type,
        features=features,
        min_hospitals=min_hospitals_per_region)
    clusters = cluster_regions(
        aggregates,
        features=features,
        n_clusters=n_clusters)
    hotspots = score_hotspots(
        aggregates,
        features=features,
        hotspot_z_threshold=hotspot_z_threshold)

    # Attach cluster labels back to hotspot rows
    region_to_cluster: Dict[str, str] = {}
    for c in clusters:
        for r in c.regions:
            region_to_cluster[r] = c.cluster_label
    for h in hotspots:
        h.cluster_label = region_to_cluster.get(h.region)

    notes: List[str] = []
    n_hotspots = sum(1 for h in hotspots if h.is_hotspot)
    if n_hotspots > 0:
        notes.append(
            f"{n_hotspots} region"
            f"{'s' if n_hotspots != 1 else ''} flagged as "
            f"underperformance hotspots "
            f"(composite z > {hotspot_z_threshold}). Top: "
            f"{', '.join(h.region for h in hotspots[:3] if h.is_hotspot)}.")
    if not aggregates:
        notes.append(
            f"No regions met the {min_hospitals_per_region}-"
            f"hospital floor; ingest more hospital records "
            f"or lower min_hospitals_per_region.")

    return HuntingGroundReport(
        region_type=region_type,
        n_regions=len(aggregates),
        n_hospitals_total=sum(
            a.n_hospitals for a in aggregates),
        clusters=clusters,
        hotspots=hotspots,
        notes=notes,
    )
