"""Predicted-at-diligence vs actual-at-hold comparison (Prompt 43).

For each metric where we predicted a target during diligence and the
deal now has quarterly actuals, compute the variance and whether the
actual fell within the original confidence interval.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PredictedVsActual:
    deal_id: str = ""
    quarter: str = ""
    metric_key: str = ""
    predicted_at_diligence: float = 0.0
    actual_now: float = 0.0
    variance_pct: float = 0.0
    was_predicted: bool = True
    prediction_method: str = "ridge"
    within_ci: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "quarter": self.quarter,
            "metric_key": self.metric_key,
            "predicted_at_diligence": float(self.predicted_at_diligence),
            "actual_now": float(self.actual_now),
            "variance_pct": float(self.variance_pct),
            "was_predicted": bool(self.was_predicted),
            "prediction_method": self.prediction_method,
            "within_ci": bool(self.within_ci),
        }


@dataclass
class PredictionReport:
    pct_within_ci: float = 0.0
    mean_absolute_error: float = 0.0
    n_metrics: int = 0
    worst_misses: List[PredictedVsActual] = field(default_factory=list)
    best_hits: List[PredictedVsActual] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pct_within_ci": float(self.pct_within_ci),
            "mean_absolute_error": float(self.mean_absolute_error),
            "n_metrics": int(self.n_metrics),
            "worst_misses": [m.to_dict() for m in self.worst_misses],
            "best_hits": [h.to_dict() for h in self.best_hits],
        }


def compute_predicted_vs_actual(
    store: Any, deal_id: str, quarter: Optional[str] = None,
) -> List[PredictedVsActual]:
    """Load the deal's earliest packet + latest quarter actuals,
    compare metric-by-metric."""
    results: List[PredictedVsActual] = []
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
    except Exception:  # noqa: BLE001
        return results
    rows = list_packets(store, deal_id)
    if not rows:
        return results
    # Earliest packet = the diligence-stage one.
    packet = load_packet_by_id(store, rows[-1]["id"])
    if packet is None:
        return results
    predicted = packet.predicted_metrics or {}
    if not predicted:
        return results
    # Load actuals.
    try:
        with store.connect() as con:
            if quarter:
                row = con.execute(
                    "SELECT kpis_json, quarter FROM quarterly_actuals "
                    "WHERE deal_id = ? AND quarter = ?",
                    (deal_id, quarter),
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT kpis_json, quarter FROM quarterly_actuals "
                    "WHERE deal_id = ? ORDER BY quarter DESC LIMIT 1",
                    (deal_id,),
                ).fetchone()
    except Exception:  # noqa: BLE001
        return results
    if row is None:
        return results
    actuals = json.loads(row["kpis_json"] or "{}")
    qtr = row["quarter"]
    for metric_key, pred in predicted.items():
        actual_val = actuals.get(metric_key)
        if actual_val is None:
            continue
        try:
            a = float(actual_val)
            p = float(pred.value)
        except (TypeError, ValueError):
            continue
        variance = ((a - p) / abs(p)) if abs(p) > 1e-9 else 0.0
        ci_lo = float(pred.ci_low) if pred.ci_low is not None else p
        ci_hi = float(pred.ci_high) if pred.ci_high is not None else p
        within = ci_lo <= a <= ci_hi
        results.append(PredictedVsActual(
            deal_id=deal_id, quarter=qtr, metric_key=metric_key,
            predicted_at_diligence=p, actual_now=a,
            variance_pct=variance,
            was_predicted=True,
            prediction_method=str(pred.method or "ridge"),
            within_ci=within,
        ))
    return results


def prediction_accuracy_summary(
    results: List[PredictedVsActual],
) -> PredictionReport:
    n = len(results)
    if n == 0:
        return PredictionReport()
    within = sum(1 for r in results if r.within_ci)
    mae = sum(abs(r.variance_pct) for r in results) / n
    sorted_by_miss = sorted(results, key=lambda r: abs(r.variance_pct), reverse=True)
    return PredictionReport(
        pct_within_ci=(within / n) * 100.0,
        mean_absolute_error=mae,
        n_metrics=n,
        worst_misses=sorted_by_miss[:3],
        best_hits=sorted_by_miss[-3:] if n >= 3 else sorted_by_miss,
    )
