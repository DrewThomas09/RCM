"""Saved views — partner-defined named filter snapshots.

PROMPTS.md Phase 4 / Prompt 47: partners re-enter the same filter
combinations daily. This module persists named (user, route, name)
→ query-string snapshots so a "Saved views" dropdown can restore a
named filter on any list page.

Public API::

    from rcm_mc.portfolio.saved_views import (
        ensure_table, save_view, list_views, get_view, delete_view,
    )

The table key is (``user_id``, ``route``, ``name``). The same name
under a different route is a separate row — partners can keep a
"My Florida deals" view scoped per page.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .store import PortfolioStore


def ensure_table(store: PortfolioStore) -> None:
    """Create ``user_saved_views`` if it doesn't exist. Idempotent.

    Schema is intentionally simple — query_string is stored verbatim
    so callers don't have to round-trip through a parsed-form layer
    when restoring.
    """
    with store.connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS user_saved_views (
                user_id      TEXT NOT NULL,
                route        TEXT NOT NULL,
                name         TEXT NOT NULL,
                query_string TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                PRIMARY KEY (user_id, route, name)
            )
            """
        )
        con.commit()


def save_view(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    name: str,
    query_string: str,
) -> None:
    """Insert or replace a saved view. Empty name is rejected."""
    if not name.strip():
        raise ValueError("name must be non-empty")
    if not user_id.strip():
        raise ValueError("user_id must be non-empty")
    ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute(
            """
            INSERT INTO user_saved_views
                (user_id, route, name, query_string, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (user_id, route, name) DO UPDATE SET
                query_string = excluded.query_string,
                created_at   = excluded.created_at
            """,
            (user_id, route, name.strip(), query_string, now),
        )
        con.commit()


def list_views(
    store: PortfolioStore,
    *,
    user_id: str,
    route: Optional[str] = None,
) -> list[dict]:
    """Return saved views for ``user_id``, optionally scoped to a
    route. Newest first."""
    ensure_table(store)
    sql = (
        "SELECT user_id, route, name, query_string, created_at "
        "FROM user_saved_views WHERE user_id = ?"
    )
    params: list[object] = [user_id]
    if route is not None:
        sql += " AND route = ?"
        params.append(route)
    sql += " ORDER BY created_at DESC"
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_view(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    name: str,
) -> Optional[dict]:
    """Return one saved view, or None if not found."""
    ensure_table(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT user_id, route, name, query_string, created_at "
            "FROM user_saved_views "
            "WHERE user_id = ? AND route = ? AND name = ?",
            (user_id, route, name),
        ).fetchone()
    return dict(r) if r else None


def delete_view(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    name: str,
) -> bool:
    """Delete a saved view. Returns True if a row was removed."""
    ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM user_saved_views "
            "WHERE user_id = ? AND route = ? AND name = ?",
            (user_id, route, name),
        )
        con.commit()
        return cur.rowcount > 0
