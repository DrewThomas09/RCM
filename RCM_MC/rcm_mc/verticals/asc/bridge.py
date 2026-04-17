"""ASC value bridge (Prompt 78).

Different levers from hospitals: room utilization, case-mix
optimization, out-of-network negotiation, prior-auth workflow,
implant pricing, surgeon distribution model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ASCLeverImpact:
    lever_key: str
    current_value: float = 0.0
    target_value: float = 0.0
    revenue_impact: float = 0.0
    cost_impact: float = 0.0
    ebitda_impact: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever_key": self.lever_key,
            "current_value": float(self.current_value),
            "target_value": float(self.target_value),
            "revenue_impact": float(self.revenue_impact),
            "cost_impact": float(self.cost_impact),
            "ebitda_impact": float(self.ebitda_impact),
        }


@dataclass
class ASCBridgeResult:
    lever_impacts: List[ASCLeverImpact] = field(default_factory=list)
    total_ebitda_impact: float = 0.0
    status: str = "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever_impacts": [li.to_dict() for li in self.lever_impacts],
            "total_ebitda_impact": float(self.total_ebitda_impact),
            "status": self.status,
        }


_ASC_LEVER_COEFFICIENTS = {
    "cases_per_room_per_day": {"revenue_per_unit": 3500, "direction": 1},
    "room_turnover_minutes": {"revenue_per_unit": -50, "direction": -1},
    "prior_auth_denial_rate": {"revenue_per_unit": -200, "direction": -1},
    "same_day_cancellation_rate": {"revenue_per_unit": -300, "direction": -1},
    "out_of_network_pct": {"revenue_per_unit": -100, "direction": -1},
    "implant_revenue_pct": {"revenue_per_unit": 500, "direction": 1},
}


def compute_asc_bridge(
    current_metrics: Dict[str, float],
    target_metrics: Dict[str, float],
    *,
    case_volume: int = 8000,
) -> ASCBridgeResult:
    """Run ASC-specific lever calculations."""
    impacts: List[ASCLeverImpact] = []
    for metric, coef in _ASC_LEVER_COEFFICIENTS.items():
        cur = current_metrics.get(metric)
        tgt = target_metrics.get(metric)
        if cur is None or tgt is None:
            continue
        delta = (float(tgt) - float(cur)) * coef["direction"]
        rev = delta * coef["revenue_per_unit"] * (case_volume / 8000.0)
        impacts.append(ASCLeverImpact(
            lever_key=metric,
            current_value=float(cur),
            target_value=float(tgt),
            revenue_impact=rev,
            ebitda_impact=rev,
        ))
    total = sum(li.ebitda_impact for li in impacts)
    return ASCBridgeResult(
        lever_impacts=impacts,
        total_ebitda_impact=total,
    )
