"""Schema migration registry.

Collects all ALTER TABLE / CREATE INDEX migrations in one place
with idempotent execution. Each migration runs inside a try/except
so already-applied changes are silently skipped (SQLite's ALTER TABLE
raises if the column already exists).

Call ``run_pending(store)`` on server startup or store init to ensure
all migrations are applied.
"""
from __future__ import annotations

import logging
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

_MIGRATIONS: List[Tuple[str, str]] = [
    ("deals_archived_at",
     "ALTER TABLE deals ADD COLUMN archived_at TEXT"),
    ("audit_events_request_id",
     "ALTER TABLE audit_events ADD COLUMN request_id TEXT"),
    ("deal_notes_deleted_at",
     "ALTER TABLE deal_notes ADD COLUMN deleted_at TEXT"),
    ("deal_deadlines_owner",
     "ALTER TABLE deal_deadlines ADD COLUMN owner TEXT NOT NULL DEFAULT ''"),
]


def run_pending(store: Any) -> int:
    """Execute all pending migrations. Returns count applied."""
    store.init_db()
    applied = 0
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        con.commit()
        for name, sql in _MIGRATIONS:
            row = con.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (name,),
            ).fetchone()
            if row:
                continue
            from datetime import datetime, timezone
            try:
                con.execute(sql)
                con.commit()
                logger.info("migration applied: %s", name)
            except Exception:
                pass
            con.execute(
                "INSERT OR IGNORE INTO _migrations (name, applied_at) VALUES (?, ?)",
                (name, datetime.now(timezone.utc).isoformat()),
            )
            con.commit()
            applied += 1
    return applied


def list_applied(store: Any) -> List[str]:
    """Return names of already-applied migrations."""
    store.init_db()
    try:
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS _migrations "
                "(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            rows = con.execute(
                "SELECT name FROM _migrations ORDER BY name"
            ).fetchall()
        return [r["name"] for r in rows]
    except Exception:
        return []
