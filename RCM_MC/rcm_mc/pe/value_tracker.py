"""Post-close value creation tracker.

When a deal closes, the EBITDA bridge becomes the value creation plan.
Each quarter, actuals are recorded per lever. The system compares
actual vs planned improvement, computes realization rates, detects
ramp deviations, and feeds accuracy data back to the prediction ledger.

This is the feedback loop that makes every closed deal improve the
next underwrite.

Tables:
- value_creation_plans: the frozen EBITDA bridge at close
- value_creation_actuals: quarterly realized impact per lever
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


_SCHEMA = """
CREATE TABLE IF NOT EXISTS value_creation_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    ccn TEXT NOT NULL,
    hospital_name TEXT DEFAULT '',
    plan_json TEXT NOT NULL,
    total_planned_uplift REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(deal_id)
);
CREATE INDEX IF NOT EXISTS ix_vcp_deal ON value_creation_plans(deal_id);

CREATE TABLE IF NOT EXISTS value_creation_actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    quarter TEXT NOT NULL,
    lever TEXT NOT NULL,
    planned_impact REAL DEFAULT 0,
    actual_impact REAL DEFAULT 0,
    realization_pct REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    entered_at TEXT NOT NULL,
    UNIQUE(deal_id, quarter, lever)
);
CREATE INDEX IF NOT EXISTS ix_vca_deal ON value_creation_actuals(deal_id);
CREATE INDEX IF NOT EXISTS ix_vca_quarter ON value_creation_actuals(deal_id, quarter);
"""


@dataclass
class PlanLever:
    name: str
    metric: str
    current: float
    target: float
    planned_annual_impact: float
    ramp_months: int


@dataclass
class LeverActual:
    lever: str
    quarter: str
    planned_impact: float
    actual_impact: float
    realization_pct: float
    notes: str


@dataclass
class ValueTrackingSummary:
    deal_id: str
    hospital_name: str
    total_planned: float
    total_realized: float
    realization_pct: float
    quarters_tracked: int
    levers: List[Dict[str, Any]]
    on_track_count: int
    lagging_count: int
    off_track_count: int
    ramp_assessment: str


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


def freeze_bridge_as_plan(
    con: sqlite3.Connection,
    deal_id: str,
    ccn: str,
    hospital_name: str,
    bridge_result: Dict[str, Any],
) -> int:
    """Freeze the current EBITDA bridge as the value creation plan at close."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    total = bridge_result.get("total_ebitda_impact", 0)
    plan_json = json.dumps(bridge_result)
    cur = con.execute(
        "INSERT OR REPLACE INTO value_creation_plans "
        "(deal_id, ccn, hospital_name, plan_json, total_planned_uplift, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (deal_id, ccn, hospital_name, plan_json, total, now),
    )
    return cur.lastrowid


