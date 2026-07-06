"""Canonical NIH RePORTER tables + an idempotent SQLite store.

Two normalization targets:

  nih_projects     — one row per NIH funding application (project ×
                     fiscal-year × subproject), keyed by RePORTER's
                     globally unique ``appl_id``.
  nih_publications — the project ↔ PubMed link edges RePORTER exposes,
                     keyed by a composed ``{pmid}:{applid}`` (one paper
                     can acknowledge many applications and vice versa).

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
# Column names snapshot the live v2 field names (probed 2026-07), flattened
# per connectors/nih_reporter/normalize.py. Everything is TEXT — SQLite is
# dynamically typed and the uniform /v1/query layer owns explicit casts.
_META = ("source_endpoint", "ingested_at")

TABLES: Dict[str, TableDef] = {
    "nih_projects": TableDef(
        "nih_projects", "appl_id",
        ("appl_id", "project_num", "core_project_num", "subproject_id",
         "project_serial_num", "fiscal_year", "project_title",
         "activity_code", "award_type", "agency_code", "agency_ic_admin",
         "agency_ic_admin_name", "funding_mechanism", "mechanism_code_dc",
         "cfda_code", "opportunity_number", "full_study_section",
         "org_name", "org_city", "org_state", "org_country", "org_zipcode",
         "org_dept_type", "org_uei", "org_duns", "org_ipf_code",
         "organization_type", "cong_dist", "org_latitude", "org_longitude",
         "contact_pi_name", "pi_names", "pi_profile_ids",
         "program_officer_names", "award_amount", "direct_cost_amt",
         "indirect_cost_amt", "award_notice_date", "project_start_date",
         "project_end_date", "budget_start", "budget_end", "is_active",
         "is_new", "arra_funded", "covid_response",
         "spending_categories_desc", "date_added", "project_detail_url",
         *_META),
    ),
    "nih_publications": TableDef(
        "nih_publications", "pub_key",
        ("pub_key", "pmid", "appl_id", "core_project_num", *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = ("nih_projects", "nih_publications")


class NihReporterStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the NIH RePORTER SQLite file directly,
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
        # Helpful secondary indexes for the /v1/query + lookup paths:
        # grants are looked up by project number, grantee orgs by name,
        # and the common slices are fiscal year + state.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_np_core_project_num "
                    "ON nih_projects(core_project_num)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_np_project_num "
                    "ON nih_projects(project_num)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_np_org_name "
                    "ON nih_projects(org_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_np_fiscal_year "
                    "ON nih_projects(fiscal_year)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_np_org_state "
                    "ON nih_projects(org_state)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_npub_pmid "
                    "ON nih_publications(pmid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_npub_core_project_num "
                    "ON nih_publications(core_project_num)")
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
