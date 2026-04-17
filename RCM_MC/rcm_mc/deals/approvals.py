"""Lightweight approval workflow for IC decisions (Prompt 50).

Two approval stages: ``ic_review`` (VP signs off on analysis) and
``investment_approval`` (partner approves the investment). Each is
a row in ``approval_requests`` with pending → approved / rejected
status. The workbench renders a "Request IC Review" button that
creates the request and notifies the approver.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                approver TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                decided_at TEXT,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_approvals_deal "
            "ON approval_requests(deal_id, status)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_approvals_approver "
            "ON approval_requests(approver, status)"
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_approval(
    store: Any, deal_id: str, stage: str,
    approver: str, requested_by: str,
) -> int:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO approval_requests "
            "(deal_id, stage, requested_by, requested_at, approver) "
            "VALUES (?, ?, ?, ?, ?)",
            (deal_id, stage, requested_by, _utcnow(), approver),
        )
        con.commit()
        return int(cur.lastrowid)


def decide_approval(
    store: Any, request_id: int, status: str,
    *, notes: Optional[str] = None,
) -> bool:
    if status not in ("approved", "rejected"):
        raise ValueError(f"status must be approved/rejected, got {status!r}")
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE approval_requests SET status = ?, decided_at = ?, notes = ? "
            "WHERE id = ?",
            (status, _utcnow(), notes, request_id),
        )
        con.commit()
        return cur.rowcount > 0


def pending_approvals(
    store: Any, *, approver: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        if approver:
            rows = con.execute(
                "SELECT * FROM approval_requests "
                "WHERE status = 'pending' AND approver = ? "
                "ORDER BY requested_at DESC",
                (approver,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM approval_requests "
                "WHERE status = 'pending' ORDER BY requested_at DESC",
            ).fetchall()
    return [dict(r) for r in rows]
