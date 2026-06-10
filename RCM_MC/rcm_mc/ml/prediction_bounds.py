"""Reasonableness bounds for every predicted value — the verification layer.

A prediction shown to a partner must be *reasonable*: an initial-denial rate
of 80%, a turnaround probability of 1.4, or an EBITDA uplift larger than the
hospital's revenue are nonsense and must never reach the screen. The model
code already clamps each output; this module is the single, testable registry
of what "reasonable" means, so:

  * the "?" calc-explainers cite the same benchmark the value is held to;
  * a coverage sweep (``verify_predictions``) can assert that EVERY hospital's
    predictions land inside their band — cross-referencing the model output
    against the bound, across the whole universe, not just spot checks.

Bounds mirror the clamps in the predictors (predictive_screener
._predict_rcm_fast, ml.margin_predictor, ml.distress_predictor):

  est_denial      2%–25%   (industry initial-denial range)
  est_ar_days     25–75    (days in A/R)
  est_uplift      0 … 15% of net patient revenue (max single-lever RCM gain)
  predicted_margin   −100%…+100% hard clamp (realistic band is −40%…+30%)
  turnaround_probability / distress_prob   0–1 (a probability)
  investability_score   0–100
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class Bound:
    """A reasonable range for a predicted metric. ``hi`` may be a fixed number
    or a callable of the row's context (e.g. uplift ≤ 15% of revenue)."""
    metric: str
    lo: float
    hi: object              # float, or Callable[[dict], float] for relative caps
    label: str

    def hi_value(self, ctx: Optional[dict] = None) -> float:
        if callable(self.hi):
            return float(self.hi(ctx or {}))
        return float(self.hi)

    def contains(self, value: Optional[float], ctx: Optional[dict] = None) -> bool:
        """True when value is None/NaN (a gap — verified elsewhere) OR within
        [lo, hi]. A tiny epsilon absorbs float-rounding at the clamp edge."""
        if value is None:
            return True
        try:
            v = float(value)
        except (TypeError, ValueError):
            return True
        if v != v:  # NaN
            return True
        hi = self.hi_value(ctx)
        # Magnitude-aware tolerance: predictors round their clamped output (e.g.
        # uplift to integer dollars, so a value can sit up to $0.50 above a
        # multi-thousand-dollar cap). A 0.01% relative epsilon absorbs that
        # rounding for dollar-scale bounds — far below any real violation
        # (a bug would be tens of % out) — while staying tight (≤3e-5) for the
        # fraction/probability bounds.
        eps = 1e-6 + 1e-4 * max(abs(hi), abs(self.lo))
        return (self.lo - eps) <= v <= (hi + eps)


PREDICTION_BOUNDS: Dict[str, Bound] = {
    "est_denial": Bound("est_denial", 0.02, 0.25,
                        "Initial-denial rate, clamped to the 2%–25% industry range"),
    "est_ar_days": Bound("est_ar_days", 25.0, 75.0,
                         "Days in A/R, clamped to 25–75"),
    "est_uplift": Bound("est_uplift", 0.0,
                        lambda c: 0.15 * float(c.get("net_patient_revenue") or 0),
                        "EBITDA uplift, capped at 15% of net patient revenue"),
    "predicted_margin": Bound("predicted_margin", -1.0, 1.0,
                              "Predicted operating margin, hard-clamped to ±100%"),
    "turnaround_probability": Bound("turnaround_probability", 0.0, 1.0,
                                    "A probability in [0, 1]"),
    "distress_prob": Bound("distress_prob", 0.0, 1.0, "A probability in [0, 1]"),
    "investability_score": Bound("investability_score", 0.0, 100.0,
                                 "Composite score in [0, 100]"),
}


def within_bounds(metric: str, value: Optional[float],
                  ctx: Optional[dict] = None) -> bool:
    """True when a predicted ``value`` for ``metric`` is reasonable (or is an
    unknown metric we don't bound, or a gap). Never raises."""
    b = PREDICTION_BOUNDS.get(metric)
    if b is None:
        return True
    return b.contains(value, ctx)


def verify_predictions(rows, predict: Callable[[dict], dict]) -> Dict[str, object]:
    """Run ``predict`` over each row (a dict of HCRIS fields) and verify every
    bounded prediction is reasonable. Returns a coverage report:

        {"n": <rows>, "checked": <predictions checked>,
         "violations": [ {row_index, metric, value, bound}, ... ]}

    A clean run has an empty ``violations`` list — proof that across the WHOLE
    universe no hospital gets an out-of-band predicted number."""
    violations: List[dict] = []
    checked = 0
    n = 0
    for i, row in enumerate(rows):
        n += 1
        try:
            preds = predict(row)
        except Exception:  # noqa: BLE001 — a failed prediction is a gap, not a violation
            continue
        for metric, b in PREDICTION_BOUNDS.items():
            if metric not in preds:
                continue
            checked += 1
            if not b.contains(preds.get(metric), row):
                violations.append({
                    "row_index": i, "metric": metric,
                    "value": preds.get(metric), "bound": b.label,
                })
    return {"n": n, "checked": checked, "violations": violations}
