"""Canonical CMS Coverage tables + an idempotent SQLite store.

Two normalization targets:

  dim_coverage_document   — every national + local coverage document
                            (NCD/NCA/CAL/MEDCAC/TA, LCD/Proposed LCD/
                            Article), keyed by a composed
                            ``{document_type}:{document_id}:{document_version}``.
  dim_medicare_contractor — Medicare Administrative Contractors, keyed by
                            ``{contractor_id}:{contractor_version}``.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the native id** so a re-run
never double-counts — idempotency is enforced at the table, not the
caller. All SQL is parameterised; the column lists below are the only
interpolated identifiers and they are module constants, never user input.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class TableDef:
    name: str
    pk: str
    columns: Tuple[str, ...]   # all columns incl. pk, in order

    def create_sql(self) -> str:
        cols = []
        for c in self.columns:
            if c == self.pk:
                cols.append(f"{c} TEXT PRIMARY KEY")
            else:
                cols.append(f"{c} TEXT")
        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n  " + ",\n  ".join(cols) + "\n)"

    def upsert_sql(self) -> str:
        cols = ", ".join(self.columns)
        placeholders = ", ".join("?" for _ in self.columns)
        updates = ", ".join(
            f"{c}=excluded.{c}" for c in self.columns if c != self.pk
        )
        return (
            f"INSERT INTO {self.name} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT({self.pk}) DO UPDATE SET {updates}"
        )


# ── Canonical schema ──────────────────────────────────────────────────
_META = ("source_endpoint", "ingested_at")

TABLES: Dict[str, TableDef] = {
    "dim_coverage_document": TableDef(
        "dim_coverage_document", "document_key",
        ("document_key", "document_id", "document_version",
         "document_display_id", "document_type", "title", "chapter",
         "is_lab", "coverage_level", "contractor_id", "contractor_name",
         "last_updated", "last_updated_sort", "url", *_META),
    ),
    "dim_medicare_contractor": TableDef(
        "dim_medicare_contractor", "contractor_key",
        ("contractor_key", "contractor_id", "contractor_version",
         "contractor_name", "contract_type_id", "contract_subtype_id",
         "contract_number", *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "dim_coverage_document", "dim_medicare_contractor",
)


class CmsCoverageStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the CMS Coverage SQLite file directly,
    mirroring the RCM-MC convention that a single store owns the
    connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer, one worker thread per request) can share the
        # connection. Writes only happen single-threaded in the pipeline, so
        # this does not introduce a write race; WAL + busy_timeout cover the
        # rest.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.ensure_schema()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        for tdef in TABLES.values():
            cur.execute(tdef.create_sql())
        # Helpful secondary indexes for the /v1/query + lookup paths.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_dcd_document_id "
                    "ON dim_coverage_document(document_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_dcd_chapter "
                    "ON dim_coverage_document(chapter)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_dcd_contractor "
                    "ON dim_coverage_document(contractor_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_dmc_contractor_id "
                    "ON dim_medicare_contractor(contractor_id)")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's native PK.

        Rows are dicts of column→value; missing columns default to NULL,
        extra keys are ignored. Returns the number of rows written.
        """
        if not rows:
            return 0
        tdef = TABLES[table]
        now = _utc_now()
        sql = tdef.upsert_sql()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            self.conn.executemany(sql, params)
        return len(params)

    def count(self, table: str, where: str = "", args: Sequence[Any] = ()) -> int:
        sql = f"SELECT COUNT(*) AS n FROM {table}"
        if where:
            sql += f" WHERE {where}"
        row = self.conn.execute(sql, tuple(args)).fetchone()
        return int(row["n"]) if row else 0

    def fetchall(self, sql: str, args: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return list(self.conn.execute(sql, tuple(args)).fetchall())

    def close(self) -> None:
        self.conn.close()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _coerce(value: Any) -> Any:
    """SQLite stores TEXT; coerce lists/dicts to JSON and scalars to str.

    None stays None (NULL). We keep everything TEXT so the uniform
    ``/v1/query`` layer has one type model — numeric comparisons there
    cast explicitly.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
