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

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_NAME = "npi_cleaner_wishlist.sqlite3"
_DB_PATH = Path(WORKDIR) / _DB_NAME
_LOCK = threading.Lock()


def _db_path() -> Path:
    """Default store root is /tmp, which a reboot or tmp cleaner wipes —
    erasing the improvement backlog this module promises to keep. Set
    RCM_MC_NPI_WORKDIR to a persistent directory to keep it; read
    per-call so tests can still monkeypatch ``_DB_PATH``."""
    root = (os.environ.get("RCM_MC_NPI_WORKDIR") or "").strip()
    if root:
        return Path(root) / _DB_NAME
    return _DB_PATH

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
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
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


def list_requests(status: Optional[str] = None,
                  source: Optional[str] = None) -> List[Dict[str, object]]:
    """Newest first, bounded. ``status`` / ``source`` filter when given
    (``source`` is 'user' or 'auto'; additive parameter)."""
    try:
        with _LOCK, _conn() as con:
            sql = ("SELECT id, created, category, title, details, status,"
                   " source FROM wishlist")
            where: List[str] = []
            args: List[object] = []
            if status and status in _STATUSES:
                where.append("status = ?")
                args.append(status)
            if source and source in ("user", "auto"):
                where.append("source = ?")
                args.append(source)
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY id DESC LIMIT ?"
            args.append(_LIST_MAX)
            rows = con.execute(sql, args).fetchall()
    except Exception:  # noqa: BLE001 — a broken store must not 500 the page
        return []
    return [{"id": r[0], "created": r[1], "category": r[2],
             "title": r[3], "details": r[4], "status": r[5],
             "source": (r[6] if len(r) > 6 else "user")} for r in rows]


def set_status(request_id: int, status: str) -> bool:
    """Move a request through the backlog (open → planned → shipped).
    Guarded like the rest of the module: a corrupt/locked store returns
    False instead of raising through the POST handler."""
    if status not in _STATUSES:
        return False
    try:
        with _LOCK, _conn() as con:
            cur = con.execute("UPDATE wishlist SET status = ? WHERE id = ?",
                              (status, int(request_id)))
            return cur.rowcount > 0
    except Exception:  # noqa: BLE001 — never 500 the page
        return False


def delete_request(request_id: int) -> bool:
    try:
        with _LOCK, _conn() as con:
            cur = con.execute("DELETE FROM wishlist WHERE id = ?",
                              (int(request_id),))
            return cur.rowcount > 0
    except Exception:  # noqa: BLE001 — never 500 the page
        return False


def mark_shipped(title_contains: str, *,
                 source: Optional[str] = "auto") -> int:
    """The backlog's "shipped" transition for the improvement loop: mark
    every OPEN request whose title contains ``title_contains``
    (case-insensitive) as shipped. Defaults to auto-filed requests only —
    the loop ships machine-detected gaps; a human decides about human
    asks (pass ``source=None`` to include those too). Returns how many
    requests moved; 0 on any store error (never raises)."""
    frag = " ".join(str(title_contains or "").split()).lower()
    if not frag:
        return 0
    try:
        with _LOCK, _conn() as con:
            if source in ("user", "auto"):
                rows = con.execute(
                    "SELECT id, title FROM wishlist WHERE status = 'open'"
                    " AND source = ?", (source,)).fetchall()
            else:
                rows = con.execute(
                    "SELECT id, title FROM wishlist"
                    " WHERE status = 'open'").fetchall()
            hit_ids = [int(r[0]) for r in rows
                       if frag in str(r[1] or "").lower()]
            for rid in hit_ids:
                con.execute(
                    "UPDATE wishlist SET status = 'shipped' WHERE id = ?",
                    (rid,))
            return len(hit_ids)
    except Exception:  # noqa: BLE001 — never blocks the loop
        return 0
