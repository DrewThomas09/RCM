"""EBITDA bridge + NWC normalization.

Given the rule-detector flags, build:

  • An EBITDA bridge: reported EBITDA → adjusted EBITDA, with each
    flag's contribution as a discrete line item. This is the
    output the partner pastes into the IC memo.

  • A normalized NWC schedule: average of TTM NWC (excluding the
    most-recent period if it shows window-dressing) → the peg the
    seller has to deliver at close.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .detectors import QoEFlag


@dataclass
class EBITDABridgeLine:
    label: str
    amount_mm: float
    category: str = ""
    confidence: float = 1.0


@dataclass
class EBITDABridge:
    period: str
    reported_ebitda_mm: float
    adjustments: List[EBITDABridgeLine] = field(default_factory=list)
    adjusted_ebitda_mm: float = 0.0
    confidence_weighted_adjusted_ebitda_mm: float = 0.0


def compute_ebitda_bridge(
    panel: Dict[str, Any],
    flags: List[QoEFlag],
    *,
    period: Optional[str] = None,
) -> EBITDABridge:
    """Build the bridge for a single period (defaults to the most
    recent period in the panel, e.g. 'TTM').

    Adjusted = reported + Σ flag.proposed_adjustment_mm
    Confidence-weighted = reported + Σ flag.adjustment × flag.confidence
    """
    periods = list(panel.get("periods", []) or [])
    if not periods:
        return EBITDABridge(period="", reported_ebitda_mm=0.0)
    target_period = period or periods[-1]
    try:
        idx = periods.index(target_period)
    except ValueError:
        idx = len(periods) - 1
        target_period = periods[-1]

    reported_series = (panel.get("income_statement", {}) or {}).get(
        "ebitda_reported", []) or []
    reported = (float(reported_series[idx])
                if idx < len(reported_series) else 0.0)

    bridge = EBITDABridge(
        period=str(target_period),
        reported_ebitda_mm=reported,
    )

    running = reported
    weighted_running = reported
    for f in flags:
        # If the flag is keyed to a specific period and it isn't
        # this one, skip — bridge is per-period.
        if f.period and f.period != target_period:
            continue
        line = EBITDABridgeLine(
            label=f.title,
            amount_mm=f.proposed_adjustment_mm,
            category=f.category,
            confidence=f.confidence,
        )
        bridge.adjustments.append(line)
        running += f.proposed_adjustment_mm
        weighted_running += f.proposed_adjustment_mm * f.confidence

    bridge.adjusted_ebitda_mm = round(running, 3)
    bridge.confidence_weighted_adjusted_ebitda_mm = round(
        weighted_running, 3)
    return bridge


@dataclass
class NWCNormalization:
    periods: List[str]
    nwc_by_period_mm: List[float]
    ttm_average_mm: float
    proposed_peg_mm: float
    excluded_period: Optional[str] = None


def normalize_nwc(panel: Dict[str, Any]) -> NWCNormalization:
    """Compute a partner-defensible NWC peg:

      1. NWC = AR + Inventory − AP for each period.
      2. TTM average across all periods.
      3. If the most-recent period sits >15% below the TTM average,
         flag it as window-dressed and recompute the average without
         it; that becomes the proposed peg.
    """
    periods = list(panel.get("periods", []) or [])
    bs = panel.get("balance_sheet", {}) or {}
    ar = list(bs.get("ar", []) or [])
    ap = list(bs.get("ap", []) or [])
    inv = list(bs.get("inventory", []) or [])
    n = min(len(periods), len(ar), len(ap), len(inv))
    nwc = [
        float(ar[i] + inv[i] - ap[i])
        for i in range(n)
    ]
    if not nwc:
        return NWCNormalization(
            periods=[], nwc_by_period_mm=[],
            ttm_average_mm=0.0, proposed_peg_mm=0.0)

    ttm_avg = sum(nwc) / len(nwc)
    excluded_period: Optional[str] = None
    proposed = ttm_avg

    if len(nwc) >= 3:
        most_recent = nwc[-1]
        if most_recent < ttm_avg * 0.85:
            ex_avg = sum(nwc[:-1]) / max(1, len(nwc) - 1)
            proposed = ex_avg
            excluded_period = periods[-1] if n > 0 else None

    return NWCNormalization(
        periods=[str(p) for p in periods[:n]],
        nwc_by_period_mm=[round(v, 3) for v in nwc],
        ttm_average_mm=round(ttm_avg, 3),
        proposed_peg_mm=round(proposed, 3),
        excluded_period=excluded_period,
    )
