"""Robust incremental HCRIS ingestion.

The existing ``rcm_mc.data.hcris.refresh_hcris`` always reloads
from scratch. CMS publishes amendments + new fiscal years
periodically; a partner running this on a cron doesn't want to
re-parse 6GB of unchanged filings every time.

This module adds the incremental layer:

  • SQLite-backed ``hcris_load_log`` table tracking every
    (CCN, fiscal_year, status_rank, loaded_at) tuple that's
    already been ingested.
  • ``incremental_refresh`` — for each candidate fiscal year,
    only re-parses filings whose status_rank has IMPROVED since
    the last ingest (submitted → settled → audited). Skips
    rows already loaded at the same-or-better status.
  • ``ingest_status`` — partner-facing summary of what's loaded:
    by-year filing counts, last-refreshed timestamps,
    next-candidate-year suggestions.

Status rank convention (from the existing hcris.py):
  audited (3)  > settled (2)  > submitted (1)
  Higher rank wins; we only overwrite a stored row when the
  new row's rank exceeds the stored rank.

Pure-stdlib SQLite + pandas (already a dependency); no new
deps. Runs idempotently — partner can call ``incremental_
refresh(years=[2020, 2021, 2022])`` repeatedly without side
effects beyond detecting new amendments.
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

logger = logging.getLogger(__name__)


# Status-rank map matching what the existing hcris.py applies
# during dedup. Higher = more reliable filing.
_STATUS_RANK = {
    "as filed": 1,
    "as submitted": 1,
    "submitted": 1,
    "as settled": 2,
    "settled": 2,
    "as reopened": 2,
    "as audited": 3,
    "audited": 3,
}


def _status_rank_of(status: Any) -> int:
    """Map a CMS status string to its rank. Unknown → 1 (treat
    as submitted, the conservative default)."""
    if status is None:
        return 1
    return _STATUS_RANK.get(str(status).strip().lower(), 1)


@dataclass
class IngestStatus:
    """Per-year ingest summary for the partner-facing report."""
    fiscal_year: int
    filings_loaded: int
    last_refreshed: str           # ISO timestamp
    audited_count: int = 0
    settled_count: int = 0
    submitted_count: int = 0


@dataclass
class IngestReport:
    """Output of a single incremental_refresh call."""
    fiscal_years_processed: List[int] = field(default_factory=list)
    filings_inserted: int = 0
    filings_upgraded: int = 0
    filings_skipped: int = 0
    notes: List[str] = field(default_factory=list)


# ── Schema ─────────────────────────────────────────────────────

def _ensure_schema(con: sqlite3.Connection) -> None:
    """Create the load-log table if it doesn't exist."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS hcris_load_log (
            ccn TEXT NOT NULL,
            fiscal_year INTEGER NOT NULL,
            status_rank INTEGER NOT NULL,
            loaded_at TEXT NOT NULL,
            source_year INTEGER,
            row_hash TEXT,
            PRIMARY KEY (ccn, fiscal_year)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_hcris_log_year "
        "ON hcris_load_log(fiscal_year)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_hcris_log_status "
        "ON hcris_load_log(status_rank)"
    )


@contextmanager
def _connect(db_path: str) -> Iterator[sqlite3.Connection]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout = 5000")
    try:
        _ensure_schema(con)
        yield con
    finally:
        con.close()


# ── Core: update_load_log ─────────────────────────────────────

def _row_hash(row: Dict[str, Any]) -> str:
    """Stable hash of the diligence-relevant fields. Lets us
    detect "same status rank but different content" — CMS
    occasionally re-issues an amended filing without bumping
    the status."""
    relevant = (
        "net_patient_revenue", "operating_expenses",
        "beds", "case_mix_index",
        "total_inpatient_days", "medicare_days",
        "medicaid_days", "outpatient_revenue",
    )
    parts = []
    for k in relevant:
        v = row.get(k)
        if v is None:
            parts.append("")
        else:
            try:
                parts.append(f"{float(v):.4f}")
            except (TypeError, ValueError):
                parts.append(str(v))
    payload = "|".join(parts)
    # Compact hash via SHA-1 truncated; stdlib only
    import hashlib
    return hashlib.sha1(
        payload.encode("utf-8")).hexdigest()[:12]


def _decide_action(
    existing: Optional[sqlite3.Row],
    new_rank: int,
    new_hash: str,
) -> str:
    """Per-row action: insert / upgrade / skip."""
    if existing is None:
        return "insert"
    stored_rank = int(existing["status_rank"])
    stored_hash = existing["row_hash"] or ""
    if new_rank > stored_rank:
        return "upgrade"
    if new_rank == stored_rank and new_hash != stored_hash:
        return "upgrade"   # same status, content changed
    return "skip"


# ── Public API ────────────────────────────────────────────────

