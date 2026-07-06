"""Canonical Census ACS tables + an idempotent SQLite store.

Three normalization targets — one per geography profile, because the
three geographies have different natural keys:

  census_acs_county — one row per county × vintage, keyed by a composed
                      ``{fips5}:{year}`` (fips5 = state+county FIPS).
  census_acs_state  — one row per state × vintage, ``{state_fips}:{year}``.
  census_acs_cbsa   — one row per metro/micro CBSA × vintage,
                      ``{cbsa_code}:{year}``.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the natural id** so a
re-run never double-counts — idempotency is enforced at the table, not
the caller. All SQL is parameterised; the column lists below are the
only interpolated identifiers and they are module constants, never user
input. Estimates stay TEXT (SQLite is dynamically typed; the uniform
``/v1/query`` layer casts explicitly when comparing) — jam values were
already collapsed to NULL by the normalizer.
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

# The measure columns every profile shares, in display order.
_MEASURES = ("total_pop", "median_age", "median_hh_income", "poverty_count",
             "pop_65_plus", "uninsured_rate")

TABLES: Dict[str, TableDef] = {
    "census_acs_county": TableDef(
        "census_acs_county", "county_key",
        ("county_key", "fips5", "state_fips", "county_fips", "name", "year",
         *_MEASURES, *_META),
    ),
    "census_acs_state": TableDef(
        "census_acs_state", "state_key",
        ("state_key", "state_fips", "name", "year", *_MEASURES, *_META),
    ),
    "census_acs_cbsa": TableDef(
        "census_acs_cbsa", "cbsa_key",
        ("cbsa_key", "cbsa_code", "name", "year", *_MEASURES, *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "census_acs_county", "census_acs_state", "census_acs_cbsa",
)


class CensusAcsStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the Census ACS SQLite file directly,
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
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cac_fips5 "
                    "ON census_acs_county(fips5)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cac_state "
                    "ON census_acs_county(state_fips)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cac_year "
                    "ON census_acs_county(year)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cas_state "
                    "ON census_acs_state(state_fips)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cab_cbsa "
                    "ON census_acs_cbsa(cbsa_code)")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's natural PK.

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
