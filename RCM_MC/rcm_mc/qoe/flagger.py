"""Top-level QoE auto-flagger entry point.

Combines rule-based detectors + isolation-forest anomaly scoring
+ EBITDA bridge + NWC normalization into a single result dict
ready for the diligence packet UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .bridge import (
    compute_ebitda_bridge,
    normalize_nwc,
    EBITDABridge,
    NWCNormalization,
)
from .detectors import QoEFlag, run_rule_detectors
from .isolation_forest import isolation_forest_scores


@dataclass
class QoEResult:
    deal_name: str
    flags: List[QoEFlag] = field(default_factory=list)
    ebitda_bridge: Optional[EBITDABridge] = None
    nwc_normalization: Optional[NWCNormalization] = None
    isolation_forest_scores: List[float] = field(default_factory=list)
    isolation_forest_anomalies: List[Dict[str, Any]] = field(
        default_factory=list)


def _isolation_forest_signal(
    panel: Dict[str, Any],
) -> Dict[str, Any]:
    """Run isolation-forest on the income-statement matrix
    (rows=line items, cols=periods → transposed to rows=periods).
    Anomaly rows = periods with unusual line-item profiles."""
    is_block = panel.get("income_statement", {}) or {}
    series_keys = [
        "revenue", "cogs", "opex_compensation", "opex_other",
        "ebitda_reported",
    ]
    rows: List[List[float]] = []
    for k in series_keys:
        v = is_block.get(k)
        if v:
            rows.append([float(x) for x in v])
    if not rows:
        return {"scores": [], "anomalies": []}
    # Pad rows to same length (use 0 for missing periods)
    max_n = max(len(r) for r in rows)
    rows = [r + [0.0] * (max_n - len(r)) for r in rows]
    arr = np.array(rows).T  # shape (n_periods, n_features)
    if arr.shape[0] < 2:
        return {"scores": [], "anomalies": []}

    scores = isolation_forest_scores(arr, n_trees=80, seed=42)
    periods = list(panel.get("periods", []) or [])
    anomalies = []
    for i, s in enumerate(scores):
        if s > 0.6 and i < len(periods):
            anomalies.append({
                "period": periods[i],
                "score": float(round(s, 3)),
                "note": "Isolation-forest flagged this period",
            })
    return {
        "scores": [float(s) for s in scores.tolist()],
        "anomalies": anomalies,
    }


def run_qoe_flagger(panel: Dict[str, Any]) -> QoEResult:
    """Single entry point — runs every detector + the iforest +
    builds the bridge + normalizes NWC."""
    rule_flags = run_rule_detectors(panel)
    bridge = compute_ebitda_bridge(panel, rule_flags)
    nwc = normalize_nwc(panel)
    iforest = _isolation_forest_signal(panel)

    return QoEResult(
        deal_name=str(panel.get("deal_name", "")),
        flags=rule_flags,
        ebitda_bridge=bridge,
        nwc_normalization=nwc,
        isolation_forest_scores=iforest["scores"],
        isolation_forest_anomalies=iforest["anomalies"],
    )
