"""Health-system reconstruction (organization → organization clustering).

`bridge_provider_affiliation` links individuals to organizations. This module
goes one level up: it clusters Type-2 organization NPIs into the multi-site
*health systems* they belong to — the unit a CDD analyst reasons about when
sizing a competitor or an acquisition platform.

Heuristic (documented, confidence-scored): two organizations are joined into
the same system when they share a distinctive legal-business-name token
(≥4 chars, not a corporate-form/industry stopword) AND corroborating
evidence — either a shared other-organization name token or co-location in
the same metro (state). Connected components over those edges are systems.
This is deliberately conservative to avoid merging unrelated "SMITH"
practices; a system needs name cohesion *plus* a second signal.

Read-only over the canonical tables; returns ranked system descriptors with
member NPIs, geographic spread, and captive-provider footprint. Kept as an
analytics function (not a materialized table) so it adds no pipeline schema
and re-derives cleanly on every call.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from .affiliation import _name_tokens  # reuse the same tokenizer/stopwords

# Specialty / industry / corporate-form words are NOT distinctive enough to
# anchor a system — "INTERNAL MEDICINE" practices are not one company. Only
# brand or surname tokens should anchor. This extends the affiliation
# stopword set with the clinical-vocabulary terms that recur across
# unaffiliated practice names.
SYSTEM_STOPWORDS = {
    "MEDICINE", "FAMILY", "INTERNAL", "GENERAL", "PRIMARY", "CARDIOLOGY",
    "PRACTICE", "SOLO", "PEDIATRIC", "PEDIATRICS", "SURGERY", "SURGICAL",
    "ORTHOPEDIC", "ORTHOPEDICS", "DERMATOLOGY", "ONCOLOGY", "RADIOLOGY",
    "NEUROLOGY", "OBGYN", "OB", "GYN", "URGENT", "SPECIALISTS", "SPECIALTY",
    "PHYSICIANS", "PHYSICIAN", "HOSPITAL", "HOSPITALS", "REGIONAL",
    "COMMUNITY", "CENTERS", "INSTITUTE", "FOUNDATION", "NETWORK", "SYSTEM",
    "AFFILIATES", "PROFESSIONAL", "PROFESSIONALS", "WELLNESS", "TREATMENT",
}


def _distinctive_tokens(name: str) -> Set[str]:
    return {t for t in _name_tokens(name)
            if len(t) >= 4 and t not in SYSTEM_STOPWORDS}


class _UnionFind:
    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def health_systems(
    store: Any, *, min_members: int = 2, limit: int = 100,
) -> List[Dict[str, Any]]:
    """Reconstruct multi-site health systems from Type-2 organizations.
    Returns systems (≥ ``min_members`` org NPIs) ranked by member count then
    captive-provider footprint."""
    with store.connect() as con:
        orgs = con.execute(
            "SELECT p.npi, p.organization_name, "
            "  (SELECT a.state FROM dim_provider_address a "
            "   WHERE a.npi=p.npi AND a.address_purpose='practice' LIMIT 1) AS state "
            "FROM dim_provider p WHERE p.entity_type=2 AND p.status='active'"
        ).fetchall()
        other = defaultdict(set)
        for r in con.execute("SELECT npi, other_name FROM nppes_other_name"):
            other[r["npi"]] |= _distinctive_tokens(r["other_name"])
        captive = {r["organization_npi"]: r["c"] for r in con.execute(
            "SELECT organization_npi, COUNT(DISTINCT individual_npi) c "
            "FROM bridge_provider_affiliation GROUP BY organization_npi")}

    # token -> orgs carrying it (from legal name + other names)
    token_orgs: Dict[str, List[str]] = defaultdict(list)
    org_meta: Dict[str, Dict] = {}
    org_tokens: Dict[str, Set[str]] = {}
    for r in orgs:
        npi = r["npi"]
        toks = _distinctive_tokens(r["organization_name"]) | other.get(npi, set())
        org_tokens[npi] = toks
        org_meta[npi] = {"name": r["organization_name"] or "",
                         "state": r["state"] or "",
                         "captive": captive.get(npi, 0)}
        for t in toks:
            token_orgs[t].append(npi)

    uf = _UnionFind()
    for npi in org_meta:
        uf.find(npi)  # ensure singleton present
    edge_tokens: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for token, members in token_orgs.items():
        if len(members) < 2:
            continue
        # only join pairs that ALSO share a second signal: another shared
        # token, a shared other-name token, or the same state.
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                shared = org_tokens[a] & org_tokens[b]
                same_state = (org_meta[a]["state"] and
                              org_meta[a]["state"] == org_meta[b]["state"])
                if len(shared) >= 2 or same_state:
                    uf.union(a, b)
                    edge_tokens[(uf.find(a), uf.find(b))] |= shared

    comps: Dict[str, List[str]] = defaultdict(list)
    for npi in org_meta:
        comps[uf.find(npi)].append(npi)

    systems = []
    for root, members in comps.items():
        if len(members) < min_members:
            continue
        # system name = the most common distinctive token across members
        tok_count: Dict[str, int] = defaultdict(int)
        for m in members:
            for t in org_tokens[m]:
                tok_count[t] += 1
        sys_token = max(tok_count, key=lambda t: (tok_count[t], -len(t))) if tok_count else "?"
        states = sorted({org_meta[m]["state"] for m in members if org_meta[m]["state"]})
        total_captive = sum(org_meta[m]["captive"] for m in members)
        # cohesion: share of members carrying the system token
        cohesion = round(tok_count.get(sys_token, 0) / len(members), 3)
        systems.append({
            "system_name": sys_token,
            "member_count": len(members),
            "states": states,
            "state_count": len(states),
            "captive_providers": total_captive,
            "cohesion": cohesion,
            "member_npis": sorted(members)[:50],
        })
    systems.sort(key=lambda s: (s["member_count"], s["captive_providers"]),
                 reverse=True)
    return systems[:limit]
