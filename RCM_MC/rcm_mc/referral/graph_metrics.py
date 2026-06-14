"""Graph-structure metrics that degree/eigenvector centrality miss.

The existing ``centrality.py`` answers "who is a hub" (degree) and
"who is connected to hubs" (eigenvector). Three structural questions it
does *not* answer, all decision-useful in referral diligence:

  • **PageRank** — referral *influence* under flow, not just raw
    in-degree. A node fed by other influential referrers ranks above a
    node fed by the same volume from peripheral ones. The right "who
    really anchors the network" metric for a directed referral graph.
  • **Betweenness** (Brandes) — the *brokers*. A provider that sits on
    the only path between a referrer pool and a facility is a
    single-point-of-failure for that volume even if its own degree is
    modest. Key-person risk that degree centrality hides.
  • **Communities** (label propagation) — the natural sub-networks /
    catchments, so you can see whether a target is one cohesive
    referral community or a loose federation that could fragment.

All operate on the existing :class:`ReferralGraph`; no new dependency,
no networkx. Stdlib only (these are integer/float graph algorithms;
numpy buys nothing here).
"""
from __future__ import annotations

import random
from typing import Dict

from .graph import ReferralGraph


def pagerank(
    graph: ReferralGraph,
    *,
    damping: float = 0.85,
    max_iter: int = 200,
    tol: float = 1e-9,
) -> Dict[str, float]:
    """Weighted directed PageRank via power iteration.

    Edge direction and weight both matter: mass flows along referral
    direction in proportion to weight. Dangling nodes (no outbound
    referrals) redistribute their mass uniformly — the standard fix
    that keeps the vector a proper probability distribution summing to
    1. Returns {npi → score}; empty graph → empty dict."""
    nodes = sorted(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {}
    out_w = {nd: graph.out_weight(nd) for nd in nodes}
    pr = {nd: 1.0 / n for nd in nodes}
    for _ in range(max_iter):
        new = {nd: (1 - damping) / n for nd in nodes}
        dangling = sum(pr[nd] for nd in nodes if out_w[nd] == 0)
        dangle_share = damping * dangling / n
        for nd in nodes:
            new[nd] += dangle_share
        for nd in nodes:
            s = out_w[nd]
            if s == 0:
                continue
            base = damping * pr[nd] / s
            for dst, w in graph.out_neighbors(nd).items():
                new[dst] += base * w
        diff = sum(abs(new[nd] - pr[nd]) for nd in nodes)
        pr = new
        if diff < tol:
            break
    return pr


def betweenness_centrality(graph: ReferralGraph) -> Dict[str, float]:
    """Brandes betweenness on the directed referral graph (unweighted
    path counting — betweenness is about path topology, not flow
    volume). Normalized by (n-1)(n-2). Surfaces broker providers that
    bridge otherwise-separate parts of the network."""
    nodes = sorted(graph.nodes())
    if not nodes:
        return {}
    adj = {nd: list(graph.out_neighbors(nd).keys()) for nd in nodes}
    bet = {nd: 0.0 for nd in nodes}
    for s in nodes:
        stack = []
        pred: Dict[str, list] = {w: [] for w in nodes}
        sigma = {w: 0.0 for w in nodes}
        sigma[s] = 1.0
        dist = {w: -1 for w in nodes}
        dist[s] = 0
        queue = [s]
        qi = 0
        while qi < len(queue):
            v = queue[qi]
            qi += 1
            stack.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                bet[w] += delta[w]
    n = len(nodes)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        bet = {k: v * scale for k, v in bet.items()}
    return bet


def detect_communities(
    graph: ReferralGraph,
    *,
    seed: int = 0,
    max_iter: int = 100,
) -> Dict[str, int]:
    """Community detection by weighted label propagation on the
    undirected projection (a referral relationship clusters two
    providers regardless of direction). Each node adopts the label with
    the greatest summed neighbor weight; ties broken by lowest label id;
    node order shuffled with a seeded RNG for reproducibility. Returns
    {npi → community_id} renumbered 0..k-1 by first appearance."""
    nodes = sorted(graph.nodes())
    if not nodes:
        return {}
    undirected: Dict[str, Dict[str, float]] = {nd: {} for nd in nodes}
    for src, dst, w in graph.edges():
        undirected[src][dst] = undirected[src].get(dst, 0.0) + w
        undirected[dst][src] = undirected[dst].get(src, 0.0) + w

    rng = random.Random(seed)
    label = {nd: i for i, nd in enumerate(nodes)}
    order = list(nodes)
    for _ in range(max_iter):
        rng.shuffle(order)
        changed = False
        for nd in order:
            nbrs = undirected[nd]
            if not nbrs:
                continue
            weights: Dict[int, float] = {}
            for m, w in nbrs.items():
                weights[label[m]] = weights.get(label[m], 0.0) + w
            best = min(weights.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            if label[nd] != best:
                label[nd] = best
                changed = True
        if not changed:
            break
    remap: Dict[int, int] = {}
    out: Dict[str, int] = {}
    for nd in nodes:
        lab = label[nd]
        if lab not in remap:
            remap[lab] = len(remap)
        out[nd] = remap[lab]
    return out
