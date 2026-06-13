"""Quasi-experimental policy-shock evaluation for diligence.

Difference-in-differences (with cluster-robust inference, event-study
parallel-trends and placebo checks) plus a synthetic-control fallback,
turning "what does this policy do to the asset" into an estimated,
defensible number instead of a flat revenue haircut. A curated library
of dated policy shocks (OBBBA Medicaid, CY2027 MA rate, PFS, site
neutral) scopes the natural experiments.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .did_estimator import (
    DiDResult,
    EventStudyResult,
    PanelData,
    PolicyEbitdaOverlay,
    PolicyVerdict,
    SyntheticControlResult,
    did_2x2,
    estimate_did,
    event_study,
    placebo_test,
    policy_ebitda_overlay,
    synthetic_control,
)
from .policy_library import (
    POLICY_SHOCKS,
    ExpectedSign,
    PolicyShock,
    get_policy,
    list_policies,
)

__all__ = [
    "POLICY_SHOCKS",
    "DiDResult",
    "EventStudyResult",
    "ExpectedSign",
    "PanelData",
    "PolicyEbitdaOverlay",
    "PolicyShock",
    "PolicyVerdict",
    "SyntheticControlResult",
    "did_2x2",
    "estimate_did",
    "event_study",
    "get_policy",
    "list_policies",
    "placebo_test",
    "policy_ebitda_overlay",
    "synthetic_control",
]
