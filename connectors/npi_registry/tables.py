"""Canonical NPI tables + an idempotent SQLite store.

Three normalization targets:

  dim_provider           (one row per NPI; primary practice address +
                          primary taxonomy flattened onto the row)
  fact_provider_taxonomy (one row per (npi, taxonomy code))
  fact_provider_address  (one row per (npi, address_purpose))

Storage is SQLite to match the rest of RCM (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the native id** so a
re-run or an overlapping seed never double-counts — idempotency is
enforced at the table, not the caller. All SQL is parameterised; the
column lists below are the only interpolated identifiers and they are
module constants, never user input.
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
    "dim_provider": TableDef(
        "dim_provider", "npi",
        ("npi", "enumeration_type", "status", "first_name", "last_name",
         "credential", "organization_name", "sole_proprietor", "gender",
         "enumeration_date", "last_updated", "primary_taxonomy_code",
         "primary_taxonomy_desc", "primary_license", "primary_license_state",
         "city", "state", "postal_code", "country_code", "telephone", *_META),
    ),
    "fact_provider_taxonomy": TableDef(
        "fact_provider_taxonomy", "taxonomy_key",
        ("taxonomy_key", "npi", "code", "desc", "is_primary", "state",
         "license", *_META),
    ),
    "fact_provider_address": TableDef(
        "fact_provider_address", "address_key",
        ("address_key", "npi", "address_purpose", "address_1", "address_2",
         "city", "state", "postal_code", "country_code", "telephone_number",
         *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "dim_provider", "fact_provider_taxonomy", "fact_provider_address",
)


class NpiStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the NPI SQLite file directly, mirroring
    the RCM convention that a single store owns the connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer) can share the connection. Writes only
        # happen single-threaded at ingest, so no write race; WAL +
        # busy_timeout cover the rest.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.ensure_schema()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        for tdef in TABLES.values():
            cur.execute(tdef.create_sql())
        # Helpful secondary indexes for the /v1/query filter paths.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_prov_state "
                    "ON dim_provider(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_prov_ptax "
                    "ON dim_provider(primary_taxonomy_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_tax_npi "
                    "ON fact_provider_taxonomy(npi)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_tax_code "
                    "ON fact_provider_taxonomy(code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_addr_npi "
                    "ON fact_provider_address(npi)")
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

    None stays None (NULL). Everything is TEXT so the uniform
    ``/v1/query`` layer has one type model.
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
