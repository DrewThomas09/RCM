"""Centrality metrics — who are the actual referral hubs.

We implement three:

  • In-degree centrality (weighted)  — who receives the most
    referrals. The "destination" hub.
  • Out-degree centrality (weighted) — who sends the most.
    The "source" hub. In MSO/PC deals these are the high-value
    physicians whose departure deserves a retention package.
  • Eigenvector centrality           — who's connected to the
    most-connected. Captures hub-of-hubs structure that pure
    degree misses.

Power iteration runs in O(edges) per round, converges in ~50
rounds for typical PE-target graphs (a few thousand NPIs). We cap
at 200 rounds with a 1e-6 convergence tolerance.
"""
from __future__ import annotations

from typing import Dict

from .graph import ReferralGraph


def in_degree_centrality(graph: ReferralGraph) -> Dict[str, float]:
    """Weighted in-degree per node, normalized so the largest =
    1.0. Empty graph → empty dict."""
    raw = {npi: graph.in_weight(npi) for npi in graph.nodes()}
    if not raw:
        return {}
    mx = max(raw.values()) or 1.0
    return {npi: w / mx for npi, w in raw.items()}


def out_degree_centrality(graph: ReferralGraph) -> Dict[str, float]:
    """Weighted out-degree per node, normalized so the largest =
    1.0."""
    raw = {npi: graph.out_weight(npi) for npi in graph.nodes()}
    if not raw:
        return {}
    mx = max(raw.values()) or 1.0
    return {npi: w / mx for npi, w in raw.items()}


def eigenvector_centrality(
    graph: ReferralGraph,
    *,
    max_iter: int = 200,
    tol: float = 1e-6,
) -> Dict[str, float]:
    """Power-iteration eigenvector centrality on the referral
    network. Treats edges as undirected for centrality (a referral
    relationship matters regardless of direction).

    Returns a dict {npi → centrality} normalized to L2 = 1.
    Disconnected graphs get zero score on isolated nodes.
    """
    nodes = sorted(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {}

    idx = {npi: i for i, npi in enumerate(nodes)}
    # Build symmetric weighted adjacency for iteration
    adj: Dict[int, Dict[int, float]] = {i: {} for i in range(n)}
    for src, dst, w in graph.edges():
        a, b = idx[src], idx[dst]
        adj[a][b] = adj[a].get(b, 0.0) + w
        adj[b][a] = adj[b].get(a, 0.0) + w

    # Start with uniform vector
    x = [1.0 / n] * n

    for _ in range(max_iter):
        # y = A · x
        y = [0.0] * n
        for i, neighbors in adj.items():
            s = 0.0
            for j, w in neighbors.items():
                s += w * x[j]
            y[i] = s
        # Normalize L2
        norm = sum(v * v for v in y) ** 0.5
        if norm == 0.0:
            return {npi: 0.0 for npi in nodes}
        y = [v / norm for v in y]
        # Convergence check
        diff = sum(abs(y[i] - x[i]) for i in range(n))
        x = y
        if diff < tol:
            break

    return {nodes[i]: x[i] for i in range(n)}
