"""Risk contract (ACO REACH / MSSP / full-risk MA) projector.

Minimal model — attributed beneficiary count × (actual PMPM -
benchmark PMPM) × shared-savings rate. Uses caller inputs; this
module does not ingest CMS files directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RiskContractProjection:
    contract_type: str                  # ACO_REACH | MSSP | FULL_RISK_MA
    attributed_beneficiaries: int
    benchmark_pmpm_usd: float
    actual_pmpm_usd: float
    performance_delta_usd: float         # positive = savings
    shared_savings_rate: float
    projected_earnings_usd: float
    band: str                            # LOW | MEDIUM | HIGH loss tier

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def project_risk_contract(
    *,
    contract_type: str = "MSSP",
    attributed_beneficiaries: int,
    benchmark_pmpm_usd: float,
    actual_pmpm_usd: float,
    shared_savings_rate: float = 0.50,
    shared_loss_rate: Optional[float] = None,
    stop_loss_cap_usd: Optional[float] = None,
) -> RiskContractProjection:
    ct = contract_type.upper()
    delta = benchmark_pmpm_usd - actual_pmpm_usd
    # Annualise: 12 × per-beneficiary delta × shared rate.
    raw_annual = 12.0 * delta * attributed_beneficiaries
    if raw_annual >= 0:
        earnings = raw_annual * shared_savings_rate
    else:
        loss_rate = shared_loss_rate if shared_loss_rate is not None \
            else shared_savings_rate
        earnings = raw_annual * loss_rate
    if stop_loss_cap_usd is not None:
        earnings = max(
            earnings, -abs(float(stop_loss_cap_usd)),
        )

    if earnings <= -1_000_000:
        band = "HIGH"
    elif earnings <= -250_000:
        band = "MEDIUM"
    else:
        band = "LOW"

    return RiskContractProjection(
        contract_type=ct,
        attributed_beneficiaries=attributed_beneficiaries,
        benchmark_pmpm_usd=benchmark_pmpm_usd,
        actual_pmpm_usd=actual_pmpm_usd,
        performance_delta_usd=raw_annual,
        shared_savings_rate=shared_savings_rate,
        projected_earnings_usd=earnings,
        band=band,
    )
