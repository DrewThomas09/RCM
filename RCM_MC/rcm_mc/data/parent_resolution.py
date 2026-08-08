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
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .health_systems import (
    CHAIN_ALIASES, UNMAPPED_ID, get_system, match_system, normalize_name,
)
from .nppes_ingest import _CIVIL_BODY_RE

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
TIER_NAME_SYSTEM = "name_system"
#: Organizations naming the same NPPES authorised official. A corporate
#: officer signs for every entity their company owns, so this reaches
#: subsidiaries no name or address match can — but the same shape is
#: produced by a billing agent or a county EMS coordinator signing for
#: dozens of unrelated clients, so it is heavily guarded. See
#: :func:`edges_from_officials`.
TIER_SHARED_OFFICIAL = "shared_official"
#: An individual linked to an organization by the derived affiliation
#: bridge — co-located AND sharing a name token. The weakest tier here,
#: deliberately: it is the only one that is an inference about a person
#: rather than a filing about an organization. Edges on this tier carry
#: the bridge's own per-pair confidence instead of the tier constant.
TIER_AFFILIATION = "affiliation"

TIER_CONFIDENCE: Dict[str, float] = {
    TIER_NPPES_SUBPART: 0.95,
    TIER_PECOS_GROUP: 0.90,
    TIER_CCN_PARENT: 0.90,
    TIER_NPI_CCN: 0.85,
    TIER_CCN_CHAIN: 0.80,
    TIER_CCN_SYSTEM: 0.75,
    TIER_SHARED_OFFICIAL: 0.70,
    TIER_NAME_SYSTEM: 0.60,
    TIER_AFFILIATION: 0.50,
}

#: Lower rank wins when a node has more than one candidate parent.
TIER_RANK: Dict[str, int] = {
    tier: i for i, tier in enumerate((
        TIER_NPPES_SUBPART, TIER_PECOS_GROUP, TIER_CCN_PARENT,
        TIER_NPI_CCN, TIER_CCN_CHAIN, TIER_CCN_SYSTEM, TIER_SHARED_OFFICIAL,
        TIER_NAME_SYSTEM, TIER_AFFILIATION))
}

#: The affiliation bridge emits two methods. Only one of them is an
#: affiliation claim: ``shared_address+name`` means Dr. Smith bills at
#: the same address as Smith Family Medicine. ``shared_practice_address``
#: alone means two providers are in the same building, which is not
#: evidence of anything — it is the exact claim this crosswalk refuses
#: to make, so it is filtered out rather than scored down.
AFFILIATION_METHODS: Tuple[str, ...] = ("shared_address+name",)
#: …and even within that method, a pair scoring below this is a suite
#: shared by so many organizations that the name overlap is likely
#: coincidence.
AFFILIATION_MIN_CONFIDENCE = 0.50

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
NS_OFFICIAL = "official"
NS_EIN = "ein"

