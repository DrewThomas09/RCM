"""
Step 83: SQLite-based run history.

Auto-appends a row after each CLI run for tracking model evolution.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .logger import logger


_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actual_config_hash TEXT,
    benchmark_config_hash TEXT,
    n_sims INTEGER,
    seed INTEGER,
    ebitda_drag_mean REAL,
    ebitda_drag_p10 REAL,
    ebitda_drag_p90 REAL,
    ev_impact REAL,
    output_dir TEXT,
    hospital_name TEXT,
    notes TEXT
);
"""


def _hash_file(path: str) -> Optional[str]:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _get_db_path(outdir: str) -> str:
    return os.path.join(outdir, "runs.sqlite")


def record_run(
    outdir: str,
    *,
    actual_config_path: Optional[str] = None,
    benchmark_config_path: Optional[str] = None,
    n_sims: int = 0,
    seed: int = 0,
    ebitda_drag_mean: float = 0.0,
    ebitda_drag_p10: float = 0.0,
    ebitda_drag_p90: float = 0.0,
    ev_impact: float = 0.0,
    hospital_name: str = "",
    notes: str = "",
) -> None:
    """Record a simulation run to the SQLite history."""
    db_path = _get_db_path(outdir)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_DB_SCHEMA)
        conn.execute(
            """INSERT INTO runs (timestamp, actual_config_hash, benchmark_config_hash,
               n_sims, seed, ebitda_drag_mean, ebitda_drag_p10, ebitda_drag_p90,
               ev_impact, output_dir, hospital_name, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                _hash_file(actual_config_path),
                _hash_file(benchmark_config_path),
                n_sims, seed,
                ebitda_drag_mean, ebitda_drag_p10, ebitda_drag_p90,
                ev_impact, outdir, hospital_name, notes,
            ),
        )
        conn.commit()
        logger.info("Run recorded to %s", db_path)
    finally:
        conn.close()


def list_runs(outdir: str, limit: int = 20) -> List[Dict[str, Any]]:
    """List recent runs from the history database."""
    db_path = _get_db_path(outdir)
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
