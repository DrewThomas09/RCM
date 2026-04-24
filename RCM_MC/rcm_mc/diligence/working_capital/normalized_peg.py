"""Seasonality-adjusted normalized-working-capital peg.

Compute the NWC peg target from trailing monthly NWC snapshots.
Method: detrend by mean + adjust for seasonality (quarterly
indices), then average across 12-24 months.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass
class PegResult:
    trailing_12_mean_usd: float
    trailing_24_mean_usd: float
    seasonality_adjusted_peg_usd: float
    quarterly_indices: List[float]
    dispersion_pct: float             # 1-sigma / mean
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def compute_normalized_peg(
    monthly_nwc_usd: Sequence[float],
    *,
    use_24_month: bool = True,
) -> PegResult:
    """Compute the peg. Requires at least 12 months of data;
    24 months preferred."""
    values = [float(x) for x in monthly_nwc_usd]
    if len(values) < 12:
        # Too little data — return simple mean with warning.
        mean12 = sum(values) / max(len(values), 1)
        return PegResult(
            trailing_12_mean_usd=mean12,
            trailing_24_mean_usd=mean12,
            seasonality_adjusted_peg_usd=mean12,
            quarterly_indices=[1.0] * 4,
            dispersion_pct=0.0,
            notes=["<12 months supplied — simple mean only"],
        )

    mean12 = sum(values[-12:]) / 12
    mean24 = (
        sum(values[-24:]) / min(24, len(values))
        if use_24_month else mean12
    )
    # Quarterly seasonality indices (over the last 12 months).
    q_idx: List[float] = []
    last12 = values[-12:]
    mean_last12 = sum(last12) / 12
    for q in range(4):
        q_values = [last12[q * 3 + i] for i in range(3)]
        q_mean = sum(q_values) / 3
        idx = q_mean / mean_last12 if mean_last12 else 1.0
        q_idx.append(idx)

    # Apply inverse of the mean seasonality to de-seasonalize.
    mean_of_indices = sum(q_idx) / 4
    adjusted = (mean24 / mean_of_indices) if mean_of_indices else mean24

    # Dispersion (1-sigma / mean) as a stability signal.
    import statistics as stats
    dispersion = stats.pstdev(last12) / mean_last12 if mean_last12 else 0.0

    notes: List[str] = []
    if dispersion > 0.20:
        notes.append(
            f"High dispersion ({dispersion*100:.0f}%) — peg should "
            "use widened bands in the SPA."
        )
    return PegResult(
        trailing_12_mean_usd=mean12,
        trailing_24_mean_usd=mean24,
        seasonality_adjusted_peg_usd=adjusted,
        quarterly_indices=q_idx,
        dispersion_pct=dispersion,
        notes=notes,
    )
