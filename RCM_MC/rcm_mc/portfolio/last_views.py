"""Per-user-per-entity last-viewed tracking.

PROMPTS.md Phase 4 / Prompt 51: each entity page (deal, portfolio,
diligence module) shows "Since you last looked (N days ago):" so a
partner returning to a deal can see what's changed without
re-reading every section.

The storage shape is the bare minimum needed to compute that diff:
``(user_id, entity_type, entity_id) → last_viewed_at``. The page
fetches the previous timestamp BEFORE calling ``mark_viewed`` so it
can run a "give me everything since X" query against audit events,
alerts, runs, etc. ``mark_viewed`` returns the previous value as a
convenience for the common "fetch + update" sequence.

Public API::

    from rcm_mc.portfolio.last_views import (
        ensure_table, mark_viewed, previous_view,
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
            CREATE TABLE IF NOT EXISTS user_last_views (
                user_id        TEXT NOT NULL,
                entity_type    TEXT NOT NULL,
                entity_id      TEXT NOT NULL,
                last_viewed_at TEXT NOT NULL,
                PRIMARY KEY (user_id, entity_type, entity_id)
            )
            """
        )
        con.commit()


def previous_view(
    store: PortfolioStore,
    *,
    user_id: str,
    entity_type: str,
    entity_id: str,
) -> Optional[str]:
    """Return the last_viewed_at ISO timestamp, or None if the user
    has never viewed this entity."""
    ensure_table(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT last_viewed_at FROM user_last_views "
            "WHERE user_id = ? AND entity_type = ? AND entity_id = ?",
            (user_id, entity_type, entity_id),
        ).fetchone()
    return r[0] if r else None


def recent_deals(
    store: PortfolioStore,
    *,
    user_id: str,
    limit: int = 10,
) -> list[dict]:
    """Return the user's most-recently-viewed deals, newest first.

    P53: Home renders this as a horizontal scroll of small deal
    cards so partners pick up where they left off. Derived from the
    same ``user_last_views`` table mark_viewed writes to — no
    separate "recents" log to keep in sync.
    """
    if limit <= 0:
        return []
    ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT entity_id, last_viewed_at FROM user_last_views "
            "WHERE user_id = ? AND entity_type = 'deal' "
            "ORDER BY last_viewed_at DESC LIMIT ?",
            (user_id, int(limit)),
        ).fetchall()
    return [
        {"deal_id": r[0], "last_viewed_at": r[1]} for r in rows
    ]


def mark_viewed(
    store: PortfolioStore,
    *,
    user_id: str,
    entity_type: str,
    entity_id: str,
) -> Optional[str]:
    """Record that ``user_id`` viewed this entity now. Returns the
    PREVIOUS last_viewed_at timestamp (or None if first view) — the
    caller uses that to render the "since you last looked" rail."""
    ensure_table(store)
    prev = previous_view(
        store, user_id=user_id,
        entity_type=entity_type, entity_id=entity_id,
    )
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute(
            """
            INSERT INTO user_last_views
                (user_id, entity_type, entity_id, last_viewed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, entity_type, entity_id) DO UPDATE SET
                last_viewed_at = excluded.last_viewed_at
            """,
            (user_id, entity_type, entity_id, now),
        )
        con.commit()
    return prev
