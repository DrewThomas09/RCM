"""Canonical data.cdc.gov tables + an idempotent SQLite store.

Twenty-nine normalization targets — one catalog table, twenty-seven
curated dataset tables whose columns are live-sampled snapshots of the
real Socrata field names (see :mod:`connectors.cdc_data.endpoints`), and
one generic JSON-blob table so ANY 4x4 on the domain stays queryable:

  cdc_data_catalog     — every dataset on data.cdc.gov, keyed by 4x4 id.
  cdc_places_county …  — curated tables, keyed by a composed natural key
                         built in :mod:`connectors.cdc_data.normalize`.
  cdc_data_rows        — generic fetched rows, keyed by
                         ``{dataset_key}:{row_idx}`` with ``dataset_key``
                         mirrored into ``source_endpoint`` so the query
                         engine's slice-pinning grammar still works.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the natural id** so a
re-run never double-counts — idempotency is enforced at the table, not
the caller. All SQL is parameterised; the column lists below are the
only interpolated identifiers and they are module constants, never user
input. Everything is stored TEXT (SQLite is dynamically typed; the
uniform ``/v1/query`` layer keeps one type model) except ``row_idx``,
declared INTEGER so generic-row ordering is numeric.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from .endpoints import curated_endpoints


@dataclass(frozen=True)
class TableDef:
    name: str
    pk: str
    columns: Tuple[str, ...]        # all columns incl. pk, in order
    int_columns: Tuple[str, ...] = ()   # declared INTEGER (affinity only)

    def create_sql(self) -> str:
        cols = []
        for c in self.columns:
            if c == self.pk:
                cols.append(f"{c} TEXT PRIMARY KEY")
            elif c in self.int_columns:
                cols.append(f"{c} INTEGER")
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

# Curated tables derive their column lists from the EndpointSpec column
# snapshots so the schema and the live-sample stay one source of truth.
_CURATED_TABLES: Dict[str, TableDef] = {
    spec.target_table: TableDef(
        spec.target_table, "record_key",
        ("record_key", *spec.columns, *_META),
    )
    for spec in curated_endpoints()
}

TABLES: Dict[str, TableDef] = {
    "cdc_data_catalog": TableDef(
        "cdc_data_catalog", "dataset_uid",
        ("dataset_uid", "name", "description", "category", "attribution",
         "provenance", "update_frequency", "created_at", "data_updated_at",
         "metadata_updated_at", "updated_at", "data_uri", "web_uri",
         "license", "tags", "hide_from_catalog", *_META),
    ),
    **_CURATED_TABLES,
    "cdc_data_rows": TableDef(
        "cdc_data_rows", "row_key",
        ("row_key", "dataset_key", "row_idx", "row_json", "fetched_at",
         *_META),
        int_columns=("row_idx",),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = tuple(TABLES)


class CdcDataStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the cdc_data SQLite file directly,
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
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cat_category "
                    "ON cdc_data_catalog(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_cat_name "
                    "ON cdc_data_catalog(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_places_fips "
                    "ON cdc_places_county(locationid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_places_state "
                    "ON cdc_places_county(stateabbr)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_places_measure "
                    "ON cdc_places_county(measureid)")
        # County CKD prevalence (PLACES 2023 KIDNEY measure) keyed by FIPS
        # for the county-health lookup.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_ckd_fips "
                    "ON cdc_places_county_ckd(locationid)")
        # County datasets from the 2026-07 sweep that the county-health
        # lookup fans a FIPS across (all key counties by 5-digit FIPS).
        cur.execute("CREATE INDEX IF NOT EXISTS ix_teenbirth_fips "
                    "ON cdc_teen_birth_county(combined_fips_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_stroke_fips "
                    "ON cdc_stroke_mortality_county(locationid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_injury_fips "
                    "ON cdc_injury_violence_county(geoid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rows_dataset "
                    "ON cdc_data_rows(dataset_key)")
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
    cast explicitly. (``row_idx``'s INTEGER affinity converts its numeric
    string back to an int at the storage layer.)
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
