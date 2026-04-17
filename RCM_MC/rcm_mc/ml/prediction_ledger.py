"""Prediction ledger — persistent storage for predictions and actuals.

Every prediction the system makes gets recorded here. When actuals arrive,
they're matched to predictions. This creates the feedback loop that makes
the models improve over time.

Tables:
- predictions: (id, ccn, metric, predicted_value, ci_low, ci_high, method,
                model_r2, coverage_target, created_at)
- prediction_actuals: (prediction_id, actual_value, recorded_at, source)
- model_performance_log: (metric, timestamp, mae, rmse, r2, coverage_rate,
                          n_predictions, n_actuals, cohort)
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ccn TEXT NOT NULL,
    metric TEXT NOT NULL,
    predicted_value REAL NOT NULL,
    ci_low REAL,
    ci_high REAL,
    method TEXT,
    model_r2 REAL,
    coverage_target REAL DEFAULT 0.90,
    features_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pred_ccn ON predictions(ccn);
CREATE INDEX IF NOT EXISTS ix_pred_metric ON predictions(metric);
CREATE INDEX IF NOT EXISTS ix_pred_created ON predictions(created_at);

CREATE TABLE IF NOT EXISTS prediction_actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL REFERENCES predictions(id),
    actual_value REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    UNIQUE(prediction_id)
);

CREATE TABLE IF NOT EXISTS model_performance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    cohort TEXT DEFAULT 'all',
    timestamp TEXT NOT NULL,
    mae REAL,
    rmse REAL,
    r2 REAL,
    coverage_rate REAL,
    mean_interval_width REAL,
    n_predictions INTEGER,
    n_actuals INTEGER,
    bias REAL,
    detail_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_mpl_metric ON model_performance_log(metric);
CREATE INDEX IF NOT EXISTS ix_mpl_ts ON model_performance_log(timestamp);
"""


@dataclass
class PredictionRecord:
    id: int
    ccn: str
    metric: str
    predicted_value: float
    ci_low: Optional[float]
    ci_high: Optional[float]
    method: Optional[str]
    model_r2: Optional[float]
    created_at: str
    actual_value: Optional[float] = None
    error: Optional[float] = None
    covered: Optional[bool] = None


@dataclass
class MetricPerformance:
    metric: str
    mae: float
    rmse: float
    r2: float
    coverage_rate: float
    mean_interval_width: float
    bias: float
    n_predictions: int
    n_actuals: int
    grade: str


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


def record_prediction(
    con: sqlite3.Connection,
    ccn: str,
    metric: str,
    predicted_value: float,
    ci_low: Optional[float] = None,
    ci_high: Optional[float] = None,
    method: Optional[str] = None,
    model_r2: Optional[float] = None,
    features: Optional[Dict[str, float]] = None,
) -> int:
    """Record a prediction in the ledger. Returns prediction_id."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    features_json = json.dumps(features) if features else None
    cur = con.execute(
        "INSERT INTO predictions "
        "(ccn, metric, predicted_value, ci_low, ci_high, method, model_r2, "
        " coverage_target, features_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 0.90, ?, ?)",
        (ccn, metric, predicted_value, ci_low, ci_high, method, model_r2,
         features_json, now),
    )
    return cur.lastrowid


def record_actual(
    con: sqlite3.Connection,
    prediction_id: int,
    actual_value: float,
    source: str = "manual",
) -> None:
    """Record an actual observation against a prediction."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "INSERT OR REPLACE INTO prediction_actuals "
        "(prediction_id, actual_value, recorded_at, source) VALUES (?, ?, ?, ?)",
        (prediction_id, actual_value, now, source),
    )


