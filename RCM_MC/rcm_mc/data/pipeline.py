"""Deal pipeline — saved searches and hospital tracking through deal stages.

Converts SeekingChartis from a screening tool into a workflow platform.
Analysts save screener filters, track hospitals through pipeline stages,
and get notified when new hospitals match saved searches.

Tables:
- saved_searches: named filter sets with last-run stats
- pipeline_hospitals: hospitals being tracked with stage + notes
- pipeline_activity: timestamped log of stage changes
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    filters_json TEXT NOT NULL,
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    last_run_at TEXT,
    last_result_count INTEGER DEFAULT 0,
    pinned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pipeline_hospitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ccn TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    state TEXT DEFAULT '',
    beds INTEGER DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'screening',
    priority TEXT DEFAULT 'medium',
    assigned_to TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    added_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(ccn)
);
CREATE INDEX IF NOT EXISTS ix_ph_stage ON pipeline_hospitals(stage);

CREATE TABLE IF NOT EXISTS pipeline_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ccn TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pa_ccn ON pipeline_activity(ccn);
"""

PIPELINE_STAGES = [
    ("screening", "Screening", "Identified as potential target"),
    ("outreach", "Outreach", "Initial contact / management meeting"),
    ("loi", "LOI", "Letter of intent submitted"),
    ("diligence", "Diligence", "Active due diligence"),
    ("ic", "IC Review", "Investment committee review"),
    ("closed", "Closed", "Deal closed — moved to portfolio"),
    ("passed", "Passed", "Decided not to pursue"),
]

PRIORITIES = ["high", "medium", "low"]


@dataclass
class SavedSearch:
    id: int
    name: str
    filters: Dict[str, Any]
    created_by: str
    created_at: str
    last_run_at: Optional[str]
    last_result_count: int
    pinned: bool


@dataclass
class PipelineHospital:
    id: int
    ccn: str
    hospital_name: str
    state: str
    beds: int
    stage: str
    priority: str
    assigned_to: str
    notes: str
    added_at: str
    updated_at: str


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


# ── Saved searches ──

def save_search(
    con: sqlite3.Connection,
    name: str,
    filters: Dict[str, Any],
    created_by: str = "",
) -> int:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    cur = con.execute(
        "INSERT INTO saved_searches (name, filters_json, created_by, created_at) "
        "VALUES (?, ?, ?, ?)",
        (name, json.dumps(filters), created_by, now),
    )
    return cur.lastrowid


def list_searches(con: sqlite3.Connection) -> List[SavedSearch]:
    _ensure_tables(con)
    rows = con.execute(
        "SELECT id, name, filters_json, created_by, created_at, "
        "last_run_at, last_result_count, pinned "
        "FROM saved_searches ORDER BY pinned DESC, created_at DESC"
    ).fetchall()
    return [
        SavedSearch(
            id=r[0], name=r[1], filters=json.loads(r[2] or "{}"),
            created_by=r[3], created_at=r[4],
            last_run_at=r[5], last_result_count=r[6], pinned=bool(r[7]),
        ) for r in rows
    ]


def update_search_stats(
    con: sqlite3.Connection,
    search_id: int,
    result_count: int,
) -> None:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "UPDATE saved_searches SET last_run_at = ?, last_result_count = ? WHERE id = ?",
        (now, result_count, search_id),
    )


def delete_search(con: sqlite3.Connection, search_id: int) -> None:
    _ensure_tables(con)
    con.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))


# ── Pipeline ──

def add_to_pipeline(
    con: sqlite3.Connection,
    ccn: str,
    hospital_name: str,
    state: str = "",
    beds: int = 0,
    stage: str = "screening",
    priority: str = "medium",
    assigned_to: str = "",
    notes: str = "",
) -> int:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    cur = con.execute(
        "INSERT OR REPLACE INTO pipeline_hospitals "
        "(ccn, hospital_name, state, beds, stage, priority, assigned_to, notes, added_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ccn, hospital_name, state, beds, stage, priority, assigned_to, notes, now, now),
    )
    con.execute(
        "INSERT INTO pipeline_activity (ccn, action, new_value, actor, created_at) "
        "VALUES (?, 'added', ?, ?, ?)",
        (ccn, stage, assigned_to, now),
    )
    return cur.lastrowid


def update_stage(
    con: sqlite3.Connection,
    ccn: str,
    new_stage: str,
    actor: str = "",
) -> None:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    row = con.execute(
        "SELECT stage FROM pipeline_hospitals WHERE ccn = ?", (ccn,)
    ).fetchone()
    old_stage = row[0] if row else ""
    con.execute(
        "UPDATE pipeline_hospitals SET stage = ?, updated_at = ? WHERE ccn = ?",
        (new_stage, now, ccn),
    )
    con.execute(
        "INSERT INTO pipeline_activity (ccn, action, old_value, new_value, actor, created_at) "
        "VALUES (?, 'stage_change', ?, ?, ?, ?)",
        (ccn, old_stage, new_stage, actor, now),
    )


def update_priority(con: sqlite3.Connection, ccn: str, priority: str) -> None:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "UPDATE pipeline_hospitals SET priority = ?, updated_at = ? WHERE ccn = ?",
        (priority, now, ccn),
    )


def remove_from_pipeline(con: sqlite3.Connection, ccn: str) -> None:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute("DELETE FROM pipeline_hospitals WHERE ccn = ?", (ccn,))
    con.execute(
        "INSERT INTO pipeline_activity (ccn, action, actor, created_at) "
        "VALUES (?, 'removed', '', ?)",
        (ccn, now),
    )


def list_pipeline(
    con: sqlite3.Connection,
    stage: Optional[str] = None,
) -> List[PipelineHospital]:
    _ensure_tables(con)
    if stage:
        rows = con.execute(
            "SELECT id, ccn, hospital_name, state, beds, stage, priority, "
            "assigned_to, notes, added_at, updated_at "
            "FROM pipeline_hospitals WHERE stage = ? "
            "ORDER BY priority ASC, updated_at DESC",
            (stage,),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT id, ccn, hospital_name, state, beds, stage, priority, "
            "assigned_to, notes, added_at, updated_at "
            "FROM pipeline_hospitals "
            "ORDER BY stage ASC, priority ASC, updated_at DESC"
        ).fetchall()
    return [PipelineHospital(*r) for r in rows]


def pipeline_summary(con: sqlite3.Connection) -> Dict[str, int]:
    _ensure_tables(con)
    rows = con.execute(
        "SELECT stage, COUNT(*) FROM pipeline_hospitals GROUP BY stage"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def get_activity(
    con: sqlite3.Connection,
    ccn: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    _ensure_tables(con)
    if ccn:
        rows = con.execute(
            "SELECT ccn, action, old_value, new_value, actor, created_at "
            "FROM pipeline_activity WHERE ccn = ? ORDER BY created_at DESC LIMIT ?",
            (ccn, limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT ccn, action, old_value, new_value, actor, created_at "
            "FROM pipeline_activity ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"ccn": r[0], "action": r[1], "old_value": r[2],
         "new_value": r[3], "actor": r[4], "created_at": r[5]}
        for r in rows
    ]


def is_in_pipeline(con: sqlite3.Connection, ccn: str) -> Optional[str]:
    """Returns stage if in pipeline, None otherwise."""
    _ensure_tables(con)
    row = con.execute(
        "SELECT stage FROM pipeline_hospitals WHERE ccn = ?", (ccn,)
    ).fetchone()
    return row[0] if row else None
