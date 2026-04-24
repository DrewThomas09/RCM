"""Feed counterfactual savings into the v2 EBITDA bridge as a new
"reg-risk mitigated" lever.

The v2 bridge (rcm_mc.pe.value_bridge_v2) takes a packet and produces
lever-by-lever EBITDA contributions. We don't touch the bridge code;
instead we provide a :class:`CounterfactualLever` that a caller
attaches to the packet's supplementary levers list and renders
alongside the native v2 levers.

Convention: each counterfactual's estimated_dollar_impact_usd is
treated as:
    - POSITIVE savings if we actually capture the counterfactual
      (flip the band). The EBITDA impact is the savings × realization
      probability (0.5 default — partners quote conservatively).
    - QUALITATIVE zero when the solver can't quantify (Steward-score
      factor changes don't carry a dollar number because they depend
      on the specific landlord).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .advisor import Counterfactual, CounterfactualSet


@dataclass
class CounterfactualLever:
    """Lever shape that attaches to the EBITDA bridge."""
    name: str = "counterfactual_reg_mitigation"
    label: str = "Reg-Risk Mitigation (Counterfactual)"
    revenue_impact_usd: float = 0.0
    cost_impact_usd: float = 0.0
    ebitda_impact_usd: float = 0.0
    working_capital_impact_usd: float = 0.0
    realization_probability: float = 0.5
    confidence: str = "MEDIUM"          # HIGH | MEDIUM | LOW
    provenance: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "label": self.label,
            "revenue_impact_usd": self.revenue_impact_usd,
            "cost_impact_usd": self.cost_impact_usd,
            "ebitda_impact_usd": self.ebitda_impact_usd,
            "working_capital_impact_usd": self.working_capital_impact_usd,
            "realization_probability": self.realization_probability,
            "confidence": self.confidence,
            "provenance": list(self.provenance),
        }


def counterfactual_bridge_lever(
    cf_set: CounterfactualSet,
    *,
    realization_probability: float = 0.5,
) -> CounterfactualLever:
    """Translate a counterfactual set into a bridge-ready lever.

    Only counterfactuals with a positive dollar impact contribute.
    Feasibility modulates realization:
        HIGH feasibility → full realization_probability
        MEDIUM → 0.7 × realization_probability
        LOW → 0.3 × realization_probability

    Produces only a revenue_impact (counterfactuals reduce revenue
    AT RISK; effective EBITDA impact is the avoided loss).
    """
    total_avoided = 0.0
    provenance: List[Dict[str, Any]] = []
    high_count = 0
    for cf in cf_set.items:
        if cf.estimated_dollar_impact_usd <= 0:
            continue
        feasibility_multiplier = {
            "HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.3,
        }.get(cf.feasibility, 0.5)
        effective = (
            cf.estimated_dollar_impact_usd
            * realization_probability
            * feasibility_multiplier
        )
        total_avoided += effective
        provenance.append({
            "module": cf.module, "lever": cf.lever,
            "original_band": cf.original_band,
            "target_band": cf.target_band,
            "raw_impact_usd": cf.estimated_dollar_impact_usd,
            "effective_impact_usd": effective,
            "feasibility": cf.feasibility,
        })
        if cf.feasibility == "HIGH":
            high_count += 1
    if not provenance:
        return CounterfactualLever(
            revenue_impact_usd=0.0,
            ebitda_impact_usd=0.0,
            realization_probability=realization_probability,
            confidence="LOW",
        )
    # Overall confidence: HIGH if >=2 HIGH-feasibility levers;
    # MEDIUM if at least one HIGH; LOW otherwise.
    if high_count >= 2:
        confidence = "HIGH"
    elif high_count >= 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    return CounterfactualLever(
        revenue_impact_usd=total_avoided,
        # Counterfactuals are avoided-loss; treat as revenue preserved
        # → full EBITDA pass-through.
        ebitda_impact_usd=total_avoided,
        realization_probability=realization_probability,
        confidence=confidence,
        provenance=provenance,
    )