#: Namespaces that identify a *facility*, not an owner. Landing on one
#: means the walk ran out of ownership data, not that it found a parent.
_FACILITY_NAMESPACES = frozenset({NS_CCN, NS_NPI})


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
    #: Per-edge override. Most tiers score every edge the same because
    #: the confidence is a statement about the *source*. The affiliation
    #: bridge is the exception: it scores each pair individually, and
    #: flattening that to a tier constant would throw away the one thing
    #: that separates a strong link from a weak one.
    score: Optional[float] = None

    @property
    def confidence(self) -> float:
        if self.score is not None:
            return float(self.score)
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
                 evidence: str = "", score: Optional[float] = None) -> bool:
        """Record a claim. Returns False when the claim is unusable.

        A self-edge is dropped rather than stored: a node cannot be its
        own parent, and letting one in makes every downstream cycle
        report meaningless.
        """
        if not child or not parent or child == parent:
            return False
        self._claims.setdefault(child, []).append(
            ParentEdge(child, parent, tier, evidence, score))
        kids = self._children.setdefault(parent, [])
        if not kids or kids[-1] != child:
            kids.append(child)
        self._resolved.clear()
        return True

    def add_edges(self, edges: Iterable[ParentEdge]) -> int:
        return sum(self.add_edge(e.child, e.parent, e.tier, e.evidence,
                                 e.score)
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
            # A claim that dead-ends on another facility named no owner,
            # so it cannot disagree with one. Comparing it anyway flagged
            # every hospital-based unit whose parent hospital happens to
            # be unmapped — five in this data, all of which resolve
            # correctly through the unit's own system.
            finals = sorted({
                final for final in (self.resolve(c.parent).final_parent
                                    for c in claims)
                if final.partition(":")[0] not in _FACILITY_NAMESPACES})
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

        # Where the node lands: the strongest tier decides — but only
        # among claims that actually name an owner.
        #
        # A route ending on ``ccn:`` or ``npi:`` has not answered the
        # ownership question; it has walked to another facility whose
        # owner is unknown. That happened on five hospital-based units
        # whose parent CCN outranked their own system: the unit knew it
        # was UCHealth, its parent hospital's filed name carried no
        # brand, and the stronger tier buried the better answer under
        # ``ccn:060022``. Both statements are true and one of them is
        # useless.
        named = [e for e in claims
                 if upstream[e].final_parent.partition(":")[0]
                 not in _FACILITY_NAMESPACES]
        anchor = min(named or claims, key=lambda e: (e.rank, e.parent))
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
                           states: Iterable[str] = ()) -> bool:
    """Point a chain or parent-organization name at a registry system.

    This is what turns a *local* parent into a *final* one. Without it
    a dialysis clinic stops at ``chain:FRESENIUS MEDICAL CARE`` and a
    subpart stops at ``org:ASCENSION HEALTH``, both of which are the
    right answer one hop too early.

    ``states`` matters more than it looks. Many registry patterns are
    state-scoped, because MERCY and BAPTIST and CENTRAL FLORIDA KIDNEY
    name several unrelated organizations. Matching a chain name with no
    state skips every one of those patterns, so the chain stayed its own
    root while the facilities under it resolved to the very system the
    chain *is* — and the two then showed up as an ownership
    disagreement with itself. The states of the node's own children are
    the right ones to try.
    """
    # CMS's own chain strings already have a curated mapping in the
    # registry; the regex patterns are a *second* route for names it
    # does not cover. Skipping the table meant "ATLANTIC DIALYSIS
    # MANAGEMENT SERVICES" never reached atlantic_dms, whose pattern is
    # "^ATLANTIC DMS" — the same operator under two spellings, showing
    # up as an ownership disagreement with itself.
    alias = CHAIN_ALIASES.get(str(name or "").strip().upper())
    if alias:
        return graph.add_edge(node, node_key(NS_SYSTEM, alias),
                              TIER_NAME_SYSTEM, "CMS chain alias")

    candidates = [s for s in dict.fromkeys(states) if s] or [""]
    for state in candidates:
        sysdef, pattern = match_system(name, str(state).upper())
        if sysdef is not None:
            return graph.add_edge(node, node_key(NS_SYSTEM, sysdef.system_id),
                                  TIER_NAME_SYSTEM, f"name: {pattern}")
    return False


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


def edges_from_affiliations(
    frame: pd.DataFrame,
    *,
    methods: Iterable[str] = AFFILIATION_METHODS,
    min_confidence: float = AFFILIATION_MIN_CONFIDENCE,
) -> List[ParentEdge]:
    """Individual→organization links from the derived affiliation bridge.

    This is the only route by which a person gets a parent, and it is
    fenced on both sides. NPPES has no employer field, so the bridge in
    ``connectors/nppes/affiliation.py`` infers one from co-location plus
    a shared name token — Dr. Smith billing at the same address as Smith
    Family Medicine. That is a real signal.

    Co-location *alone* is not, and the bridge emits it as a separate
    method scored 0.20-0.45. Two physicians in the same medical office
    building are not colleagues, and a crosswalk that says otherwise is
    worse than one that says nothing. Those rows are filtered out by
    method rather than scored down, because a low score on a claim that
    should never have been made is still a claim.

    The per-pair confidence is carried through onto the edge rather than
    collapsed to the tier constant: the bridge already knows that a pair
    in a two-tenant building is stronger evidence than one in a
    forty-tenant tower, and that is exactly what a reviewer needs.
    """
    wanted = frozenset(methods)
    edges: List[ParentEdge] = []
    for rec in frame.to_dict("records"):
        method = str(rec.get("method") or "").strip()
        if wanted and method not in wanted:
            continue
        try:
            score = float(rec.get("confidence") or 0.0)
        except (TypeError, ValueError):
            continue
        if score < min_confidence:
            continue
        child = node_key(NS_NPI, rec.get("individual_npi"))
        parent = node_key(NS_NPI, rec.get("organization_npi"))
        if not child or not parent:
            continue
        edges.append(ParentEdge(
            child, parent, TIER_AFFILIATION,
            f"{method}: {str(rec.get('evidence') or '').strip()}".strip(": "),
            score))
    return edges


