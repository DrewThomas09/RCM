"""Every identifier walked up to a final parent, with the reason kept.

The problem
-----------
Ownership in US healthcare is not published in one place, and no single
source gets an identifier all the way to the top. NPPES knows that an
NPI is a subpart of a parent organization but not that the parent is a
health system. The Compare files know a dialysis clinic's chain but not
that the chain has a system behind it. HCRIS knows a CCN's cost-report
filer. The registry in :mod:`health_systems` knows the brands. Each one
is a single hop.

So this module does not add another source. It composes the hops
already available into a graph and walks each identifier to a fixed
point — the node with nothing above it. That node is the final parent,
and the path taken is kept alongside it, because a parent nobody can
audit is a parent nobody should trust.

Nodes are namespaced, always
----------------------------
``npi:1234567890``, ``ccn:450358``, ``sys:ascension``,
``chain:FRESENIUS MEDICAL CARE``, ``pecos:12345``,
``org:ASCENSION HEALTH``. The namespace is not decoration: NPIs and
CCNs are both numeric and both ten-ish characters, and a graph that
mixes them will silently join a CCN to an unrelated NPI exactly once
and then be wrong forever.

Tiers, and why the weakest hop decides
--------------------------------------
Every edge carries the tier that produced it. Tiers are ranked by how
directly the source asserts ownership — NPPES's own subpart field
outranks a name match against a brand registry, and it should, because
one is a filing and the other is an inference.

A path's confidence is the *minimum* over its hops, not the product.
The path asserts every hop it contains, so it cannot be more certain
than its least certain link; and multiplying would pretend the hops are
independent probability estimates, which they are not — they are
heuristics of known relative strength. Minimum keeps the number
interpretable: 0.6 means "somewhere in this chain is a name match".

Cycles
------
Two facilities can each name the other as parent — a genuine filing
error, and one that turns a naive walk into an infinite loop. The walk
carries a visited set, stops at the repeat, and marks the resolution
``cycle=True`` rather than pretending it found a root. A flagged cycle
is a data-quality finding; a hung process is not.

Public API::

    ParentGraph()                       — add_edge / resolve / resolve_all
    build_parent_graph(...)  -> ParentGraph
    resolve_identifiers(...) -> pandas.DataFrame
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .health_systems import UNMAPPED_ID, match_system, normalize_name

# ── Tiers, strongest first ─────────────────────────────────────────
#
# Confidence is a statement about the SOURCE, not about a particular
# row: "how directly does this source assert that A is owned by B".

#: NPPES's "Is Organization Subpart" plus "Parent Organization LBN" —
#: the provider's own filing about its own ownership.
TIER_NPPES_SUBPART = "nppes_subpart"
#: PECOS Associate Control ID. CMS groups these NPIs under one enrolled
#: organization; it is CMS's assertion, not our inference.
TIER_PECOS_GROUP = "pecos_group"
#: A CCN whose provider number encodes a parent facility — a rehab or
#: psych unit inside a hospital.
TIER_CCN_PARENT = "ccn_parent"
#: An organization NPI matched to a certified facility by name, state
#: and ZIP. Address is the only bridge CMS leaves between the two
#: numbering systems.
TIER_NPI_CCN = "npi_ccn"
#: A chain name published by the operator in a CMS Compare file.
TIER_CCN_CHAIN = "ccn_chain"
#: The health system a CCN belongs to, per the registry.
TIER_CCN_SYSTEM = "ccn_system"
#: A name matched against the brand registry, with no CCN behind it.
#: The weakest tier here and the one that needs the guards most.
TIER_NAME_SYSTEM = "name_system"

TIER_CONFIDENCE: Dict[str, float] = {
    TIER_NPPES_SUBPART: 0.95,
    TIER_PECOS_GROUP: 0.90,
    TIER_CCN_PARENT: 0.90,
    TIER_NPI_CCN: 0.85,
    TIER_CCN_CHAIN: 0.80,
    TIER_CCN_SYSTEM: 0.75,
    TIER_NAME_SYSTEM: 0.60,
}

#: Lower rank wins when a node has more than one candidate parent.
TIER_RANK: Dict[str, int] = {
    tier: i for i, tier in enumerate((
        TIER_NPPES_SUBPART, TIER_PECOS_GROUP, TIER_CCN_PARENT,
        TIER_NPI_CCN, TIER_CCN_CHAIN, TIER_CCN_SYSTEM, TIER_NAME_SYSTEM))
}

#: Walking further than this means the graph is pathological, not deep.
#: Real ownership chains here are three or four hops; the cap is a
#: backstop that turns a runaway into a flagged row instead of a hang.
MAX_HOPS = 24

NS_NPI = "npi"
NS_CCN = "ccn"
NS_SYSTEM = "sys"
NS_CHAIN = "chain"
NS_PECOS = "pecos"
NS_ORG = "org"


def node_key(namespace: str, value: Any) -> str:
    """``npi:1234567890``. Empty value gives ``""``, never a bare colon.

    Namespacing is what stops a CCN from being joined to an NPI that
    happens to be the same digits — a mistake that is invisible until
    someone audits a single row and finds a dialysis clinic parented to
    an orthopaedic surgeon.

    ``_unmapped`` is treated as empty. It is the registry's sentinel for
    "no system was found", and 34,085 of the crosswalk's 48,510 rows
    carry it. Letting it become a node would parent seven facilities in
    ten to a fictional health system called "unmapped" and report
    100% ownership coverage — the most convincing wrong answer this
    module could produce.
    """
    text = str(value or "").strip()
    if not text or text == UNMAPPED_ID:
        return ""
    if namespace in (NS_CHAIN, NS_ORG):
        text = normalize_name(text)
        if not text:
            return ""
    return f"{namespace}:{text}"


@dataclass(frozen=True)
class ParentEdge:
    """One asserted hop: ``child`` is owned by ``parent``, per ``tier``."""

    child: str
    parent: str
    tier: str
    evidence: str = ""

    @property
    def confidence(self) -> float:
        return TIER_CONFIDENCE.get(self.tier, 0.0)

    @property
    def rank(self) -> int:
        return TIER_RANK.get(self.tier, len(TIER_RANK))


@dataclass(frozen=True)
class Resolution:
    """Where one node ends up, and how it got there."""

    node: str
    final_parent: str
    tiers: Tuple[str, ...]
    path: Tuple[str, ...]
    confidence: float
    hops: int
    cycle: bool = False
    truncated: bool = False

    @property
    def is_root(self) -> bool:
        return self.hops == 0

    @property
    def weakest_tier(self) -> str:
        """The tier the confidence came from — the hop to argue about."""
        if not self.tiers:
            return ""
        return max(self.tiers, key=lambda t: TIER_RANK.get(t, len(TIER_RANK)))

    @property
    def provenance(self) -> str:
        """Human-readable chain: ``npi:… →(nppes_subpart) org:… →(…) sys:…``"""
        if not self.tiers:
            return self.node
        parts = [self.path[0]]
        for tier, node in zip(self.tiers, self.path[1:], strict=True):
            parts.append(f"→({tier}) {node}")
        return " ".join(parts)


class ParentGraph:
    """A directed child→parent graph with one winning edge per child.

    Several sources will claim a parent for the same identifier and
    they will disagree. Rather than picking whichever loaded last, every
    claim is kept and the strongest tier wins; ties inside a tier break
    on the parent key so the result does not depend on iteration order.
    ``contested()`` reports the children where sources actually
    disagreed, which is where a reviewer's time is worth spending.
    """

    def __init__(self) -> None:
        self._claims: Dict[str, List[ParentEdge]] = {}
        #: parent -> the children that named it. Maintained on write
        #: rather than scanned on read: the group-lifting pass asks this
        #: question once per PECOS node, and a scan made building the
        #: real graph a 98-second job instead of a 2-second one.
        self._children: Dict[str, List[str]] = {}
        self._resolved: Dict[str, Resolution] = {}

    # ── construction ───────────────────────────────────────────────
    def add_edge(self, child: str, parent: str, tier: str,
                 evidence: str = "") -> bool:
        """Record a claim. Returns False when the claim is unusable.

        A self-edge is dropped rather than stored: a node cannot be its
        own parent, and letting one in makes every downstream cycle
        report meaningless.
        """
        if not child or not parent or child == parent:
            return False
        self._claims.setdefault(child, []).append(
            ParentEdge(child, parent, tier, evidence))
        kids = self._children.setdefault(parent, [])
        if not kids or kids[-1] != child:
            kids.append(child)
        self._resolved.clear()
        return True

    def add_edges(self, edges: Iterable[ParentEdge]) -> int:
        return sum(self.add_edge(e.child, e.parent, e.tier, e.evidence)
                   for e in edges)

    # ── inspection ─────────────────────────────────────────────────
    @property
    def nodes(self) -> frozenset:
        out = set(self._claims)
        for claims in self._claims.values():
            out.update(c.parent for c in claims)
        return frozenset(out)

    def children_of(self, parent: str) -> Tuple[str, ...]:
        """Every child that named ``parent``, in a stable order."""
        return tuple(sorted(set(self._children.get(parent, ()))))

    def claims_for(self, child: str) -> Tuple[ParentEdge, ...]:
        return tuple(self._claims.get(child, ()))

    def winning_edge(self, child: str) -> Optional[ParentEdge]:
        claims = self._claims.get(child)
        if not claims:
            return None
        return min(claims, key=lambda e: (e.rank, e.parent))

    def contested(self) -> Dict[str, Tuple[str, ...]]:
        """Children whose sources disagree about where they end up.

        Compared at the *final* parent, not the immediate one, because
        most multi-claim children are not in conflict at all: a DaVita
        clinic names both ``chain:DAVITA`` and ``sys:davita``, which are
        two roads to the same place. Reporting those as contested buries
        the 100-odd real disagreements under 7,000 agreements and makes
        the number useless to whoever has to review it.
        """
        out: Dict[str, Tuple[str, ...]] = {}
        for child, claims in self._claims.items():
            if len({c.parent for c in claims}) < 2:
                continue
            finals = sorted({self.resolve(c.parent).final_parent
                             for c in claims})
            if len(finals) > 1:
                out[child] = tuple(finals)
        return out

    # ── the walk ───────────────────────────────────────────────────
    def resolve(self, node: str, _stack: Tuple[str, ...] = ()) -> Resolution:
        """Walk ``node`` up to the first node with nothing above it.

        Every claim is followed, not just the winning one. The strongest
        tier still decides *where* the node lands, but once the
        destination is fixed, the best-supported route to it sets the
        confidence. Corroboration should raise a score, not lower it,
        and following only the top-ranked edge does the opposite: a
        dialysis clinic that names its chain AND its system would score
        0.60 on the chain route while the direct system edge sitting
        right beside it is worth 0.75.
        """
        cached = self._resolved.get(node)
        if cached is not None:
            return cached

        if node in _stack:
            return Resolution(node, node, (), (node,), 1.0, 0, cycle=True)
        if len(_stack) >= MAX_HOPS:
            return Resolution(node, node, (), (node,), 1.0, 0, truncated=True)

        claims = self._claims.get(node)
        if not claims:
            result = Resolution(node, node, (), (node,), 1.0, 0)
            self._resolved[node] = result
            return result

        deeper = _stack + (node,)
        upstream = {edge: self.resolve(edge.parent, deeper) for edge in claims}

        # Where the node lands: the strongest tier decides.
        anchor = min(claims, key=lambda e: (e.rank, e.parent))
        target = upstream[anchor].final_parent

        # How sure we are: the best-supported route to that same place.
        reaching = [e for e in claims if upstream[e].final_parent == target]
        chosen = min(reaching, key=lambda e: (
            -min(e.confidence, upstream[e].confidence), e.rank, e.parent))
        above = upstream[chosen]

        result = Resolution(
            node=node,
            final_parent=target,
            tiers=(chosen.tier,) + above.tiers,
            path=(node,) + above.path,
            confidence=min(chosen.confidence, above.confidence),
            hops=1 + above.hops,
            cycle=above.cycle,
            truncated=above.truncated,
        )
        # A result computed under the stack guard is only correct for
        # this entry point, so it must not be memoised for other ones.
        if not (result.cycle or result.truncated):
            self._resolved[node] = result
        return result

    def resolve_all(self) -> Dict[str, Resolution]:
        return {n: self.resolve(n) for n in sorted(self.nodes)}

    def stats(self) -> Dict[str, Any]:
        """What the graph actually contains — measured, never estimated."""
        resolutions = self.resolve_all()
        by_tier: Dict[str, int] = {}
        for claims in self._claims.values():
            for claim in claims:
                by_tier[claim.tier] = by_tier.get(claim.tier, 0) + 1
        rooted = [r for r in resolutions.values() if r.hops > 0]
        return {
            "nodes": len(resolutions),
            "children": len(self._claims),
            "claims": sum(len(c) for c in self._claims.values()),
            "claims_by_tier": dict(sorted(by_tier.items())),
            "contested": len(self.contested()),
            "resolved_to_a_parent": len(rooted),
            "roots": len(resolutions) - len(rooted),
            "cycles": sum(1 for r in resolutions.values() if r.cycle),
            "truncated": sum(1 for r in resolutions.values() if r.truncated),
            "max_hops": max((r.hops for r in resolutions.values()), default=0),
        }


# ── building the graph from the sources we have ────────────────────

def _system_edges_for_name(graph: ParentGraph, node: str, name: Any,
                           state: Any = "") -> bool:
    """Point a chain or parent-organization name at a registry system.

    This is what turns a *local* parent into a *final* one. Without it
    a dialysis clinic stops at ``chain:FRESENIUS MEDICAL CARE`` and a
    subpart stops at ``org:ASCENSION HEALTH``, both of which are the
    right answer one hop too early.
    """
    sysdef, pattern = match_system(name, str(state or "").upper())
    if sysdef is None:
        return False
    return graph.add_edge(node, node_key(NS_SYSTEM, sysdef.system_id),
                          TIER_NAME_SYSTEM, f"name: {pattern}")


def edges_from_crosswalk(frame: pd.DataFrame) -> List[ParentEdge]:
    """Ownership hops carried by the CCN crosswalk.

    Four distinct claims live in one row and they are not the same
    claim: the parent CCN of a hospital-based unit, the operator-
    published chain, the registry system, and the organization NPI that
    bills for the facility. Collapsing them would throw away the only
    thing that makes the answer auditable — which one was used.
    """
    edges: List[ParentEdge] = []
    for rec in frame.to_dict("records"):
        ccn = node_key(NS_CCN, rec.get("ccn"))
        if not ccn:
            continue

        parent_ccn = node_key(NS_CCN, rec.get("parent_ccn"))
        if parent_ccn:
            edges.append(ParentEdge(
                ccn, parent_ccn, TIER_CCN_PARENT,
                str(rec.get("parent_ccn_source") or "parent facility")))

        chain = node_key(NS_CHAIN, rec.get("chain_name"))
        if chain:
            edges.append(ParentEdge(ccn, chain, TIER_CCN_CHAIN,
                                    str(rec.get("chain_name") or "")))

        system = node_key(NS_SYSTEM, rec.get("system_id"))
        if system:
            edges.append(ParentEdge(
                ccn, system, TIER_CCN_SYSTEM,
                str(rec.get("system_match") or rec.get("system_name") or "")))

        npi = node_key(NS_NPI, rec.get("npi"))
        if npi:
            edges.append(ParentEdge(npi, ccn, TIER_NPI_CCN,
                                    str(rec.get("npi_source") or "")))
    return edges


def edges_from_npi_frame(frame: pd.DataFrame) -> List[ParentEdge]:
    """Ownership hops carried by an NPI-level frame.

    Accepts either the ambulance registry frame or a frame read back
    from the ``npi_crosswalk`` table; the columns it looks for are
    optional throughout, so a source that lacks PECOS or subpart data
    contributes what it has instead of raising.
    """
    edges: List[ParentEdge] = []
    columns = set(frame.columns)
    for rec in frame.to_dict("records"):
        npi = node_key(NS_NPI, rec.get("npi"))
        if not npi:
            continue

        if "parent_org_lbn" in columns:
            org = node_key(NS_ORG, rec.get("parent_org_lbn"))
            if org:
                edges.append(ParentEdge(
                    npi, org, TIER_NPPES_SUBPART,
                    f"NPPES parent organization: "
                    f"{str(rec.get('parent_org_lbn') or '').strip()}"))

        if "pecos_group" in columns:
            pecos = node_key(NS_PECOS, rec.get("pecos_group"))
            if pecos:
                edges.append(ParentEdge(
                    npi, pecos, TIER_PECOS_GROUP,
                    f"PECOS associate control ID: "
                    f"{str(rec.get('pecos_group') or '').strip()}"))

        if "ccn" in columns:
            ccn = node_key(NS_CCN, rec.get("ccn"))
            if ccn:
                edges.append(ParentEdge(npi, ccn, TIER_NPI_CCN,
                                        "name + state + ZIP"))

        system = node_key(NS_SYSTEM, rec.get("system_id"))
        if system:
            edges.append(ParentEdge(
                npi, system, TIER_NAME_SYSTEM,
                str(rec.get("match_basis") or rec.get("system_match") or "")))
    return edges


def build_parent_graph(
    *,
    crosswalk: Optional[pd.DataFrame] = None,
    npi_frame: Optional[pd.DataFrame] = None,
    lift_names_to_systems: bool = True,
) -> ParentGraph:
    """Assemble the ownership graph from whichever sources are supplied.

    Nothing is fetched here. Callers pass the frames they already have —
    :func:`provider_crosswalk.get_crosswalk`, the ambulance NPI
    registry, or a read of the ``npi_crosswalk`` table — and this
    composes them. That keeps the engine testable on a five-row fixture
    and unchanged when the full 8-million-row file finally arrives.

    ``lift_names_to_systems`` is what makes a parent *final*: chain and
    parent-organization nodes are themselves matched against the brand
    registry, so ``chain:DAVITA`` resolves on to ``sys:davita`` when the
    registry knows the brand, and stands as its own root when it does
    not. Turn it off to see the raw one-hop structure.
    """
    graph = ParentGraph()
    if crosswalk is not None and not crosswalk.empty:
        graph.add_edges(edges_from_crosswalk(crosswalk))
    if npi_frame is not None and not npi_frame.empty:
        graph.add_edges(edges_from_npi_frame(npi_frame))

    if lift_names_to_systems:
        for node in sorted(graph.nodes):
            namespace, _, value = node.partition(":")
            if namespace in (NS_CHAIN, NS_ORG):
                _system_edges_for_name(graph, node, value)
        _lift_groups_to_systems(graph)
    return graph


def _lift_groups_to_systems(graph: ParentGraph) -> int:
    """Give a PECOS group the brand its own members carry.

    A PECOS Associate Control ID outranks a name match, so an NPI that
    could be recognised by name stops at ``pecos:12345`` instead — CMS's
    grouping is the better answer about *which* organization, and a
    worse one about *whose* organization. But the group's members
    collectively know: if any of them matched a brand, that brand is the
    group's.

    Unanimity is required. A group whose members point at two different
    systems is a group that has been through an acquisition, a
    mis-match, or both, and guessing between them would put the whole
    group under the wrong parent. Those stay as their own root and show
    up in ``contested`` if anything else disagrees.
    """
    lifted = 0
    for node in sorted(graph.nodes):
        if not node.startswith(f"{NS_PECOS}:"):
            continue
        systems = set()
        evidence = ""
        for child in graph.children_of(node):
            for claim in graph.claims_for(child):
                if claim.tier == TIER_NAME_SYSTEM:
                    systems.add(claim.parent)
                    evidence = evidence or claim.evidence
        if len(systems) == 1:
            lifted += graph.add_edge(node, systems.pop(), TIER_NAME_SYSTEM,
                                     f"group member {evidence}".strip())
    return lifted


RESOLUTION_COLUMNS: Tuple[str, ...] = (
    "node", "namespace", "identifier", "final_parent",
    "final_parent_namespace", "final_parent_identifier",
    "tier", "confidence", "hops", "cycle", "truncated", "provenance",
)


def resolve_identifiers(graph: ParentGraph, *,
                        namespaces: Optional[Iterable[str]] = None
                        ) -> pd.DataFrame:
    """One row per node: where it lands, how far, how sure, and why.

    ``namespaces`` filters to the identifier types a caller cares about
    — ``("npi",)`` for the master NPI file. Roots are included rather
    than dropped: "this is the top of its tree" is an answer, and a
    file that silently omits them looks like it lost rows.
    """
    wanted = frozenset(namespaces) if namespaces else None
    rows: List[Dict[str, Any]] = []
    for node, res in graph.resolve_all().items():
        namespace, _, identifier = node.partition(":")
        if wanted is not None and namespace not in wanted:
            continue
        parent_ns, _, parent_id = res.final_parent.partition(":")
        rows.append({
            "node": node,
            "namespace": namespace,
            "identifier": identifier,
            "final_parent": res.final_parent,
            "final_parent_namespace": parent_ns,
            "final_parent_identifier": parent_id,
            "tier": res.weakest_tier,
            "confidence": res.confidence,
            "hops": res.hops,
            "cycle": res.cycle,
            "truncated": res.truncated,
            "provenance": res.provenance,
        })
    if not rows:
        return pd.DataFrame(columns=list(RESOLUTION_COLUMNS))
    return pd.DataFrame(rows, columns=list(RESOLUTION_COLUMNS))
