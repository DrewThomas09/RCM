"""The canonical RxNorm tables + an idempotent SQLite store.

Three normalization targets for this workstream:

  dim_rxnorm_concept  — one row per RxCUI: name, term type, ingredient
                        set, ATC / DailyMed class set. The drug
                        dimension the money tables join to.
  xwalk_ndc_rxcui     — one row per NDC → RxCUI. The join bridge to
                        NADAC, State Drug Utilization, Part B/D spending
                        and the openFDA NDC directory.
  xwalk_name_rxcui    — one row per free-text drug name → RxCUI, keeping
                        which candidate string actually matched
                        (``matched_on``) and whether the match was exact
                        or approximate, so a downstream analyst can tell
                        a confident join from a fuzzy one.

Ingredient and class sets are stored as ``; ``-joined TEXT (the estate's
all-TEXT storage model) with the count alongside, so a caller can filter
single-ingredient products without parsing.

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
    "dim_rxnorm_concept": TableDef(
        "dim_rxnorm_concept", "rxcui",
        ("rxcui", "name", "tty", "synonym", "ingredients", "n_ingredients",
         "atc_classes", "dailymed_classes", "class_source", "raw", *_META),
    ),
    "xwalk_ndc_rxcui": TableDef(
        "xwalk_ndc_rxcui", "ndc",
        ("ndc", "ndc_digits", "rxcui", "resolved_name", "raw", *_META),
    ),
    "xwalk_name_rxcui": TableDef(
        "xwalk_name_rxcui", "name_key",
        ("name_key", "query_name", "rxcui", "resolved_name", "matched_on",
         "match_type", "raw", *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "dim_rxnorm_concept", "xwalk_ndc_rxcui", "xwalk_name_rxcui")


class RxNormStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the RxNorm SQLite file directly,
    mirroring the RCM-MC convention that a single store owns the
    connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer, one worker thread per request) can share the
        # connection. Writes only happen single-threaded, so this does not
        # introduce a write race; WAL + busy_timeout cover the rest.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.ensure_schema()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        for tdef in TABLES.values():
            cur.execute(tdef.create_sql())
        # Secondary indexes for the /v1/query + lookup filter paths. The
        # rxcui indexes are the ones that matter: every join from a money
        # table lands on them.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rxnorm_ndc_rxcui "
                    "ON xwalk_ndc_rxcui(rxcui)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rxnorm_name_rxcui "
                    "ON xwalk_name_rxcui(rxcui)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_rxnorm_concept_name "
                    "ON dim_rxnorm_concept(name)")
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

    None stays None (NULL). Everything else is TEXT so the uniform
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