#: A cluster whose distinct legal names divided by its NPIs exceeds this
#: is not an owner. The ratio is the whole discriminator, and it is
#: sharp: Global Medical Response's officer signs for 123 NPIs under 21
#: names (0.17) because one company holds many entities under repeated
#: names, while a billing agent signs for 98 NPIs under 98 names (1.00)
#: because every client is a different organization.
OFFICIAL_MAX_NAME_RATIO = 0.70
#: …and a cluster that is mostly municipalities is a county or state EMS
#: coordinator, not an owner. Towns do not own each other.
OFFICIAL_MAX_CIVIL_SHARE = 0.34

#: Tokens that say nothing about who owns a provider. Stripped before
#: asking whether a cluster's members share a brand.
_OFFICIAL_STOP = frozenset({
    "AMBULANCE", "SERVICE", "SERVICES", "INC", "LLC", "EMS", "MEDICAL",
    "INCORPORATED", "CORPORATION", "CORP", "COMPANY", "THE", "OF", "AND",
    "VOLUNTEER", "FIRE", "DEPARTMENT", "DISTRICT", "COUNTY", "CITY", "TOWN",
    "RESCUE", "SQUAD", "LTD", "EMERGENCY", "HEALTH", "CARE", "CENTER",
})


def _official_key(name: Any) -> str:
    """A person's name, normalised enough to cluster on.

    Two words minimum. A single token is a title or a placeholder, and
    clustering on "ADMINISTRATOR" would merge a thousand unrelated
    organizations in one edge.
    """
    text = "".join(c if c.isalpha() or c.isspace() else " "
                   for c in str(name or "").upper())
    parts = [p for p in text.split() if len(p) > 1]
    return " ".join(parts) if len(parts) >= 2 else ""


def edges_from_officials(
    frame: pd.DataFrame,
    *,
    max_name_ratio: float = OFFICIAL_MAX_NAME_RATIO,
    max_civil_share: float = OFFICIAL_MAX_CIVIL_SHARE,
) -> List[ParentEdge]:
    """Organizations sharing an NPPES authorised official.

    This is the signal that reaches subsidiaries nothing else does. A
    corporate officer signs the filing for every entity their company
    owns, so Global Medical Response's officer connects Eagle Air Med,
    Air Evac EMS and Gold Cross Ambulance — three names with no shared
    token, no shared address, and no shared chain field.

    It is also the signal most likely to invent a conglomerate, because
    the identical shape is produced by someone who is not an owner at
    all: a billing agent, or a county EMS coordinator listed as
    authorised official for every volunteer squad in the county. Taking
    the whole cluster would merge 98 unrelated town ambulance services
    into one imaginary operator.

    Two guards separate them, and on this data they agree on every
    cluster:

    **Name diversity.** Distinct legal names divided by NPIs. One
    company holding many entities repeats its names — GMR's officer,
    123 NPIs across 21 names, scores 0.17. An agent's clients are all
    different organizations, so the ratio pins at 1.00. Above
    ``max_name_ratio`` the cluster is rejected.

    **Civil bodies.** A cluster that is mostly towns, counties and
    volunteer fire departments is a public-sector coordinator.
    Municipalities do not own each other, and the existing civil-body
    pattern already recognises them.

    Both are deliberately strict. They reject some genuine clusters —
    an officer at 0.89 with no civil bodies is probably real — and that
    is the trade this crosswalk makes everywhere: a wrong parent is
    worse than a missing one, because nobody audits a mapping that
    looks complete.
    """
    if frame.empty or "auth_official" not in frame.columns:
        return []
    name_column = "legal_name" if "legal_name" in frame.columns else "name"
    if name_column not in frame.columns:
        return []

    clusters: Dict[str, List[Tuple[str, str]]] = {}
    for npi, official, legal in zip(
            frame["npi"], frame["auth_official"], frame[name_column],
            strict=True):
        key = _official_key(official)
        node = node_key(NS_NPI, npi)
        if key and node:
            clusters.setdefault(key, []).append((node, str(legal or "")))

    edges: List[ParentEdge] = []
    for key, members in clusters.items():
        if len(members) < 2:
            continue
        names = {normalize_name(name) for _, name in members if name}
        if not names:
            continue
        ratio = len(names) / len(members)
        civil = sum(bool(_CIVIL_BODY_RE.search(n)) for n in names) / len(names)
        if ratio > max_name_ratio or civil > max_civil_share:
            continue
        parent = node_key(NS_OFFICIAL, key)
        evidence = (f"authorised official {key}: {len(members)} NPIs under "
                    f"{len(names)} names")
        for node, _name in members:
            edges.append(ParentEdge(node, parent, TIER_SHARED_OFFICIAL,
                                    evidence))
    return edges


