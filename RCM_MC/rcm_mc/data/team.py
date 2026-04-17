"""Team collaboration — comments, assignments, and activity feed.

Adds collaborative features on top of the existing auth/RBAC system:
- Comments on any entity (hospital, pipeline deal, data room entry)
- Assignment tracking (who owns what)
- Team activity feed (who did what, when)
- Mention notifications (@analyst)

Tables:
- team_comments: threaded comments on any entity
- team_assignments: who is responsible for what
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS team_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tc_entity ON team_comments(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS team_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    assigned_to TEXT NOT NULL,
    assigned_by TEXT DEFAULT '',
    role TEXT DEFAULT 'owner',
    created_at TEXT NOT NULL,
    UNIQUE(entity_type, entity_id, assigned_to)
);
CREATE INDEX IF NOT EXISTS ix_ta_entity ON team_assignments(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_ta_user ON team_assignments(assigned_to);

CREATE TABLE IF NOT EXISTS team_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT DEFAULT '',
    entity_id TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tact_time ON team_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tact_actor ON team_activity(actor);
"""


@dataclass
class Comment:
    id: int
    entity_type: str
    entity_id: str
    author: str
    body: str
    created_at: str


@dataclass
class Assignment:
    entity_type: str
    entity_id: str
    assigned_to: str
    assigned_by: str
    role: str
    created_at: str


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA)


# ── Comments ──

def add_comment(
    con: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    author: str,
    body: str,
) -> int:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    cur = con.execute(
        "INSERT INTO team_comments (entity_type, entity_id, author, body, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_id, author, body, now),
    )
    _log_activity(con, author, "comment", entity_type, entity_id, body[:80])
    return cur.lastrowid


def get_comments(
    con: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    limit: int = 50,
) -> List[Comment]:
    _ensure_tables(con)
    rows = con.execute(
        "SELECT id, entity_type, entity_id, author, body, created_at "
        "FROM team_comments WHERE entity_type = ? AND entity_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (entity_type, entity_id, limit),
    ).fetchall()
    return [Comment(*r) for r in rows]


def count_comments(con: sqlite3.Connection, entity_type: str, entity_id: str) -> int:
    _ensure_tables(con)
    row = con.execute(
        "SELECT COUNT(*) FROM team_comments WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    ).fetchone()
    return row[0] if row else 0


# ── Assignments ──

def assign(
    con: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    assigned_to: str,
    assigned_by: str = "",
    role: str = "owner",
) -> None:
    _ensure_tables(con)
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "INSERT OR REPLACE INTO team_assignments "
        "(entity_type, entity_id, assigned_to, assigned_by, role, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (entity_type, entity_id, assigned_to, assigned_by, role, now),
    )
    _log_activity(con, assigned_by or assigned_to, "assign", entity_type, entity_id,
                   f"→ {assigned_to} ({role})")


def get_assignments(
    con: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
) -> List[Assignment]:
    _ensure_tables(con)
    rows = con.execute(
        "SELECT entity_type, entity_id, assigned_to, assigned_by, role, created_at "
        "FROM team_assignments WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    ).fetchall()
    return [Assignment(*r) for r in rows]


def get_user_assignments(
    con: sqlite3.Connection,
    username: str,
) -> List[Assignment]:
    _ensure_tables(con)
    rows = con.execute(
        "SELECT entity_type, entity_id, assigned_to, assigned_by, role, created_at "
        "FROM team_assignments WHERE assigned_to = ? "
        "ORDER BY created_at DESC",
        (username,),
    ).fetchall()
    return [Assignment(*r) for r in rows]


# ── Activity feed ──

def _log_activity(
    con: sqlite3.Connection,
    actor: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    detail: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "INSERT INTO team_activity (actor, action, entity_type, entity_id, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (actor, action, entity_type, entity_id, detail[:200], now),
    )


def log_activity(
    con: sqlite3.Connection,
    actor: str,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    detail: str = "",
) -> None:
    _ensure_tables(con)
    _log_activity(con, actor, action, entity_type, entity_id, detail)


def get_activity_feed(
    con: sqlite3.Connection,
    limit: int = 30,
    actor: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _ensure_tables(con)
    if actor:
        rows = con.execute(
            "SELECT actor, action, entity_type, entity_id, detail, created_at "
            "FROM team_activity WHERE actor = ? ORDER BY created_at DESC LIMIT ?",
            (actor, limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT actor, action, entity_type, entity_id, detail, created_at "
            "FROM team_activity ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"actor": r[0], "action": r[1], "entity_type": r[2],
         "entity_id": r[3], "detail": r[4], "created_at": r[5]}
        for r in rows
    ]


def get_entity_url(entity_type: str, entity_id: str) -> str:
    """Map entity type + ID to a URL."""
    urls = {
        "hospital": f"/hospital/{entity_id}",
        "pipeline": f"/hospital/{entity_id}",
        "data_room": f"/data-room/{entity_id}",
        "bridge": f"/ebitda-bridge/{entity_id}",
        "memo": f"/ic-memo/{entity_id}",
    }
    return urls.get(entity_type, f"/hospital/{entity_id}")
