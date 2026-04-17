"""Unified audit log (Brick 133).

Per-operation tables (acks, owner_history, etc.) capture domain state
— but answering "show me everything AT did Monday" required querying
each one. This module adds a single append-only ``audit_events``
table the server writes to from every sensitive handler, giving
compliance / ops a single pane of glass.

Append-only by design: audit rows are never updated or deleted in
normal operation. A bug in a handler should never silently mutate
history.

Public API::

    log_event(store, *, actor, action, target, detail=None) -> int
    list_events(store, *, since=None, actor=None, action=None,
                limit=200) -> pd.DataFrame
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL DEFAULT '',
                detail_json TEXT NOT NULL DEFAULT '{}',
                request_id TEXT
            )"""
        )
        # Prompt 21: migrate older DBs that predate ``request_id``. The
        # column ship-date is recent, so we only need one idempotent
        # ALTER — catch-and-swallow because adding an existing column
        # is a hard error, not a soft one.
        try:
            cols = [
                r["name"] for r in con.execute(
                    "PRAGMA table_info(audit_events)"
                ).fetchall()
            ]
            if "request_id" not in cols:
                con.execute(
                    "ALTER TABLE audit_events ADD COLUMN request_id TEXT"
                )
        except Exception:  # noqa: BLE001 — best-effort migration
            pass
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_events_at "
            "ON audit_events(at DESC)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_events_actor "
            "ON audit_events(actor, at DESC)"
        )
        con.commit()


def log_event(
    store: PortfolioStore,
    *,
    actor: str,
    action: str,
    target: str = "",
    detail: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> int:
    """Append one event. Never raises on missing tables.

    ``request_id`` (Prompt 21) correlates the audit row back to the
    HTTP access-log JSON line so ops can trace a sensitive action to
    the exact request that caused it.
    """
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO audit_events "
            "(at, actor, action, target, detail_json, request_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                _iso(_utcnow()),
                str(actor or "system"),
                str(action),
                str(target or ""),
                json.dumps(detail or {}, default=str),
                request_id,
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_events(
    store: PortfolioStore,
    *,
    since: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> pd.DataFrame:
    """Recent audit events, newest-first.

    Filters (all optional): ``since`` ISO timestamp, exact ``actor``,
    exact ``action``. Returns columns ``id, at, actor, action, target,
    detail`` (detail parsed back to dict).

    B159 fix: ``offset`` supports pagination past the ``limit`` cap so
    compliance tooling can page through long audit histories.
    """
    _ensure_table(store)
    where = []
    params: list = []
    if since:
        where.append("at >= ?")
        params.append(since)
    if actor:
        where.append("actor = ?")
        params.append(actor)
    if action:
        where.append("action = ?")
        params.append(action)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with store.connect() as con:
        rows = con.execute(
            f"SELECT id, at, actor, action, target, detail_json "
            f"FROM audit_events {where_sql} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [int(limit), max(int(offset), 0)],
        ).fetchall()
    out = []
    for r in rows:
        detail: Dict[str, Any] = {}
        try:
            detail = json.loads(r["detail_json"] or "{}")
        except (ValueError, TypeError):
            detail = {}
        out.append({
            "id": r["id"], "at": r["at"], "actor": r["actor"],
            "action": r["action"], "target": r["target"],
            "detail": detail,
        })
    return pd.DataFrame(out)


def cleanup_old_events(
    store: PortfolioStore,
    *,
    retention_days: int = 365,
) -> int:
    """Delete audit events older than ``retention_days``.

    Returns the number of rows removed. Intended to be called from
    a maintenance cron or on server startup to bound table growth.
    """
    _ensure_table(store)
    from datetime import timedelta
    cutoff = _iso(_utcnow() - timedelta(days=retention_days))
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM audit_events WHERE at < ?", (cutoff,),
        )
        con.commit()
        return cur.rowcount


def event_count(store: PortfolioStore) -> int:
    """Total number of audit events (for monitoring)."""
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute("SELECT COUNT(*) AS cnt FROM audit_events").fetchone()
    return int(row["cnt"]) if row else 0
