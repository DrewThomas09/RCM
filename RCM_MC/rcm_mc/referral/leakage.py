"""Leakage + key-person-risk scoring.

Leakage = referrals OUT of the platform's controlled physician set
to providers outside the organization. In an MSO/Friendly-PC
deal, leakage is the partner's primary financial risk: every
out-of-network referral is revenue earned by a competitor.

Key-person risk = % of platform inbound referrals concentrated in
a single non-platform physician. If 40% of the platform's inbound
volume comes from one referring doc, losing that doc is a
material outcome.

Both metrics are computed against an organization tag stored on
each NPI (``ReferralGraph.set_node_org``). The "platform" set is
identified by an org name or list of orgs the partner targets.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from .graph import ReferralGraph


def _platform_set(
    graph: ReferralGraph,
    platform_orgs: Iterable[str],
) -> Set[str]:
    """Build the NPI set associated with the platform organizations."""
    plat_orgs = {str(o) for o in platform_orgs if o}
    return {npi for npi in graph.nodes()
            if graph.node_org(npi) in plat_orgs}


def compute_leakage(
    graph: ReferralGraph,
    platform_orgs: Iterable[str],
) -> dict:
    """Compute platform-wide leakage.

    Returns:
        {
          "internal_referral_volume": float,
          "external_referral_volume": float,
          "leakage_rate": float (0-1),
          "platform_npi_count": int,
          "external_destinations": [(npi, weight), ...]  top 10 by volume
        }
    """
    plat = _platform_set(graph, platform_orgs)
    internal = 0.0
    external = 0.0
    ext_volumes: Dict[str, float] = {}

    for src, dst, w in graph.edges():
        if src not in plat:
            continue
        if dst in plat:
            internal += w
        else:
            external += w
            ext_volumes[dst] = ext_volumes.get(dst, 0.0) + w

    total = internal + external
    rate = (external / total) if total > 0 else 0.0
    top_external = sorted(
        ext_volumes.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "internal_referral_volume": round(internal, 2),
        "external_referral_volume": round(external, 2),
        "leakage_rate": round(rate, 4),
        "platform_npi_count": len(plat),
        "external_destinations": [
            {"npi": npi, "weight": round(w, 2)}
            for npi, w in top_external
        ],
    }


def compute_key_person_risk(
    graph: ReferralGraph,
    platform_orgs: Iterable[str],
    *,
    threshold: float = 0.20,
) -> dict:
    """Identify referring NPIs (outside the platform) whose volume
    represents a critical share of platform inbound referrals.

    A "critical" referrer is anyone whose contribution exceeds
    ``threshold`` (default 20%) of total inbound referral volume.
    """
    plat = _platform_set(graph, platform_orgs)
    referrer_volumes: Dict[str, float] = {}
    total = 0.0

    for src, dst, w in graph.edges():
        if dst not in plat:
            continue
        if src in plat:
            continue  # internal — not a key-person dependency
        referrer_volumes[src] = referrer_volumes.get(src, 0.0) + w
        total += w

    ranked = sorted(
        referrer_volumes.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    risk_list = []
    for src, w in ranked:
        share = (w / total) if total > 0 else 0.0
        risk_list.append({
            "npi": src,
            "volume": round(w, 2),
            "share_of_inbound": round(share, 4),
            "critical": share >= threshold,
        })
    critical = [r for r in risk_list if r["critical"]]
    return {
        "total_inbound_volume": round(total, 2),
        "external_referrer_count": len(risk_list),
        "critical_count": len(critical),
        "critical_threshold_pct": threshold,
        "referrers": risk_list[:25],   # cap for digest size
    }
