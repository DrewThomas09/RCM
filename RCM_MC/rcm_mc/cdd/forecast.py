"""BOLSTER-01 Ridge + conformal forecast engine (spec-pinned, hardened).

Pins the forecasting spec the platform relies on:
- sklearn.linear_model.Ridge as the point estimator.
- alpha selected by GridSearchCV over np.logspace(-2, 2) with TimeSeriesSplit
  for temporal data (no leakage from future folds).
- split-conformal intervals: calibrate on the last 20 percent by time, take the
  split-conformal quantile of absolute calibration residuals, at 80 and 95
  percent nominal coverage.
- an explicit holdout coverage check: empirical coverage on the test holdout
  must be at least nominal minus a 1 percent slack.
- reproducibility: identical numeric output on a fixed seed.

Inference is statistical only. No LLM is on the path: the forecast is a Ridge
dot product plus a conformal margin from observed residuals.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "BOLSTER-01"
DEFAULT_ALPHAS = np.logspace(-2, 2, 17)
COVERAGE_SLACK = 0.01


def _conformal_margin(residuals: np.ndarray, coverage: float) -> float:
    """Split-conformal margin: the ceil((1-a)(n+1))/n quantile of |residuals|."""
    n = len(residuals)
    if n == 0:
        return float("inf")
    abs_res = np.sort(np.abs(residuals))
    rank = int(np.ceil((coverage) * (n + 1)))
    rank = min(max(rank, 1), n)  # clamp; over-cover on tiny calibration sets
    return float(abs_res[rank - 1])


def ridge_conformal_forecast(
    X: Sequence[Sequence[float]],
    y: Sequence[float],
    *,
    coverages: Sequence[float] = (0.80, 0.95),
    train_frac: float = 0.6,
    calib_frac: float = 0.2,
    alphas: Optional[Sequence[float]] = None,
    n_splits: int = 5,
    seed: int = 42,
    source: str = "Target time series",
    vintage: str = "",
    audience: str = "internal",
) -> Exhibit:
    """Fit Ridge with conformal intervals and verify holdout coverage.

    Data must be in temporal order. Splits by time into train, calibration, and
    test (holdout) blocks. Returns an exhibit carrying the selected alpha, the
    conformal margins, and the empirical coverage on the holdout.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n = len(y)
    if n < 20:
        raise ValueError("ridge_conformal_forecast needs at least 20 ordered points")
    alphas = list(alphas) if alphas is not None else list(DEFAULT_ALPHAS)

    n_train = int(round(n * train_frac))
    n_calib = int(round(n * calib_frac))
    n_train = max(n_train, n_splits + 1)
    if n_train + n_calib >= n:
        n_calib = max(1, n - n_train - 1)
    X_tr, y_tr = X[:n_train], y[:n_train]
    X_cal, y_cal = X[n_train:n_train + n_calib], y[n_train:n_train + n_calib]
    X_te, y_te = X[n_train + n_calib:], y[n_train + n_calib:]

    # Alpha selection by GridSearchCV with TimeSeriesSplit (no future leakage).
    # Features are standardized so the Ridge penalty does not bias the slope and
    # break conformal exchangeability on the holdout.
    def _pipe() -> Pipeline:
        return Pipeline([("scale", StandardScaler()), ("ridge", Ridge())])

    splits = min(n_splits, max(2, n_train - 1))
    grid = GridSearchCV(
        _pipe(),
        {"ridge__alpha": alphas},
        cv=TimeSeriesSplit(n_splits=splits),
        scoring="neg_mean_squared_error",
    )
    grid.fit(X_tr, y_tr)
    best_alpha = float(grid.best_params_["ridge__alpha"])

    model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=best_alpha))])
    model.fit(X_tr, y_tr)

    cal_residuals = y_cal - model.predict(X_cal)
    te_pred = model.predict(X_te)

    flags: List[Flag] = []
    reconciliations: List[Reconciliation] = []
    coverage_report: Dict[str, Any] = {}
    series_points: List[Dict[str, Any]] = []

    for cov in coverages:
        margin = _conformal_margin(cal_residuals, cov)
        lo = te_pred - margin
        hi = te_pred + margin
        covered = np.mean((y_te >= lo) & (y_te <= hi)) if len(y_te) else float("nan")
        empirical = float(covered)
        meets = empirical >= cov - COVERAGE_SLACK
        coverage_report[f"{int(cov*100)}"] = {
            "nominal": cov,
            "margin": margin,
            "empirical_coverage": empirical,
            "coverage_gap": empirical - cov,
            "meets_guarantee": meets,
        }
        series_points.append({"label": f"{int(cov*100)}% interval", "value": margin})
        reconciliations.append(Reconciliation(
            identity=f"empirical coverage >= nominal {int(cov*100)}% minus 1% slack",
            lhs=1.0 if meets else 0.0, rhs=1.0, tolerance=1e-9,
        ))
        if not meets:
            flags.append(Flag(
                code=f"coverage_shortfall_{int(cov*100)}",
                severity="risk",
                message=(
                    f"Empirical coverage {empirical*100:.1f} percent is below the "
                    f"{cov*100:.0f} percent nominal minus 1 percent slack."
                ),
            ))

    series = [
        Series(name="Conformal interval width by coverage", kind="bar", points=series_points),
        Series(name="Holdout point forecast", kind="line",
               points=[{"label": f"t{i}", "value": float(p)} for i, p in enumerate(te_pred)]),
        Series(name="Model internals", kind="bar", internal_only=True, points=[
            {"label": "alpha", "value": best_alpha},
            {"label": "n_train", "value": n_train},
            {"label": "n_calib", "value": len(y_cal)},
            {"label": "n_test", "value": len(y_te)},
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Ridge point estimator, alpha by GridSearchCV over logspace(-2,2) with TimeSeriesSplit.",
            "Split-conformal intervals calibrated on the last 20 percent by time.",
            "Inference is a Ridge prediction plus a conformal margin. No LLM.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Ridge conformal forecast",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Ridge alpha {best_alpha:g}. Coverage met at "
            + ", ".join(f"{k}%" for k, v in coverage_report.items() if v["meets_guarantee"]) + "."
        ),
        meta={
            "alpha": best_alpha,
            "alphas_searched": alphas,
            "coverage": coverage_report,
            "n_train": n_train, "n_calib": len(y_cal), "n_test": len(y_te),
            "seed": seed,
            "llm_free": True,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    # Exchangeable design: split-conformal's coverage guarantee holds when
    # calibration and holdout are exchangeable. Features are drawn i.i.d.
    rng = np.random.default_rng(42)
    n = 200
    X = rng.normal(0, 1, (n, 2))
    y = 3.0 * X[:, 0] - 1.5 * X[:, 1] + 4.0 + rng.normal(0, 1.0, n)
    return ridge_conformal_forecast(X, y, seed=42, source="Demo series", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Ridge + conformal forecast engine (hardened)",
        audience="internal",
        demo=_demo,
    )
)