def record_batch_predictions(
    con: sqlite3.Connection,
    predictions: List[Dict[str, Any]],
) -> List[int]:
    """Record multiple predictions at once. Each dict needs ccn, metric, predicted_value."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    ids = []
    for p in predictions:
        cur = con.execute(
            "INSERT INTO predictions "
            "(ccn, metric, predicted_value, ci_low, ci_high, method, model_r2, "
            " coverage_target, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0.90, ?)",
            (p["ccn"], p["metric"], p["predicted_value"],
             p.get("ci_low"), p.get("ci_high"), p.get("method"),
             p.get("model_r2"), now),
        )
        ids.append(cur.lastrowid)
    return ids


def get_predictions_with_actuals(
    con: sqlite3.Connection,
    metric: Optional[str] = None,
    limit: int = 500,
) -> List[PredictionRecord]:
    """Get predictions that have matching actuals (for validation)."""
    _ensure_tables(con)
    query = (
        "SELECT p.id, p.ccn, p.metric, p.predicted_value, p.ci_low, p.ci_high, "
        "p.method, p.model_r2, p.created_at, pa.actual_value "
        "FROM predictions p "
        "JOIN prediction_actuals pa ON pa.prediction_id = p.id "
    )
    params: list = []
    if metric:
        query += "WHERE p.metric = ? "
        params.append(metric)
    query += "ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)

    rows = con.execute(query, params).fetchall()
    results = []
    for r in rows:
        pred = r[3]
        actual = r[9]
        ci_lo = r[4]
        ci_hi = r[5]
        error = actual - pred if actual is not None else None
        covered = (ci_lo <= actual <= ci_hi) if (ci_lo is not None and ci_hi is not None and actual is not None) else None
        results.append(PredictionRecord(
            id=r[0], ccn=r[1], metric=r[2],
            predicted_value=pred, ci_low=ci_lo, ci_high=ci_hi,
            method=r[6], model_r2=r[7], created_at=r[8],
            actual_value=actual, error=error, covered=covered,
        ))
    return results


def compute_metric_performance(
    con: sqlite3.Connection,
    metric: str,
    cohort: str = "all",
) -> Optional[MetricPerformance]:
    """Compute validation stats for a specific metric."""
    records = get_predictions_with_actuals(con, metric=metric)
    if len(records) < 3:
        return None

    errors = [r.error for r in records if r.error is not None]
    coverages = [r.covered for r in records if r.covered is not None]
    predictions = [r.predicted_value for r in records]
    actuals = [r.actual_value for r in records if r.actual_value is not None]
    widths = [r.ci_high - r.ci_low for r in records if r.ci_high is not None and r.ci_low is not None]

    if not errors:
        return None

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.array(errors) ** 2)))
    bias = float(np.mean(errors))
    coverage = float(np.mean(coverages)) if coverages else 0
    mean_width = float(np.mean(widths)) if widths else 0

    ss_res = sum(e ** 2 for e in errors)
    ss_tot = sum((a - np.mean(actuals)) ** 2 for a in actuals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    if r2 >= 0.7 and coverage >= 0.85:
        grade = "A"
    elif r2 >= 0.5 and coverage >= 0.75:
        grade = "B"
    elif r2 >= 0.3:
        grade = "C"
    else:
        grade = "D"

    return MetricPerformance(
        metric=metric, mae=round(mae, 6), rmse=round(rmse, 6),
        r2=round(r2, 4), coverage_rate=round(coverage, 4),
        mean_interval_width=round(mean_width, 6), bias=round(bias, 6),
        n_predictions=len(records), n_actuals=len(actuals), grade=grade,
    )


def log_performance(
    con: sqlite3.Connection,
    perf: MetricPerformance,
    cohort: str = "all",
) -> None:
    """Log a performance snapshot for trend tracking."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "INSERT INTO model_performance_log "
        "(metric, cohort, timestamp, mae, rmse, r2, coverage_rate, "
        " mean_interval_width, n_predictions, n_actuals, bias) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (perf.metric, cohort, now, perf.mae, perf.rmse, perf.r2,
         perf.coverage_rate, perf.mean_interval_width,
         perf.n_predictions, perf.n_actuals, perf.bias),
    )


