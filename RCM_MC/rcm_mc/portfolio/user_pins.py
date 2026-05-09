"""User pins — per-user shortcut list of platform routes.

PROMPTS.md Phase 4 / Prompt 48: partners want their five most-used
pages pinned to Home. Each route gets a pin toggle in the page
header; pinning persists to a ``user_pins`` row. Home reads this
table to render the per-user pinned strip.

The shape (user_id, route) is the primary key, so a re-pin is
idempotent. Order is preserved by ``pinned_at`` so the most-recent
pin sorts to the top.

Public API::

    from rcm_mc.portfolio.user_pins import (
        ensure_table, pin, unpin, is_pinned, list_pins,
    )
"""
from __future__ import annotations

from datetime import datetime, timezone

from .store import PortfolioStore


def ensure_table(store: PortfolioStore) -> None:
    with store.connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS user_pins (
                user_id    TEXT NOT NULL,
                route      TEXT NOT NULL,
                label      TEXT NOT NULL,
                pinned_at  TEXT NOT NULL,
                PRIMARY KEY (user_id, route)
            )
            """
        )
        con.commit()


def pin(
    store: PortfolioStore,
    *,
    user_id: str,
    route: str,
    label: str,
) -> None:
    """Insert or update a pin. Re-pinning the same route refreshes
    its ``pinned_at`` so it sorts to the top of the user's strip."""
    if not user_id or not route or not label:
        raise ValueError("user_id, route, and label must be non-empty")
    ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute(
            """
            INSERT INTO user_pins (user_id, route, label, pinned_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, route) DO UPDATE SET
                label     = excluded.label,
                pinned_at = excluded.pinned_at
            """,
            (user_id, route, label, now),
        )
        con.commit()


def unpin(store: PortfolioStore, *, user_id: str, route: str) -> bool:
    """Remove a pin. Returns True if a row was deleted."""
    ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM user_pins WHERE user_id = ? AND route = ?",
            (user_id, route),
        )
        con.commit()
        return cur.rowcount > 0


def is_pinned(store: PortfolioStore, *, user_id: str, route: str) -> bool:
    ensure_table(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT 1 FROM user_pins WHERE user_id = ? AND route = ?",
            (user_id, route),
        ).fetchone()
    return r is not None


def list_pins(store: PortfolioStore, *, user_id: str) -> list[dict]:
    """Return pins for ``user_id`` newest-first."""
    ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT user_id, route, label, pinned_at "
            "FROM user_pins WHERE user_id = ? "
            "ORDER BY pinned_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]
