"""Per-note tags (Brick 123).

Deal tags (B86) slice the portfolio; note tags slice the analyst's
written context. Partners asking "show me everything tagged
``board_meeting`` from the last quarter" or "all notes flagged
``blocker``" now have a pivot beyond full-text search.

Reuses the same normalisation rules as :mod:`rcm_mc.deal_tags` so an
analyst's muscle memory carries over (lowercase, alnum + ``._-:``,
max 40 chars, no spaces).

Public API::

    add_note_tag(store, note_id, tag) -> bool
    remove_note_tag(store, note_id, tag) -> bool
    tags_for_note(store, note_id) -> list[str]
    tags_for_notes(store, note_ids) -> dict[int, list[str]]  # bulk
    search_notes_by_tag(store, tag) -> pd.DataFrame
    all_note_tags(store) -> list[(tag, count)]
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .deal_tags import _normalize  # reuse validation
from ..portfolio.store import PortfolioStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS note_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(note_id) REFERENCES deal_notes(note_id)
            )"""
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_note_tags_unique "
            "ON note_tags(note_id, tag)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_note_tags_tag "
            "ON note_tags(tag)"
        )
        con.commit()


def add_note_tag(store: PortfolioStore, note_id: int, tag: str) -> bool:
    """Attach ``tag`` to ``note_id``. Returns True if state changed."""
    tag_n = _normalize(tag)
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO note_tags (note_id, tag, created_at) "
            "VALUES (?, ?, ?)",
            (int(note_id), tag_n, _utcnow()),
        )
        con.commit()
        return cur.rowcount > 0


def remove_note_tag(store: PortfolioStore, note_id: int, tag: str) -> bool:
    """Remove ``tag`` from ``note_id``. Returns True if a row was deleted."""
    tag_n = _normalize(tag)
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM note_tags WHERE note_id = ? AND tag = ?",
            (int(note_id), tag_n),
        )
        con.commit()
        return cur.rowcount > 0


def tags_for_note(store: PortfolioStore, note_id: int) -> List[str]:
    """Tags on one note, alphabetically."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT tag FROM note_tags WHERE note_id = ? ORDER BY tag",
            (int(note_id),),
        ).fetchall()
    return [r["tag"] for r in rows]


def tags_for_notes(
    store: PortfolioStore, note_ids: Iterable[int],
) -> Dict[int, List[str]]:
    """Bulk fetch: ``{note_id: [tag, ...]}`` for the supplied ids."""
    _ensure_table(store)
    ids = [int(i) for i in note_ids]
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    out: Dict[int, List[str]] = {i: [] for i in ids}
    with store.connect() as con:
        for r in con.execute(
            f"SELECT note_id, tag FROM note_tags "
            f"WHERE note_id IN ({placeholders}) ORDER BY tag",
            ids,
        ).fetchall():
            out.setdefault(int(r["note_id"]), []).append(r["tag"])
    return out


def search_notes_by_tag(store: PortfolioStore, tag: str) -> pd.DataFrame:
    """All non-deleted notes carrying ``tag``, newest-first."""
    tag_n = _normalize(tag)
    _ensure_table(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT n.note_id, n.deal_id, n.created_at, n.author, n.body "
            "FROM deal_notes n JOIN note_tags t ON n.note_id = t.note_id "
            "WHERE t.tag = ? AND n.deleted_at IS NULL "
            "ORDER BY n.created_at DESC",
            con, params=(tag_n,),
        )


def all_note_tags(store: PortfolioStore) -> List[Tuple[str, int]]:
    """(tag, count) of every known note tag, most-used first."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT tag, COUNT(*) AS n FROM note_tags "
            "GROUP BY tag ORDER BY n DESC, tag ASC"
        ).fetchall()
    return [(r["tag"], int(r["n"])) for r in rows]
