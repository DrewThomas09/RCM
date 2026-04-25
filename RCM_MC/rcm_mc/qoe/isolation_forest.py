"""Isolation forest in pure numpy.

Isolation forest scores each row by how easily it can be isolated
via random tree cuts. Anomalies isolate quickly (short paths);
normal points sit deep in the tree.

We implement a minimal but correct version sufficient for QoE
panel-level anomaly detection over a few hundred rows of monthly
financial data. No sklearn dependency.

Usage::

    from rcm_mc.qoe import isolation_forest_scores
    scores = isolation_forest_scores(X, n_trees=100, seed=0)

Where ``X`` is a 2D numpy array (rows = observations, cols =
financial line-items). Returns a per-row score in (0, 1] — higher
= more anomalous. Threshold around 0.6 is the convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np


# ── Single tree ──────────────────────────────────────────────────

@dataclass
class _Node:
    feature: int = -1
    threshold: float = 0.0
    left: Optional["_Node"] = None
    right: Optional["_Node"] = None
    size: int = 0          # leaf size if terminal


def _c(n: int) -> float:
    """Average path length in a BST of n points — used to scale
    the raw path lengths into the (0, 1] anomaly score."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    H = np.log(n - 1) + 0.5772156649  # Euler–Mascheroni
    return 2.0 * H - (2.0 * (n - 1) / n)


def _build_tree(
    X: np.ndarray,
    height: int,
    height_limit: int,
    rng: np.random.Generator,
) -> _Node:
    n = X.shape[0]
    if height >= height_limit or n <= 1:
        return _Node(size=n)

    # Random feature with non-zero variance
    n_features = X.shape[1]
    feature_order = rng.permutation(n_features)
    feature, lo, hi = -1, 0.0, 0.0
    for f in feature_order:
        col = X[:, f]
        col_min = float(col.min())
        col_max = float(col.max())
        if col_min < col_max:
            feature, lo, hi = f, col_min, col_max
            break
    if feature < 0:
        return _Node(size=n)

    threshold = rng.uniform(lo, hi)
    left_mask = X[:, feature] < threshold
    right_mask = ~left_mask
    if not left_mask.any() or not right_mask.any():
        return _Node(size=n)

    return _Node(
        feature=feature,
        threshold=threshold,
        left=_build_tree(X[left_mask], height + 1,
                         height_limit, rng),
        right=_build_tree(X[right_mask], height + 1,
                          height_limit, rng),
    )


def _path_length(tree: _Node, x: np.ndarray, depth: int) -> float:
    if tree.feature < 0:
        return depth + _c(tree.size)
    if x[tree.feature] < tree.threshold:
        return _path_length(tree.left, x, depth + 1)
    return _path_length(tree.right, x, depth + 1)


# ── Forest ───────────────────────────────────────────────────────

@dataclass
class IsolationForest:
    trees: List[_Node]
    sample_size: int

    def score(self, X: np.ndarray) -> np.ndarray:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        n_rows = X.shape[0]
        scores = np.zeros(n_rows, dtype=float)
        c_ss = _c(self.sample_size)
        for i in range(n_rows):
            paths = np.array(
                [_path_length(t, X[i], 0) for t in self.trees]
            )
            avg_path = float(paths.mean())
            scores[i] = 2.0 ** (-avg_path / max(1e-12, c_ss))
        return scores


def isolation_forest_scores(
    X: Union[np.ndarray, list],
    *,
    n_trees: int = 100,
    sample_size: Optional[int] = None,
    seed: int = 0,
) -> np.ndarray:
    """Train an isolation forest on ``X`` and return per-row
    anomaly scores.

    Args:
      X: 2D array (rows = observations, cols = features).
      n_trees: forest size (default 100).
      sample_size: subsample per tree (default min(256, n)).
      seed: RNG seed for reproducibility.

    Returns:
      np.ndarray of shape (n,) with values in (0, 1]. Higher =
      more anomalous. The conventional threshold is 0.6.
    """
    arr = np.asarray(X, dtype=float)
    if arr.ndim != 2 or arr.size == 0:
        return np.array([])
    n = arr.shape[0]
    ss = sample_size or min(256, n)
    height_limit = int(np.ceil(np.log2(max(2, ss))))
    rng = np.random.default_rng(seed)

    trees: List[_Node] = []
    for _ in range(n_trees):
        idx = rng.choice(n, size=min(ss, n), replace=False)
        sample = arr[idx]
        trees.append(_build_tree(sample, 0, height_limit, rng))
    forest = IsolationForest(trees=trees, sample_size=ss)
    return forest.score(arr)
