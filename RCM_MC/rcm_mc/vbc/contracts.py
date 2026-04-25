"""Capitation contract terms + revenue/savings math.

Models the three dominant value-based contract structures:

  PCC — Primary Care Capitation. Fixed PMPM for primary-care
        services, fee-for-service for everything else.
  TCC — Total Care Capitation. Fixed PMPM for ALL covered
        services. Used by ACO REACH (Direct Contracting), full-
        risk MA contracts, and the LEAD model launching 2027.
  Shared Savings — Two-sided risk: provider keeps a % of savings
        below the benchmark, owes a % of losses above it. Quality
        withhold is held back as a quality-gate.

The math is straightforward but the parameter space is wide —
this module defines a single ``ContractTerms`` dataclass that
encodes the partner-relevant levers (benchmark PMPM, MSR/MLR
thresholds, withhold %, sharing rate) and two pure functions:
``compute_capitation_revenue`` and ``compute_shared_savings``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ContractTerms:
    """All the levers that distinguish one VBC contract from another."""
    contract_type: str = "TCC"            # "PCC" / "TCC" / "SS"
    benchmark_pmpm: float = 1100.0        # base capitation rate
    risk_score: float = 1.0               # member panel HCC score
    quality_withhold_pct: float = 0.02    # 2% standard for ACO REACH

    # Two-sided risk parameters (used for SS / TCC under-/over-spend)
    msr_pct: float = 0.02                 # Min Savings Rate (kept by provider 100%)
    mlr_pct: float = 0.02                 # Min Loss Rate (owed by provider 100%)
    upside_share: float = 1.00            # % of savings above MSR kept
    downside_share: float = 1.00          # % of losses above MLR owed
    upside_cap_pct: float = 0.10          # cap savings at +10% of benchmark
    downside_cap_pct: float = 0.05        # cap losses at -5% of benchmark


def compute_capitation_revenue(
    cohort_size: int,
    contract: ContractTerms,
    *,
    months_eligible: float = 12.0,
    quality_score: float = 0.85,
) -> dict:
    """Annual capitation revenue for a cohort.

    Returns a dict with the gross capitation, the quality-withhold
    held back, and the net released after quality scoring. The
    quality_score (0-1) is applied to the withhold pool linearly:
    a panel scoring 1.0 reclaims the full withhold, a panel
    scoring 0.5 reclaims half.
    """
    gross = (cohort_size * contract.benchmark_pmpm
             * contract.risk_score * months_eligible)
    withhold = gross * contract.quality_withhold_pct
    quality_released = withhold * max(0.0, min(1.0, quality_score))
    forfeited = withhold - quality_released
    net = gross - withhold + quality_released

    return {
        "gross_capitation": round(gross, 2),
        "quality_withhold": round(withhold, 2),
        "quality_released": round(quality_released, 2),
        "withhold_forfeited": round(forfeited, 2),
        "net_revenue": round(net, 2),
        "effective_pmpm": round(net / max(1, cohort_size)
                                / max(1.0, months_eligible), 2),
    }


def compute_shared_savings(
    cohort_size: int,
    contract: ContractTerms,
    *,
    actual_pmpm: float,
    months: float = 12.0,
) -> dict:
    """Two-sided shared-savings result given an observed PMPM.

    A positive ``net_savings`` means the provider EARNED money
    (came in below benchmark + MSR). A negative value means the
    provider OWES money (came in above benchmark + MLR).
    """
    benchmark = (contract.benchmark_pmpm * contract.risk_score
                 * cohort_size * months)
    actual = actual_pmpm * cohort_size * months
    delta_pct = (benchmark - actual) / max(1.0, benchmark)

    upside_threshold = contract.msr_pct
    downside_threshold = -contract.mlr_pct

    if delta_pct >= upside_threshold:
        # Savings: above MSR
        savings_pct = min(
            delta_pct - upside_threshold,
            contract.upside_cap_pct - upside_threshold,
        )
        savings_dollars = savings_pct * benchmark
        net = savings_dollars * contract.upside_share
        side = "savings"
    elif delta_pct <= downside_threshold:
        # Losses: below MLR
        loss_pct = max(
            delta_pct - downside_threshold,
            -contract.downside_cap_pct - downside_threshold,
        )
        loss_dollars = loss_pct * benchmark  # negative
        net = loss_dollars * contract.downside_share
        side = "losses"
    else:
        net = 0.0
        side = "neutral"

    return {
        "benchmark_total": round(benchmark, 2),
        "actual_total": round(actual, 2),
        "delta_pct": round(delta_pct, 4),
        "side": side,
        "net_shared": round(net, 2),
    }
