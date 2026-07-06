"""Canonical OIG LEIE tables + an idempotent SQLite store.

Two normalization targets:

  oig_exclusions     — the cumulative exclusion list. The monthly
                       ``{yy}{mm}excl.csv`` supplements upsert (merge)
                       here; a *complete* pull of the full-replacement
                       UPDATED.csv atomically REPLACES the whole table
                       via :meth:`OigLeieStore.replace_all` (the full
                       file is cumulative and supersedes the previous
                       full pull plus every supplement — a merge would
                       keep reinstated providers flagged forever). A
                       row-capped/partial full pull falls back to
                       merge-only with a warning. ``source_endpoint``
                       records which pull last touched each row.
  oig_reinstatements — monthly reinstatement rows (providers removed
                       from the LEIE; ``reindate`` populated). Kept in
                       their own table because a reinstated provider is
                       *absent* from the current full file — mixing them
                       into oig_exclusions would re-flag cleared
                       providers.

Column lists are snapshots of the LIVE header row (sampled 2026-07-06:
LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,
ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,WVRSTATE)
passed through :func:`connectors.oig_leie.normalize.snake`; every
published column is kept.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the composed natural id**
so a re-run never double-counts — idempotency is enforced at the table,
not the caller. All SQL is parameterised; the column lists below are the
only interpolated identifiers and they are module constants, never user
input.
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

# The live 18-column LEIE header, snake_cased in file order. Both files
# (full + supplements, exclusions + reinstatements) publish exactly this
# shape (verified live 2026-07-06).
_LEIE_COLUMNS: Tuple[str, ...] = (
    "lastname", "firstname", "midname", "busname", "general", "specialty",
    "upin", "npi", "dob", "address", "city", "state", "zip", "excltype",
    "excldate", "reindate", "waiverdate", "wvrstate",
)

TABLES: Dict[str, TableDef] = {
    "oig_exclusions": TableDef(
        "oig_exclusions", "exclusion_key",
        ("exclusion_key", *_LEIE_COLUMNS, *_META),
    ),
    "oig_reinstatements": TableDef(
        "oig_reinstatements", "reinstatement_key",
        ("reinstatement_key", *_LEIE_COLUMNS, *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = ("oig_exclusions", "oig_reinstatements")


class OigLeieStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the LEIE SQLite file directly,
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
        # NPI and name are the compliance-screening access patterns;
        # state/excldate serve the analytic slices.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_excl_npi "
                    "ON oig_exclusions(npi)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_excl_lastname "
                    "ON oig_exclusions(lastname)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_excl_busname "
                    "ON oig_exclusions(busname)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_excl_state "
                    "ON oig_exclusions(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_excl_excldate "
                    "ON oig_exclusions(excldate)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rein_npi "
                    "ON oig_reinstatements(npi)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rein_lastname "
                    "ON oig_reinstatements(lastname)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rein_busname "
                    "ON oig_reinstatements(busname)")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's natural PK.

        Rows are dicts of column→value; missing columns default to NULL,
        extra keys are ignored. Returns the number of rows written.
        """
        if not rows:
            return 0
        tdef = TABLES[table]
        sql = tdef.upsert_sql()
        params = self._row_params(tdef, rows)
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            self.conn.executemany(sql, params)
        return len(params)

    def replace_all(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Atomically replace the ENTIRE contents of ``table`` with ``rows``.

        One transaction: DELETE every existing row, then write the fresh
        snapshot (rolled back wholly on any error, so a reader never
        observes an empty or half-written table). Used by the connector
        when a *complete* full-replacement file (``UPDATED.csv``) was
        ingested: the full LEIE is cumulative and supersedes both the
        previous full pull and every monthly supplement merged since, so
        rows absent from the new snapshot (reinstated providers) must
        disappear — a merge-only write would flag them excluded forever.

        The snapshot insert still uses the upsert statement so the
        couple dozen byte-identical duplicate source lines in the live
        file collapse exactly as they do on the merge path. Returns the
        number of rows written (before duplicate-key collapse).
        """
        tdef = TABLES[table]
        sql = tdef.upsert_sql()
        params = self._row_params(tdef, rows)
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            self.conn.execute(f"DELETE FROM {tdef.name}")  # noqa: S608 (module-constant name)
            if params:
                self.conn.executemany(sql, params)
        return len(params)

    @staticmethod
    def _row_params(tdef: TableDef, rows: Sequence[Dict[str, Any]]
                    ) -> List[Tuple[Any, ...]]:
        now = _utc_now()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        return params

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
