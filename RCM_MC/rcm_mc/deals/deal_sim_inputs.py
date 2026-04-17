"""Per-deal simulation input paths (Brick 121).

The job queue (B95) can run any simulation if given paths to
``actual.yaml``, ``benchmark.yaml``, and an ``outdir``. Previously a
partner had to re-type those paths in the `/jobs` form every time. For
a monitored deal they don't change — ``ccf``'s management reporting
yaml lives in the same place whether you re-run today or next quarter.

This module stores the mapping so a single "Rerun simulation" button
on ``/deal/<id>`` can queue the job.

Design:

- One row per deal. Rerunning mutates the existing row rather than
  versioning — if you moved the yaml, the new path is the truth.
- ``outdir_base`` is the *directory* under which each rerun creates a
  timestamped subfolder (so reruns don't clobber each other). When
  empty, we fall back to a default beneath the deal_id.

Public API::

    set_inputs(store, deal_id, actual_path, benchmark_path, outdir_base="")
    get_inputs(store, deal_id) -> dict | None
    next_outdir(deal_id, outdir_base) -> str   # timestamped subdir
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Optional

from ..portfolio.store import PortfolioStore


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_sim_inputs (
                deal_id TEXT PRIMARY KEY,
                actual_path TEXT NOT NULL,
                benchmark_path TEXT NOT NULL,
                outdir_base TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )"""
        )
        con.commit()


def set_inputs(
    store: PortfolioStore,
    *,
    deal_id: str,
    actual_path: str,
    benchmark_path: str,
    outdir_base: str = "",
) -> None:
    """Upsert a deal's stored simulation input paths.

    Raises ``ValueError`` if actual or benchmark is empty. We do NOT
    require the files to exist at call time — the partner may be
    editing the path on disk concurrently; the check happens when we
    actually queue the job.
    """
    if not deal_id or not str(deal_id).strip():
        raise ValueError("deal_id required")
    if not actual_path or not str(actual_path).strip():
        raise ValueError("actual_path required")
    if not benchmark_path or not str(benchmark_path).strip():
        raise ValueError("benchmark_path required")
    _ensure_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        con.execute(
            """INSERT INTO deal_sim_inputs
               (deal_id, actual_path, benchmark_path, outdir_base, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(deal_id) DO UPDATE SET
                 actual_path = excluded.actual_path,
                 benchmark_path = excluded.benchmark_path,
                 outdir_base = excluded.outdir_base,
                 updated_at = excluded.updated_at""",
            (str(deal_id).strip(),
             str(actual_path).strip(),
             str(benchmark_path).strip(),
             str(outdir_base or "").strip(),
             _utcnow_iso()),
        )
        con.commit()


def get_inputs(store: PortfolioStore, deal_id: str) -> Optional[Dict[str, str]]:
    """Return stored paths, or None if the deal has none."""
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT actual_path, benchmark_path, outdir_base, updated_at "
            "FROM deal_sim_inputs WHERE deal_id = ?",
            (deal_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "actual_path": row["actual_path"],
        "benchmark_path": row["benchmark_path"],
        "outdir_base": row["outdir_base"],
        "updated_at": row["updated_at"],
    }


def next_outdir(deal_id: str, outdir_base: str = "") -> str:
    """Timestamped subfolder path so reruns don't clobber each other.

    B149 fix: reject outdir_base values containing ``..`` path segments
    so a malicious caller can't escape the intended directory tree.
    Also rejects deal_id with path separators for the same reason.
    """
    if ".." in (outdir_base or "").split(os.sep):
        raise ValueError(
            f"outdir_base may not contain '..' segments: {outdir_base!r}"
        )
    if os.sep in deal_id or "/" in deal_id or ".." in deal_id:
        raise ValueError(f"deal_id may not contain path separators: {deal_id!r}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = outdir_base or os.path.join("runs", deal_id)
    return os.path.join(base, stamp)
