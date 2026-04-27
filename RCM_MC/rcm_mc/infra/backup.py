"""Atomic SQLite backup, restore, and verification.

Partners run on a single-machine SQLite deployment. Losing the
database means losing all deal history, analysis packets, and
audit trails. This module provides:

- ``create_backup`` — atomic copy via ``VACUUM INTO`` + gzip
  compression. Filename includes a UTC timestamp for sort order.
- ``restore_backup`` — decompress, copy, then ``PRAGMA integrity_check``
  to verify the result is a valid database.
- ``verify_backup`` — non-destructive check: opens the backup, runs
  integrity check, counts rows in key tables.

The ``VACUUM INTO`` approach is atomic with respect to concurrent
writers — it's the recommended way to create a consistent snapshot
of a SQLite database that may be in use.
"""
from __future__ import annotations

import gzip
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..portfolio.store import PortfolioStore

logger = logging.getLogger(__name__)


# Key tables to count rows in for verification
_KEY_TABLES = (
    "deals",
    "runs",
    "analysis_runs",
    "automation_rules",
    "custom_metrics",
    "funds",
)


def _utcnow_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def create_backup(store: Any, dest_dir: str) -> Path:
    """Create a gzipped atomic backup of the store's database.

    Uses ``VACUUM INTO`` for a consistent snapshot even while the
    database is open. Returns the path to the compressed file.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    stamp = _utcnow_stamp()
    raw_name = f"rcm_mc_backup_{stamp}.db"
    gz_name = f"rcm_mc_backup_{stamp}.db.gz"
    raw_path = dest / raw_name
    gz_path = dest / gz_name

    # VACUUM INTO creates an atomic snapshot
    with store.connect() as con:
        con.execute(f"VACUUM INTO ?", (str(raw_path),))

    # Compress
    with open(raw_path, "rb") as f_in:
        with gzip.open(gz_path, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Remove the uncompressed copy
    raw_path.unlink()
    logger.info("backup created: %s", gz_path)
    return gz_path


def restore_backup(backup_path: str, target_db: str) -> bool:
    """Decompress a gzipped backup and copy to target_db.

    After decompression, runs ``PRAGMA integrity_check`` to verify the
    restored database is valid. Returns True on success, False on
    integrity failure.
    """
    backup = Path(backup_path)
    target = Path(target_db)

    if not backup.exists():
        logger.error("backup file not found: %s", backup)
        return False

    target.parent.mkdir(parents=True, exist_ok=True)

    # Decompress to a temp file first, then verify before moving
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with gzip.open(str(backup), "rb") as f_in:
            with open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    except (gzip.BadGzipFile, OSError) as exc:
        logger.error("decompression failed: %s", exc)
        tmp_path.unlink(missing_ok=True)
        return False

    # Integrity check on the decompressed file. Routed through
    # PortfolioStore (campaign target 4E) so the integrity probe
    # uses the same connection-management contract as every other
    # store. The backup file is a temp snapshot, not the canonical
    # store — PortfolioStore's __init__ does NOT auto-init schema
    # (verified at portfolio/store.py:80-81), so this is a
    # read-only probe that won't mutate the file.
    try:
        with PortfolioStore(str(tmp_path)).connect() as con:
            result = con.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            logger.error("integrity check failed on restored backup")
            tmp_path.unlink(missing_ok=True)
            return False
    except Exception as exc:
        # Used to catch sqlite3.DatabaseError specifically;
        # broadening to Exception lets the module fully drop
        # the sqlite3 import. Recovery shape is identical:
        # log, unlink temp, return False.
        logger.error("not a valid SQLite database: %s", exc)
        tmp_path.unlink(missing_ok=True)
        return False

    # Move into place
    shutil.move(str(tmp_path), str(target))
    logger.info("backup restored to %s", target)
    return True


def verify_backup(backup_path: str) -> Dict[str, Any]:
    """Non-destructive verification of a gzipped backup.

    Returns a dict with:
    - ``valid`` (bool)
    - ``integrity`` (str) — result of PRAGMA integrity_check
    - ``tables`` (dict) — row counts for key tables
    - ``error`` (str or None)
    """
    result: Dict[str, Any] = {
        "valid": False,
        "integrity": "",
        "tables": {},
        "error": None,
    }

    backup = Path(backup_path)
    if not backup.exists():
        result["error"] = "file not found"
        return result

    # Decompress to temp
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with gzip.open(str(backup), "rb") as f_in:
            with open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    except (gzip.BadGzipFile, OSError) as exc:
        result["error"] = f"decompression failed: {exc}"
        tmp_path.unlink(missing_ok=True)
        return result

    # Same routing through PortfolioStore as restore_backup — the
    # backup is a temp snapshot, this is a read-only probe.
    try:
        with PortfolioStore(str(tmp_path)).connect() as con:
            check = con.execute("PRAGMA integrity_check").fetchone()
            integrity_str = check[0] if check else "unknown"
            result["integrity"] = integrity_str
            result["valid"] = integrity_str == "ok"

            # Count rows in key tables (skip tables that don't exist)
            all_tables = {
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            table_counts: Dict[str, int] = {}
            for tbl in _KEY_TABLES:
                if tbl in all_tables:
                    count = con.execute(
                        f"SELECT COUNT(*) FROM [{tbl}]"
                    ).fetchone()
                    table_counts[tbl] = count[0] if count else 0
            result["tables"] = table_counts
    except Exception as exc:
        # Broadened from sqlite3.DatabaseError; same recovery shape.
        result["error"] = f"database error: {exc}"
        result["valid"] = False
    finally:
        tmp_path.unlink(missing_ok=True)

    return result