def edges_from_eins(frame: pd.DataFrame) -> List[ParentEdge]:
    """Organizations sharing an Employer Identification Number.

    The strongest ownership signal NPPES carries and the simplest: an
    EIN is one taxpayer. Two NPIs filing under the same EIN are the same
    legal entity, not merely related ones — no inference involved.

    Empty in this build, because EIN reaches us only through the full
    dissemination file, which the ingest reads and the network does not
    reach. Wired anyway: it costs nothing and it is the first thing that
    should fire the day the real file lands.
    """
    if frame.empty or "ein" not in frame.columns:
        return []
    edges: List[ParentEdge] = []
    for npi, ein in zip(frame["npi"], frame["ein"], strict=True):
        node = node_key(NS_NPI, npi)
        # NPPES writes <UNAVAIL> and zero-fills where an EIN is withheld.
        text = str(ein or "").strip()
        if not node or not text or set(text) <= {"0"} or "UNAVAIL" in text.upper():
            continue
        parent = node_key(NS_EIN, text)
        if parent:
            edges.append(ParentEdge(node, parent, TIER_NPPES_SUBPART,
                                    f"shared EIN {text}"))
    return edges


def load_affiliations(db_path: Any) -> pd.DataFrame:
    """Read ``bridge_provider_affiliation`` from an NPPES connector store.

    Optional throughout. The bridge is built by a pipeline that needs
    the full dissemination file, so most builds will not have one, and
    a missing table degrades to an empty frame rather than raising —
    the same rule every other reference loader in this package follows.
    """
    import sqlite3

    columns = ["individual_npi", "organization_npi", "method", "confidence",
               "evidence"]
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return pd.DataFrame(columns=columns)
    try:
        rows = con.execute(
            f"SELECT {', '.join(columns)} FROM bridge_provider_affiliation"
        ).fetchall()
    except sqlite3.Error:
        return pd.DataFrame(columns=columns)
    finally:
        con.close()
    return pd.DataFrame(rows, columns=columns)


