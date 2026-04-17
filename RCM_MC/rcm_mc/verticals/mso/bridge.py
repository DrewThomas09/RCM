"""MSO value bridge (Prompt 79).

Levers: provider recruitment, panel growth, value-based contract
optimization, quality bonus capture, MSO fee optimization.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class MSOLeverImpact:
    lever_key: str
    current_value: float = 0.0
    target_value: float = 0.0
    ebitda_impact: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return {"lever_key": self.lever_key, "current_value": self.current_value,
                "target_value": self.target_value, "ebitda_impact": self.ebitda_impact}

@dataclass
class MSOBridgeResult:
    lever_impacts: List[MSOLeverImpact] = field(default_factory=list)
    total_ebitda_impact: float = 0.0
    status: str = "OK"
    def to_dict(self) -> Dict[str, Any]:
        return {"lever_impacts": [l.to_dict() for l in self.lever_impacts],
                "total_ebitda_impact": self.total_ebitda_impact, "status": self.status}

_MSO_COEFFICIENTS = {
    "wrvus_per_provider": 50.0,
    "panel_size_per_provider": 20.0,
    "value_based_revenue_pct": 5000.0,
    "quality_bonus_revenue": 0.5,
    "provider_turnover_rate": -8000.0,
}

def compute_mso_bridge(current: Dict[str, float], target: Dict[str, float],
                       *, provider_count: int = 50) -> MSOBridgeResult:
    impacts: List[MSOLeverImpact] = []
    for metric, coef in _MSO_COEFFICIENTS.items():
        cur, tgt = current.get(metric), target.get(metric)
        if cur is None or tgt is None: continue
        delta = float(tgt) - float(cur)
        impact = delta * coef * (provider_count / 50.0)
        impacts.append(MSOLeverImpact(lever_key=metric, current_value=float(cur),
                                       target_value=float(tgt), ebitda_impact=impact))
    return MSOBridgeResult(lever_impacts=impacts,
                           total_ebitda_impact=sum(l.ebitda_impact for l in impacts))
