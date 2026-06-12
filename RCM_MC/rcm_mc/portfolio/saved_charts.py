"""Saved charts — owner-scoped persistence for Chart Builder / Exhibit
configurations.

A configured chart IS its URL query string (type + data + shaping +
annotations all live in qs — the same property saved_screens exploits
for the Target Screener), so persisting a named chart is persisting a
route + query string per owner. The library page relists them as
one-click reopens; nothing is re-rendered at save time.

Additive, new-table only (``CREATE TABLE IF NOT EXISTS`` — no-op on
existing DBs). Mirrors the saved_screens store pattern: parameterised
SQL only, ``BEGIN IMMEDIATE`` around check-then-write, owner-scoped
reads and deletes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .store import PortfolioStore

# Only the two qs-driven chart surfaces are reopenable from the
# library; anything else is a programming error or a forged form.
ALLOWED_ROUTES = ("/chart-builder", "/exhibit")


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS saved_charts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                title TEXT NOT NULL,
                route TEXT NOT NULL,
                query_params TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


def save_chart(store: PortfolioStore, owner: str, title: str,
               route: str, query_params: str) -> int:
    """Persist a named chart for ``owner``; returns the new row id.

    Inputs are trimmed/capped defensively; an empty owner or title or a
    route outside ALLOWED_ROUTES is rejected (ValueError) so the
    library never lists an orphaned or non-reopenable row. The data
    payload cap (8000) is larger than saved_screens' because a pasted
    table rides in the qs."""
    owner = (owner or "").strip()
    title = (title or "").strip()[:160]
    route = (route or "").strip()
    query_params = (query_params or "").strip().lstrip("?")[:8000]
    if not owner or not title:
        raise ValueError("saved chart requires a non-empty owner and title")
    if route not in ALLOWED_ROUTES:
        raise ValueError(f"saved chart route must be one of "
                         f"{ALLOWED_ROUTES}")
    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO saved_charts "
            "(owner, title, route, query_params, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (owner, title, route, query_params, now),
        )
        con.commit()
        return int(cur.lastrowid)


def list_charts(store: PortfolioStore, owner: str) -> List[Dict[str, Any]]:
    """All saved charts for ``owner``, newest first."""
    owner = (owner or "").strip()
    if not owner:
        return []
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT id, title, route, query_params, created_at "
            "FROM saved_charts WHERE owner = ? "
            "ORDER BY created_at DESC, id DESC",
            (owner,),
        ).fetchall()
    return [
        {"id": int(r[0]), "title": str(r[1]), "route": str(r[2]),
         "query_params": str(r[3]), "created_at": str(r[4])}
        for r in rows
    ]


def delete_chart(store: PortfolioStore, owner: str, chart_id: int) -> bool:
    """Delete one of ``owner``'s charts; True when a row went away.
    Owner-scoped in the WHERE clause so one user can never delete
    another's chart by guessing ids."""
    owner = (owner or "").strip()
    if not owner or not chart_id:
        return False
    _ensure_table(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM saved_charts WHERE id = ? AND owner = ?",
            (int(chart_id), owner),
        )
        con.commit()
        return cur.rowcount > 0
