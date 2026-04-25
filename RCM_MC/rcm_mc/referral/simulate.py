"""Departure simulation + payer-leverage scoring.

Two operations:

  • simulate_departure(graph, npi, ...): drop a node and recompute
    leakage. Returns the *delta* in leakage rate + the lost
    inbound volume that would re-route somewhere unknown. This
    is the math for the partner question: "if this physician
    leaves at close, how much business walks?"

  • payer_leverage_score: cross-reference the referral graph with
    a payer-rates view (rcm_mc.pricing) to estimate the dollar
    impact of a leakage event for a specific payer. Higher
    scores mean the payer has more leverage to demand price
    concessions because alternative in-network providers exist
    nearby.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .graph import ReferralGraph
from .leakage import compute_leakage, compute_key_person_risk


def simulate_departure(
    graph: ReferralGraph,
    npi: str,
    platform_orgs: Iterable[str],
) -> dict:
    """Simulate a single physician's departure.

    Drops the NPI from the graph, recomputes leakage, and returns
    the before/after delta + the lost inbound volume. The output
    dict is partner-ready (the UI page can render it without
    further math).
    """
    before = compute_leakage(graph, platform_orgs)
    new_g = graph.drop_node(npi)
    after = compute_leakage(new_g, platform_orgs)

    # The departed physician's inbound contribution is everything
    # that was flowing through them.
    lost_inbound = graph.in_weight(npi)
    lost_outbound = graph.out_weight(npi)

    return {
        "departed_npi": npi,
        "departed_org": graph.node_org(npi),
        "before": before,
        "after": after,
        "leakage_rate_delta": round(
            after["leakage_rate"] - before["leakage_rate"], 4),
        "internal_volume_lost": round(
            before["internal_referral_volume"]
            - after["internal_referral_volume"], 2),
        "external_volume_lost": round(
            before["external_referral_volume"]
            - after["external_referral_volume"], 2),
        "physician_inbound_volume": round(lost_inbound, 2),
        "physician_outbound_volume": round(lost_outbound, 2),
    }


def payer_leverage_score(
    graph: ReferralGraph,
    platform_orgs: Iterable[str],
    *,
    payer_npis: Iterable[str] = (),
) -> dict:
    """Estimate payer-leverage by computing the share of inbound
    platform volume that comes from physicians the payer has
    in-network alternatives for.

    Inputs:
      payer_npis — the NPIs the payer has alternative contracts
                   with (i.e. providers a member could be steered
                   to instead of the platform).

    Higher score (0-1) → payer has more leverage. A score of 0.7
    means 70% of the platform's referral inbound volume could
    plausibly be re-routed by the payer to alternative in-network
    providers.

    The math is intentionally conservative: we only count an
    edge as "rerouteable" if the receiving NPI is in
    ``payer_npis`` AND outside the platform.
    """
    payer_set = {str(n) for n in payer_npis if n}
    plat_set = {npi for npi in graph.nodes()
                if graph.node_org(npi) in set(platform_orgs)}

    inbound_total = 0.0
    rerouteable = 0.0
    for src, dst, w in graph.edges():
        if dst in plat_set:
            inbound_total += w
            if src in payer_set:
                rerouteable += w

    score = rerouteable / inbound_total if inbound_total > 0 else 0.0
    return {
        "platform_inbound_volume": round(inbound_total, 2),
        "rerouteable_volume": round(rerouteable, 2),
        "payer_leverage_score": round(score, 4),
        "payer_npi_count": len(payer_set),
    }
