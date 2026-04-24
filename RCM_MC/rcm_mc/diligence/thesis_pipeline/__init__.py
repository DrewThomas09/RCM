"""Thesis Pipeline — close the diligence-to-investment-math loop.

Previously, a partner ran the diligence analytics individually
(benchmarks, denial prediction, PPAM, Deal Autopsy, counterfactual,
Steward, cyber, V28) and then hand-entered the Deal MC + EBITDA
bridge drivers. This orchestrator takes the same inputs a partner
would type and runs the full chain, returning a populated
``DealScenario`` for Deal MC plus a ``ThesisPipelineReport``
bundling every analytic output for downstream consumers (Deal
Profile writeback, IC Packet headline-number wiring, Checklist
auto-completion).

Why this is the highest-leverage closing move:

    Two prior retros flagged "writeback from analytics → Deal
    Profile" as next-cycle #1. The friction point is a partner
    running Deal MC and having to mentally carry P50 MOIC over
    to the IC Packet. This pipeline makes that one button.

Public API::

    from rcm_mc.diligence.thesis_pipeline import (
        PipelineInput, ThesisPipelineReport,
        run_thesis_pipeline,
    )
"""
from __future__ import annotations

from .orchestrator import (
    PipelineInput, ThesisPipelineReport, run_thesis_pipeline,
    pipeline_observations,
)

__all__ = [
    "PipelineInput",
    "ThesisPipelineReport",
    "pipeline_observations",
    "run_thesis_pipeline",
]