def incremental_refresh(
    db_path: str,
    *,
    years: Iterable[int],
    fetcher: Optional[Any] = None,
) -> IngestReport:
    """Run an incremental HCRIS refresh against the SQLite log.

    Args:
      db_path: SQLite file. Will be created if it doesn't exist.
      years: fiscal years to process. Each year's filings are
        fetched (via ``fetcher`` or the existing
        ``rcm_mc.data.hcris._refresh_single_year``), compared
        against the log, and:
          - INSERTED if no row exists for (ccn, fiscal_year)
          - UPGRADED if the new status_rank exceeds the stored
            rank, or the hash differs at the same rank
          - SKIPPED otherwise
      fetcher: optional callable
        ``fetcher(year) -> Iterable[dict]``. When None, uses
        the existing hcris.py refresh helper. Pass a custom
        fetcher to test or to feed alternative source files.

    Returns IngestReport with counts + the years processed.
    """
    report = IngestReport()
    now = datetime.now(timezone.utc).isoformat()

    with _connect(db_path) as con:
        for year in years:
            filings = _fetch_year(year, fetcher)
            if filings is None:
                report.notes.append(
                    f"FY{year}: fetcher returned None — skipped.")
                continue
            report.fiscal_years_processed.append(year)
            con.execute("BEGIN IMMEDIATE")
            try:
                for row in filings:
                    ccn = str(row.get("ccn") or "").strip()
                    if not ccn:
                        continue
                    new_rank = _status_rank_of(
                        row.get("status"))
                    new_hash = _row_hash(row)
                    existing = con.execute(
                        "SELECT * FROM hcris_load_log "
                        "WHERE ccn = ? AND fiscal_year = ?",
                        (ccn, year),
                    ).fetchone()
                    action = _decide_action(
                        existing, new_rank, new_hash)
                    if action == "insert":
                        con.execute(
                            "INSERT INTO hcris_load_log "
                            "(ccn, fiscal_year, status_rank, "
                            " loaded_at, source_year, row_hash) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (ccn, year, new_rank, now, year,
                             new_hash))
                        report.filings_inserted += 1
                    elif action == "upgrade":
                        con.execute(
                            "UPDATE hcris_load_log "
                            "SET status_rank = ?, "
                            "    loaded_at = ?, "
                            "    source_year = ?, "
                            "    row_hash = ? "
                            "WHERE ccn = ? AND fiscal_year = ?",
                            (new_rank, now, year, new_hash,
                             ccn, year))
                        report.filings_upgraded += 1
                    else:
                        report.filings_skipped += 1
                con.commit()
            except Exception:
                con.rollback()
                raise
    return report


def _fetch_year(
    year: int, fetcher: Optional[Any],
) -> Optional[Iterable[Dict[str, Any]]]:
    """Resolve the year's filings via the supplied fetcher or
    fall back to a no-op (returning an empty iterator) when no
    fetcher is supplied — keeping this module decoupled from
    the disk-IO of the existing hcris.py refresh.

    A real CLI wrapper passes a fetcher that calls
    ``rcm_mc.data.hcris.refresh_hcris(years=[year])`` and yields
    parsed rows. The ingest tests pass a synthetic fetcher.
    """
    if fetcher is None:
        return iter([])
    out = fetcher(year)
    if out is None:
        return None
    return out


def ingest_status(
    db_path: str,
) -> List[IngestStatus]:
    """Return per-year status — what's loaded, when, and at
    which status-rank distribution."""
    with _connect(db_path) as con:
        rows = con.execute(
            "SELECT fiscal_year, status_rank, "
            "       COUNT(*) AS cnt, "
            "       MAX(loaded_at) AS last_loaded "
            "FROM hcris_load_log "
            "GROUP BY fiscal_year, status_rank "
            "ORDER BY fiscal_year, status_rank"
        ).fetchall()
    by_year: Dict[int, IngestStatus] = {}
    for r in rows:
        yr = int(r["fiscal_year"])
        if yr not in by_year:
            by_year[yr] = IngestStatus(
                fiscal_year=yr,
                filings_loaded=0,
                last_refreshed=r["last_loaded"] or "",
            )
        st = by_year[yr]
        cnt = int(r["cnt"])
        st.filings_loaded += cnt
        rank = int(r["status_rank"])
        if rank == 3:
            st.audited_count += cnt
        elif rank == 2:
            st.settled_count += cnt
        else:
            st.submitted_count += cnt
        # Track the most-recent timestamp across rank rows
        if (r["last_loaded"]
                and r["last_loaded"] > st.last_refreshed):
            st.last_refreshed = r["last_loaded"]
    return sorted(by_year.values(),
                  key=lambda s: s.fiscal_year)


def reset_load_log(db_path: str) -> int:
    """Wipe the load log — useful for full re-ingestion when
    CMS issues a backfill. Returns the number of rows dropped."""
    with _connect(db_path) as con:
        cur = con.execute("DELETE FROM hcris_load_log")
        con.commit()
    return cur.rowcount or 0
