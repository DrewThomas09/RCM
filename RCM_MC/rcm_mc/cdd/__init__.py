"""CDD analytics expansion for PEDesk / RCM-MC.

A cohesive subpackage of commercial-due-diligence analytics. Every analytic is
a pure, deterministic, statistical estimator that returns an audience-aware
:class:`~rcm_mc.cdd.exhibit.Exhibit` with machine-readable footnotes and an
emitted reconciliation. No analytic routes a prediction through an LLM.

Import the registry to enumerate and run features::

    from rcm_mc.cdd import registry
    registry.run("NEW-01", internal_mode=True)
"""
from __future__ import annotations

from .exhibit import (
    AssumptionNode,
    Exhibit,
    Flag,
    Footnote,
    Reconciliation,
    Series,
    lint_copy,
)

__all__ = [
    "AssumptionNode",
    "Exhibit",
    "Flag",
    "Footnote",
    "Reconciliation",
    "Series",
    "lint_copy",
]
