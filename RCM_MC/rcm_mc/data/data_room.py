"""Seller Data Room — persistent storage for analyst-entered KPIs.

When a PE firm enters diligence, they receive actual operational data
from the seller (denial rates, AR aging, payer contracts, staffing).
This module stores those data points, links them to ML predictions,
and computes Bayesian posterior estimates that blend seller data with
our predictions.

Every data point is attributed (source, analyst, date) so the IC memo
can show provenance: "Denial rate: 9.3% (seller Q4 report) vs 11.2%
(ML prediction) → Bayesian estimate: 9.8% (90% CI: 8.1-11.5%)."

Tables:
- data_room_entries: (hospital_ccn, metric, value, source, analyst, notes, entered_at)
- data_room_calibrations: (hospital_ccn, metric, ml_predicted, seller_value,
                           bayesian_posterior, ci_low, ci_high, shrinkage, computed_at)
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np


_SCHEMA = """
CREATE TABLE IF NOT EXISTS data_room_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_ccn TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    sample_size INTEGER DEFAULT 0,
    source TEXT DEFAULT '',
    analyst TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    entered_at TEXT NOT NULL,
    superseded_by INTEGER DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS ix_dre_ccn ON data_room_entries(hospital_ccn);
CREATE INDEX IF NOT EXISTS ix_dre_metric ON data_room_entries(hospital_ccn, metric);

CREATE TABLE IF NOT EXISTS data_room_calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_ccn TEXT NOT NULL,
    metric TEXT NOT NULL,
    ml_predicted REAL,
    seller_value REAL,
    seller_n INTEGER DEFAULT 0,
    bayesian_posterior REAL,
    ci_low REAL,
    ci_high REAL,
    shrinkage REAL,
    data_quality TEXT,
    computed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_drc_ccn ON data_room_calibrations(hospital_ccn);
"""

_METRIC_DEFINITIONS = {
    "denial_rate": {"label": "Denial Rate", "type": "rate", "unit": "%", "direction": "lower"},
    "days_in_ar": {"label": "Days in AR", "type": "continuous", "unit": "days", "direction": "lower"},
    "clean_claim_rate": {"label": "Clean Claim Rate", "type": "rate", "unit": "%", "direction": "higher"},
    "net_collection_rate": {"label": "Net Collection Rate", "type": "rate", "unit": "%", "direction": "higher"},
    "cost_to_collect": {"label": "Cost to Collect", "type": "rate", "unit": "%", "direction": "lower"},
    "first_pass_resolution": {"label": "First Pass Resolution", "type": "rate", "unit": "%", "direction": "higher"},
    "appeals_overturn_rate": {"label": "Appeals Overturn Rate", "type": "rate", "unit": "%", "direction": "higher"},
    "dnfb_days": {"label": "DNFB Days", "type": "continuous", "unit": "days", "direction": "lower"},
    "ar_over_90_pct": {"label": "AR Over 90 Days %", "type": "rate", "unit": "%", "direction": "lower"},
    "bad_debt_rate": {"label": "Bad Debt Rate", "type": "rate", "unit": "%", "direction": "lower"},
    "case_mix_index": {"label": "Case Mix Index", "type": "continuous", "unit": "index", "direction": "higher"},
    "coding_accuracy": {"label": "Coding Accuracy", "type": "rate", "unit": "%", "direction": "higher"},
    "charge_lag_days": {"label": "Charge Lag Days", "type": "continuous", "unit": "days", "direction": "lower"},
    "total_claims_volume": {"label": "Annual Claims Volume", "type": "continuous", "unit": "count", "direction": "neutral"},
    "fte_rcm_staff": {"label": "RCM FTE Staff", "type": "continuous", "unit": "FTEs", "direction": "neutral"},
    "annual_revenue": {"label": "Annual Net Revenue", "type": "continuous", "unit": "$", "direction": "higher"},
    "ebitda": {"label": "EBITDA", "type": "continuous", "unit": "$", "direction": "higher"},
    "ebitda_margin": {"label": "EBITDA Margin", "type": "rate", "unit": "%", "direction": "higher"},
}


@dataclass
class DataRoomEntry:
    id: int
    hospital_ccn: str
    metric: str
    value: float
    sample_size: int
    source: str
    analyst: str
    notes: str
    entered_at: str


@dataclass
class CalibratedMetric:
    metric: str
    label: str
    ml_predicted: Optional[float]
    seller_value: float
    seller_n: int
    bayesian_posterior: float
    ci_low: float
    ci_high: float
    shrinkage: float
    data_quality: str
    delta_from_prediction: Optional[float]
    direction: str


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


def save_entry(
    con: sqlite3.Connection,
    hospital_ccn: str,
    metric: str,
    value: float,
    sample_size: int = 0,
    source: str = "",
    analyst: str = "",
    notes: str = "",
) -> int:
    """Save a seller data point. Returns entry ID."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()

    # Supersede previous entries for same metric
    con.execute(
        "UPDATE data_room_entries SET superseded_by = -1 "
        "WHERE hospital_ccn = ? AND metric = ? AND superseded_by IS NULL",
        (hospital_ccn, metric),
    )

    cur = con.execute(
        "INSERT INTO data_room_entries "
        "(hospital_ccn, metric, value, sample_size, source, analyst, notes, entered_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (hospital_ccn, metric, value, sample_size, source, analyst, notes, now),
    )
    return cur.lastrowid


