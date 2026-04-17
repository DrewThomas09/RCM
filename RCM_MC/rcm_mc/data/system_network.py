"""Hospital system network graph + acquisition target finder (Prompt 70).

Builds a graph of hospital systems and their member hospitals from
the HCRIS bundle. Finds standalone hospitals near a system's
footprint as potential add-on acquisition targets.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .geo_lookup import STATE_CENTROIDS, haversine_miles


@dataclass
class HospitalNode:
    ccn: str
    name: str
    state: str = ""
    bed_count: int = 0
    system: str = ""
    lat: float = 0.0
    lon: float = 0.0
    is_portfolio: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn, "name": self.name, "state": self.state,
            "bed_count": int(self.bed_count),
            "system": self.system, "lat": self.lat, "lon": self.lon,
            "is_portfolio": self.is_portfolio,
        }


@dataclass
class ProximityEdge:
    hospital_a: str   # ccn
    hospital_b: str
    distance_miles: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hospital_a": self.hospital_a,
            "hospital_b": self.hospital_b,
            "distance_miles": float(self.distance_miles),
        }


@dataclass
class SystemGraph:
    systems: Dict[str, List[HospitalNode]] = field(default_factory=dict)
    standalone: List[HospitalNode] = field(default_factory=list)
    edges: List[ProximityEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "systems": {
                k: [n.to_dict() for n in v]
                for k, v in self.systems.items()
            },
            "standalone": [n.to_dict() for n in self.standalone],
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class AcquisitionTarget:
    hospital: HospitalNode
    distance_to_nearest: float
    fit_score: float
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hospital": self.hospital.to_dict(),
            "distance_to_nearest": float(self.distance_to_nearest),
            "fit_score": float(self.fit_score),
            "rationale": self.rationale,
        }


def _node_from_row(row: Dict[str, Any]) -> HospitalNode:
    state = str(row.get("state") or "").upper()
    coords = STATE_CENTROIDS.get(state, (0.0, 0.0))
    system = str(row.get("system_affiliation") or row.get("system") or "")
    return HospitalNode(
        ccn=str(row.get("ccn") or ""),
        name=str(row.get("name") or ""),
        state=state,
        bed_count=int(row.get("beds") or 0),
        system=system,
        lat=coords[0], lon=coords[1],
    )


def build_system_graph(*, limit: int = 5000) -> SystemGraph:
    """Construct a graph from the shipped HCRIS bundle."""
    try:
        from .hcris import _get_latest_per_ccn, _row_to_dict
    except Exception:  # noqa: BLE001
        return SystemGraph()
    df = _get_latest_per_ccn()
    if df.empty:
        return SystemGraph()

    graph = SystemGraph()
    for _, raw_row in df.head(limit).iterrows():
        row = _row_to_dict(raw_row)
        node = _node_from_row(row)
        if node.system:
            graph.systems.setdefault(node.system, []).append(node)
        else:
            graph.standalone.append(node)
    return graph


def find_acquisition_targets(
    system_name: str, *, radius_miles: float = 50,
    limit: int = 20,
) -> List[AcquisitionTarget]:
    """Standalone hospitals near the system's existing footprint."""
    graph = build_system_graph()
    system_nodes = graph.systems.get(system_name, [])
    if not system_nodes:
        return []

    targets: List[AcquisitionTarget] = []
    for standalone in graph.standalone:
        if standalone.lat == 0 and standalone.lon == 0:
            continue
        nearest_dist = float("inf")
        for sn in system_nodes:
            if sn.lat == 0 and sn.lon == 0:
                continue
            d = haversine_miles(standalone.lat, standalone.lon,
                                sn.lat, sn.lon)
            if d < nearest_dist:
                nearest_dist = d
        if nearest_dist > radius_miles:
            continue
        # Fit score: closer + similar size = better fit.
        avg_beds = (
            sum(n.bed_count for n in system_nodes) / len(system_nodes)
        ) if system_nodes else 200
        size_fit = max(0, 1.0 - abs(standalone.bed_count - avg_beds) / max(avg_beds, 1))
        proximity_fit = max(0, 1.0 - nearest_dist / radius_miles)
        score = (proximity_fit * 60 + size_fit * 40)
        targets.append(AcquisitionTarget(
            hospital=standalone,
            distance_to_nearest=nearest_dist,
            fit_score=score,
            rationale=(
                f"{standalone.name} ({standalone.bed_count} beds, "
                f"{nearest_dist:.0f} mi from nearest {system_name} facility)"
            ),
        ))

    targets.sort(key=lambda t: t.fit_score, reverse=True)
    return targets[:limit]
