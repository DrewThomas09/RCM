"""ReferralGraph: directed weighted graph between physician NPIs.

CMS publishes shared-patient files annually (via the Medicare
Physician Referrals dataset). Each row is an edge: NPI A referred
N patients to NPI B in the calendar year. We represent the result
as a sparse directed graph keyed by NPI.

Edges are weighted by referral volume — the operations downstream
treat heavier edges as more leakage-relevant. Multiple observations
between the same (A, B) pair are summed via ``add_edge``.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple


@dataclass
class ReferralEdge:
    src: str          # referring NPI
    dst: str          # receiving NPI
    weight: float     # patient count (or other volume metric)


@dataclass
class ReferralGraph:
    """Sparse directed graph of physician referrals.

    Internal representation:
      _out[src]: dict[dst -> weight]   (edges from src)
      _in[dst]:  dict[src -> weight]   (edges into dst)
      _node_org[npi]: organization affiliation (for leakage math)
    """
    _out: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict))
    _in: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(dict))
    _node_org: Dict[str, str] = field(default_factory=dict)

    # ── Construction ────────────────────────────────────────────

    def add_edge(self, src: str, dst: str, weight: float = 1.0) -> None:
        """Add or augment a directed edge. Repeat calls add weights."""
        if not src or not dst:
            return
        self._out[src][dst] = self._out[src].get(dst, 0.0) + float(weight)
        self._in[dst][src] = self._in[dst].get(src, 0.0) + float(weight)
        # Ensure the empty endpoint dict exists so node_count is correct
        self._out.setdefault(dst, {})
        self._in.setdefault(src, {})

    def set_node_org(self, npi: str, org: str) -> None:
        """Tag an NPI with the organization it bills under. Also
        registers the NPI as a node so it counts in
        ``node_count()`` even with no edges yet."""
        if npi:
            self._node_org[npi] = org or ""
            self._out.setdefault(npi, {})
            self._in.setdefault(npi, {})

    def add_edges_from(
        self, edges: Iterable[ReferralEdge],
    ) -> None:
        for e in edges:
            self.add_edge(e.src, e.dst, e.weight)

    # ── Inspection ──────────────────────────────────────────────

    def nodes(self) -> Set[str]:
        return set(self._out.keys()) | set(self._in.keys())

    def node_count(self) -> int:
        return len(self.nodes())

    def edge_count(self) -> int:
        return sum(len(d) for d in self._out.values())

    def out_neighbors(self, npi: str) -> Dict[str, float]:
        return dict(self._out.get(npi, {}))

    def in_neighbors(self, npi: str) -> Dict[str, float]:
        return dict(self._in.get(npi, {}))

    def out_weight(self, npi: str) -> float:
        return sum(self._out.get(npi, {}).values())

    def in_weight(self, npi: str) -> float:
        return sum(self._in.get(npi, {}).values())

    def node_org(self, npi: str) -> str:
        return self._node_org.get(npi, "")

    # ── Mutation: drop a node (used by simulate_departure) ──────

    def drop_node(self, npi: str) -> "ReferralGraph":
        """Return a new graph with all edges to/from ``npi`` removed.
        Original is left untouched — partners often want to A/B
        compare the with-vs-without view."""
        new = ReferralGraph()
        for src, dsts in self._out.items():
            if src == npi:
                continue
            for dst, w in dsts.items():
                if dst == npi:
                    continue
                new.add_edge(src, dst, w)
        for n, org in self._node_org.items():
            if n == npi:
                continue
            new.set_node_org(n, org)
        return new

    # ── Iteration helpers ───────────────────────────────────────

    def edges(self) -> Iterator[Tuple[str, str, float]]:
        for src, dsts in self._out.items():
            for dst, w in dsts.items():
                yield (src, dst, w)
