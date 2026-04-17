"""Stale-analysis detector and auto-refresh scheduler.

Partners build analysis packets from the latest data. When a public
data source refreshes (HCRIS, Care Compare, etc.) *after* the packet
was built, the packet is stale — conclusions might change with the new
data. This module detects that gap and optionally rebuilds the stalest
packets.

Design:
- Detection compares each deal's latest packet ``created_at`` against
  ``data_source_status.last_refresh_at`` for every source. If any
  source refreshed after the packet, the packet is stale.
- Auto-refresh calls ``get_or_build_packet(force_rebuild=True)`` on
  the top-N stalest deals, capped at ``max_refreshes`` to avoid
  overwhelming the system on a big refresh day.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StaleAnalysis:
    """One deal whose latest packet is behind at least one data source."""
    deal_id: str
    packet_age_days: int
    stale_sources: List[str] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_tables_exist(store: Any) -> None:
    """Make sure the tables we read exist (idempotent)."""
    store.init_db()
    # analysis_runs table
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                scenario_id TEXT,
                as_of TEXT,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                packet_json BLOB NOT NULL,
                hash_inputs TEXT NOT NULL,
                run_id TEXT NOT NULL,
                notes TEXT
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS data_source_status (
                source_name TEXT PRIMARY KEY,
                last_refresh_at TEXT,
                record_count INTEGER DEFAULT 0,
                next_refresh_at TEXT,
                status TEXT,
                error_detail TEXT,
                interval_days INTEGER DEFAULT 30
            )"""
        )
        con.commit()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string, returning None on failure."""
    if not s:
        return None
    try:
        # Handle both +00:00 and Z suffixes
        cleaned = s.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def detect_stale_analyses(store: Any) -> List[StaleAnalysis]:
    """Check each deal's latest packet against data-source refresh times.

    Returns a list of :class:`StaleAnalysis` sorted by staleness
    (most stale first).
    """
    _ensure_tables_exist(store)
    now = _utcnow()

    # Get latest packet created_at per deal
    with store.connect() as con:
        packet_rows = con.execute(
            """SELECT deal_id, MAX(created_at) AS latest_at
               FROM analysis_runs
               GROUP BY deal_id"""
        ).fetchall()

        source_rows = con.execute(
            "SELECT source_name, last_refresh_at FROM data_source_status"
        ).fetchall()

    if not packet_rows or not source_rows:
        return []

    # Parse source refresh times
    source_refreshes: Dict[str, datetime] = {}
    for sr in source_rows:
        dt = _parse_iso(sr["last_refresh_at"])
        if dt is not None:
            source_refreshes[sr["source_name"]] = dt

    if not source_refreshes:
        return []

    results: List[StaleAnalysis] = []
    for pr in packet_rows:
        deal_id = pr["deal_id"]
        packet_dt = _parse_iso(pr["latest_at"])
        if packet_dt is None:
            continue

        stale_sources: List[str] = []
        for src_name, refresh_dt in source_refreshes.items():
            # Make both tz-aware for comparison
            pdt = packet_dt if packet_dt.tzinfo else packet_dt.replace(tzinfo=timezone.utc)
            rdt = refresh_dt if refresh_dt.tzinfo else refresh_dt.replace(tzinfo=timezone.utc)
            if rdt > pdt:
                stale_sources.append(src_name)

        if stale_sources:
            pdt = packet_dt if packet_dt.tzinfo else packet_dt.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - pdt).days)
            results.append(StaleAnalysis(
                deal_id=deal_id,
                packet_age_days=age_days,
                stale_sources=sorted(stale_sources),
            ))

    results.sort(key=lambda s: s.packet_age_days, reverse=True)
    return results


def auto_refresh_stale(
    store: Any,
    *,
    max_refreshes: int = 10,
) -> List[str]:
    """Rebuild the top-N stalest packets.

    Returns a list of deal_ids that were refreshed. Failures are
    logged and skipped — we don't let one bad deal block the rest.
    """
    from .analysis_store import get_or_build_packet

    stale = detect_stale_analyses(store)
    to_refresh = stale[:max_refreshes]
    refreshed: List[str] = []

    for sa in to_refresh:
        try:
            get_or_build_packet(store, sa.deal_id, force_rebuild=True)
            refreshed.append(sa.deal_id)
        except Exception:
            logger.warning(
                "auto_refresh failed for deal %s", sa.deal_id,
                exc_info=True,
            )

    return refreshed
