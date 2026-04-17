"""Data retention + compliance (Prompt 57).

Configurable retention per table; ``enforce_retention`` deletes rows
older than policy. ``export_user_data`` for GDPR-style data export.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS: Dict[str, int] = {
    "analysis_runs": 730,        # 24 months
    "mc_simulation_runs": 365,   # 12 months
    "audit_events": 1095,        # 36 months
    "sessions": 30,
    "webhook_deliveries": 90,
}


def enforce_retention(
    store: Any,
    policy: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Delete rows older than policy. Returns {table: rows_deleted}."""
    policy = policy or DEFAULT_RETENTION_DAYS
    deleted: Dict[str, int] = {}
    now = datetime.now(timezone.utc)
    for table, days in policy.items():
        cutoff = (now - timedelta(days=days)).isoformat()
        # Each table has a different timestamp column.
        ts_col = {
            "analysis_runs": "created_at",
            "mc_simulation_runs": "created_at",
            "audit_events": "at",
            "sessions": "created_at",
            "webhook_deliveries": "delivered_at",
        }.get(table, "created_at")
        try:
            with store.connect() as con:
                cur = con.execute(
                    f"DELETE FROM {table} WHERE {ts_col} < ?",  # noqa: S608 — table names are from our own constant
                    (cutoff,),
                )
                con.commit()
                deleted[table] = cur.rowcount or 0
        except Exception as exc:  # noqa: BLE001
            logger.debug("retention for %s failed: %s", table, exc)
            deleted[table] = 0
    return deleted


def export_user_data(store: Any, user_id: str, out_dir: Path) -> Path:
    """GDPR-style export: all rows referencing this user."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, List[Dict[str, Any]]] = {}
    tables = [
        ("audit_events", "actor", user_id),
        ("sessions", "username", user_id),
        ("deal_overrides", "set_by", user_id),
    ]
    for table, col, val in tables:
        try:
            with store.connect() as con:
                rows = con.execute(
                    f"SELECT * FROM {table} WHERE {col} = ?",  # noqa: S608
                    (val,),
                ).fetchall()
            result[table] = [dict(r) for r in rows]
        except Exception:  # noqa: BLE001
            result[table] = []
    path = out_dir / f"user_data_{user_id}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return path
