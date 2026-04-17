"""Audit log for generated exports.

``generated_exports`` is append-only — partners' trail-of-breadcrumbs
for what was handed out, when, to whom, and which analysis run the
numbers came from. Kept in a dedicated module so the export renderer
itself stays focused on rendering.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS generated_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT,
                analysis_run_id TEXT,
                format TEXT NOT NULL,
                filepath TEXT,
                generated_at TEXT NOT NULL,
                generated_by TEXT,
                file_size_bytes INTEGER,
                packet_hash TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE SET NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_ge_deal "
            "ON generated_exports(deal_id, generated_at)"
        )
        con.commit()


def record_export(
    store: Any,
    *,
    deal_id: str,
    analysis_run_id: Optional[str],
    format: str,
    filepath: Optional[str],
    file_size_bytes: Optional[int] = None,
    packet_hash: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> int:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO generated_exports
               (deal_id, analysis_run_id, format, filepath,
                generated_at, generated_by, file_size_bytes, packet_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(deal_id), analysis_run_id or None, str(format),
             filepath, _utcnow_iso(), generated_by,
             int(file_size_bytes) if file_size_bytes is not None else None,
             packet_hash),
        )
        con.commit()
        return int(cur.lastrowid)


def list_exports(
    store: Any, deal_id: Optional[str] = None, *, limit: int = 100,
) -> List[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        if deal_id:
            rows = con.execute(
                """SELECT * FROM generated_exports
                   WHERE deal_id = ? ORDER BY generated_at DESC LIMIT ?""",
                (str(deal_id), int(limit)),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT * FROM generated_exports
                   ORDER BY generated_at DESC LIMIT ?""",
                (int(limit),),
            ).fetchall()
    return [dict(r) for r in rows]
