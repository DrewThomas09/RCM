"""Per-user-per-route preference storage.

PROMPTS.md Phase 4 / Prompt 52: every page resets to platform
defaults — partners' last sort order on Library, their preferred
filters on Hospital Screener, their last form values on Bridge
Audit are all forgotten on the next visit. This module persists
small string-keyed preferences keyed by ``(user_id, route, key)``
so pages can read on render and write on change.

This sits alongside ``saved_views`` (named filter snapshots) and
``user_pins`` (pinned routes); together they form the user's
memory layer.

Public API::

    from rcm_mc.portfolio.user_preferences import (
        ensure_table, get_pref, set_pref, delete_pref, list_prefs,
    )
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .store import PortfolioStore


def ensure_table(store: PortfolioStore) -> None:
    with store.connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id    TEXT NOT NULL,
                route      TEXT NOT NULL,
                pref_key   TEXT NOT NULL,
                pref_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, route, pref_key)
            )
            """
        )
        con.commit()


def set_pref(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    key: str,
    value: str,
) -> None:
    if not user_id or not route or not key:
        raise ValueError("user_id, route, key must be non-empty")
    ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute(
            """
            INSERT INTO user_preferences
                (user_id, route, pref_key, pref_value, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (user_id, route, pref_key) DO UPDATE SET
                pref_value = excluded.pref_value,
                updated_at = excluded.updated_at
            """,
            (user_id, route, key, value, now),
        )
        con.commit()


def get_pref(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    ensure_table(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT pref_value FROM user_preferences "
            "WHERE user_id = ? AND route = ? AND pref_key = ?",
            (user_id, route, key),
        ).fetchone()
    return r[0] if r else default


def delete_pref(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    key: str,
) -> bool:
    ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM user_preferences "
            "WHERE user_id = ? AND route = ? AND pref_key = ?",
            (user_id, route, key),
        )
        con.commit()
        return cur.rowcount > 0


def list_prefs(
    store: PortfolioStore,
    *,
    user_id: str,
    route: Optional[str] = None,
) -> list[dict]:
    """Return all prefs for a user, optionally scoped to a route."""
    ensure_table(store)
    sql = (
        "SELECT user_id, route, pref_key, pref_value, updated_at "
        "FROM user_preferences WHERE user_id = ?"
    )
    params: list[object] = [user_id]
    if route is not None:
        sql += " AND route = ?"
        params.append(route)
    sql += " ORDER BY route, pref_key"
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
