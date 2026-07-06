"""Cleaner wishlist — "missing something? tell us and we'll fill it in".

Users hit the cleaner with feeds we haven't seen: a payer whose family
isn't in the catalog, a field the detector doesn't recognize, a check
their compliance team needs. This store captures those requests right on
the page so they become a concrete backlog instead of a lost Slack
message. The improvement loop reads open requests and ships them.

Storage follows the profiles/mappings convention: a dedicated SQLite file
in the cleaner's WORKDIR holding short free-text config ONLY — never
claim rows, never PHI. Every string is length-capped at write time and
HTML-escaped at render time.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_PATH = Path(WORKDIR) / "npi_cleaner_wishlist.sqlite3"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wishlist (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    created  REAL NOT NULL,
    category TEXT NOT NULL,
    title    TEXT NOT NULL,
    details  TEXT NOT NULL DEFAULT '',
    status   TEXT NOT NULL DEFAULT 'open'
);
"""

# What kind of gap is being reported. Fixed vocabulary so the backlog can
# be sliced; anything else is coerced to "other".
CATEGORIES = ("rule", "field", "payer", "format", "integration", "other")
_STATUSES = ("open", "planned", "shipped", "declined")

_TITLE_MAX = 120
_DETAILS_MAX = 2000
_LIST_MAX = 500


def _conn() -> sqlite3.Connection:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_DB_PATH)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    # Migration: where a request came from — 'user' (typed on the page) vs
    # 'auto' (filed by the engine when it hit a gap it couldn't handle). Kept
    # separable so machine-detected gaps don't drown the human request list.
    # Idempotent: ADD COLUMN raises on an existing column, swallowed.
    try:
        con.execute("ALTER TABLE wishlist ADD COLUMN source TEXT "
                    "NOT NULL DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass
    return con


def add_request(category: str, title: str,
                details: str = "") -> Dict[str, object]:
    """Log a request. Title required; everything length-capped so a
    hostile client can't grow the store unbounded."""
    title = " ".join(str(title or "").split())[:_TITLE_MAX]
    if not title:
        raise ValueError("a short title for the request is required")
    category = str(category or "").strip().lower()
    if category not in CATEGORIES:
        category = "other"
    details = str(details or "").strip()[:_DETAILS_MAX]
    now = time.time()
    with _LOCK, _conn() as con:
        cur = con.execute(
            "INSERT INTO wishlist (created, category, title, details, status)"
            " VALUES (?,?,?,?, 'open')",
            (now, category, title, details))
        rid = int(cur.lastrowid or 0)
    return {"id": rid, "created": now, "category": category,
            "title": title, "details": details, "status": "open"}


def auto_file(category: str, title: str,
              details: str = "") -> Optional[Dict[str, object]]:
    """File a machine-detected gap (source='auto'), deduplicated by title so
    the same gap hitting on every upload doesn't pile up. Returns the new row,
    or None when an auto entry with that title already exists (any status) or
    on any store error — auto-filing must never break a cleaning run."""
    title = " ".join(str(title or "").split())[:_TITLE_MAX]
    if not title:
        return None
    category = str(category or "").strip().lower()
    if category not in CATEGORIES:
        category = "other"
    details = str(details or "").strip()[:_DETAILS_MAX]
    now = time.time()
    try:
        with _LOCK, _conn() as con:
            dup = con.execute(
                "SELECT id FROM wishlist WHERE source = 'auto' AND title = ? "
                "LIMIT 1", (title,)).fetchone()
            if dup is not None:
                return None
            cur = con.execute(
                "INSERT INTO wishlist (created, category, title, details,"
                " status, source) VALUES (?,?,?,?, 'open', 'auto')",
                (now, category, title, details))
            rid = int(cur.lastrowid or 0)
    except Exception:  # noqa: BLE001 — auto-file never blocks cleaning
        return None
    return {"id": rid, "created": now, "category": category, "title": title,
            "details": details, "status": "open", "source": "auto"}


def list_requests(status: Optional[str] = None) -> List[Dict[str, object]]:
    """Newest first, bounded. ``status`` filters when given."""
    try:
        with _LOCK, _conn() as con:
            if status and status in _STATUSES:
                rows = con.execute(
                    "SELECT id, created, category, title, details, status,"
                    " source FROM wishlist WHERE status = ? "
                    "ORDER BY id DESC LIMIT ?", (status, _LIST_MAX)).fetchall()
            else:
                rows = con.execute(
                    "SELECT id, created, category, title, details, status,"
                    " source FROM wishlist ORDER BY id DESC LIMIT ?",
                    (_LIST_MAX,)).fetchall()
    except Exception:  # noqa: BLE001 — a broken store must not 500 the page
        return []
    return [{"id": r[0], "created": r[1], "category": r[2],
             "title": r[3], "details": r[4], "status": r[5],
             "source": (r[6] if len(r) > 6 else "user")} for r in rows]


def set_status(request_id: int, status: str) -> bool:
    """Move a request through the backlog (open → planned → shipped)."""
    if status not in _STATUSES:
        return False
    with _LOCK, _conn() as con:
        cur = con.execute("UPDATE wishlist SET status = ? WHERE id = ?",
                          (status, int(request_id)))
        return cur.rowcount > 0


def delete_request(request_id: int) -> bool:
    with _LOCK, _conn() as con:
        cur = con.execute("DELETE FROM wishlist WHERE id = ?",
                          (int(request_id),))
        return cur.rowcount > 0
