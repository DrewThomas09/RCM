"""Orchestrator for the four core CMS public-data sources.

This module owns the ``hospital_benchmarks`` and ``data_source_status``
tables and the top-level refresh loop that keeps them fresh. The
individual source loaders (``cms_hcris``, ``cms_care_compare``,
``cms_utilization``, ``irs990_loader``) do the actual
download/parse/load work; this module sequences them, records
provenance, and produces a :class:`RefreshReport`.

Design:

- Each source is an opaque ``(name, refresh_fn)`` pair. Adding a new
  CMS dataset is a one-liner in ``SOURCES``.
- ``refresh_fn`` takes the store and returns an int: records loaded.
  Any exception → the source's row in ``data_source_status`` is marked
  ``ERROR`` with the exception message, and the next source still
  runs. Partial failure shouldn't kill the pipeline.
- All writes to ``hospital_benchmarks`` go through :func:`save_benchmarks`
  here, which normalizes the (provider_id, source, metric_key, period)
  tuple so downstream queries are consistent.
"""
from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────

KNOWN_SOURCES: Tuple[str, ...] = (
    "hcris",
    "care_compare",
    "utilization",
    "irs990",
    "cms_pos",
)

# Allowed status values for data_source_status.status.
_STATUS_OK = "OK"
_STATUS_STALE = "STALE"
_STATUS_ERROR = "ERROR"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_refresh(interval_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=int(interval_days))).isoformat()


# ── Tables ────────────────────────────────────────────────────────────

def _ensure_tables(store: Any) -> None:
    """Idempotent CREATE for the two public-data tables.

    Kept here rather than in :mod:`rcm_mc.portfolio.store` so the
    benchmarks layer owns its own schema — the portfolio store has no
    reason to know the hospital-benchmark columns exist.
    """
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS hospital_benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT NOT NULL,
                source TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                value REAL,
                text_value TEXT,
                period TEXT,
                loaded_at TEXT NOT NULL,
                quality_flags TEXT
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_hb_provider "
            "ON hospital_benchmarks(provider_id)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_hb_source_metric "
            "ON hospital_benchmarks(source, metric_key)"
        )
        # Dedup key — one row per (provider_id, source, metric_key, period).
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_hb_dedup "
            "ON hospital_benchmarks(provider_id, source, metric_key, period)"
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


# ── Benchmark writes ──────────────────────────────────────────────────

def save_benchmarks(
    store: Any,
    rows: Iterable[Dict[str, Any]],
    *,
    source: str,
    period: Optional[str] = None,
) -> int:
    """Upsert ``rows`` into ``hospital_benchmarks``.

    Each row is a dict with keys:
      - ``provider_id`` (required)
      - ``metric_key`` (required)
      - ``value`` (required, numeric or None)
      - ``period`` (optional; defaults to the outer ``period`` arg)
      - ``quality_flags`` (optional list; serialized JSON)

    On conflict with ``(provider_id, source, metric_key, period)`` we
    replace — most recent load wins. Partners fixing a mis-loaded row
    by re-running the refresh should see their fix applied.
    """
    _ensure_tables(store)
    loaded_at = _utcnow_iso()
    n = 0
    with store.connect() as con:
        for r in rows:
            try:
                pid = str(r["provider_id"])
                mk = str(r["metric_key"])
            except KeyError:
                continue
            val = r.get("value")
            text_val: Optional[str] = None
            v: Optional[float] = None
            # Accept either a numeric value or a string. Strings go in
            # text_value; numbers go in value. Lets one table carry both
            # ``bed_count = 420`` and ``state = "IL"``.
            if isinstance(val, str):
                text_val = val
            elif val is not None:
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    text_val = str(val)
            per = str(r.get("period") or period or "")
            flags = r.get("quality_flags")
            flags_json = json.dumps(list(flags)) if flags else None
            con.execute(
                """INSERT INTO hospital_benchmarks
                   (provider_id, source, metric_key, value, text_value, period, loaded_at, quality_flags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(provider_id, source, metric_key, period)
                   DO UPDATE SET
                     value = excluded.value,
                     text_value = excluded.text_value,
                     loaded_at = excluded.loaded_at,
                     quality_flags = excluded.quality_flags""",
                (pid, str(source), mk, v, text_val, per, loaded_at, flags_json),
            )
            n += 1
        con.commit()
    return n


