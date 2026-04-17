"""Behavioral health value bridge (Prompt 80).

Levers: prior-auth workflow, length-of-stay optimization,
outcome-based contracts, level-of-care optimization.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class BHLeverImpact:
    lever_key: str
    current_value: float = 0.0
    target_value: float = 0.0
    ebitda_impact: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return {"lever_key": self.lever_key, "current_value": self.current_value,
                "target_value": self.target_value, "ebitda_impact": self.ebitda_impact}

@dataclass
class BHBridgeResult:
    lever_impacts: List[BHLeverImpact] = field(default_factory=list)
    total_ebitda_impact: float = 0.0
    status: str = "OK"
    def to_dict(self) -> Dict[str, Any]:
        return {"lever_impacts": [l.to_dict() for l in self.lever_impacts],
                "total_ebitda_impact": self.total_ebitda_impact, "status": self.status}

_BH_COEFFICIENTS = {
    "avg_length_of_stay": -2000.0,      # shorter stays = less cost
    "readmission_30day": -5000.0,       # lower readmit = quality bonus
    "prior_auth_days": -3000.0,         # faster auth = less revenue leakage
    "occupancy_rate": 4000.0,           # higher occupancy = more revenue
    "payer_denial_rate": -3500.0,       # lower denial = more collected
}

def compute_bh_bridge(current: Dict[str, float], target: Dict[str, float],
                      *, bed_days: int = 15000) -> BHBridgeResult:
    impacts: List[BHLeverImpact] = []
    for metric, coef in _BH_COEFFICIENTS.items():
        cur, tgt = current.get(metric), target.get(metric)
        if cur is None or tgt is None: continue
        delta = float(tgt) - float(cur)
        impact = delta * coef * (bed_days / 15000.0)
        impacts.append(BHLeverImpact(lever_key=metric, current_value=float(cur),
                                      target_value=float(tgt), ebitda_impact=impact))
    return BHBridgeResult(lever_impacts=impacts,
                          total_ebitda_impact=sum(l.ebitda_impact for l in impacts))