def get_performance_trend(
    con: sqlite3.Connection,
    metric: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get historical performance snapshots for trend analysis."""
    _ensure_tables(con)
    rows = con.execute(
        "SELECT timestamp, mae, rmse, r2, coverage_rate, n_actuals, bias "
        "FROM model_performance_log WHERE metric = ? "
        "ORDER BY timestamp DESC LIMIT ?",
        (metric, limit),
    ).fetchall()
    return [
        {"timestamp": r[0], "mae": r[1], "rmse": r[2], "r2": r[3],
         "coverage_rate": r[4], "n_actuals": r[5], "bias": r[6]}
        for r in rows
    ]


def run_synthetic_backtest(
    con: sqlite3.Connection,
    hcris_df: Any,
    n_trials: int = 100,
    seed: int = 42,
) -> Dict[str, MetricPerformance]:
    """Run a synthetic backtest using HCRIS data as ground truth.

    Hide one hospital's metrics, predict from peers, compare to actual.
    This creates the initial validation dataset from public data.
    """
    import pandas as pd
    _ensure_tables(con)

    rng = np.random.RandomState(seed)
    df = hcris_df.copy()

    # Metrics we can validate from HCRIS
    testable = {
        "operating_margin": ("operating_margin", "pct"),
        "revenue_per_bed": ("revenue_per_bed", "dollars"),
        "occupancy_rate": ("occupancy_rate", "pct"),
        "net_to_gross_ratio": ("net_to_gross_ratio", "pct"),
    }

    # Compute derived cols if missing
    if "operating_margin" not in df.columns:
        rev = df.get("net_patient_revenue", pd.Series(dtype=float))
        opex = df.get("operating_expenses", pd.Series(dtype=float))
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "revenue_per_bed" not in df.columns and "beds" in df.columns:
        df["revenue_per_bed"] = df["net_patient_revenue"] / df["beds"].replace(0, np.nan)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "net_to_gross_ratio" not in df.columns and "gross_patient_revenue" in df.columns:
        df["net_to_gross_ratio"] = (
            df["net_patient_revenue"] / df["gross_patient_revenue"].replace(0, np.nan)
        ).clip(0, 1)

    clean = df.dropna(subset=list(testable.keys()))
    if len(clean) < 50:
        return {}

    sample_idx = rng.choice(len(clean), size=min(n_trials, len(clean)), replace=False)

    results_by_metric: Dict[str, list] = {m: [] for m in testable}

    for idx in sample_idx:
        target = clean.iloc[idx]
        ccn = str(target.get("ccn", ""))
        state = str(target.get("state", ""))
        beds = float(target.get("beds", 100))

        # Find peers (same state, similar size)
        peers = clean[(clean["ccn"] != ccn)]
        same_state = peers[peers["state"] == state]
        if len(same_state) >= 10:
            peer_df = same_state
        else:
            peer_df = peers

        for metric, (col, unit) in testable.items():
            actual = float(target[col])
            if pd.isna(actual):
                continue

            # Predict: peer median (simple but honest)
            peer_vals = peer_df[col].dropna()
            if len(peer_vals) < 5:
                continue
            predicted = float(peer_vals.median())
            ci_lo = float(peer_vals.quantile(0.05))
            ci_hi = float(peer_vals.quantile(0.95))

            # Record
            pid = record_prediction(
                con, ccn, metric, predicted,
                ci_low=ci_lo, ci_high=ci_hi,
                method="peer_median_backtest",
                model_r2=None,
            )
            record_actual(con, pid, actual, source="hcris_backtest")

            results_by_metric[metric].append({
                "predicted": predicted, "actual": actual,
                "ci_low": ci_lo, "ci_high": ci_hi,
            })

    # Compute and log performance
    performances = {}
    for metric in testable:
        perf = compute_metric_performance(con, metric)
        if perf:
            log_performance(con, perf)
            performances[metric] = perf

    return performances
