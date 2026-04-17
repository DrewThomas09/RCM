"""Benchmark evolution tracker (Prompt 55).

Industry benchmarks shift year-over-year. Tracks snapshots and
detects when the P50 has drifted >1pp — so re-marks use current
industry context, not stale numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkDrift:
    metric_key: str
    current_p50: float
    prior_p50: float
    drift_pp: float
    direction: str          # "industry_improving" | "industry_declining" | "stable"
    adjusted_target: Optional[float] = None
    period: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "current_p50": self.current_p50,
            "prior_p50": self.prior_p50,
            "drift_pp": self.drift_pp,
            "direction": self.direction,
            "adjusted_target": self.adjusted_target,
            "period": self.period,
        }


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS benchmark_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_key TEXT NOT NULL,
                p50 REAL NOT NULL,
                period TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                UNIQUE(metric_key, period)
            )"""
        )
        con.commit()


def save_snapshot(store: Any, metric_key: str, p50: float, period: str) -> None:
    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO benchmark_snapshots "
            "(metric_key, p50, period, captured_at) VALUES (?, ?, ?, ?)",
            (metric_key, float(p50), period, now),
        )
        con.commit()


def detect_benchmark_drift(
    metric_key: str, store: Any,
) -> Optional[BenchmarkDrift]:
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT p50, period FROM benchmark_snapshots "
            "WHERE metric_key = ? ORDER BY period DESC LIMIT 2",
            (metric_key,),
        ).fetchall()
    if len(rows) < 2:
        return None
    current_p50 = float(rows[0]["p50"])
    prior_p50 = float(rows[1]["p50"])
    drift = current_p50 - prior_p50
    if abs(drift) < 1.0:
        return None
    direction = "stable"
    # For most RCM metrics, lower P50 = industry improving.
    if drift < -1.0:
        direction = "industry_improving"
    elif drift > 1.0:
        direction = "industry_declining"
    return BenchmarkDrift(
        metric_key=metric_key,
        current_p50=current_p50,
        prior_p50=prior_p50,
        drift_pp=drift,
        direction=direction,
        period=rows[0]["period"],
    )
