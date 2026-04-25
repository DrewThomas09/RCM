"""Physician referral network — graph + leakage + key-person risk.

In MSO and Friendly-PC deals (and any sponsor playbook that hinges
on physician retention), the partner's #1 question is:

    "If our top 5 referring physicians walk after close, how much
     of the platform's downstream business goes with them?"

This package turns that into a tractable, data-driven answer:

  • Build a directed multi-edge referral graph from CMS Physician
    Referral data (publicly available shared-patient files) joined
    against NPPES (the pricing.nppes table) for organizational
    context.
  • Compute centrality metrics so the partner can name the actual
    hub physicians, not "physicians in general."
  • Score key-person-risk per physician — the % of platform
    inbound referrals that flow through that single NPI.
  • Simulate post-acquisition departures: drop a node, recompute
    leakage, return a $-quantified retention recommendation.

Public API::

    from rcm_mc.referral import (
        ReferralGraph, ReferralEdge,
        eigenvector_centrality, in_degree_centrality,
        compute_leakage, compute_key_person_risk,
        simulate_departure, payer_leverage_score,
    )

The graph implementation is pure stdlib — no networkx dependency.
For the panel sizes typical in PE diligence (a few thousand NPIs),
power-iteration on a sparse adjacency dict converges in <100ms.
"""
from .graph import ReferralGraph, ReferralEdge
from .centrality import (
    eigenvector_centrality,
    in_degree_centrality,
    out_degree_centrality,
)
from .leakage import compute_leakage, compute_key_person_risk
from .simulate import simulate_departure, payer_leverage_score

__all__ = [
    "ReferralGraph",
    "ReferralEdge",
    "eigenvector_centrality",
    "in_degree_centrality",
    "out_degree_centrality",
    "compute_leakage",
    "compute_key_person_risk",
    "simulate_departure",
    "payer_leverage_score",
]
