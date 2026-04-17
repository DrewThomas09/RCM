"""Cross-deal learning: fund-calibrated predictions (Prompt 30).

If the fund has closed 5 hospital deals, the system should learn from
actual outcomes. "Our model overestimates denial-rate improvement by
15% based on our last 4 deals" is the kind of institutional knowledge
that currently lives in a partner's head.

This module:

1. Extracts predicted-at-diligence vs actual-at-hold pairs for every
   metric and every completed deal in the portfolio.
2. Computes systematic bias per metric across the fund's history.
3. Adjusts new predictions by shrinking toward actual experience.
4. Builds supplementary comparables from the fund's own historical
   hospitals (weighted 2× in similarity scoring).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class OutcomePair:
    """One metric's prediction vs reality for one deal."""
    deal_id: str
    metric: str
    predicted_at_diligence: float
    actual_at_hold: float
    error: float = 0.0       # actual - predicted
    pct_error: float = 0.0   # (actual - predicted) / |predicted|

    def __post_init__(self) -> None:
        self.error = self.actual_at_hold - self.predicted_at_diligence
        if abs(self.predicted_at_diligence) > 1e-9:
            self.pct_error = (
                self.error / abs(self.predicted_at_diligence)
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "metric": self.metric,
            "predicted_at_diligence": float(self.predicted_at_diligence),
            "actual_at_hold": float(self.actual_at_hold),
            "error": float(self.error),
            "pct_error": float(self.pct_error),
        }


@dataclass
class BiasStats:
    """Systematic bias for one metric across the fund."""
    metric: str
    mean_error: float = 0.0
    mean_pct_error: float = 0.0
    n_deals: int = 0
    direction: str = ""      # overestimates | underestimates | unbiased

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "mean_error": float(self.mean_error),
            "mean_pct_error": float(self.mean_pct_error),
            "n_deals": int(self.n_deals),
            "direction": self.direction,
        }


@dataclass
class AdjustmentReport:
    """What the learner did to the predictions for one build."""
    adjustments_applied: int = 0
    bias_stats: Dict[str, BiasStats] = field(default_factory=dict)
    fund_deals_used: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adjustments_applied": int(self.adjustments_applied),
            "bias_stats": {
                k: v.to_dict() for k, v in self.bias_stats.items()
            },
            "fund_deals_used": int(self.fund_deals_used),
            "summary": self.summary,
        }


# ── Learner ────────────────────────────────────────────────────────

_MIN_DEALS_FOR_ADJUSTMENT = 3


