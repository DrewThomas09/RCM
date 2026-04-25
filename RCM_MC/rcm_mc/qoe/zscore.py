"""Time-series z-score anomaly detection on financial line-items.

Complementary to the pattern-based rule detectors (V-shape NWC,
comp excess, etc.) and to the isolation forest. The z-score path
is the partner's "explain it to me in one sentence" story:

    "Revenue in TTM is 2.4σ above the trailing two-period mean —
     that's a 99th-percentile move and warrants explanation."

For every income-statement / balance-sheet / cash-flow series in
the panel, compute the trailing mean + std (excluding the focal
period itself), then flag any period where |z| > threshold.

Two detection modes:

  • Trailing-window: mean + std over the previous N periods.
    Robust to series that are growing — a shock against the
    immediate prior baseline. Best for revenue-trajectory
    breaks.

  • Full-history: mean + std over every period except the focal
    one (leave-one-out). Captures truly outlier periods rather
    than recent-trend breaks. Best for non-recurring spikes.

Output: QoEFlag-compatible records that drop into the existing
EBITDA bridge alongside the rule-detector flags.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .detectors import QoEFlag


# Series we routinely scan for anomalies. Keys = (section, key)
# pairs as they appear in the panel dict.
_ZSCORE_SERIES = (
    ("income_statement", "revenue", "revenue"),
    ("income_statement", "cogs", "COGS"),
    ("income_statement", "opex_compensation", "compensation opex"),
    ("income_statement", "opex_other", "other opex"),
    ("income_statement", "ebitda_reported", "reported EBITDA"),
    ("balance_sheet", "ar", "accounts receivable"),
    ("balance_sheet", "inventory", "inventory"),
    ("balance_sheet", "ap", "accounts payable"),
    ("cash_flow", "cash_receipts", "cash receipts"),
)


def _series(panel: Dict[str, Any], section: str,
            key: str) -> List[float]:
    sec = panel.get(section, {}) or {}
    vals = sec.get(key, []) or []
    out = []
    for v in vals:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            return []
    return out


def _trailing_zscore(values: List[float],
                     window: int) -> List[Optional[float]]:
    """Per-period trailing z-score over the previous ``window``
    periods. Returns None for the first ``window`` periods (no
    baseline to compare against).
    """
    out: List[Optional[float]] = []
    for i, v in enumerate(values):
        if i < window:
            out.append(None)
            continue
        prior = np.array(values[i - window:i], dtype=float)
        mu = float(prior.mean())
        sd = float(prior.std(ddof=1)) if len(prior) > 1 else 0.0
        if sd <= 1e-9:
            out.append(None)
            continue
        out.append((v - mu) / sd)
    return out


def _leave_one_out_zscore(values: List[float],
                          ) -> List[Optional[float]]:
    """For each period, z-score against the mean+std of the OTHER
    periods. Captures outlier periods irrespective of trend."""
    if len(values) < 3:
        return [None] * len(values)
    arr = np.array(values, dtype=float)
    out: List[Optional[float]] = []
    for i in range(len(arr)):
        rest = np.delete(arr, i)
        mu = float(rest.mean())
        sd = float(rest.std(ddof=1))
        if sd <= 1e-9:
            out.append(None)
            continue
        out.append((arr[i] - mu) / sd)
    return out


def detect_line_item_anomalies(
    panel: Dict[str, Any],
    *,
    threshold: float = 2.5,
    mode: str = "trailing",
    trailing_window: int = 2,
) -> List[QoEFlag]:
    """Z-score detection across every standard line-item series.

    Args:
      panel: same shape the rule detectors consume.
      threshold: |z| above which to fire a flag (default 2.5σ —
        roughly top/bottom 1% under Normal assumption; partner
        conservative).
      mode: "trailing" or "leave_one_out".
      trailing_window: window size for trailing mode.

    Returns: list of QoEFlag records, keyed with category
    "line_item_zscore" so they're distinguishable from the
    rule-detector flags downstream.
    """
    periods = list(panel.get("periods", []) or [])
    if not periods:
        return []

    out: List[QoEFlag] = []
    for section, key, label in _ZSCORE_SERIES:
        series = _series(panel, section, key)
        if len(series) < 3:
            continue
        if mode == "trailing":
            zs = _trailing_zscore(series, trailing_window)
        else:
            zs = _leave_one_out_zscore(series)
        for i, z in enumerate(zs):
            if z is None or i >= len(periods):
                continue
            if abs(z) < threshold:
                continue
            direction = "up" if z > 0 else "down"
            sign = "+" if z > 0 else ""
            # The proposed adjustment is the deviation from the
            # baseline mean, signed so increases reduce EBITDA
            # confidence (revenue jumps that don't match the
            # trend are typically "unwound" by the QoE team) and
            # decreases inflate the bridge.
            if mode == "trailing":
                prior = series[max(0, i - trailing_window):i]
            else:
                prior = series[:i] + series[i+1:]
            baseline = float(np.mean(prior)) if prior else series[i]
            deviation = series[i] - baseline
            # Convert to $M sign: revenue/EBITDA increases above
            # trend → negative adjustment (haircut). Costs
            # increases above trend → positive adjustment
            # (recurring run-rate higher).
            is_inflow_series = key in (
                "revenue", "ebitda_reported", "cash_receipts")
            adj = (-deviation if (is_inflow_series and z > 0)
                   else deviation if (is_inflow_series and z < 0)
                   else deviation if (not is_inflow_series and z > 0)
                   else -deviation)

            out.append(QoEFlag(
                flag_id=f"ZS_{section[:3].upper()}_{key[:6]}_{i:02d}",
                category="line_item_zscore",
                title=f"{label.title()} {direction} {abs(z):.1f}σ",
                description=(
                    f"{label.title()} of ${series[i]:,.1f} in "
                    f"{periods[i]} is {sign}{z:.2f}σ vs the "
                    f"{'trailing-window' if mode == 'trailing' else 'leave-one-out'} "
                    f"baseline mean of ${baseline:,.1f}. "
                    f"Investigate whether this is one-time or "
                    f"part of a sustainable run-rate."),
                period=str(periods[i]),
                proposed_adjustment_mm=round(adj * 0.5, 2),
                confidence=min(0.95, 0.5 + (abs(z) - threshold) / 5),
                evidence=[
                    f"{section}.{key}[{i}] = {series[i]:.2f}",
                    f"baseline = {baseline:.2f}",
                    f"z = {z:.3f}",
                ],
            ))
    out.sort(
        key=lambda f: abs(f.proposed_adjustment_mm), reverse=True)
    return out
