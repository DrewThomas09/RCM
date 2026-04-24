"""Pre-close collections pull-forward detector.

Sellers sometimes accelerate collections in the 60 days pre-close
to inflate the closing NWC. Flag when the last-60-days cash-flow
index is meaningfully above trailing months.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence


@dataclass
class PullForwardFinding:
    last_60d_collections_usd: float
    trailing_12_monthly_mean_usd: float
    lift_ratio: float                # last60 / (trailing monthly mean × 2)
    severity: str                    # LOW | MEDIUM | HIGH | CRITICAL
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def detect_pre_close_pull_forward(
    *,
    last_60_days_collections_usd: float,
    prior_12_monthly_collections_usd: Sequence[float],
) -> PullForwardFinding:
    """Compare last-60-day collections to 2x the trailing 12-month
    monthly mean. Lift > 1.15 is a WATCH; > 1.3 is HIGH; > 1.5
    CRITICAL."""
    values = [float(x) for x in prior_12_monthly_collections_usd]
    mean_month = sum(values) / len(values) if values else 1.0
    baseline = mean_month * 2  # 60 days ≈ 2 months
    lift = (
        last_60_days_collections_usd / baseline if baseline > 0 else 1.0
    )
    if lift >= 1.5:
        sev = "CRITICAL"
    elif lift >= 1.3:
        sev = "HIGH"
    elif lift >= 1.15:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    return PullForwardFinding(
        last_60d_collections_usd=float(last_60_days_collections_usd),
        trailing_12_monthly_mean_usd=mean_month,
        lift_ratio=lift,
        severity=sev,
        narrative=(
            f"Pre-close 60d collections ${last_60_days_collections_usd:,.0f} "
            f"vs trailing 12 mo monthly mean ${mean_month:,.0f} "
            f"(lift {lift:.2f}x, 2-month baseline)."
        ),
    )
