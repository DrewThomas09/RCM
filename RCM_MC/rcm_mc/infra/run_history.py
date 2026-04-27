"""
Step 83: SQLite-based run history.

Auto-appends a row after each CLI run for tracking model evolution.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..portfolio.store import PortfolioStore
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

    # Route through PortfolioStore (campaign target 4E) so the
    # CLI run-history write inherits busy_timeout=5000,
    # foreign_keys=ON, and Row factory consistent with every
    # other store in the codebase. PortfolioStore.connect()
    # closes the connection on exit but does NOT auto-commit,
    # so the explicit conn.commit() is preserved inside the
    # with-block.
    with PortfolioStore(db_path).connect() as conn:
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


def list_runs(outdir: str, limit: int = 20) -> List[Dict[str, Any]]:
    """List recent runs from the history database."""
    db_path = _get_db_path(outdir)
    if not os.path.exists(db_path):
        return []

    # Read path also routes through PortfolioStore — Row factory
    # is provided by default so the manual assignment is dropped.
    with PortfolioStore(db_path).connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
