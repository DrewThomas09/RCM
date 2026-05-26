"""Saved Target-Screener screens — owner-scoped, query-param persistence.

A saved screen is just a Target Screener URL's query string (the screen IS
its params — see docs/TARGET_SCREENER_WORKBENCH.md). This module persists a
named screen per owner so the workbench's Saved-screens tab can list real
saved searches instead of only shareable links.

Additive, new-table only (``CREATE TABLE IF NOT EXISTS`` — no-op on existing
DBs, never a destructive migration). Mirrors the watchlist/notes store
pattern: parameterised SQL only, ``BEGIN IMMEDIATE`` around check-then-write.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .store import PortfolioStore


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS saved_screens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                title TEXT NOT NULL,
                query_params TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


def save_screen(store: PortfolioStore, owner: str, title: str,
                query_params: str) -> int:
    """Persist a named screen for ``owner``; returns the new row id.

    ``title`` and ``query_params`` are trimmed/capped defensively; an empty
    owner or title is rejected (raises ValueError) so we never store an
    orphaned or unlabeled screen.
    """
    owner = (owner or "").strip()
    title = (title or "").strip()[:160]
    query_params = (query_params or "").strip().lstrip("?")[:2000]
    if not owner or not title:
        raise ValueError("saved screen requires a non-empty owner and title")
    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO saved_screens (owner, title, query_params, created_at) "
            "VALUES (?, ?, ?, ?)",
            (owner, title, query_params, now),
        )
        con.commit()
        return int(cur.lastrowid)


def list_screens(store: PortfolioStore, owner: str) -> List[Dict[str, Any]]:
    """All saved screens for ``owner``, newest first."""
    owner = (owner or "").strip()
    if not owner:
        return []
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT id, title, query_params, created_at FROM saved_screens "
            "WHERE owner = ? ORDER BY created_at DESC, id DESC",
            (owner,),
        ).fetchall()
    return [
        {"id": int(r[0]), "title": str(r[1]), "query_params": str(r[2]),
         "created_at": str(r[3])}
        for r in rows
    ]


def delete_screen(store: PortfolioStore, owner: str, screen_id: int) -> bool:
    """Delete one of ``owner``'s screens by id. Owner-scoped so a user can
    only delete their own. Returns True if a row was removed."""
    owner = (owner or "").strip()
    if not owner:
        return False
    _ensure_table(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM saved_screens WHERE id = ? AND owner = ?",
            (int(screen_id), owner),
        )
        con.commit()
        return cur.rowcount > 0
