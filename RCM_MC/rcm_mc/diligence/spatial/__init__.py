"""Spatial competition — Huff gravity model + Moran's I.

Patient-capture probability by attractiveness and distance (the
rigorous service area, not a radius circle), plus a spatial-clustering
test on utilization. Distances via haversine; no geo dependencies.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .competition import (
    DemandPoint,
    EntrantImpactResult,
    Facility,
    HuffResult,
    LisaPoint,
    LisaResult,
    MoranResult,
    SpatialVerdict,
    competitor_impact,
    haversine_km,
    huff_capture,
    local_morans_i,
    morans_i,
)

__all__ = [
    "DemandPoint",
    "EntrantImpactResult",
    "Facility",
    "HuffResult",
    "LisaPoint",
    "LisaResult",
    "MoranResult",
    "SpatialVerdict",
    "competitor_impact",
    "haversine_km",
    "huff_capture",
    "local_morans_i",
    "morans_i",
]
