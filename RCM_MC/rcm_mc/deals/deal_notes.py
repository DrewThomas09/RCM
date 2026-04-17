"""Per-deal notes (Brick 71).

PE analysts take running notes on calls, management commentary, pending
data asks, and board decisions. Without a durable place to park them
they live in Slack threads or loose Evernote pages — disconnected from
the deal data they describe. This module stores notes in the same
SQLite portfolio store so they're co-located with snapshots, actuals,
and initiative attribution.

Design:
- Append-only. Notes are an audit trail, not editable blobs. Corrections
  = write a new note referencing the prior one.
- Freeform body. No tag taxonomy; the text itself is the content.
- Optional ``author`` field. No auth (yet — Brick 75 will add it), so
  the UI asks who's writing and stamps the field for provenance.
- Timestamp from insert (UTC ISO 8601). Ordered newest-first on read.

Public API:
    record_note(store, deal_id, body, author="") -> int
    list_notes(store, deal_id=None) -> pd.DataFrame
    delete_note(store, note_id) -> bool
        (Soft-noop if the note is already gone; returns whether a row changed.
        Deletion is a hedge against accidental paste of sensitive info —
        most product flows should never need it.)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_notes_table(store: PortfolioStore) -> None:
    """Create deal_notes table if absent. Idempotent.

    Schema carries a ``deleted_at`` column so deletes are soft — an
    analyst's accidental click is recoverable via :func:`undelete_note`.
    Older DBs without the column get it added on first touch (ALTER
    TABLE … ADD COLUMN is cheap on SQLite).
    """
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                author TEXT,
                body TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            )"""
        )
        # Back-compat migration for DBs created before soft-delete
        cols = {r[1] for r in con.execute("PRAGMA table_info(deal_notes)").fetchall()}
        if "deleted_at" not in cols:
            con.execute("ALTER TABLE deal_notes ADD COLUMN deleted_at TEXT")
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_notes_deal "
            "ON deal_notes(deal_id, created_at DESC)"
        )
        con.commit()


def record_note(
    store: PortfolioStore,
    *,
    deal_id: str,
    body: str,
    author: str = "",
) -> int:
    """Append a note on ``deal_id``. Returns the new ``note_id``.

    Empty bodies are rejected — there's no value in blank notes and
    they'd clutter the audit trail. B151 also caps body length to
    keep runaway POSTs from filling the DB.
    """
    if not body or not body.strip():
        raise ValueError("note body cannot be empty")
    MAX_BODY = 50_000  # ~50 KB, covers any realistic analyst note
    if len(body) > MAX_BODY:
        raise ValueError(
            f"note body too long: {len(body)} chars (max {MAX_BODY})"
        )
    MAX_DEAL_ID = 128
    if not deal_id or len(deal_id) > MAX_DEAL_ID:
        raise ValueError(
            f"deal_id must be 1..{MAX_DEAL_ID} chars"
        )
    _ensure_notes_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO deal_notes (deal_id, created_at, author, body) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, _utcnow(), author.strip() or None, body.strip()),
        )
        con.commit()
        return int(cur.lastrowid)


def list_notes(
    store: PortfolioStore,
    deal_id: Optional[str] = None,
    *,
    include_deleted: bool = False,
    limit: int = 0,
    offset: int = 0,
) -> pd.DataFrame:
    """Return notes newest-first. Filter by ``deal_id`` when provided.

    Soft-deleted rows are hidden by default (``include_deleted=True`` to
    see the trash bin). ``limit=0`` means no limit.
    """
    _ensure_notes_table(store)
    where_parts = []
    params: list = []
    if not include_deleted:
        where_parts.append("deleted_at IS NULL")
    if deal_id:
        where_parts.append("deal_id = ?")
        params.append(deal_id)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    limit_sql = ""
    if limit > 0:
        limit_sql = f" LIMIT {int(limit)}"
        if offset > 0:
            limit_sql += f" OFFSET {int(offset)}"
    with store.connect() as con:
        rows = con.execute(
            f"SELECT note_id, deal_id, created_at, author, body, deleted_at "
            f"FROM deal_notes {where_sql} ORDER BY created_at DESC{limit_sql}",
            params,
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def delete_note(store: PortfolioStore, note_id: int) -> bool:
    """Soft-delete a note (B91). Returns True if a row was marked.

    Row survives in the table with a ``deleted_at`` timestamp so
    :func:`undelete_note` can restore it. Use :func:`hard_delete_note`
    for permanent removal once the analyst confirms.
    """
    _ensure_notes_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE deal_notes SET deleted_at = ? "
            "WHERE note_id = ? AND deleted_at IS NULL",
            (_utcnow(), int(note_id)),
        )
        con.commit()
        return cur.rowcount > 0


def undelete_note(store: PortfolioStore, note_id: int) -> bool:
    """Restore a soft-deleted note. Returns True if a row was restored."""
    _ensure_notes_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE deal_notes SET deleted_at = NULL "
            "WHERE note_id = ? AND deleted_at IS NOT NULL",
            (int(note_id),),
        )
        con.commit()
        return cur.rowcount > 0