def get_plan(con: sqlite3.Connection, deal_id: str) -> Optional[Dict[str, Any]]:
    """Get the frozen bridge plan for a deal."""
    _ensure_tables(con)
    row = con.execute(
        "SELECT plan_json, total_planned_uplift, hospital_name, ccn, created_at "
        "FROM value_creation_plans WHERE deal_id = ?",
        (deal_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "plan": json.loads(row[0]),
        "total_planned": row[1],
        "hospital_name": row[2],
        "ccn": row[3],
        "created_at": row[4],
    }


def record_quarterly_lever(
    con: sqlite3.Connection,
    deal_id: str,
    quarter: str,
    lever: str,
    actual_impact: float,
    notes: str = "",
) -> None:
    """Record actual realized impact for one lever in one quarter."""
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()

    # Look up planned impact from the bridge plan
    plan_data = get_plan(con, deal_id)
    planned = 0
    if plan_data:
        plan = plan_data["plan"]
        for lev in plan.get("levers", []):
            if lev.get("name") == lever or lev.get("metric") == lever:
                # Planned impact at this quarter's ramp %
                ramp = lev.get("ramp_months", 12)
                # Parse quarter to months since close (Q1=3, Q2=6, etc.)
                try:
                    q_num = int(quarter[-1]) if quarter[-1].isdigit() else 1
                    year_offset = int(quarter[:4]) - 2026 if len(quarter) >= 4 else 0
                    months = year_offset * 12 + q_num * 3
                except (ValueError, IndexError):
                    months = 3
                ramp_pct = min(1.0, months / ramp) if ramp > 0 else 1.0
                planned = lev.get("ebitda_impact", 0) * ramp_pct / 4  # quarterly
                break

    realization = actual_impact / planned if planned != 0 else 0

    con.execute(
        "INSERT OR REPLACE INTO value_creation_actuals "
        "(deal_id, quarter, lever, planned_impact, actual_impact, realization_pct, notes, entered_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (deal_id, quarter, lever, planned, actual_impact, realization, notes, now),
    )


def get_tracking_summary(
    con: sqlite3.Connection,
    deal_id: str,
) -> Optional[ValueTrackingSummary]:
    """Get the complete value tracking summary for a deal."""
    _ensure_tables(con)
    plan_data = get_plan(con, deal_id)
    if not plan_data:
        return None

    actuals = con.execute(
        "SELECT lever, quarter, planned_impact, actual_impact, realization_pct, notes "
        "FROM value_creation_actuals WHERE deal_id = ? "
        "ORDER BY quarter, lever",
        (deal_id,),
    ).fetchall()

    quarters = sorted(set(r[1] for r in actuals))
    lever_totals: Dict[str, Dict[str, float]] = {}
    for r in actuals:
        lever = r[0]
        if lever not in lever_totals:
            lever_totals[lever] = {"planned": 0, "actual": 0}
        lever_totals[lever]["planned"] += r[2]
        lever_totals[lever]["actual"] += r[3]

    total_planned = sum(v["planned"] for v in lever_totals.values())
    total_realized = sum(v["actual"] for v in lever_totals.values())
    realization = total_realized / total_planned if total_planned != 0 else 0

    on_track = 0
    lagging = 0
    off_track = 0
    lever_details = []
    for lever, vals in lever_totals.items():
        r_pct = vals["actual"] / vals["planned"] if vals["planned"] != 0 else 0
        if r_pct >= 0.85:
            status = "on_track"
            on_track += 1
        elif r_pct >= 0.60:
            status = "lagging"
            lagging += 1
        else:
            status = "off_track"
            off_track += 1
        lever_details.append({
            "lever": lever,
            "planned": vals["planned"],
            "actual": vals["actual"],
            "realization_pct": r_pct,
            "status": status,
        })

    lever_details.sort(key=lambda l: -abs(l["actual"]))

    if realization >= 0.85:
        ramp = "On track — value creation plan is being realized as underwritten"
    elif realization >= 0.60:
        ramp = "Lagging — partial realization, consider accelerating specific levers"
    else:
        ramp = "Off track — significant deviation from plan, intervention required"

    return ValueTrackingSummary(
        deal_id=deal_id,
        hospital_name=plan_data["hospital_name"],
        total_planned=total_planned,
        total_realized=total_realized,
        realization_pct=realization,
        quarters_tracked=len(quarters),
        levers=lever_details,
        on_track_count=on_track,
        lagging_count=lagging,
        off_track_count=off_track,
        ramp_assessment=ramp,
    )


def feed_prediction_ledger(
    con: sqlite3.Connection,
    deal_id: str,
) -> int:
    """Feed realized values back to the prediction ledger for model improvement.

    Returns number of records fed back.
    """
    _ensure_tables(con)
    summary = get_tracking_summary(con, deal_id)
    if not summary:
        return 0

    try:
        from ..ml.prediction_ledger import record_prediction, record_actual, _ensure_tables as _pl_ensure
        _pl_ensure(con)
    except ImportError:
        return 0

    plan_data = get_plan(con, deal_id)
    if not plan_data:
        return 0

    ccn = plan_data.get("ccn", deal_id)
    fed = 0
    for lever in summary.levers:
        if lever["planned"] == 0:
            continue
        pid = record_prediction(
            con, ccn, f"bridge_{lever['lever']}",
            lever["planned"],
            method="ebitda_bridge_plan",
        )
        record_actual(con, pid, lever["actual"], source="quarterly_actuals")
        fed += 1

    return fed
