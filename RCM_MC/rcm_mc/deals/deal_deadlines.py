"""Per-deal deadlines / tasks (Brick 114).

Alerts answer "what's broken now"; deadlines answer "what's due soon".
Together they form a real partner inbox: covenant test on 2026-05-31,
debt refi closing window 2026-06-30, board meeting 2026-04-22.

Design:

- One row per deadline. ``due_date`` is YYYY-MM-DD (string for SQLite
  comparability — a partner picking dates in 4 timezones doesn't need
  micro-precision).
- ``status`` is ``"open"`` or ``"completed"``. Completion is soft —
  we keep the row + ``completed_at`` for audit.
- Cross-portfolio queries: ``upcoming(store, days_ahead=14)`` and
  ``overdue(store)`` power the /deadlines inbox view.

Public API::

    add_deadline(store, deal_id, label, due_date, notes="") -> int
    complete_deadline(store, deadline_id) -> bool
    delete_deadline(store, deadline_id) -> bool      # permanent
    list_deadlines(store, deal_id=None, include_completed=False) -> pd.DataFrame
    upcoming(store, days_ahead=14) -> pd.DataFrame   # next N days, open only
    overdue(store) -> pd.DataFrame                   # past due, open only
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_date(due_date: str) -> str:
    s = str(due_date).strip()
    if not _DATE_RE.match(s):
        raise ValueError(f"due_date must be YYYY-MM-DD (got {due_date!r})")
    try:
        date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"due_date {due_date!r} is not a real date: {exc}")
    return s


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_deadlines (
                deadline_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                label TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                notes TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT ''
            )"""
        )
        # Back-compat migration for DBs created before B116 added owner
        cols = {r[1] for r in con.execute(
            "PRAGMA table_info(deal_deadlines)"
        ).fetchall()}
        if "owner" not in cols:
            con.execute(
                "ALTER TABLE deal_deadlines ADD COLUMN owner TEXT NOT NULL "
                "DEFAULT ''"
            )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_deadlines_due "
            "ON deal_deadlines(status, due_date)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_deadlines_owner "
            "ON deal_deadlines(owner, status)"
        )
        con.commit()


def add_deadline(
    store: PortfolioStore,
    *,
    deal_id: str,
    label: str,
    due_date: str,
    notes: str = "",
    owner: str = "",
) -> int:
    """Insert a new open deadline, or return the existing one if an
    identical open deadline already exists.

    B158 fix: idempotent on ``(deal_id, label, due_date)`` while status
    is ``open``. Two concurrent POSTs with identical payload now
    produce one row, not two. A partner can re-submit the same form
    without doubling up the inbox. Completed deadlines with the same
    label are ignored by the dedupe so an analyst can re-open an old
    task after it was completed.
    """
    if not deal_id or not str(deal_id).strip():
        raise ValueError("deal_id required")
    if not label or not str(label).strip():
        raise ValueError("label required")
    due = _validate_date(due_date)
    label_clean = str(label).strip()
    _ensure_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            existing = con.execute(
                "SELECT deadline_id FROM deal_deadlines "
                "WHERE deal_id = ? AND label = ? AND due_date = ? "
                "AND status = 'open' LIMIT 1",
                (deal_id, label_clean, due),
            ).fetchone()
            if existing is not None:
                con.rollback()
                return int(existing["deadline_id"])
            cur = con.execute(
                "INSERT INTO deal_deadlines "
                "(deal_id, label, due_date, status, created_at, "
                " notes, owner) "
                "VALUES (?, ?, ?, 'open', ?, ?, ?)",
                (deal_id, label_clean, due, _utcnow_iso(),
                 str(notes or "").strip(), str(owner or "").strip()),
            )
            did = int(cur.lastrowid)
            con.commit()
            return did
        except Exception:
            con.rollback()
            raise


def assign_deadline_owner(
    store: PortfolioStore, deadline_id: int, owner: str,
) -> bool:
    """Reassign a deadline to ``owner``. Returns True if a row changed."""
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE deal_deadlines SET owner = ? WHERE deadline_id = ?",
            (str(owner or "").strip(), int(deadline_id)),
        )
        con.commit()
        return cur.rowcount > 0


def complete_deadline(store: PortfolioStore, deadline_id: int) -> bool:
    """Mark a deadline completed. Returns True if state changed."""
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE deal_deadlines SET status='completed', completed_at=? "
            "WHERE deadline_id=? AND status='open'",
            (_utcnow_iso(), int(deadline_id)),
        )
        con.commit()
        return cur.rowcount > 0


def delete_deadline(store: PortfolioStore, deadline_id: int) -> bool:
    """Hard-delete a deadline. Returns True if a row was removed."""
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM deal_deadlines WHERE deadline_id = ?",
            (int(deadline_id),),
        )
        con.commit()
        return cur.rowcount > 0


def list_deadlines(
    store: PortfolioStore,
    deal_id: Optional[str] = None,
    *,
    include_completed: bool = False,
    owner: Optional[str] = None,
) -> pd.DataFrame:
    """Return deadlines, due-date ascending. Filter by deal/owner/status."""
    _ensure_table(store)
    where = []
    params: list = []
    if not include_completed:
        where.append("status = 'open'")
    if deal_id:
        where.append("deal_id = ?")
        params.append(deal_id)
    if owner:
        where.append("owner = ?")
        params.append(owner)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with store.connect() as con:
        return pd.read_sql_query(
            f"SELECT deadline_id, deal_id, label, due_date, status, "
            f"created_at, completed_at, notes, owner "
            f"FROM deal_deadlines {where_sql} ORDER BY due_date ASC",
            con, params=params,
        )


def upcoming(
    store: PortfolioStore,
    *,
    days_ahead: int = 14,
    today: Optional[date] = None,
    owner: Optional[str] = None,
) -> pd.DataFrame:
    """Open deadlines due within the next ``days_ahead`` days.

    The window is inclusive of today and spans *exactly* ``days_ahead``
    calendar days. ``days_ahead=14`` with today = 2026-04-15 includes
    due_dates 2026-04-15 through 2026-04-28 (14 rows max per day).

    Pass ``owner`` to narrow to one analyst's pipeline.

    B146 fix: off-by-one in cutoff.
    B148 fix: use UTC today so server-timezone drift doesn't shift the
    window. ``due_date`` strings in the DB are untyped YYYY-MM-DD; we
    treat them as UTC calendar dates consistently.
    """
    today = today or datetime.now(timezone.utc).date()
    # Subtract 1 so today + N-1 days is the inclusive upper bound.
    cutoff = today + timedelta(days=max(int(days_ahead) - 1, 0))
    df = list_deadlines(store, owner=owner)
    if df.empty:
        return df
    df = df[(df["due_date"] >= today.isoformat())
            & (df["due_date"] <= cutoff.isoformat())]
    return df.reset_index(drop=True)


def overdue(
    store: PortfolioStore,
    *,
    today: Optional[date] = None,
    owner: Optional[str] = None,
) -> pd.DataFrame:
    """Open deadlines whose due_date is strictly before today (UTC).

    B148 fix: use UTC-today so the cutoff is timezone-stable.
    """
    today = today or datetime.now(timezone.utc).date()
    df = list_deadlines(store, owner=owner)
    if df.empty:
        return df
    df = df[df["due_date"] < today.isoformat()]
    df = df.copy()
    df["days_overdue"] = df["due_date"].apply(
        lambda d: (today - date.fromisoformat(d)).days
    )
    return df.sort_values("days_overdue", ascending=False).reset_index(drop=True)
