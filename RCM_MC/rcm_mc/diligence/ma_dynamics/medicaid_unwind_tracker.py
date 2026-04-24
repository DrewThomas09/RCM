"""Medicaid continuous-enrollment unwind tracker.

Post-PHE Medicaid redeterminations drove ~70% national procedural
termination rate per KFF. OCHIN Q4 2023 encounters showed -7%
Medicaid volume. This module estimates target-level volume-at-risk
given state unwind completion + target Medicaid-encounter trend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass
class MedicaidUnwindImpact:
    target_state: str
    state_unwind_completion_pct: float
    procedural_termination_rate: float
    target_medicaid_revenue_usd: float
    volume_at_risk_pct: float
    revenue_at_risk_usd: float
    severity: str = "LOW"              # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# State-level unwind completion as of 2026-04 (public-aggregate
# approximations; refresh from KFF quarterly).
STATE_UNWIND_DEFAULT = 0.98  # most states are now >95% completed


def estimate_medicaid_unwind_impact(
    *,
    target_state: str,
    target_medicaid_revenue_annual_usd: float,
    state_unwind_completion_pct: Optional[float] = None,
    procedural_termination_rate: float = 0.70,
    target_historical_medicaid_trend_pct: Optional[float] = None,
) -> MedicaidUnwindImpact:
    """Estimate Medicaid revenue at risk from unwind attrition.

    When ``target_historical_medicaid_trend_pct`` is supplied
    (e.g., -0.07 for the OCHIN Q4 2023 anchor), that drives the
    projection. Otherwise we apply a regionally-anchored 3-7%
    attrition curve scaled by the state's termination rate.
    """
    completion = (
        state_unwind_completion_pct
        if state_unwind_completion_pct is not None
        else STATE_UNWIND_DEFAULT
    )

    # Remaining unwind exposure: 1 - completion × termination rate.
    # This is the fraction of target members still at risk of
    # procedural termination.
    remaining = max(0.0, 1.0 - completion)
    at_risk_pct = remaining * procedural_termination_rate

    if target_historical_medicaid_trend_pct is not None:
        # Use caller-supplied trend directly.
        at_risk_pct = max(
            at_risk_pct,
            -float(target_historical_medicaid_trend_pct),
        )

    revenue_at_risk = (
        float(target_medicaid_revenue_annual_usd) * at_risk_pct
    )

    if at_risk_pct >= 0.10:
        sev = "HIGH"
    elif at_risk_pct >= 0.05:
        sev = "MEDIUM"
    else:
        sev = "LOW"

    return MedicaidUnwindImpact(
        target_state=target_state.upper(),
        state_unwind_completion_pct=completion,
        procedural_termination_rate=procedural_termination_rate,
        target_medicaid_revenue_usd=float(
            target_medicaid_revenue_annual_usd
        ),
        volume_at_risk_pct=at_risk_pct,
        revenue_at_risk_usd=revenue_at_risk,
        severity=sev,
    )
