"""Per-metric time-series trend detection + short-horizon forecasting.

Every RCM metric today is treated as a point-in-time snapshot. But
denial rates drift with payer-rule changes, AR days pulse with
month-end billing cycles, and payer mix moves year-over-year. When
the analyst has 3+ years of quarterly history (from Prompt 25's
document reader or partner uploads), the platform should say:

    "denial rate is trending UP at 0.8pp/quarter —
     it projects to 14.2% in 4 quarters if nothing changes."

Three forecast methods, auto-selected on period count + structure:

1. **Linear OLS** (≥6 periods). ``y = a + b·t``; intercept + slope
   via normal equations; confidence bands from residual σ.
2. **Additive Holt-Winters** (≥8 periods + detected seasonality).
   Level + trend + seasonal components updated period-by-period.
3. **Weighted-recent** (<6 periods). Exponential-decay weights on
   the observed history. Not a forecast, just a "best current
   estimate" — partners see this and know the sample is thin.

Stdlib-only implementation — numpy arithmetic, no statsmodels, no
scipy. Keeps the RCM-MC runtime footprint unchanged.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class TrendResult:
    """Mann-Kendall–style trend direction + magnitude.

    ``direction`` is a plain-English label the UI shows next to each
    metric — most renderers want the arrow shape (↑/↓/→), not the
    numeric slope.

    ``p_value_approx`` is computed from the normal approximation of
    Mann-Kendall's S statistic (no scipy needed). Partners reading the
    number know the approximation is rough at n<10 but directionally
    correct.
    """
    direction: str = "stable"         # improving | deteriorating | stable
    slope_per_period: float = 0.0
    p_value_approx: float = 1.0
    n_periods: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "slope_per_period": float(self.slope_per_period),
            "p_value_approx": float(self.p_value_approx),
            "n_periods": int(self.n_periods),
        }


@dataclass
class TemporalForecast:
    """Per-metric forecast package.

    ``forecasted`` is a list of ``(period_label, value, ci_low, ci_high)``
    tuples the renderer can turn into a sparkline. ``seasonality_detected``
    drives whether Holt-Winters was used; callers that want a simple
    "is this metric seasonal" check should read that flag.
    """
    metric_key: str = ""
    historical: List[Tuple[str, float]] = field(default_factory=list)
    trend: TrendResult = field(default_factory=TrendResult)
    seasonality_detected: bool = False
    forecasted: List[Tuple[str, float, float, float]] = field(
        default_factory=list,
    )
    method: str = "weighted_recent"    # linear | holt_winters | weighted_recent
    period: int = 4                    # seasonal period, default quarterly

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "historical": [
                {"period": p, "value": float(v)}
                for p, v in self.historical
            ],
            "trend": self.trend.to_dict(),
            "seasonality_detected": bool(self.seasonality_detected),
            "forecasted": [
                {"period": p, "value": float(v),
                 "ci_low": float(lo), "ci_high": float(hi)}
                for p, v, lo, hi in self.forecasted
            ],
            "method": self.method,
            "period": int(self.period),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TemporalForecast":
        d = d or {}
        trend_raw = d.get("trend") or {}
        return cls(
            metric_key=str(d.get("metric_key") or ""),
            historical=[
                (str(row.get("period") or ""), float(row.get("value") or 0))
                for row in (d.get("historical") or [])
            ],
            trend=TrendResult(
                direction=str(trend_raw.get("direction") or "stable"),
                slope_per_period=float(trend_raw.get("slope_per_period") or 0),
                p_value_approx=float(trend_raw.get("p_value_approx") or 1.0),
                n_periods=int(trend_raw.get("n_periods") or 0),
            ),
            seasonality_detected=bool(d.get("seasonality_detected") or False),
            forecasted=[
                (str(row.get("period") or ""),
                 float(row.get("value") or 0),
                 float(row.get("ci_low") or 0),
                 float(row.get("ci_high") or 0))
                for row in (d.get("forecasted") or [])
            ],
            method=str(d.get("method") or "weighted_recent"),
            period=int(d.get("period") or 4),
        )


# ── Direction resolver ─────────────────────────────────────────────

# Metrics where a rising value is bad (lower-is-better). Mirrors the
# v2 bridge's ``_LOWER_IS_BETTER`` set; kept local so this module
# doesn't drag in the bridge just to label arrows.
_LOWER_IS_BETTER = frozenset({
    "denial_rate", "initial_denial_rate", "final_denial_rate",
    "days_in_ar", "ar_over_90_pct", "cost_to_collect",
    "discharged_not_final_billed_days", "coding_denial_rate",
    "auth_denial_rate", "eligibility_denial_rate",
    "timely_filing_denial_rate", "medical_necessity_denial_rate",
    "bad_debt",
})


def _label_direction(metric_key: str, slope: float,
                     p_value: float) -> str:
    """Translate numeric slope + p into an English label.

    Rules:
    - |slope| tiny or p > 0.15 → "stable".
    - Positive slope on a lower-is-better metric → "deteriorating".
    - Positive slope on a higher-is-better metric → "improving".
    - Negative slope — inverse.
    """
    if abs(slope) < 1e-9 or p_value > 0.15:
        return "stable"
    lower_better = metric_key in _LOWER_IS_BETTER
    rising = slope > 0
    if lower_better:
        return "deteriorating" if rising else "improving"
    return "improving" if rising else "deteriorating"


# ── Mann-Kendall trend test ────────────────────────────────────────

def detect_trend(
    values: Sequence[float], *, metric_key: str = "",
) -> TrendResult:
    """Mann-Kendall S statistic + normal-approximation p-value.

    Rank-based, so it's robust to non-normal residuals — partners'
    historical quarterly data usually has a heavy tail from billing-
    cycle artifacts. Slope is estimated by OLS for a concrete
    "per-period" number the UI can show.

    Returns an empty/stable result when ``values`` has fewer than
    three points.
    """
    xs = [float(v) for v in values if v is not None
          and not (isinstance(v, float) and math.isnan(v))]
    n = len(xs)
    if n < 3:
        return TrendResult(n_periods=n)

    # Mann-Kendall S: count pairwise increases minus decreases.
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = xs[j] - xs[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    # Normal approximation variance.
    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    if var_s <= 0:
        return TrendResult(n_periods=n)
    z = ((s - 1) / math.sqrt(var_s)) if s > 0 else (
        (s + 1) / math.sqrt(var_s) if s < 0 else 0.0
    )
    # Two-tailed p via the standard-normal CDF approximation
    # (Abramowitz & Stegun 7.1.26; borrowed from the MC module).
    p = 2.0 * (1.0 - _normal_cdf(abs(z)))

    # OLS slope for the magnitude.
    t = np.arange(n, dtype=float)
    mean_t = t.mean()
    mean_y = sum(xs) / n
    denom = float(np.sum((t - mean_t) ** 2))
    if denom <= 0:
        slope = 0.0
    else:
        slope = float(np.sum((t - mean_t) * (np.asarray(xs) - mean_y))) / denom

    direction = _label_direction(metric_key, slope, p)
    return TrendResult(
        direction=direction,
        slope_per_period=slope,
        p_value_approx=float(p),
        n_periods=n,
    )


def _normal_cdf(x: float) -> float:
    """Abramowitz & Stegun 7.1.26 CDF approximation. Max err ~1.5e-7."""
    a1, a2, a3 = 0.254829592, -0.284496736, 1.421413741
    a4, a5 = -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1.0 if x >= 0 else -1.0
    ax = abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + p * ax)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-ax * ax)
    return 0.5 * (1.0 + sign * y)


# ── Seasonality detection ──────────────────────────────────────────

def detect_seasonality(
    values: Sequence[float], period: int = 4,
) -> bool:
    """Autocorrelation at lag ``period`` > 0.3 → seasonal.

    Period 4 = quarterly data with an annual cycle (the common case).
    Below 2·period samples we can't say anything, so return False.
    """
    xs = np.asarray(
        [float(v) for v in values if v is not None
         and not (isinstance(v, float) and math.isnan(v))],
        dtype=float,
    )
    n = len(xs)
    if n < 2 * period + 1:
        return False
    mean = xs.mean()
    deviations = xs - mean
    denom = float(np.sum(deviations ** 2))
    if denom <= 0:
        return False
    numer = float(np.sum(deviations[:-period] * deviations[period:]))
    acf = numer / denom
    return acf > 0.3


# ── Linear OLS forecast ────────────────────────────────────────────

def _linear_forecast(
    xs: List[float], n_forward: int,
) -> Tuple[List[Tuple[float, float, float]], float]:
    """Return ``(forecast_rows, residual_sigma)``. ``forecast_rows``
    is a list of ``(value, ci_low, ci_high)`` tuples for the next
    ``n_forward`` periods."""
    n = len(xs)
    t = np.arange(n, dtype=float)
    y = np.asarray(xs, dtype=float)
    # Closed-form OLS.
    t_mean = t.mean()
    y_mean = y.mean()
    denom = float(np.sum((t - t_mean) ** 2))
    if denom <= 0:
        slope = 0.0
    else:
        slope = float(np.sum((t - t_mean) * (y - y_mean))) / denom
    intercept = y_mean - slope * t_mean
    y_hat = intercept + slope * t
    residuals = y - y_hat
    # ``ddof=2`` — we fit intercept + slope.
    sigma = float(np.sqrt(
        float(np.sum(residuals ** 2)) / max(1, n - 2)
    )) if n > 2 else 0.0
    # 90% band → ±1.645σ. Widen by sqrt(1 + h/n) as we step forward.
    rows: List[Tuple[float, float, float]] = []
    for h in range(1, n_forward + 1):
        v = intercept + slope * (n - 1 + h)
        widen = 1.645 * sigma * math.sqrt(1.0 + h / max(1, n))
        rows.append((v, v - widen, v + widen))
    return rows, sigma


# ── Holt-Winters (additive) ────────────────────────────────────────

def _holt_winters_forecast(
    xs: List[float], n_forward: int, period: int = 4,
    alpha: float = 0.4, beta: float = 0.1, gamma: float = 0.3,
) -> List[Tuple[float, float, float]]:
    """Additive Holt-Winters. CI widens by ``sqrt(h)``.

    Defaults chosen to be partner-defensible on quarterly RCM data:
    - ``alpha`` (level smoothing) 0.4 — moderately responsive.
    - ``beta`` (trend) 0.1 — slow trend updates; prevents a single
      outlier from flipping direction.
    - ``gamma`` (seasonal) 0.3 — moderate seasonal adaptation.
    """
    n = len(xs)
    if n < 2 * period:
        return []

    # Initialize level + trend + seasonal components.
    level = float(np.mean(xs[:period]))
    trend = (float(np.mean(xs[period:2 * period]))
             - float(np.mean(xs[:period]))) / period
    seasonal = [xs[i] - level for i in range(period)]

    # Walk the history.
    residuals: List[float] = []
    for i, y in enumerate(xs):
        s_idx = i % period
        last_level = level
        last_trend = trend
        last_s = seasonal[s_idx]
        y_hat = last_level + last_trend + last_s
        residuals.append(y - y_hat)
        level = alpha * (y - last_s) + (1 - alpha) * (last_level + last_trend)
        trend = beta * (level - last_level) + (1 - beta) * last_trend
        seasonal[s_idx] = gamma * (y - level) + (1 - gamma) * last_s

    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    out: List[Tuple[float, float, float]] = []
    for h in range(1, n_forward + 1):
        s_idx = (n + h - 1) % period
        v = level + h * trend + seasonal[s_idx]
        widen = 1.645 * sigma * math.sqrt(h)
        out.append((v, v - widen, v + widen))
    return out


# ── Weighted-recent fallback ──────────────────────────────────────

def _weighted_recent_forecast(
    xs: List[float], n_forward: int, half_life: float = 2.0,
) -> List[Tuple[float, float, float]]:
    """Exponentially-weighted mean of the observed history.

    Not really a forecast — we project the weighted mean flat forward
    and widen the CI with h. Used when period count is too low for a
    real model; the UI should badge this as "best estimate" rather
    than a trend projection.
    """
    n = len(xs)
    if n == 0:
        return []
    y = np.asarray(xs, dtype=float)
    # Weights exp(−(n-1-i)/half_life); most recent point weight 1.0.
    ages = np.arange(n - 1, -1, -1, dtype=float)
    weights = np.exp(-ages / max(1e-6, float(half_life)))
    weights = weights / weights.sum()
    weighted_mean = float(np.sum(weights * y))
    deviations = y - weighted_mean
    sigma = float(np.sqrt(np.sum(weights * deviations ** 2)))
    out: List[Tuple[float, float, float]] = []
    for h in range(1, n_forward + 1):
        widen = 1.645 * sigma * math.sqrt(h)
        out.append((weighted_mean, weighted_mean - widen, weighted_mean + widen))
    return out


# ── Period-label generator ─────────────────────────────────────────

def _next_period_labels(
    last_label: str, n_forward: int,
) -> List[str]:
    """Best-effort "2024-Q3" → "2024-Q4" / "2025-Q1" / "2025-Q2" ...

    Partners paste arbitrary period formats into the uploads (some
    prefer "FY24", some "2024-01-31"). When we can't parse, we fall
    back to generic "+1", "+2", ... so the forecast still renders.
    """
    if not last_label:
        return [f"+{i}" for i in range(1, n_forward + 1)]
    import re
    # Quarterly ``YYYY-QN`` or ``YYYYQN``.
    m = re.match(r"^(\d{4})[-\s]?Q([1-4])$", last_label.strip().upper())
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        out: List[str] = []
        for _ in range(n_forward):
            q += 1
            if q > 4:
                q = 1; year += 1
            out.append(f"{year}-Q{q}")
        return out
    # YYYY-MM.
    m = re.match(r"^(\d{4})-(\d{2})$", last_label.strip())
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        out = []
        for _ in range(n_forward):
            month += 1
            if month > 12:
                month = 1; year += 1
            out.append(f"{year}-{month:02d}")
        return out
    return [f"+{i}" for i in range(1, n_forward + 1)]


# ── Public entry ──────────────────────────────────────────────────

def forecast_metric(
    metric_key: str,
    values: Sequence[Tuple[str, float]],
    *,
    n_forward: int = 4,
    period: int = 4,
) -> TemporalForecast:
    """Pick the right method based on history length + seasonality,
    and return a :class:`TemporalForecast` the UI can sparkline.

    ``values`` is a sequence of ``(period_label, value)`` tuples in
    chronological order. Non-finite values are dropped. With fewer
    than 3 points we skip the trend test entirely — the UI shows a
    flat "insufficient history" indicator.
    """
    pairs: List[Tuple[str, float]] = []
    for row in values or []:
        try:
            label, v = row[0], float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not math.isfinite(v):
            continue
        pairs.append((str(label), v))
    if not pairs:
        return TemporalForecast(metric_key=metric_key)

    xs = [p[1] for p in pairs]
    n = len(pairs)
    trend = detect_trend(xs, metric_key=metric_key)
    seasonal = detect_seasonality(xs, period=period)

    last_label = pairs[-1][0]
    future_labels = _next_period_labels(last_label, n_forward)

    method = "weighted_recent"
    if n >= 8 and seasonal:
        method = "holt_winters"
        rows = _holt_winters_forecast(xs, n_forward, period=period)
    elif n >= 6:
        method = "linear"
        rows, _sigma = _linear_forecast(xs, n_forward)
    else:
        rows = _weighted_recent_forecast(xs, n_forward)

    forecasted: List[Tuple[str, float, float, float]] = [
        (lbl, val, lo, hi) for lbl, (val, lo, hi) in zip(future_labels, rows)
    ]
    return TemporalForecast(
        metric_key=metric_key,
        historical=pairs,
        trend=trend,
        seasonality_detected=seasonal,
        forecasted=forecasted,
        method=method,
        period=period,
    )


def forecast_all(
    historical_values: Dict[str, Sequence[Tuple[str, float]]],
    *,
    n_forward: int = 4,
    period: int = 4,
) -> Dict[str, TemporalForecast]:
    """Run :func:`forecast_metric` across every metric in the
    history dict. Used by the packet builder when the analyst
    uploaded multi-period data."""
    out: Dict[str, TemporalForecast] = {}
    for metric, series in (historical_values or {}).items():
        try:
            out[str(metric)] = forecast_metric(
                str(metric), series,
                n_forward=n_forward, period=period,
            )
        except Exception as exc:  # noqa: BLE001 — never let one metric kill the batch
            logger.debug("forecast for %s failed: %s", metric, exc)
            continue
    return out