def import_notes_csv(
    store: PortfolioStore,
    csv_path: str,
) -> Dict[str, Any]:
    """Bulk-load notes from a CSV (Brick 112).

    Expected columns: ``deal_id``, ``body``, optional ``author``. Each
    valid row becomes one ``deal_notes`` row. Returns a summary dict::

        {
            "rows_ingested": int,
            "rows_skipped": int,
            "errors": [<per-row message>, ...],
        }

    Rows with empty deal_id or body are skipped with an error message;
    bad rows never block valid rows in the same file.
    """
    import csv as _csv

    summary: Dict[str, Any] = {
        "rows_ingested": 0,
        "rows_skipped": 0,
        "errors": [],
    }
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    # B151 fix: Windows Excel exports are commonly CP1252; try UTF-8
    # first (with BOM tolerance), then fall back to latin-1 so the
    # upload doesn't crash on a realistic management-deck file.
    # B154 fix: close the probe handle on fallback (fd leak).
    fh = open(csv_path, newline="", encoding="utf-8-sig")
    try:
        fh.read(1)  # probe: does the first byte decode?
        fh.seek(0)
    except UnicodeDecodeError:
        fh.close()
        fh = open(csv_path, newline="", encoding="latin-1")
    with fh:
        reader = _csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        required = {"deal_id", "body"}
        missing = required - {c.lower() for c in reader.fieldnames}
        if missing:
            raise ValueError(
                f"missing required columns: {sorted(missing)} "
                f"(got {reader.fieldnames})"
            )
        for i, raw in enumerate(reader, start=2):  # line 1 is header
            did = (raw.get("deal_id") or "").strip()
            body = (raw.get("body") or "").strip()
            author = (raw.get("author") or "").strip()
            if not did:
                summary["rows_skipped"] += 1
                summary["errors"].append(f"line {i}: missing deal_id")
                continue
            if not body:
                summary["rows_skipped"] += 1
                summary["errors"].append(f"line {i}: empty body for {did}")
                continue
            try:
                record_note(store, deal_id=did, body=body, author=author)
                summary["rows_ingested"] += 1
            except ValueError as exc:
                summary["rows_skipped"] += 1
                summary["errors"].append(f"line {i}: {exc}")
    return summary


def search_notes(
    store: PortfolioStore,
    query: str,
    *,
    limit: int = 50,
    offset: int = 0,
    deal_id: Optional[str] = None,
    tags: Optional[list] = None,
) -> pd.DataFrame:
    """Full-text search across note bodies (B110 + B123).

    Case-insensitive LIKE match on body. Returns newest-first.
    Soft-deleted notes are hidden.

    ``tags`` = list of tag strings → results must carry ALL of them
    (AND semantics). Empty list or None = no tag filter. Each tag is
    normalized via :mod:`rcm_mc.deal_tags._normalize`.

    Empty ``query`` with non-empty ``tags`` is permitted — returns all
    notes carrying those tags. Empty both = empty DataFrame.
    """
    tag_list: list = []
    if tags:
        from .deal_tags import _normalize as _norm_tag
        tag_list = [_norm_tag(t) for t in tags if str(t).strip()]

    if not query or not query.strip():
        if not tag_list:
            return pd.DataFrame(columns=[
                "note_id", "deal_id", "created_at", "author", "body",
            ])

    _ensure_notes_table(store)
    # Ensure note_tags table exists so the JOIN below doesn't error
    # when the DB was created before B123.
    if tag_list:
        from .note_tags import _ensure_table as _ensure_note_tags
        _ensure_note_tags(store)

    where_parts = ["n.deleted_at IS NULL"]
    params: list = []
    if query and query.strip():
        where_parts.append("LOWER(n.body) LIKE ?")
        params.append(f"%{query.strip().lower()}%")
    if deal_id:
        where_parts.append("n.deal_id = ?")
        params.append(deal_id)

    if tag_list:
        # Intersection: the note_id must appear with all supplied tags.
        placeholders = ",".join("?" * len(tag_list))
        where_parts.append(
            f"n.note_id IN ("
            f"  SELECT note_id FROM note_tags "
            f"  WHERE tag IN ({placeholders}) "
            f"  GROUP BY note_id "
            f"  HAVING COUNT(DISTINCT tag) = ?"
            f")"
        )
        params.extend(tag_list)
        params.append(len(tag_list))

    sql = (
        "SELECT n.note_id, n.deal_id, n.created_at, n.author, n.body "
        "FROM deal_notes n WHERE "
        + " AND ".join(where_parts)
        + " ORDER BY n.created_at DESC LIMIT ? OFFSET ?"
    )
    params.append(int(limit))
    params.append(max(int(offset), 0))
    with store.connect() as con:
        rows = con.execute(sql, params).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def hard_delete_note(store: PortfolioStore, note_id: int) -> bool:
    """Permanent deletion. Returns True when the row was actually removed."""
    _ensure_notes_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM deal_notes WHERE note_id = ?",
            (int(note_id),),
        )
        con.commit()
        return cur.rowcount > 0
