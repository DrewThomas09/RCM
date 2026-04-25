"""Mahalanobis distance + matching.

Mahalanobis distance accounts for feature correlation in a way
Euclidean distance can't — two features that move together don't
"double-count." Critical for the comparable-deal use case where
size and growth are correlated, sector and geography correlate,
etc.

We use a regularized covariance estimate (Σ + λI) so the inverse
exists even when the corpus has fewer rows than features.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .features import FeatureVector


def mahalanobis_distance_matrix(
    corpus: List[FeatureVector],
    target: FeatureVector,
    *,
    ridge: float = 0.05,
) -> np.ndarray:
    """Mahalanobis distance from target to every corpus deal.

    Returns: (n_corpus,) array of distances.

    The covariance is computed across the corpus; ridge is added
    to the diagonal before inversion to keep things stable in
    rank-deficient regimes.
    """
    if not corpus:
        return np.array([])
    X = np.vstack([fv.vector for fv in corpus])
    n, d = X.shape

    mean = X.mean(axis=0)
    centered = X - mean
    cov = (centered.T @ centered) / max(1, n - 1)

    # Ridge-regularize so the inverse exists
    cov_reg = cov + ridge * np.eye(d)
    try:
        cov_inv = np.linalg.inv(cov_reg)
    except np.linalg.LinAlgError:
        # Pseudo-inverse fallback
        cov_inv = np.linalg.pinv(cov_reg)

    delta = X - target.vector
    quad = np.einsum("ij,jk,ik->i", delta, cov_inv, delta)
    quad = np.maximum(0.0, quad)   # numerical floor
    return np.sqrt(quad)


def mahalanobis_match(
    corpus: List[FeatureVector],
    target: FeatureVector,
    *,
    k_matches: int = 15,
    ridge: float = 0.05,
) -> List[Tuple[FeatureVector, float, float]]:
    """Top-K Mahalanobis-nearest comps.

    Returns: list of (deal, distance, similarity_weight) tuples.
    Similarity weight = exp(-distance / max_distance).
    """
    distances = mahalanobis_distance_matrix(
        corpus, target, ridge=ridge)
    if distances.size == 0:
        return []
    order = np.argsort(distances)
    max_d = float(distances.max() or 1.0)
    out: List[Tuple[FeatureVector, float, float]] = []
    for idx in order[:k_matches]:
        d = float(distances[idx])
        # Exponential decay weighting — closer matches matter much more
        weight = float(np.exp(-d / max(1e-6, max_d * 0.5)))
        out.append((corpus[idx], d, weight))
    return out