def build_parent_graph(
    *,
    crosswalk: Optional[pd.DataFrame] = None,
    npi_frame: Optional[pd.DataFrame] = None,
    affiliations: Optional[pd.DataFrame] = None,
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
    states: Dict[str, List[str]] = {}
    if crosswalk is not None and not crosswalk.empty:
        graph.add_edges(edges_from_crosswalk(crosswalk))
        _collect_states(states, crosswalk, NS_CHAIN, "chain_name")
    if npi_frame is not None and not npi_frame.empty:
        graph.add_edges(edges_from_npi_frame(npi_frame))
        graph.add_edges(edges_from_officials(npi_frame))
        graph.add_edges(edges_from_eins(npi_frame))
        _collect_states(states, npi_frame, NS_ORG, "parent_org_lbn")
    if affiliations is not None and not affiliations.empty:
        graph.add_edges(edges_from_affiliations(affiliations))

    if lift_names_to_systems:
        for node in sorted(graph.nodes):
            namespace, _, value = node.partition(":")
            if namespace in (NS_CHAIN, NS_ORG):
                _system_edges_for_name(graph, node, value,
                                       states.get(node, ()))
        _lift_groups_to_systems(graph)
    return graph


def _collect_states(into: Dict[str, List[str]], frame: pd.DataFrame,
                    namespace: str, name_column: str) -> None:
    """Remember which states a named parent's facilities sit in.

    State-scoped registry patterns cannot fire without one, and the
    node key is a normalised name that has thrown the state away.
    """
    if name_column not in frame.columns or "state" not in frame.columns:
        return
    for name, state in zip(frame[name_column], frame["state"], strict=True):
        node = node_key(namespace, name)
        code = str(state or "").strip().upper()
        if node and code and code not in into.setdefault(node, []):
            into[node].append(code)


def _lift_groups_to_systems(graph: ParentGraph) -> int:
    """Give a grouping node the brand its own members carry.

    Runs over every grouping namespace — PECOS enrolments, shared
    authorised officials, shared EINs. This is where the cluster
    signals pay off: an unbranded subsidiary that shares an officer
    with a branded sibling reaches the parent through the cluster,
    which no name or address match could have done for it.

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
    prefixes = tuple(f"{ns}:" for ns in (NS_PECOS, NS_OFFICIAL, NS_EIN))
    for node in sorted(graph.nodes):
        if not node.startswith(prefixes):
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
    lifted += _stack_enrolments_under_officials(graph)
    return lifted


def _stack_enrolments_under_officials(graph: ParentGraph) -> int:
    """Put a PECOS enrolment *under* its corporate officer, not beside it.

    Both signals fire on the same NPIs and they are not rivals: a PECOS
    Associate Control ID identifies one enrolment, while the officer who
    signs for it identifies the company that holds it. An operator with
    forty enrolments has forty PECOS IDs and one officer.

    Left as competing claims on each NPI, that read as 114 ownership
    disagreements on this data — every one of them spurious, because
    both answers were right about different levels. Linking the
    enrolment node to the official node makes it the hierarchy it
    actually is: ``npi → pecos:3476565987 → official:BRIAN TIERNEY``.
    The enrolment stays visible as an intermediate rather than being
    flattened away, which is what makes the chain auditable.

    Unanimity again: an enrolment whose members name two officers is
    not stacked, because the thing that would be stacked is ambiguous.
    """
    stacked = 0
    for node in sorted(graph.nodes):
        if not node.startswith(f"{NS_PECOS}:"):
            continue
        officials = {
            claim.parent
            for child in graph.children_of(node)
            for claim in graph.claims_for(child)
            if claim.tier == TIER_SHARED_OFFICIAL
        }
        if len(officials) == 1:
            stacked += graph.add_edge(
                node, officials.pop(), TIER_SHARED_OFFICIAL,
                "every NPI in this enrolment names the same official")
    return stacked


RESOLUTION_COLUMNS: Tuple[str, ...] = (
    "node", "namespace", "identifier", "final_parent",
    "final_parent_namespace", "final_parent_identifier",
    "tier", "confidence", "hops", "cycle", "truncated", "provenance",
)


PARENT_COLUMNS: Tuple[str, ...] = (
    "final_parent", "final_parent_type", "final_parent_id",
    "final_parent_name", "parent_tier", "parent_confidence", "parent_hops",
    "parent_basis", "parent_contested",
)


def _parent_display_name(final_parent: str) -> str:
    """A partner-readable name for a resolved parent.

    ``sys:davita`` is an internal key; "DaVita Kidney Care" is the
    answer. Chain and organization roots already carry a name — the
    normalised one, which is ugly but is not a lie — and PECOS and CCN
    roots have no name at all, so they render as the identifier they
    are rather than as a blank that reads like a failure.
    """
    namespace, _, value = final_parent.partition(":")
    if namespace == NS_SYSTEM:
        sysdef = get_system(value)
        return sysdef.name if sysdef is not None else value
    if namespace in (NS_CHAIN, NS_ORG):
        return value
    if namespace == NS_PECOS:
        return f"PECOS enrolment group {value}"
    if namespace == NS_CCN:
        return f"CCN {value}"
    if namespace == NS_NPI:
        return f"NPI {value}"
    return final_parent


def attach_parents(frame: pd.DataFrame, *,
                   graph: Optional[ParentGraph] = None,
                   namespace: str = NS_CCN,
                   key: str = "ccn") -> pd.DataFrame:
    """Widen a frame of identifiers with where each one's owner ends up.

    Kept out of :func:`provider_crosswalk.get_crosswalk` on purpose. The
    graph is *built from* the crosswalk, so folding the result back into
    the same function would make the crosswalk depend on itself; and 104
    tests pin that frame's 45-column shape, which is a contract worth
    keeping stable. This is the opt-in widening instead.

    Builds a graph from ``frame`` when none is supplied, so the common
    case is one call.
    """
    if frame.empty or key not in frame.columns:
        widened = frame.copy()
        for column in PARENT_COLUMNS:
            widened[column] = ""
        return widened

    if graph is None:
        graph = build_parent_graph(crosswalk=frame)
    contested = graph.contested()

    rows: List[Dict[str, Any]] = []
    for value in frame[key]:
        node = node_key(namespace, value)
        res = graph.resolve(node) if node else None
        if res is None or res.is_root:
            # Blank text, zero counts. Mixing "" into the count columns
            # makes the whole column object-typed, and every downstream
            # `parent_hops > 1` then raises rather than filtering.
            blank = {c: "" for c in PARENT_COLUMNS}
            blank["parent_hops"] = 0
            blank["parent_contested"] = 0
            rows.append(blank)
            continue
        parent_ns, _, parent_id = res.final_parent.partition(":")
        rows.append({
            "final_parent": res.final_parent,
            "final_parent_type": parent_ns,
            "final_parent_id": parent_id,
            "final_parent_name": _parent_display_name(res.final_parent),
            "parent_tier": res.weakest_tier,
            "parent_confidence": res.confidence,
            "parent_hops": res.hops,
            "parent_basis": res.provenance,
            "parent_contested": 1 if node in contested else 0,
        })

    widened = frame.copy()
    attached = pd.DataFrame(rows, columns=list(PARENT_COLUMNS),
                            index=frame.index)
    for column in PARENT_COLUMNS:
        widened[column] = attached[column]
    return widened


@lru_cache(maxsize=1)
def crosswalk_graph() -> ParentGraph:
    """The ownership graph over the whole certified universe, built once.

    Takes no scope, deliberately. A parent is a property of the graph,
    not of whatever slice a request asked for: resolving inside a filter
    would silently drop every parent sitting outside it. Building it
    per-scope was self-consistent on today's data — hospital rows resolve
    identically either way — but it left two graphs able to disagree
    about the same CCN, which is the kind of thing that stays true right
    up until it doesn't.
    """
    from .provider_crosswalk import SCOPE_ALL, get_crosswalk

    return build_parent_graph(crosswalk=get_crosswalk(scope=SCOPE_ALL))


DISAGREEMENT_COLUMNS: Tuple[str, ...] = (
    "node", "namespace", "identifier", "resolved_parent", "resolved_tier",
    "resolved_confidence", "rival_parent", "rival_tier", "rival_confidence",
    "candidates", "evidence",
)


def ownership_disagreements(graph: ParentGraph) -> pd.DataFrame:
    """Facilities whose sources name different owners — the closest thing
    to an acquisition list this data supports.

    CMS publishes change-of-ownership only as state-by-year counts; there
    is no facility-level CHOW file, so an acquisition roster cannot be
    read off anything here. What *can* be read is disagreement. When an
    operator-published chain name and the resolved health system point at
    two different parents, one of them is usually stale, and stale
    usually means the facility changed hands: clinics still filing under
    Innovative Dialysis Systems that resolve to US Renal Care, under
    Diversified Specialty Institutes that resolve to DSI Renal.

    This is a work queue, not a transaction log. Every row is a question
    with both answers and the evidence for each, ordered so the ones a
    reviewer can settle fastest come first. Calling it an acquisition
    list would be claiming a fact; calling it a disagreement is the fact.
    """
    rows: List[Dict[str, Any]] = []
    for node, finals in sorted(graph.contested().items()):
        namespace, _, identifier = node.partition(":")
        claims = sorted(graph.claims_for(node), key=lambda e: (e.rank, e.parent))
        if not claims:
            continue
        winner = claims[0]
        resolved = graph.resolve(node)
        rival = next(
            (c for c in claims[1:]
             if graph.resolve(c.parent).final_parent != resolved.final_parent),
            None)
        rival_res = graph.resolve(rival.parent) if rival is not None else None
        rows.append({
            "node": node,
            "namespace": namespace,
            "identifier": identifier,
            "resolved_parent": resolved.final_parent,
            "resolved_tier": winner.tier,
            "resolved_confidence": resolved.confidence,
            "rival_parent": rival_res.final_parent if rival_res else "",
            "rival_tier": rival.tier if rival is not None else "",
            # The rival's score is the score of *taking that route*, not
            # the score of the node it happens to end on. A rival system
            # is always a root, and a root is always 1.0 — reporting
            # that made every rival look like the certain answer.
            "rival_confidence": (min(rival.confidence, rival_res.confidence)
                                 if rival_res is not None else ""),
            "candidates": " | ".join(finals),
            "evidence": " | ".join(
                f"{c.tier}: {c.evidence or c.parent}" for c in claims),
        })
    if not rows:
        return pd.DataFrame(columns=list(DISAGREEMENT_COLUMNS))
    frame = pd.DataFrame(rows, columns=list(DISAGREEMENT_COLUMNS))
    # Highest-confidence disagreements first: those are the ones where
    # both sources are strong and one of them is genuinely wrong.
    return frame.sort_values(["resolved_confidence", "node"],
                             ascending=[False, True]).reset_index(drop=True)


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


def _clear_cache() -> None:
    """Test hook."""
    crosswalk_graph.cache_clear()