class PortfolioLearner:
    """Fund-level calibration engine.

    Usage::

        learner = PortfolioLearner(store)
        outcomes = learner.extract_outcomes()
        bias = learner.compute_bias(outcomes)
        adjusted = learner.adjust_predictions(raw_predictions, bias)
        fund_comps = learner.build_fund_comparables()
    """

    def __init__(self, store: Any) -> None:
        self.store = store

    # ── Extract ────────────────────────────────────────────────

    def extract_outcomes(self) -> List[OutcomePair]:
        """For each deal with both a diligence-stage analysis packet
        AND at least one quarter of hold actuals, extract predicted
        vs actual metric pairs.

        "Predicted at diligence" comes from the earliest analysis
        packet's ``predicted_metrics`` section. "Actual at hold" comes
        from the most recent quarter in ``quarterly_actuals``.
        """
        pairs: List[OutcomePair] = []
        try:
            from ..analysis.analysis_store import (
                _ensure_table, list_packets, load_packet_by_id,
            )
            from ..pe.hold_tracking import _ensure_actuals_table
        except Exception as exc:  # noqa: BLE001
            logger.debug("portfolio_learning imports failed: %s", exc)
            return pairs

        _ensure_table(self.store)
        _ensure_actuals_table(self.store)

        # Walk every deal that has an analysis_run.
        packet_rows = list_packets(self.store)
        # Group by deal_id, keep the earliest.
        earliest_by_deal: Dict[str, int] = {}
        for row in packet_rows:
            did = row.get("deal_id") or ""
            rid = row.get("id") or 0
            if did not in earliest_by_deal or rid < earliest_by_deal[did]:
                earliest_by_deal[did] = rid

        for deal_id, row_id in earliest_by_deal.items():
            packet = load_packet_by_id(self.store, row_id)
            if packet is None:
                continue
            predicted = packet.predicted_metrics or {}
            if not predicted:
                continue
            # Load the most recent quarter's actuals.
            actuals = self._latest_actuals(deal_id)
            if not actuals:
                continue
            for metric_key, pred in predicted.items():
                actual_value = actuals.get(metric_key)
                if actual_value is None:
                    continue
                try:
                    pairs.append(OutcomePair(
                        deal_id=deal_id,
                        metric=metric_key,
                        predicted_at_diligence=float(pred.value),
                        actual_at_hold=float(actual_value),
                    ))
                except (TypeError, ValueError):
                    continue
        return pairs

    def _latest_actuals(self, deal_id: str) -> Dict[str, float]:
        """Pull the most recent quarter's KPIs for ``deal_id``."""
        try:
            with self.store.connect() as con:
                row = con.execute(
                    """SELECT kpis_json FROM quarterly_actuals
                       WHERE deal_id = ?
                       ORDER BY quarter DESC LIMIT 1""",
                    (deal_id,),
                ).fetchone()
        except Exception:  # noqa: BLE001
            return {}
        if row is None:
            return {}
        try:
            return json.loads(row["kpis_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    # ── Bias computation ──────────────────────────────────────

    def compute_bias(
        self, outcomes: Optional[List[OutcomePair]] = None,
    ) -> Dict[str, BiasStats]:
        """Aggregate outcomes into per-metric bias statistics."""
        if outcomes is None:
            outcomes = self.extract_outcomes()
        by_metric: Dict[str, List[OutcomePair]] = {}
        for o in outcomes:
            by_metric.setdefault(o.metric, []).append(o)
        out: Dict[str, BiasStats] = {}
        for metric, pairs in by_metric.items():
            n = len(pairs)
            if n < 1:
                continue
            mean_err = sum(p.error for p in pairs) / n
            mean_pct = sum(p.pct_error for p in pairs) / n
            direction = "unbiased"
            if abs(mean_pct) > 0.05:
                direction = (
                    "overestimates" if mean_pct < 0
                    else "underestimates"
                )
            out[metric] = BiasStats(
                metric=metric,
                mean_error=mean_err,
                mean_pct_error=mean_pct,
                n_deals=n,
                direction=direction,
            )
        return out

    # ── Prediction adjustment ─────────────────────────────────

    def adjust_predictions(
        self,
        raw: Dict[str, Any],
        bias: Dict[str, BiasStats],
    ) -> Dict[str, Any]:
        """Shrink ``raw`` predictions toward fund experience.

        For each metric with a bias entry backed by ≥
        ``_MIN_DEALS_FOR_ADJUSTMENT`` deals, scale the prediction:
        ``adjusted = raw × (1 − mean_pct_error)``.

        Returns a new dict with adjusted values; the original ``raw``
        is not mutated.
        """
        adjusted = dict(raw)
        for metric_key, pred in raw.items():
            stats = bias.get(metric_key)
            if stats is None or stats.n_deals < _MIN_DEALS_FOR_ADJUSTMENT:
                continue
            try:
                value = float(
                    getattr(pred, "value", None)
                    if hasattr(pred, "value") else pred
                )
            except (TypeError, ValueError):
                continue
            factor = 1.0 - stats.mean_pct_error
            new_value = value * factor
            if hasattr(pred, "value"):
                # It's a dataclass — create a shallow copy with the
                # adjusted value. We can't use dataclasses.replace
                # because it's a cross-module type; just set the attr.
                from copy import copy
                adj_pred = copy(pred)
                adj_pred.value = new_value
                adj_pred.provenance_chain = list(
                    getattr(adj_pred, "provenance_chain", []),
                ) + [f"portfolio_adjusted:{stats.direction}({stats.mean_pct_error:+.2%})"]
                adjusted[metric_key] = adj_pred
            else:
                adjusted[metric_key] = new_value
        return adjusted

    # ── Fund comparables ──────────────────────────────────────

    def build_fund_comparables(self) -> List[Dict[str, Any]]:
        """Return the fund's own historical hospitals as supplementary
        comparables, each with ``similarity_score`` set to 2× the
        max-peer baseline so they rank ahead of generic CMS peers.

        Only deals that have both an analysis packet AND hold actuals
        contribute — we need the full lifecycle to be a useful comp.
        """
        comps: List[Dict[str, Any]] = []
        try:
            from ..analysis.analysis_store import list_packets, load_packet_by_id
            from ..pe.hold_tracking import _ensure_actuals_table
            _ensure_actuals_table(self.store)
        except Exception:  # noqa: BLE001
            return comps

        packet_rows = list_packets(self.store)
        seen_deals: set = set()
        for row in packet_rows:
            did = row.get("deal_id") or ""
            if did in seen_deals:
                continue
            seen_deals.add(did)
            actuals = self._latest_actuals(did)
            if not actuals:
                continue
            packet = load_packet_by_id(self.store, row.get("id") or 0)
            if packet is None:
                continue
            # Build a flat record from the packet's rcm_profile +
            # actuals, suitable for the comparable_finder.
            rec: Dict[str, Any] = {
                "id": f"fund:{did}",
                "ccn": f"fund:{did}",
                "similarity_score": 2.0,   # 2× base
            }
            for k, pm in (packet.rcm_profile or {}).items():
                rec[k] = float(pm.value)
            rec.update(actuals)
            profile = packet.profile
            if profile:
                if profile.bed_count:
                    rec["bed_count"] = profile.bed_count
                if profile.state:
                    rec["state"] = profile.state
            comps.append(rec)
        return comps

    # ── Report ────────────────────────────────────────────────

    def build_report(self) -> AdjustmentReport:
        """End-to-end: extract, compute bias, count applicable metrics.

        The packet builder calls this to decide whether to apply
        adjustments and to surface the "Portfolio Intelligence" card
        on the workbench.
        """
        outcomes = self.extract_outcomes()
        bias = self.compute_bias(outcomes)
        applicable = {
            k: v for k, v in bias.items()
            if v.n_deals >= _MIN_DEALS_FOR_ADJUSTMENT
        }
        deal_ids = {o.deal_id for o in outcomes}
        parts: List[str] = []
        for metric, stats in sorted(applicable.items()):
            parts.append(
                f"{metric} predictions adjusted "
                f"{stats.mean_pct_error:+.0%} "
                f"({stats.direction}, n={stats.n_deals})"
            )
        return AdjustmentReport(
            adjustments_applied=len(applicable),
            bias_stats=bias,
            fund_deals_used=len(deal_ids),
            summary=(
                f"Based on {len(deal_ids)} completed deal(s): "
                + ("; ".join(parts) if parts else "no adjustments yet.")
            ),
        )
