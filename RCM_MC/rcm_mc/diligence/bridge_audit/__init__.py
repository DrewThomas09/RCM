"""EBITDA Bridge Auto-Auditor.

Ingests a banker-provided bridge and audits each lever against the
realized-outcome distribution from our RCM initiative library.
Produces a risk-adjusted bridge + counter-bid recommendation.

Public API::

    from rcm_mc.diligence.bridge_audit import (
        BridgeAuditReport, BridgeLever, LEVER_PRIORS,
        LeverAudit, LeverCategory, LeverVerdict,
        audit_bridge, audit_lever, classify_lever,
        parse_bridge_text,
    )
"""
from __future__ import annotations

from .auditor import (
    BridgeAuditReport, BridgeLever, LeverAudit, LeverVerdict,
    audit_bridge, audit_lever, parse_bridge_text,
)
from .lever_library import (
    LEVER_PRIORS, LeverCategory, LeverPrior,
    classify_lever, prior_for,
)

__all__ = [
    "BridgeAuditReport",
    "BridgeLever",
    "LEVER_PRIORS",
    "LeverAudit",
    "LeverCategory",
    "LeverPrior",
    "LeverVerdict",
    "audit_bridge",
    "audit_lever",
    "classify_lever",
    "parse_bridge_text",
    "prior_for",
]
