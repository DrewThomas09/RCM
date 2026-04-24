"""Commercial payer concentration + market-power squeeze scenario.

Computes payer HHI + models a 5% rate cut by the top payer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass
class CommercialConcentrationResult:
    payer_revenue_usd: Dict[str, float]
    total_commercial_revenue_usd: float
    top_payer_name: str
    top_payer_share: float
    hhi: float
    market_power_squeeze_scenario_usd: float
    band: str                           # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def compute_commercial_concentration(
    payer_revenue_usd: Mapping[str, float],
    *,
    top_payer_rate_cut_pct: float = 0.05,
) -> CommercialConcentrationResult:
    """Compute HHI + market-power squeeze scenario.

    HHI = sum(share_i * 100)^2  where share_i is fraction.
    """
    total = sum(float(v) for v in payer_revenue_usd.values())
    if total <= 0:
        return CommercialConcentrationResult(
            payer_revenue_usd=dict(payer_revenue_usd),
            total_commercial_revenue_usd=0.0,
            top_payer_name="", top_payer_share=0.0,
            hhi=0.0, market_power_squeeze_scenario_usd=0.0,
            band="LOW",
        )
    shares = {k: float(v) / total for k, v in payer_revenue_usd.items()}
    hhi = sum((s * 100.0) ** 2 for s in shares.values())
    top_name = max(shares, key=shares.get)
    top_share = shares[top_name]
    squeeze = (
        payer_revenue_usd[top_name]
        * float(top_payer_rate_cut_pct)
    )
    if hhi >= 3500:
        band = "HIGH"
    elif hhi >= 2000:
        band = "MEDIUM"
    else:
        band = "LOW"
    return CommercialConcentrationResult(
        payer_revenue_usd=dict(payer_revenue_usd),
        total_commercial_revenue_usd=total,
        top_payer_name=top_name,
        top_payer_share=top_share,
        hhi=hhi,
        market_power_squeeze_scenario_usd=squeeze,
        band=band,
    )