def query_hospitals(
    store: Any,
    *,
    state: Optional[str] = None,
    beds_min: Optional[int] = None,
    beds_max: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Search the benchmark database by structural attributes.

    Returns a list of ``{provider_id, metrics: {...}}`` dicts ordered by
    ``provider_id`` for deterministic test output. Filters:

    - ``state``     — matches the ``state`` metric_key (case-insensitive)
    - ``beds_min``  — minimum ``bed_count`` value
    - ``beds_max``  — maximum ``bed_count`` value

    Providers missing the relevant filter metric are excluded from that
    filter's match set (i.e. "no bed_count → doesn't survive
    ``beds_min=100``").
    """
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT provider_id, metric_key, value, text_value, period, source "
            "FROM hospital_benchmarks"
        ).fetchall()

    by_pid: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        pid = r["provider_id"]
        d = by_pid.setdefault(pid, {"provider_id": pid, "metrics": {}})
        mk = r["metric_key"]
        val = r["value"] if r["value"] is not None else r["text_value"]
        # Last-source-wins within a given metric (sources are ordered
        # by refresh cadence; we don't care which one "won" for a filter).
        d["metrics"].setdefault(mk, val)

    state_norm = (state or "").upper().strip()
    filtered: List[Dict[str, Any]] = []
    for pid, entry in by_pid.items():
        m = entry["metrics"]
        if state_norm:
            s = str(m.get("state") or "").upper()
            if s != state_norm:
                continue
        if beds_min is not None or beds_max is not None:
            bc = m.get("bed_count")
            if bc is None:
                continue
            try:
                bc_f = float(bc)
            except (TypeError, ValueError):
                continue
            if beds_min is not None and bc_f < float(beds_min):
                continue
            if beds_max is not None and bc_f > float(beds_max):
                continue
        filtered.append(entry)

    filtered.sort(key=lambda e: e["provider_id"])
    return filtered[: int(limit)]


# ── Status tracking ───────────────────────────────────────────────────

def set_status(
    store: Any,
    source_name: str,
    *,
    status: str,
    record_count: int = 0,
    error_detail: Optional[str] = None,
    interval_days: int = 30,
) -> None:
    _ensure_tables(store)
    now = _utcnow_iso()
    nxt = _next_refresh(interval_days) if status != _STATUS_ERROR else None
    with store.connect() as con:
        con.execute(
            """INSERT INTO data_source_status
               (source_name, last_refresh_at, record_count, next_refresh_at,
                status, error_detail, interval_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source_name) DO UPDATE SET
                 last_refresh_at = excluded.last_refresh_at,
                 record_count = excluded.record_count,
                 next_refresh_at = excluded.next_refresh_at,
                 status = excluded.status,
                 error_detail = excluded.error_detail,
                 interval_days = excluded.interval_days""",
            (str(source_name), now, int(record_count), nxt,
             str(status), error_detail, int(interval_days)),
        )
        con.commit()


def get_status(store: Any, source_name: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_tables(store)
    with store.connect() as con:
        if source_name:
            rows = con.execute(
                "SELECT * FROM data_source_status WHERE source_name = ?",
                (str(source_name),),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM data_source_status ORDER BY source_name"
            ).fetchall()
    return [dict(r) for r in rows]


def schedule_refresh(store: Any, *, interval_days: int = 30) -> None:
    """Seed ``data_source_status`` with one row per known source.

    Safe to call repeatedly. Does NOT trigger a refresh — just records
    the schedule. Existing rows keep their last_refresh_at / status.
    """
    _ensure_tables(store)
    now_iso = _utcnow_iso()
    nxt = _next_refresh(interval_days)
    with store.connect() as con:
        for name in KNOWN_SOURCES:
            row = con.execute(
                "SELECT source_name FROM data_source_status WHERE source_name = ?",
                (name,),
            ).fetchone()
            if row is None:
                con.execute(
                    """INSERT INTO data_source_status
                       (source_name, last_refresh_at, record_count, next_refresh_at,
                        status, error_detail, interval_days)
                       VALUES (?, NULL, 0, ?, ?, NULL, ?)""",
                    (name, nxt, _STATUS_STALE, int(interval_days)),
                )
        con.commit()


# ── Orchestrator ──────────────────────────────────────────────────────

@dataclass
class RefreshSourceResult:
    source: str
    status: str = _STATUS_OK
    record_count: int = 0
    error_detail: Optional[str] = None
    duration_secs: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RefreshReport:
    started_at: str = ""
    finished_at: str = ""
    per_source: List[RefreshSourceResult] = field(default_factory=list)

    @property
    def total_records(self) -> int:
        return sum(r.record_count for r in self.per_source)

    @property
    def any_errors(self) -> bool:
        return any(r.status == _STATUS_ERROR for r in self.per_source)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "per_source": [r.to_dict() for r in self.per_source],
            "total_records": self.total_records,
            "any_errors": self.any_errors,
        }


def _default_refreshers() -> Dict[str, Callable[[Any], int]]:
    """Lazy-imported source functions.

    Kept lazy so importing ``data_refresh`` doesn't pull in pandas-heavy
    parsers when a caller only wants the table helpers.
    """
    def _hcris(store):
        from . import cms_hcris
        return cms_hcris.refresh_hcris_source(store)

    def _care_compare(store):
        from . import cms_care_compare
        return cms_care_compare.refresh_care_compare_source(store)

    def _utilization(store):
        from . import cms_utilization
        return cms_utilization.refresh_utilization_source(store)

    def _irs990(store):
        from . import irs990_loader
        return irs990_loader.refresh_irs990_source(store)

    def _cms_pos(store):
        from . import cms_pos
        return cms_pos.refresh_pos_source(store)

    return {
        "hcris": _hcris,
        "care_compare": _care_compare,
        "utilization": _utilization,
        "irs990": _irs990,
        "cms_pos": _cms_pos,
    }


def refresh_all_sources(
    store: Any,
    *,
    sources: Optional[Iterable[str]] = None,
    interval_days: int = 30,
    refreshers: Optional[Dict[str, Callable[[Any], int]]] = None,
) -> RefreshReport:
    """Refresh one or more CMS data sources.

    ``sources`` — subset of ``KNOWN_SOURCES`` or ``None`` for all.
    ``refreshers`` — override dict of ``name → callable(store) -> int``
    so tests can swap in deterministic stubs without actual downloads.
    """
    _ensure_tables(store)
    refreshers = refreshers if refreshers is not None else _default_refreshers()
    selected = list(sources) if sources else list(KNOWN_SOURCES)

    report = RefreshReport(started_at=_utcnow_iso())
    for name in selected:
        fn = refreshers.get(name)
        if fn is None:
            report.per_source.append(RefreshSourceResult(
                source=name, status=_STATUS_ERROR,
                error_detail=f"no refresher registered for {name!r}",
            ))
            set_status(store, name, status=_STATUS_ERROR,
                       error_detail=f"no refresher registered",
                       interval_days=interval_days)
            continue
        t0 = datetime.now(timezone.utc)
        try:
            count = int(fn(store) or 0)
            elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
            report.per_source.append(RefreshSourceResult(
                source=name, status=_STATUS_OK,
                record_count=count, duration_secs=elapsed,
            ))
            set_status(store, name, status=_STATUS_OK,
                       record_count=count, interval_days=interval_days)
        except Exception as exc:  # noqa: BLE001 — partial failures are tolerated
            elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
            detail = f"{type(exc).__name__}: {exc}"
            logger.warning("refresh failed for %s: %s", name, detail)
            logger.debug("traceback:\n%s", traceback.format_exc())
            report.per_source.append(RefreshSourceResult(
                source=name, status=_STATUS_ERROR,
                error_detail=detail, duration_secs=elapsed,
            ))
            set_status(store, name, status=_STATUS_ERROR,
                       error_detail=detail, interval_days=interval_days)
    report.finished_at = _utcnow_iso()
    return report


# ── Staleness helper ──────────────────────────────────────────────────

def mark_stale_sources(store: Any) -> List[str]:
    """Flip any source past its ``next_refresh_at`` to ``STALE``.

    Returns the list of sources marked. Non-destructive: sources in
    ``ERROR`` are left alone (their error is the salient fact).
    """
    _ensure_tables(store)
    now = datetime.now(timezone.utc)
    marked: List[str] = []
    for row in get_status(store):
        if row.get("status") == _STATUS_ERROR:
            continue
        nxt = row.get("next_refresh_at")
        if not nxt:
            continue
        try:
            due = datetime.fromisoformat(nxt)
        except ValueError:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now and row.get("status") != _STATUS_STALE:
            with store.connect() as con:
                con.execute(
                    "UPDATE data_source_status SET status = ? WHERE source_name = ?",
                    (_STATUS_STALE, row["source_name"]),
                )
                con.commit()
            marked.append(row["source_name"])
    return marked
