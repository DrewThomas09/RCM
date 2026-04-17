"""External user management for management team + LP portals (Prompts 84-85).

Two external role types: EXTERNAL_MANAGEMENT (read-only on their deal)
and LIMITED_PARTNER (read-only on fund-level aggregates).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS external_user_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                deal_id TEXT,
                fund_id TEXT,
                role TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                granted_by TEXT,
                active INTEGER DEFAULT 1
            )"""
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def grant_access(
    store: Any, user_id: str, role: str,
    *, deal_id: Optional[str] = None,
    fund_id: Optional[str] = None,
    granted_by: str = "system",
) -> int:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO external_user_assignments "
            "(user_id, deal_id, fund_id, role, granted_at, granted_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, deal_id, fund_id, role, _utcnow(), granted_by),
        )
        con.commit()
        return int(cur.lastrowid)


def revoke_access(store: Any, assignment_id: int) -> bool:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE external_user_assignments SET active = 0 WHERE id = ?",
            (assignment_id,),
        )
        con.commit()
        return cur.rowcount > 0


def list_assignments(
    store: Any, *, user_id: Optional[str] = None,
    deal_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _ensure_table(store)
    clauses = ["active = 1"]
    params: list = []
    if user_id:
        clauses.append("user_id = ?"); params.append(user_id)
    if deal_id:
        clauses.append("deal_id = ?"); params.append(deal_id)
    where = " AND ".join(clauses)
    with store.connect() as con:
        rows = con.execute(
            f"SELECT * FROM external_user_assignments WHERE {where}",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def can_access_deal(store: Any, user_id: str, deal_id: str) -> bool:
    """Check if an external user has access to a specific deal."""
    assignments = list_assignments(store, user_id=user_id)
    for a in assignments:
        if a.get("deal_id") == deal_id:
            return True
    return False
