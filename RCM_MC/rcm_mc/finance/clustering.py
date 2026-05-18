"""Phase-5 clustering layer for the regression rebuild.

Phase 1 added rule-based segments (Academic / Critical Access /
Large Community / …) via name + CCN + bed-count heuristics. That
catches the obvious regimes but leaves real structure on the table
— e.g. a Large Community hospital with 90% Medicaid days, urban
location, and tiny operating margin is operating in a different
economic regime than a Large Community hospital with a balanced
payer mix and average occupancy, even though they share the same
rule-based label.

Phase 5 runs an unsupervised pass on the **structural** features
(deliberately excluding net_patient_revenue and its derivatives,
which would bake the answer into the clusters) to surface those
within-segment regime differences. Two algorithms, run in
sequence so the partner can compare:

  1. **Rule-based segments** — already available from
     ``hospital_taxonomy.derive_taxonomy``; reused as the baseline
     "what we'd get without clustering."

  2. **k-means** on PCA-reduced structural features, with the
     k chosen via either the elbow heuristic or partner override.
     Clusters auto-named by dominant rule-based segment + the
     bed-class / payer-class / safety-net flavour of the cluster
     centroid (e.g. "Cluster A: 312 hospitals — mostly Small
     Community · medicare_heavy · high Medicaid share").

DIAGNOSTIC SCOPE: clusters are an exploratory diagnostic, not a
sourcing recommendation. A cluster being labeled "high-margin urban
community" doesn't mean every member is a good acquisition target
— it means they share a structural profile worth segmenting before
the regression slopes are fit.

Numpy-only — no sklearn dependency (CLAUDE.md no-new-deps rule).
PCA via SVD; k-means via k-means++ init + Lloyd's iteration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Structural feature set used for clustering. Deliberately excludes
# net_patient_revenue + its derivatives because clustering on the
# regression target would bake the answer into the clusters. Bed
# count is log-transformed (heavy right-skew across hospitals);
# payer percentages are 0–100 raw; occupancy is 0–1.
STRUCTURAL_FEATURES: tuple[str, ...] = (
    "log_beds",
    "occupancy_rate",
    "medicare_day_pct",
    "medicaid_day_pct",
    "academic_or_teaching",     # binary
    "flagship_specialty",       # binary
    "critical_access",          # binary
    "safety_net_proxy",         # binary
    "expense_per_bed_log",
)


def prepare_clustering_features(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, List[str], pd.Index]:
    """Return (X, feature_names, source_index) ready for clustering.

    X is z-score-normalized (so PCA / k-means treat each feature
    on a comparable scale). source_index lets callers join cluster
    labels back to the original df rows.

    Drops any rows where ANY structural feature is missing.
    Computes log_beds and expense_per_bed_log on the fly. The
    taxonomy flags must already be present (call
    ``hospital_taxonomy.derive_taxonomy`` first).
    """
    if "academic_flag" not in df.columns:
        raise ValueError(
            "df is missing taxonomy columns (academic_flag, "
            "critical_access_flag, etc.). Call "
            "hospital_taxonomy.derive_taxonomy(df) before clustering."
        )

    out = df.copy()

    # Derived features the structural set expects
    beds = pd.to_numeric(out.get("beds"), errors="coerce")
    out["log_beds"] = np.log(beds.where(beds > 0))

    # occupancy_rate may already be present (added by
    # regression_page._add_computed_features); compute defensively
    if "occupancy_rate" not in out.columns:
        days = pd.to_numeric(
            out.get("total_patient_days"), errors="coerce",
        )
        cap = pd.to_numeric(
            out.get("bed_days_available"), errors="coerce",
        )
        out["occupancy_rate"] = (days / cap.where(cap > 0)).clip(0, 1.5)

    # Binary flags squashed to 0/1 floats so PCA / k-means treat
    # them as a small numeric perturbation
    out["academic_or_teaching"] = (
        out["academic_flag"] | out["teaching_flag"]
    ).astype(float)
    out["flagship_specialty"] = out["flagship_specialty_flag"].astype(float)
    out["critical_access"] = out["critical_access_flag"].astype(float)
    out["safety_net_proxy"] = out["safety_net_proxy_flag"].astype(float)

    opex = pd.to_numeric(
        out.get("operating_expenses"), errors="coerce",
    )
    safe_beds = beds.where(beds > 0)
    out["expense_per_bed_log"] = np.log(
        (opex / safe_beds).where((opex / safe_beds) > 0)
    )

    feature_cols = list(STRUCTURAL_FEATURES)
    clean = out[feature_cols].dropna()
    if len(clean) == 0:
        return np.zeros((0, len(feature_cols))), feature_cols, clean.index

    X = clean.values.astype(float)
    # Z-score normalize. Use ddof=0 (population std) for stability
    # when a column has zero variance (which would normally happen
    # for the binary flags on a tiny segment).
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    X_norm = (X - mu) / sigma
    return X_norm, feature_cols, clean.index


@dataclass(frozen=True)
class PCAResult:
    """SVD-based PCA. ``scores`` is the projection of every row onto
    the top-``n_components`` axes; ``components`` is the loading
    matrix; ``explained_variance_ratio`` is the share of total
    variance each component captures."""
    scores: np.ndarray
    components: np.ndarray
    explained_variance_ratio: np.ndarray


def run_pca(X: np.ndarray, n_components: int = 2) -> PCAResult:
    """SVD-based PCA. Returns the projected scores plus the loading
    matrix + explained variance ratios. Assumes X is already
    z-score normalized (call ``prepare_clustering_features`` first).
    """
    if X.size == 0:
        return PCAResult(
            scores=np.zeros((0, n_components)),
            components=np.zeros((n_components, 0)),
            explained_variance_ratio=np.zeros(n_components),
        )
    n, p = X.shape
    n_components = min(n_components, p, n)
    U, s, Vt = np.linalg.svd(X, full_matrices=False)
    scores = U[:, :n_components] * s[:n_components]
    components = Vt[:n_components]
    var = (s ** 2) / max(n - 1, 1)
    total_var = var.sum() if var.sum() > 0 else 1.0
    return PCAResult(
        scores=scores,
        components=components,
        explained_variance_ratio=var[:n_components] / total_var,
    )


def _kmeans_pp_init(
    X: np.ndarray, k: int, rng: np.random.Generator,
) -> np.ndarray:
    """k-means++ initialization for stable starting centroids."""
    n = len(X)
    centroids = np.empty((k, X.shape[1]))
    first = rng.integers(n)
    centroids[0] = X[first]
    # Squared distances to the nearest existing centroid
    closest = np.sum((X - centroids[0]) ** 2, axis=1)
    for i in range(1, k):
        probs = closest / closest.sum() if closest.sum() > 0 else None
        if probs is None:
            pick = rng.integers(n)
        else:
            pick = rng.choice(n, p=probs)
        centroids[i] = X[pick]
        new_d = np.sum((X - centroids[i]) ** 2, axis=1)
        closest = np.minimum(closest, new_d)
    return centroids


@dataclass
class KMeansResult:
    """k-means fit result.

    ``labels`` is one cluster index per row of X.
    ``centroids`` is the k × p cluster-center matrix in the
    z-score-normalized feature space (caller can multiply back if
    they want raw-units centroids).
    ``inertia`` is the sum of squared distances to the assigned
    centroid — the standard "k-means loss" used for elbow analysis.
    """
    labels: np.ndarray
    centroids: np.ndarray
    inertia: float
    n_iter: int


def run_kmeans(
    X: np.ndarray, k: int,
    *,
    max_iter: int = 100,
    tol: float = 1e-4,
    random_state: int = 42,
) -> KMeansResult:
    """Lloyd's k-means with k-means++ init.

    Deterministic given ``random_state`` — partner re-running the
    page should see the same cluster IDs. Stops when centroid shift
    is below ``tol`` or after ``max_iter`` iterations.
    """
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")
    n = len(X)
    if n < k:
        raise ValueError(f"k={k} > n={n}; need at least {k} rows")

    rng = np.random.default_rng(random_state)
    centroids = _kmeans_pp_init(X, k, rng)
    labels = np.zeros(n, dtype=int)

    for it in range(max_iter):
        # Assign each point to its nearest centroid
        dists = np.linalg.norm(
            X[:, None, :] - centroids[None, :, :], axis=2,
        )
        new_labels = np.argmin(dists, axis=1)
        if it > 0 and np.all(new_labels == labels):
            labels = new_labels
            break
        labels = new_labels
        # Recompute centroids
        new_centroids = np.array([
            X[labels == c].mean(axis=0) if np.any(labels == c)
            else centroids[c]
            for c in range(k)
        ])
        shift = np.linalg.norm(new_centroids - centroids)
        centroids = new_centroids
        if shift < tol:
            break

    # Inertia = sum of squared distances to assigned centroid
    inertia = float(np.sum(
        np.linalg.norm(X - centroids[labels], axis=1) ** 2
    ))
    return KMeansResult(
        labels=labels,
        centroids=centroids,
        inertia=inertia,
        n_iter=it + 1,
    )


@dataclass(frozen=True)
class ClusterProfile:
    """Per-cluster business profile used to auto-name a cluster.

    ``dominant_segment`` is the rule-based taxonomy label with the
    highest share within the cluster. ``segment_share`` is that
    share (0–1). The other fields summarize the cluster's
    structural characteristics in partner-readable terms.
    """
    cluster_id: int
    size: int
    dominant_segment: str
    segment_share: float
    median_beds: float
    median_medicare_pct: float
    median_medicaid_pct: float
    safety_net_share: float
    academic_share: float
    name: str  # auto-generated business name


def profile_clusters(
    labels: np.ndarray,
    source_df: pd.DataFrame,
) -> List[ClusterProfile]:
    """Build a partner-readable profile per cluster.

    ``source_df`` should be the taxonomy-tagged frame restricted to
    the rows that survived ``prepare_clustering_features`` (same
    index alignment). ``labels`` is the per-row cluster id.

    Auto-names use the dominant rule-based segment plus the
    most-distinguishing structural feature (Medicare-heavy,
    high-Medicaid, safety-net, etc.). Names are short and
    business-readable per the rebuild plan — \"Mostly Critical
    Access · medicare-heavy\" not \"Cluster 2\".
    """
    profiles: List[ClusterProfile] = []
    for cid in sorted(np.unique(labels)):
        mask = labels == cid
        sub = source_df.iloc[mask]
        if len(sub) == 0:
            continue
        seg_counts = sub["segment_label"].value_counts()
        dom = seg_counts.index[0]
        share = float(seg_counts.iloc[0]) / len(sub)
        med_beds = float(pd.to_numeric(
            sub.get("beds"), errors="coerce",
        ).median())
        med_mc = float(pd.to_numeric(
            sub.get("medicare_day_pct"), errors="coerce",
        ).median())
        med_md = float(pd.to_numeric(
            sub.get("medicaid_day_pct"), errors="coerce",
        ).median())
        sn_share = float(sub["safety_net_proxy_flag"].mean())
        acad_share = float(
            (sub["academic_flag"] | sub["teaching_flag"]).mean()
        )

        # Compose a short business name: dominant segment +
        # distinguishing flavour. Flavour wins when its share is
        # noticeably above the global rate; otherwise the segment
        # label alone tells the story.
        flavours = []
        if med_mc >= 55:
            flavours.append("medicare-heavy")
        elif med_mc <= 25:
            flavours.append("commercial-heavy")
        if sn_share > 0.5:
            flavours.append("high-Medicaid")
        if acad_share > 0.5 and dom != "Academic":
            flavours.append("teaching-affiliated")
        if med_beds < 25:
            flavours.append("micro")
        elif med_beds >= 400:
            flavours.append("flagship-scale")
        flavour_str = " · ".join(flavours)

        if share >= 0.8:
            name = (
                f"Mostly {dom}" + (f" · {flavour_str}" if flavour_str else "")
            )
        else:
            name = (
                f"Mixed: {dom} ({share * 100:.0f}%)"
                + (f" · {flavour_str}" if flavour_str else "")
            )

        profiles.append(ClusterProfile(
            cluster_id=int(cid),
            size=int(len(sub)),
            dominant_segment=str(dom),
            segment_share=share,
            median_beds=med_beds,
            median_medicare_pct=med_mc,
            median_medicaid_pct=med_md,
            safety_net_share=sn_share,
            academic_share=acad_share,
            name=name,
        ))
    return profiles


@dataclass
class ClusteringResult:
    """Top-level result bundling everything the UI needs."""
    k: int
    n_rows: int
    features: List[str]
    pca: PCAResult
    kmeans: KMeansResult
    profiles: List[ClusterProfile]
    # Index of the rows that survived prepare_clustering_features —
    # so the UI can join cluster IDs back to the source df.
    source_index: pd.Index

    def to_dict(self) -> Dict[str, object]:
        return {
            "k": self.k,
            "n_rows": self.n_rows,
            "features": self.features,
            "explained_variance_ratio": [
                round(float(v), 4)
                for v in self.pca.explained_variance_ratio
            ],
            "inertia": round(self.kmeans.inertia, 4),
            "n_iter": self.kmeans.n_iter,
            "profiles": [
                {
                    "cluster_id": p.cluster_id,
                    "name": p.name,
                    "size": p.size,
                    "dominant_segment": p.dominant_segment,
                    "segment_share": round(p.segment_share, 4),
                    "median_beds": round(p.median_beds, 0),
                    "median_medicare_pct": round(p.median_medicare_pct, 1),
                    "median_medicaid_pct": round(p.median_medicaid_pct, 1),
                    "safety_net_share": round(p.safety_net_share, 3),
                    "academic_share": round(p.academic_share, 3),
                }
                for p in self.profiles
            ],
        }


def cluster_hospitals(
    df: pd.DataFrame, *,
    k: int = 6,
    random_state: int = 42,
) -> ClusteringResult:
    """End-to-end: prepare features → PCA → k-means → profile.

    ``df`` must already carry the taxonomy columns (call
    ``hospital_taxonomy.derive_taxonomy`` first). ``k`` defaults
    to 6 to match the partner-facing universe count (Flagship
    Specialty / Academic / Large Community / Small Community /
    Critical Access / Other), but the partner can pick anything
    in [2, 12] from the UI.
    """
    X, feats, idx = prepare_clustering_features(df)
    if len(X) < max(k * 5, 30):
        raise ValueError(
            f"need at least {max(k * 5, 30)} clean rows for k={k}, "
            f"got {len(X)}"
        )
    pca = run_pca(X, n_components=2)
    km = run_kmeans(X, k, random_state=random_state)
    profiles = profile_clusters(km.labels, df.loc[idx])
    return ClusteringResult(
        k=k,
        n_rows=len(X),
        features=feats,
        pca=pca,
        kmeans=km,
        profiles=profiles,
        source_index=idx,
    )


# ── SVG scatter plot ───────────────────────────────────────────────


# Editorial chartis palette for the cluster colors. Cycles through
# the 8 entries — covers k=2..8 cleanly, repeats for k=9..12.
_CLUSTER_COLORS: tuple[str, ...] = (
    "#155752",  # teal-ink (chartis accent)
    "#b8732a",  # bronze (warning)
    "#0a8a5f",  # green (positive)
    "#b5321e",  # brick (negative)
    "#0b2341",  # navy
    "#7a3478",  # plum
    "#3b6789",  # slate blue
    "#5d6b7a",  # editorial dim
)


def render_cluster_scatter(
    result: "ClusteringResult",
    *,
    width: int = 720,
    height: int = 460,
    padding_left: int = 56,
    padding_right: int = 24,
    padding_top: int = 36,
    padding_bottom: int = 42,
) -> str:
    """Render a PCA scatter plot of the clustered hospitals as SVG.

    Each row plots at its (PC1, PC2) projection coloured by the
    cluster it belongs to. Cluster centroids render as larger
    diamond markers on top of the dot cloud so the partner can see
    where the cluster centres sit. Axes show the explained variance
    ratio for each PC so the partner knows how much of the original
    variance the 2D projection actually captures.

    Zero-dep SVG (same approach as Deal MC charts). Returns an
    empty SVG if the result has no rows or PCA wasn't computed.
    """
    pca = result.pca
    labels = result.kmeans.labels
    profiles_by_id = {p.cluster_id: p for p in result.profiles}

    if pca.scores.size == 0 or pca.scores.shape[1] < 2:
        return '<svg width="0" height="0"></svg>'

    inner_w = width - padding_left - padding_right
    inner_h = height - padding_top - padding_bottom
    pc1 = pca.scores[:, 0]
    pc2 = pca.scores[:, 1]

    x_min, x_max = float(pc1.min()), float(pc1.max())
    y_min, y_max = float(pc2.min()), float(pc2.max())
    # 6% padding so points don't kiss the axes
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0
    x_min -= x_span * 0.06
    x_max += x_span * 0.06
    y_min -= y_span * 0.06
    y_max += y_span * 0.06

    def sx(v: float) -> float:
        return padding_left + (
            (v - x_min) / (x_max - x_min) * inner_w
        )

    def sy(v: float) -> float:
        # SVG y grows downward; flip so larger PC2 sits at the top
        return padding_top + inner_h - (
            (v - y_min) / (y_max - y_min) * inner_h
        )

    # Axis tick lines + labels — 4 ticks per axis
    grid_lines = []
    for i in range(5):
        frac = i / 4
        # vertical (PC1)
        x = padding_left + frac * inner_w
        v = x_min + frac * (x_max - x_min)
        grid_lines.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" '
            f'y1="{padding_top}" y2="{padding_top + inner_h}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{x:.1f}" y="{padding_top + inner_h + 16}" '
            f'fill="#7a8699" text-anchor="middle" font-size="11" '
            f'font-family="JetBrains Mono, monospace">{v:+.1f}</text>'
        )
        # horizontal (PC2)
        y = padding_top + inner_h - frac * inner_h
        v = y_min + frac * (y_max - y_min)
        grid_lines.append(
            f'<line y1="{y:.1f}" y2="{y:.1f}" '
            f'x1="{padding_left}" x2="{padding_left + inner_w}" '
            f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
            f'<text x="{padding_left - 8}" y="{y + 4:.1f}" '
            f'fill="#7a8699" text-anchor="end" font-size="11" '
            f'font-family="JetBrains Mono, monospace">{v:+.1f}</text>'
        )

    # Plot every row as a small dot, coloured by cluster
    dot_layers: List[str] = []
    for i in range(len(pc1)):
        cid = int(labels[i])
        color = _CLUSTER_COLORS[cid % len(_CLUSTER_COLORS)]
        dot_layers.append(
            f'<circle cx="{sx(pc1[i]):.1f}" cy="{sy(pc2[i]):.1f}" '
            f'r="2.5" fill="{color}" fill-opacity="0.55" '
            f'stroke="none"/>'
        )

    # Compute centroids in PCA-score space (mean of each cluster's
    # PC1/PC2). Render as larger diamonds on top of the dot cloud.
    centroid_layers: List[str] = []
    for cid in sorted(set(int(l) for l in labels)):
        mask = labels == cid
        if not mask.any():
            continue
        cx = float(pc1[mask].mean())
        cy = float(pc2[mask].mean())
        color = _CLUSTER_COLORS[cid % len(_CLUSTER_COLORS)]
        x, y = sx(cx), sy(cy)
        # Diamond marker (rotated square)
        size = 7
        centroid_layers.append(
            f'<polygon points="'
            f'{x:.1f},{y - size:.1f} '
            f'{x + size:.1f},{y:.1f} '
            f'{x:.1f},{y + size:.1f} '
            f'{x - size:.1f},{y:.1f}" '
            f'fill="{color}" stroke="#fff" stroke-width="2"/>'
        )

    # Axis labels — explained variance ratio for each PC
    ev = pca.explained_variance_ratio
    pc1_label = (
        f"PC1 · {ev[0] * 100:.0f}% var" if len(ev) > 0 else "PC1"
    )
    pc2_label = (
        f"PC2 · {ev[1] * 100:.0f}% var" if len(ev) > 1 else "PC2"
    )
    axis_labels = (
        f'<text x="{padding_left + inner_w / 2:.1f}" '
        f'y="{height - 8}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600">'
        f'{pc1_label}</text>'
        f'<text x="14" y="{padding_top + inner_h / 2:.1f}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'transform="rotate(-90 14 {padding_top + inner_h / 2:.1f})">'
        f'{pc2_label}</text>'
    )

    # Legend — one row per cluster with its dominant-segment name
    legend_items: List[str] = []
    legend_x = padding_left + 8
    legend_y_start = padding_top + 8
    for i, cid in enumerate(sorted(profiles_by_id.keys())):
        prof = profiles_by_id[cid]
        color = _CLUSTER_COLORS[cid % len(_CLUSTER_COLORS)]
        y = legend_y_start + i * 16
        # Truncate long names so the legend stays compact
        name = prof.name if len(prof.name) <= 40 else prof.name[:37] + "…"
        legend_items.append(
            f'<g transform="translate({legend_x:.0f},{y:.0f})">'
            f'<circle cx="0" cy="0" r="4" fill="{color}"/>'
            f'<text x="10" y="4" font-size="11" '
            f'font-family="Inter, sans-serif" fill="#1a2332">'
            f'{name} <tspan fill="#7a8699">· n={prof.size}</tspan>'
            f'</text></g>'
        )

    legend_bg = (
        f'<rect x="{padding_left + 1}" y="{padding_top + 1}" '
        f'width="320" height="{len(legend_items) * 16 + 14}" '
        f'fill="#ffffff" fill-opacity="0.92" '
        f'stroke="#d6cfc0" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;">'
        f'{"".join(grid_lines)}'
        f'{"".join(dot_layers)}'
        f'{"".join(centroid_layers)}'
        f'{axis_labels}'
        f'{legend_bg}'
        f'{"".join(legend_items)}'
        f'</svg>'
    )
