"""Canonical QCEW table + an idempotent SQLite store.

One normalization target:

  qcew_industry_area — quarterly QCEW observations (one row per
                       area x ownership x industry x quarter), shared
                       by BOTH datasets: the ``industry_area`` slice
                       (all areas for one industry) and the
                       ``area_industry`` slice (all industries for one
                       area). ``source_endpoint`` slices them apart,
                       and the slice key is part of the composed pk —
                       see normalize.py for why.

The column list is a snapshot of the LIVE quarterly slice header
(sampled 2026-07-06 from ``/cew/data/api/2025/4/industry/622.csv`` and
``/cew/data/api/2025/4/area/48453.csv`` — both publish the identical
42 columns, which is exactly what makes the shared table sound). QCEW
headers are already lowercase snake_case, so the snapshot is verbatim;
normalize.py asserts that property instead of rewriting names. Every
published column is kept, including the ``lq_*`` location quotients
and ``oty_*`` over-the-year changes.

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the composed natural id**
so a re-run never double-counts — idempotency is enforced at the table,
not the caller. All SQL is parameterised; the column list below is the
only interpolated identifier set and it is a module constant, never
user input. Values stay TEXT (SQLite is dynamically typed; the uniform
query layer casts explicitly when it needs numbers).
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
        return (f"CREATE TABLE IF NOT EXISTS {self.name} (\n  "
                + ",\n  ".join(cols) + "\n)")

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

# Live header of the quarterly CSV slices (identical for industry- and
# area-cut files; verified 2026-07-06), kept verbatim in file order.
_QCEW_COLUMNS: Tuple[str, ...] = (
    "area_fips", "own_code", "industry_code", "agglvl_code", "size_code",
    "year", "qtr", "disclosure_code",
    "qtrly_estabs", "month1_emplvl", "month2_emplvl", "month3_emplvl",
    "total_qtrly_wages", "taxable_qtrly_wages", "qtrly_contributions",
    "avg_wkly_wage",
    "lq_disclosure_code", "lq_qtrly_estabs", "lq_month1_emplvl",
    "lq_month2_emplvl", "lq_month3_emplvl", "lq_total_qtrly_wages",
    "lq_taxable_qtrly_wages", "lq_qtrly_contributions", "lq_avg_wkly_wage",
    "oty_disclosure_code", "oty_qtrly_estabs_chg",
    "oty_qtrly_estabs_pct_chg", "oty_month1_emplvl_chg",
    "oty_month1_emplvl_pct_chg", "oty_month2_emplvl_chg",
    "oty_month2_emplvl_pct_chg", "oty_month3_emplvl_chg",
    "oty_month3_emplvl_pct_chg", "oty_total_qtrly_wages_chg",
    "oty_total_qtrly_wages_pct_chg", "oty_taxable_qtrly_wages_chg",
    "oty_taxable_qtrly_wages_pct_chg", "oty_qtrly_contributions_chg",
    "oty_qtrly_contributions_pct_chg", "oty_avg_wkly_wage_chg",
    "oty_avg_wkly_wage_pct_chg",
)

TABLES: Dict[str, TableDef] = {
    "qcew_industry_area": TableDef(
        "qcew_industry_area", "qcew_key",
        ("qcew_key", *_QCEW_COLUMNS, *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = ("qcew_industry_area",)


class BlsQcewStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the QCEW SQLite file directly,
    mirroring the RCM-MC convention that a single store owns the
    connection.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        # check_same_thread=False so the read-only HTTP surface
        # (ThreadingHTTPServer, one worker thread per request) can share
        # the connection. Writes only happen single-threaded in the
        # pipeline, so this does not introduce a write race; WAL +
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
        # Helpful secondary indexes for the /v1/query + lookup paths:
        # county and industry slicing dominate, always inside a quarter.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_qcew_area "
                    "ON qcew_industry_area(area_fips)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_qcew_industry "
                    "ON qcew_industry_area(industry_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_qcew_year_qtr "
                    "ON qcew_industry_area(year, qtr)")
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

    def count(self, table: str, where: str = "",
              args: Sequence[Any] = ()) -> int:
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
