"""Hospital archetype clustering via k-means on standardized HCRIS features.

Groups ~6,000 US hospitals into investable archetypes based on financial
and operational characteristics. Each cluster gets a PE-relevant label
(e.g., "Large Academic", "Rural Critical Access", "Suburban Profitable").

This is a core moat feature — Bloomberg shows raw financials; we show
which cluster a target belongs to, what the cluster's risk/return profile
looks like, and which peers are the best comps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


_CLUSTER_FEATURES = [
    "beds", "net_patient_revenue", "operating_margin",
    "medicare_day_pct", "medicaid_day_pct", "occupancy_rate",
    "revenue_per_bed",
]

_ARCHETYPE_LABELS = {
    0: ("Large Academic Medical Center", "large_academic",
        "High volume, high acuity, strong payer mix. Typically teaching hospitals with >400 beds."),
    1: ("Suburban Community Hospital", "suburban_community",
        "Mid-size facilities serving suburban populations. Balanced payer mix, moderate margins."),
    2: ("Rural/Critical Access", "rural_cah",
        "Small rural hospitals, high Medicare dependence, tight margins. CAH conversion candidates."),
    3: ("High-Margin Specialty", "specialty_high_margin",
        "Above-average margins driven by favorable service mix or commercial payer concentration."),
    4: ("Safety-Net/Medicaid Heavy", "safety_net",
        "High Medicaid/uncompensated care. Margin-pressured but mission-critical. DSH-dependent."),
    5: ("Mid-Market Growth", "mid_market_growth",
        "Medium hospitals with above-average revenue growth. PE platform acquisition targets."),
    6: ("Under-Performing / Distressed", "distressed",
        "Negative or near-zero margins. Restructuring candidates or distressed acquisition targets."),
}


@dataclass
class ClusterProfile:
    cluster_id: int
    label: str
    archetype: str
    description: str
    n_hospitals: int
    centroid: Dict[str, float]
    percentiles: Dict[str, Dict[str, float]]
    top_hospitals: List[Dict[str, Any]]
    pe_relevance: str


@dataclass
class HospitalClusterResult:
    ccn: str
    hospital_name: str
    cluster_id: int
    archetype: str
    label: str
    distance_to_centroid: float
    cluster_percentile: float
    nearest_peers: List[Dict[str, Any]]
    all_clusters: List[ClusterProfile]


def _kmeans(X: np.ndarray, k: int, max_iter: int = 100, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """Pure-numpy k-means clustering."""
    rng = np.random.RandomState(seed)
    n = len(X)
    idx = rng.choice(n, size=min(k, n), replace=False)
    centroids = X[idx].copy()

    for _ in range(max_iter):
        dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
        labels = np.argmin(dists, axis=1)
        new_centroids = np.zeros_like(centroids)
        for j in range(k):
            mask = labels == j
            if mask.sum() > 0:
                new_centroids[j] = X[mask].mean(axis=0)
            else:
                new_centroids[j] = centroids[j]
        if np.allclose(centroids, new_centroids, atol=1e-6):
            break
        centroids = new_centroids

    dists = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
    labels = np.argmin(dists, axis=1)
    return labels, centroids


def _assign_archetype(centroid: Dict[str, float], cluster_stats: Dict) -> Tuple[str, str, str, str]:
    """Assign PE-relevant archetype label based on cluster centroid characteristics."""
    beds = centroid.get("beds", 0)
    margin = centroid.get("operating_margin", 0)
    medicare = centroid.get("medicare_day_pct", 0)
    medicaid = centroid.get("medicaid_day_pct", 0)
    rev_per_bed = centroid.get("revenue_per_bed", 0)
    occupancy = centroid.get("occupancy_rate", 0)
    revenue = centroid.get("net_patient_revenue", 0)

    if margin < -0.15:
        return _ARCHETYPE_LABELS[6][:3] + (
            "Deeply negative margins signal severe distress. Evaluate asset-level acquisition at 4-6x normalized EBITDA.",)
    if beds > 300 and revenue > 5e8:
        return _ARCHETYPE_LABELS[0][:3] + (
            "Large medical centers trade at premium multiples (12-14x). Limited PE value creation but strong cash flow.",)
    if medicaid > 0.25 and margin < 0.03:
        return _ARCHETYPE_LABELS[4][:3] + (
            "High Medicaid dependence creates reimbursement risk. Assess DSH payments and state expansion status.",)
    if beds < 80 and medicare > 0.45:
        return _ARCHETYPE_LABELS[2][:3] + (
            "Rural/small hospitals face structural headwinds. Evaluate CAH conversion, telehealth, and rural health funding.",)
    if margin > 0.08:
        return _ARCHETYPE_LABELS[3][:3] + (
            "Above-average margins driven by service mix or payer contracts. Validate margin sustainability at 11-13x.",)
    if margin < -0.02:
        return _ARCHETYPE_LABELS[6][:3] + (
            "Negative margins signal operational distress. Evaluate turnaround thesis at discounted multiples (7-9x).",)
    if beds > 150 and occupancy > 0.45 and margin > 0.02:
        return _ARCHETYPE_LABELS[5][:3] + (
            "Mid-market hospitals with growth potential are ideal PE platforms. Target 10-11x entry, 2.5x+ MOIC.",)
    return _ARCHETYPE_LABELS[1][:3] + (
        "Community hospitals — the largest PE deal category. Focus on RCM improvement and cost optimization at 9-11x.",)


def cluster_hospitals(
    hcris_df: pd.DataFrame,
    k: int = 7,
) -> Tuple[pd.DataFrame, List[ClusterProfile]]:
    """Cluster all HCRIS hospitals into archetypes.

    Returns the DataFrame with cluster assignments and a list of ClusterProfile objects.
    """
    df = hcris_df.copy()

    if "revenue_per_bed" not in df.columns and "net_patient_revenue" in df.columns and "beds" in df.columns:
        df["revenue_per_bed"] = df["net_patient_revenue"] / df["beds"].replace(0, np.nan)
    if "operating_margin" not in df.columns and "net_patient_revenue" in df.columns and "operating_expenses" in df.columns:
        rev = df["net_patient_revenue"]
        df["operating_margin"] = ((rev - df["operating_expenses"]) / rev).where(rev > 1e5).clip(-0.5, 1.0)
    if "occupancy_rate" not in df.columns and "total_patient_days" in df.columns and "bed_days_available" in df.columns:
        df["occupancy_rate"] = df["total_patient_days"] / df["bed_days_available"].replace(0, np.nan)

    available = [f for f in _CLUSTER_FEATURES if f in df.columns]
    clean = df.dropna(subset=available).copy()

    if len(clean) < k * 5:
        df["cluster_id"] = 0
        return df, []

    X = clean[available].values.astype(float)
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std == 0] = 1
    X_norm = (X - X_mean) / X_std

    labels, centroids_norm = _kmeans(X_norm, k)
    centroids_raw = centroids_norm * X_std + X_mean

    clean["cluster_id"] = labels
    dists = np.linalg.norm(X_norm - centroids_norm[labels], axis=1)
    clean["distance_to_centroid"] = dists

    df["cluster_id"] = np.nan
    df.loc[clean.index, "cluster_id"] = clean["cluster_id"]
    df.loc[clean.index, "distance_to_centroid"] = clean["distance_to_centroid"]

    profiles = []
    for cid in range(k):
        mask = clean["cluster_id"] == cid
        cluster_df = clean[mask]
        n = int(mask.sum())
        if n == 0:
            continue

        centroid_dict = {feat: float(centroids_raw[cid, i]) for i, feat in enumerate(available)}

        stats = {}
        for feat in available:
            vals = cluster_df[feat].dropna()
            if len(vals) > 0:
                stats[feat] = {
                    "p25": float(vals.quantile(0.25)),
                    "p50": float(vals.median()),
                    "p75": float(vals.quantile(0.75)),
                    "mean": float(vals.mean()),
                }

        label, archetype, desc, pe_rel = _assign_archetype(centroid_dict, stats)

        top = cluster_df.nsmallest(5, "distance_to_centroid")
        top_list = []
        for _, row in top.iterrows():
            top_list.append({
                "ccn": str(row.get("ccn", "")),
                "name": str(row.get("name", ""))[:40],
                "state": str(row.get("state", "")),
                "beds": int(row.get("beds", 0)),
                "revenue": float(row.get("net_patient_revenue", 0)),
            })

        profiles.append(ClusterProfile(
            cluster_id=cid, label=label, archetype=archetype,
            description=desc, n_hospitals=n,
            centroid=centroid_dict, percentiles=stats,
            top_hospitals=top_list, pe_relevance=pe_rel,
        ))

    profiles.sort(key=lambda p: -p.n_hospitals)
    return df, profiles


def get_hospital_cluster(
    ccn: str,
    hcris_df: pd.DataFrame,
    k: int = 7,
) -> Optional[HospitalClusterResult]:
    """Get cluster assignment and peers for a specific hospital."""
    df, profiles = cluster_hospitals(hcris_df, k)
    match = df[df["ccn"] == ccn]
    if match.empty or pd.isna(match.iloc[0].get("cluster_id")):
        return None

    hospital = match.iloc[0]
    cid = int(hospital["cluster_id"])
    dist = float(hospital.get("distance_to_centroid", 0))

    profile = next((p for p in profiles if p.cluster_id == cid), None)
    if profile is None:
        return None

    cluster_df = df[df["cluster_id"] == cid].copy()
    cluster_dists = cluster_df["distance_to_centroid"].dropna()
    pctile = float((cluster_dists < dist).mean() * 100) if len(cluster_dists) > 0 else 50

    nearest = cluster_df[cluster_df["ccn"] != ccn].nsmallest(8, "distance_to_centroid")
    peers = []
    for _, row in nearest.iterrows():
        peers.append({
            "ccn": str(row.get("ccn", "")),
            "name": str(row.get("name", ""))[:40],
            "state": str(row.get("state", "")),
            "beds": int(row.get("beds", 0)),
            "distance": float(row.get("distance_to_centroid", 0)),
        })

    return HospitalClusterResult(
        ccn=ccn,
        hospital_name=str(hospital.get("name", "")),
        cluster_id=cid,
        archetype=profile.archetype,
        label=profile.label,
        distance_to_centroid=dist,
        cluster_percentile=pctile,
        nearest_peers=peers,
        all_clusters=profiles,
    )
