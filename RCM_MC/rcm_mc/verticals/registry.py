"""Vertical registry — dispatches metric registries, bridges, and
ontologies based on the deal's vertical type (Prompt 78).

Vertical enum: HOSPITAL (existing default), ASC, MSO, BEHAVIORAL_HEALTH.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, Optional


class Vertical(str, Enum):
    HOSPITAL = "HOSPITAL"
    ASC = "ASC"
    MSO = "MSO"
    BEHAVIORAL_HEALTH = "BEHAVIORAL_HEALTH"


def get_metric_registry(vertical: str) -> Dict[str, Dict[str, Any]]:
    """Return the metric registry for the given vertical."""
    v = vertical.upper()
    if v == "ASC":
        from .asc.ontology import ASC_METRIC_REGISTRY
        return ASC_METRIC_REGISTRY
    if v == "MSO":
        from .mso.ontology import MSO_METRIC_REGISTRY
        return MSO_METRIC_REGISTRY
    if v == "BEHAVIORAL_HEALTH":
        from .behavioral_health.ontology import BH_METRIC_REGISTRY
        return BH_METRIC_REGISTRY
    # Default: hospital.
    from ..analysis.completeness import RCM_METRIC_REGISTRY
    return RCM_METRIC_REGISTRY
