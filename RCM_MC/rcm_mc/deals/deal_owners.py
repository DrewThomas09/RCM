"""Deal ownership / assignee tracking (Brick 113).

Partners triaging a covenant trip need to know who to call. Tags
(``owner:AT``) approximated this, but weren't first-class: no
dashboard filter, no audit of reassignments, no "my deals" view.

This module stores a single current owner per deal plus an append-only
history so a future "who reassigned this on Tuesday" question has an
answer.

Public API::

    assign_owner(store, deal_id, owner, note="") -> int  # history row id
    current_owner(store, deal_id) -> str | None
    owner_history(store, deal_id) -> pd.DataFrame
    deals_by_owner(store, owner) -> list[str]
    all_owners(store) -> list[(owner, count)]
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import pandas as pd

from ..portfolio.store import PortfolioStore


# Keep owner strings narrow: alnum + common separators. Rejects spaces so
# IDs stay Slack-linkable.
_OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,39}$")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(owner: str) -> str:
    if owner is None:
        raise ValueError("owner cannot be None")
    o = str(owner).strip()
    if not o:
        raise ValueError("owner cannot be empty")
    if not _OWNER_RE.match(o):
        raise ValueError(
            f"invalid owner {owner!r}: alnum plus . _ - @, max 40 chars, "
            "no spaces"
        )
    return o


def _ensure_owners_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            # Report 0256 MR1057: add deal_id FK so owner-history is
            # cleared when its parent deal is deleted. New DBs only
            # (CREATE TABLE IF NOT EXISTS no-op on existing schemas).
            """CREATE TABLE IF NOT EXISTS deal_owner_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_owner_deal "
            "ON deal_owner_history(deal_id, assigned_at DESC)"
        )
        con.commit()


def assign_owner(
    store: PortfolioStore,
    *,
    deal_id: str,
    owner: str,
    note: str = "",
) -> int:
    """Set ``deal_id``'s owner. Returns the new history row id.

    Always appends — even reassigning to the same owner. Callers can
    dedupe if they care; the audit trail should faithfully reflect
    what partners asserted.
    """
    owner_n = _normalize(owner)
    _ensure_owners_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO deal_owner_history "
            "(deal_id, owner, assigned_at, note) VALUES (?, ?, ?, ?)",
            (deal_id, owner_n, _utcnow(), note or ""),
        )
        con.commit()
        return int(cur.lastrowid)


def current_owner(store: PortfolioStore, deal_id: str) -> Optional[str]:
    """Most-recently-assigned owner for a deal, or None."""
    _ensure_owners_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT owner FROM deal_owner_history "
            "WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
            (deal_id,),
        ).fetchone()
    return row["owner"] if row else None


def owner_history(store: PortfolioStore, deal_id: str) -> pd.DataFrame:
    """All historical assignments for a deal, newest first."""
    _ensure_owners_table(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT id, deal_id, owner, assigned_at, note "
            "FROM deal_owner_history WHERE deal_id = ? "
            "ORDER BY id DESC",
            con, params=(deal_id,),
        )


def deals_by_owner(store: PortfolioStore, owner: str) -> List[str]:
    """All deals whose *current* owner is ``owner``."""
    owner_n = _normalize(owner)
    _ensure_owners_table(store)
    with store.connect() as con:
        rows = con.execute(
            """SELECT deal_id FROM deal_owner_history h1
               WHERE owner = ?
                 AND id = (
                     SELECT MAX(id) FROM deal_owner_history h2
                     WHERE h2.deal_id = h1.deal_id
                 )
               ORDER BY deal_id""",
            (owner_n,),
        ).fetchall()
    return [r["deal_id"] for r in rows]


def all_owners(store: PortfolioStore) -> List[Tuple[str, int]]:
    """(owner, deal_count) for everyone currently assigned to ≥1 deal."""
    _ensure_owners_table(store)
    with store.connect() as con:
        rows = con.execute(
            """SELECT owner, COUNT(*) AS n FROM (
                 SELECT deal_id, owner FROM deal_owner_history h1
                 WHERE id = (
                     SELECT MAX(id) FROM deal_owner_history h2
                     WHERE h2.deal_id = h1.deal_id
                 )
               ) GROUP BY owner ORDER BY n DESC, owner ASC"""
        ).fetchall()
    return [(r["owner"], int(r["n"])) for r in rows]
