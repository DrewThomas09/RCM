"""Team @-mentions on entities.

PROMPTS.md Phase 4 / Prompt 59: PE diligence is collaborative; the
platform pretends it isn't. Every page gets a Share button → modal
with the current URL + a list of teammates to @-mention.
@-mentions write rows here; the recipient's notification badge
reads from this table.

Public API::

    from rcm_mc.portfolio.team_mentions import (
        ensure_table, mention, unread_for_user, mark_read,
        list_for_user,
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
            CREATE TABLE IF NOT EXISTS team_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id    TEXT NOT NULL,
                to_user_id      TEXT NOT NULL,
                entity_type     TEXT NOT NULL,
                entity_id       TEXT NOT NULL,
                share_url       TEXT NOT NULL,
                message         TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                read_at         TEXT
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_mentions_recipient "
            "ON team_mentions(to_user_id, read_at)"
        )
        con.commit()


def mention(
    store: PortfolioStore,
    *,
    from_user_id: str,
    to_user_id: str,
    entity_type: str,
    entity_id: str,
    share_url: str,
    message: str = "",
) -> int:
    """Record a mention. Returns the row id."""
    if not from_user_id or not to_user_id:
        raise ValueError("from_user_id and to_user_id must be non-empty")
    if from_user_id == to_user_id:
        raise ValueError("self-mentions are not supported")
    ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        cur = con.execute(
            """
            INSERT INTO team_mentions
                (from_user_id, to_user_id, entity_type, entity_id,
                 share_url, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (from_user_id, to_user_id, entity_type, entity_id,
             share_url, message, now),
        )
        con.commit()
        return cur.lastrowid or 0


def unread_for_user(
    store: PortfolioStore, *, user_id: str,
) -> int:
    ensure_table(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT COUNT(*) FROM team_mentions "
            "WHERE to_user_id = ? AND read_at IS NULL",
            (user_id,),
        ).fetchone()
    return int(r[0]) if r else 0


def list_for_user(
    store: PortfolioStore,
    *,
    user_id: str,
    only_unread: bool = False,
    limit: int = 50,
) -> list[dict]:
    ensure_table(store)
    sql = (
        "SELECT id, from_user_id, entity_type, entity_id, "
        "share_url, message, created_at, read_at "
        "FROM team_mentions WHERE to_user_id = ?"
    )
    params: list[object] = [user_id]
    if only_unread:
        sql += " AND read_at IS NULL"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def mark_read(
    store: PortfolioStore,
    *,
    user_id: str,
    mention_id: Optional[int] = None,
) -> int:
    """Mark mentions read. When ``mention_id`` is provided only that
    row flips; otherwise every unread mention for the user clears.
    Returns the number of rows updated."""
    ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        if mention_id is None:
            cur = con.execute(
                "UPDATE team_mentions SET read_at = ? "
                "WHERE to_user_id = ? AND read_at IS NULL",
                (now, user_id),
            )
        else:
            cur = con.execute(
                "UPDATE team_mentions SET read_at = ? "
                "WHERE id = ? AND to_user_id = ? AND read_at IS NULL",
                (now, int(mention_id), user_id),
            )
        con.commit()
        return cur.rowcount