def get_entries(
    con: sqlite3.Connection,
    hospital_ccn: str,
) -> List[DataRoomEntry]:
    """Get all active (non-superseded) entries for a hospital."""
    _ensure_tables(con)
    rows = con.execute(
        "SELECT id, hospital_ccn, metric, value, sample_size, source, analyst, notes, entered_at "
        "FROM data_room_entries "
        "WHERE hospital_ccn = ? AND superseded_by IS NULL "
        "ORDER BY entered_at DESC",
        (hospital_ccn,),
    ).fetchall()
    return [DataRoomEntry(*r) for r in rows]


def get_latest_values(
    con: sqlite3.Connection,
    hospital_ccn: str,
) -> Dict[str, DataRoomEntry]:
    """Get the latest value for each metric."""
    entries = get_entries(con, hospital_ccn)
    latest: Dict[str, DataRoomEntry] = {}
    for e in entries:
        if e.metric not in latest:
            latest[e.metric] = e
    return latest


def calibrate_metrics(
    con: sqlite3.Connection,
    hospital_ccn: str,
    ml_predictions: Dict[str, float],
    beds: float = 150,
) -> List[CalibratedMetric]:
    """Bayesian calibration: blend seller data with ML predictions.

    For each metric where we have seller data, compute the posterior
    estimate that combines the ML prediction (prior) with seller evidence.
    """
    from ..ml.bayesian_calibration import calibrate_rate_metric, calibrate_continuous_metric

    _ensure_tables(con)
    seller_data = get_latest_values(con, hospital_ccn)
    now = datetime.now(timezone.utc).isoformat()
    results = []

    for metric, defn in _METRIC_DEFINITIONS.items():
        seller_entry = seller_data.get(metric)
        ml_pred = ml_predictions.get(metric)

        if seller_entry is None and ml_pred is None:
            continue

        seller_val = seller_entry.value if seller_entry else None
        seller_n = seller_entry.sample_size if seller_entry else 0
        label = defn["label"]
        direction = defn["direction"]

        if defn["type"] == "rate" and seller_val is not None:
            est = calibrate_rate_metric(metric, seller_val, seller_n, beds=beds)
        elif defn["type"] == "continuous" and seller_val is not None:
            est = calibrate_continuous_metric(metric, seller_val, seller_n, beds=beds)
        else:
            # ML prediction only — use as-is with wide interval
            post = ml_pred or 0
            margin = abs(post) * 0.2 if post else 0.05
            results.append(CalibratedMetric(
                metric=metric, label=label,
                ml_predicted=ml_pred, seller_value=0,
                seller_n=0, bayesian_posterior=post,
                ci_low=post - margin, ci_high=post + margin,
                shrinkage=1.0, data_quality="ml_only",
                delta_from_prediction=None, direction=direction,
            ))
            continue

        delta = None
        if ml_pred is not None and seller_val is not None:
            delta = seller_val - ml_pred

        results.append(CalibratedMetric(
            metric=metric, label=label,
            ml_predicted=ml_pred, seller_value=seller_val,
            seller_n=seller_n, bayesian_posterior=est.posterior_mean,
            ci_low=est.credible_interval_90[0],
            ci_high=est.credible_interval_90[1],
            shrinkage=est.shrinkage_factor,
            data_quality=est.data_quality,
            delta_from_prediction=delta, direction=direction,
        ))

        # Persist calibration
        con.execute(
            "INSERT INTO data_room_calibrations "
            "(hospital_ccn, metric, ml_predicted, seller_value, seller_n, "
            " bayesian_posterior, ci_low, ci_high, shrinkage, data_quality, computed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (hospital_ccn, metric, ml_pred, seller_val, seller_n,
             est.posterior_mean, est.credible_interval_90[0],
             est.credible_interval_90[1], est.shrinkage_factor,
             est.data_quality, now),
        )

    return results


def get_calibrated_profile(
    con: sqlite3.Connection,
    hospital_ccn: str,
    ml_predictions: Dict[str, float],
    beds: float = 150,
) -> Dict[str, Any]:
    """Get a complete calibrated profile merging ML + seller data.

    Returns a dict usable by the EBITDA bridge and IC memo.
    """
    calibrations = calibrate_metrics(con, hospital_ccn, ml_predictions, beds)
    seller_entries = get_latest_values(con, hospital_ccn)

    profile: Dict[str, Any] = {}
    for cal in calibrations:
        profile[cal.metric] = cal.bayesian_posterior
        profile[f"{cal.metric}_source"] = cal.data_quality
        profile[f"{cal.metric}_ci"] = (cal.ci_low, cal.ci_high)
        if cal.delta_from_prediction is not None:
            profile[f"{cal.metric}_delta"] = cal.delta_from_prediction

    profile["_calibrations"] = calibrations
    profile["_n_seller_metrics"] = len(seller_entries)
    profile["_n_ml_only"] = sum(1 for c in calibrations if c.data_quality == "ml_only")

    return profile
