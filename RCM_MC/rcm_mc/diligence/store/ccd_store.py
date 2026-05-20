"""SQLite persistence for healthcare snapshot runs.

Saves a completed :class:`SnapshotResult` so a deal team can revisit a
run across sessions (the ``ccd_store`` the CCD contract docstring
anticipates). Follows the repo convention: stdlib ``sqlite3``,
idempotent ``CREATE TABLE IF NOT EXISTS`` migration, parameterised SQL.

Stored payload is PHI-safe: the SnapshotResult.to_dict() carries only
aggregates + tokenized identifiers, and the memo is aggregate-only.
Runs are keyed by ``content_hash`` so re-ingesting identical inputs
updates in place (idempotent), isolated per ``project_id``.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..snapshot import SnapshotResult

_DDL = """
CREATE TABLE IF NOT EXISTS hcrl_runs (
    content_hash            TEXT NOT NULL,
    project_id              TEXT NOT NULL DEFAULT '',
    ingest_id               TEXT NOT NULL DEFAULT '',
    deal_name               TEXT NOT NULL DEFAULT 'Target',
    data_confidence_score   INTEGER NOT NULL DEFAULT 0,
    transaction_types       TEXT NOT NULL DEFAULT '',
    parser_used             TEXT NOT NULL DEFAULT '',
    memo_markdown           TEXT NOT NULL DEFAULT '',
    result_json             TEXT NOT NULL DEFAULT '{}',
    created_at              TEXT NOT NULL,
    PRIMARY KEY (project_id, content_hash)
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    conn.execute(_DDL)
    return conn


@dataclass
class StoredRun:
    content_hash: str
    project_id: str
    deal_name: str
    data_confidence_score: int
    transaction_types: List[str]
    parser_used: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


def save_run(
    db_path: str, result: "SnapshotResult", *,
    project_id: str = "", deal_name: str = "Target",
) -> str:
    """Persist a snapshot run; returns its content_hash key. Re-saving an
    identical run (same content_hash) updates in place."""
    content_hash = result.ccd.content_hash()
    payload = json.dumps(result.to_dict(), sort_keys=True)
    now = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO hcrl_runs
               (content_hash, project_id, ingest_id, deal_name,
                data_confidence_score, transaction_types, parser_used,
                memo_markdown, result_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(project_id, content_hash) DO UPDATE SET
                 deal_name=excluded.deal_name,
                 data_confidence_score=excluded.data_confidence_score,
                 transaction_types=excluded.transaction_types,
                 parser_used=excluded.parser_used,
                 memo_markdown=excluded.memo_markdown,
                 result_json=excluded.result_json,
                 created_at=excluded.created_at""",
            (content_hash, project_id, result.ccd.ingest_id, deal_name,
             int(result.confidence.score),
             ",".join(result.transaction_types), result.parser_used,
             result.memo_markdown, payload, now),
        )
        conn.commit()
    return content_hash


def load_run(db_path: str, content_hash: str, *, project_id: str = "") -> Optional[Dict[str, Any]]:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM hcrl_runs WHERE project_id=? AND content_hash=?",
            (project_id, content_hash)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json") or "{}")
    d["transaction_types"] = (d.get("transaction_types") or "").split(",") if d.get("transaction_types") else []
    return d


def list_runs(db_path: str, *, project_id: str = "") -> List[StoredRun]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT content_hash, project_id, deal_name, data_confidence_score,
                      transaction_types, parser_used, created_at
               FROM hcrl_runs WHERE project_id=? ORDER BY created_at DESC""",
            (project_id,)).fetchall()
    return [
        StoredRun(
            content_hash=r["content_hash"], project_id=r["project_id"],
            deal_name=r["deal_name"],
            data_confidence_score=r["data_confidence_score"],
            transaction_types=(r["transaction_types"].split(",")
                               if r["transaction_types"] else []),
            parser_used=r["parser_used"], created_at=r["created_at"],
        )
        for r in rows
    ]
