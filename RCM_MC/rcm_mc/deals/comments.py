"""Metric-level + deal-level threaded comments (Prompt 49).

Comments live on specific metrics or on the deal as a whole.
Threading via ``parent_id``. @-mention parsing extracts usernames
so the notification system can alert them.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                metric_key TEXT,
                body TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parent_id INTEGER,
                resolved INTEGER DEFAULT 0,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_deal "
            "ON comments(deal_id, created_at)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_metric "
            "ON comments(deal_id, metric_key)"
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


_MENTION_RE = re.compile(r"@(\w+)")


def parse_mentions(body: str) -> List[str]:
    """Extract @username tokens from the comment body."""
    return _MENTION_RE.findall(body or "")


def add_comment(
    store: Any, deal_id: str, body: str, author: str,
    *, metric_key: Optional[str] = None,
    parent_id: Optional[int] = None,
) -> int:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO comments "
            "(deal_id, metric_key, body, author, created_at, parent_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (deal_id, metric_key, body, author, _utcnow(), parent_id),
        )
        con.commit()
        return int(cur.lastrowid)


def list_comments(
    store: Any, deal_id: str,
    *, metric_key: Optional[str] = None,
    resolved: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    _ensure_table(store)
    clauses = ["deal_id = ?"]
    params: list = [deal_id]
    if metric_key is not None:
        clauses.append("metric_key = ?")
        params.append(metric_key)
    if resolved is not None:
        clauses.append("resolved = ?")
        params.append(int(resolved))
    where = " AND ".join(clauses)
    with store.connect() as con:
        rows = con.execute(
            f"SELECT * FROM comments WHERE {where} ORDER BY created_at",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_comment(store: Any, comment_id: int) -> bool:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE comments SET resolved = 1 WHERE id = ?",
            (comment_id,),
        )
        con.commit()
        return cur.rowcount > 0
