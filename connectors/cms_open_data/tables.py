"""Canonical CMS Open Data tables + an idempotent SQLite store.

Three normalization targets, all derived from the declarative specs in
:mod:`connectors.cms_open_data.endpoints` (which snapshot the LIVE API
column names, snake_cased):

  cms_open_data_catalog — one row per dataset data.cms.gov publishes,
                          keyed by the title slug (``dataset_key``).
  cms_open_data_<key>   — one table per curated flagship dataset, keyed
                          by the composed natural key (``row_key``).
  cms_open_data_rows    — the generic on-demand store for any other
                          catalog dataset, keyed ``{dataset_key}:{row_idx}``.

Deriving ``TABLES`` from the endpoint specs (instead of hand-writing 55
literals) keeps endpoints.py the single generated source of truth for
the live schema snapshot; the resulting dict has exactly the same shape
as ``cms_coverage.tables.TABLES``.

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

from .endpoints import ENDPOINTS, GENERIC_TABLE


@dataclass(frozen=True)
class TableDef:
    name: str
    pk: str
    columns: Tuple[str, ...]   # all columns incl. pk, in order
    # Columns that should carry INTEGER affinity (row_idx in the generic
    # store, so paging windows sort/compare numerically). Values still
    # pass through _coerce as strings — SQLite's affinity converts them
    # on insert, keeping the store contract identical to the estate's.
    int_cols: Tuple[str, ...] = ()

    def create_sql(self) -> str:
        cols = []
        for c in self.columns:
            if c == self.pk:
                cols.append(f"{c} TEXT PRIMARY KEY")
            elif c in self.int_cols:
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


# ── Canonical schema (derived from the generated endpoint specs) ──────
_META = ("source_endpoint", "ingested_at")


def _build_tables() -> Dict[str, TableDef]:
    out: Dict[str, TableDef] = {}
    for spec in ENDPOINTS.values():
        if spec.target_table in out:      # defensive; tables are 1:1 today
            continue
        out[spec.target_table] = TableDef(
            name=spec.target_table,
            pk=spec.pk,
            columns=(spec.pk, *spec.columns, *_META),
            int_cols=("row_idx",) if spec.target_table == GENERIC_TABLE else (),
        )
    return out


TABLES: Dict[str, TableDef] = _build_tables()

CANONICAL_TABLES: Tuple[str, ...] = tuple(TABLES)

# Secondary indexes for the /v1/query + lookup fan-out paths. Only ever
# built from these module constants — never from caller input.
_INDEXES: Tuple[Tuple[str, str, str], ...] = (
    ("ix_cod_catalog_uuid", "cms_open_data_catalog", "uuid"),
    ("ix_cod_catalog_title", "cms_open_data_catalog", "title"),
    ("ix_cod_rows_dataset", "cms_open_data_rows", "dataset_key"),
    ("ix_cod_phys_npi", "cms_open_data_mup_physician_by_provider", "rndrng_npi"),
    ("ix_cod_prscrbr_npi", "cms_open_data_mup_partd_prescriber_by_provider", "prscrbr_npi"),
    ("ix_cod_prscrbr_drug_npi", "cms_open_data_mup_partd_prescriber_by_provider_drug", "prscrbr_npi"),
    ("ix_cod_hosp_cost_ccn", "cms_open_data_hospital_cost_report", "provider_ccn"),
    ("ix_cod_snf_cost_ccn", "cms_open_data_snf_cost_report", "provider_ccn"),
    ("ix_cod_hha_cost_ccn", "cms_open_data_hha_cost_report", "provider_ccn"),
    ("ix_cod_hosp_own_enrl", "cms_open_data_hospital_all_owners", "enrollment_id"),
    ("ix_cod_snf_own_enrl", "cms_open_data_snf_all_owners", "enrollment_id"),
    ("ix_cod_hosp_enrl_ccn", "cms_open_data_hospital_enrollments", "ccn"),
    ("ix_cod_ffs_npi", "cms_open_data_ffs_provider_enrollment", "npi"),
    ("ix_cod_optout_npi", "cms_open_data_opt_out_affidavits", "npi"),
    ("ix_cod_ordref_npi", "cms_open_data_order_and_referring", "npi"),
    ("ix_cod_pos_qies_state", "cms_open_data_pos_qies", "state_cd"),
    ("ix_cod_pos_iqies_state", "cms_open_data_pos_internet_qies", "state_cd"),
    ("ix_cod_dialysis_ccn", "cms_open_data_dialysis_facilities", "ccn"),
    ("ix_cod_psps_hcpcs",
     "cms_open_data_physician_supplier_procedure_summary", "hcpcs_cd"),
    ("ix_cod_rbcs_hcpcs", "cms_open_data_rbcs", "hcpcs_cd"),
)


class CmsOpenDataStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the CMS Open Data SQLite file directly,
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
        for ix_name, table, column in _INDEXES:
            # Guard against drift between the index list and the generated
            # schema — an index on a vanished column should fail loudly at
            # build time, not silently at query time.
            assert column in TABLES[table].columns, (ix_name, table, column)
            cur.execute(f"CREATE INDEX IF NOT EXISTS {ix_name} ON {table}({column})")
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

    def replace_slice(self, table: str, dataset_key: str,
                      rows: Sequence[Dict[str, Any]], *,
                      slice_sig: str = "") -> int:
        """Atomically replace ONE dataset's slice of a shared generic table.

        A re-fetch that returns fewer rows than the previous pull would,
        under plain upserts, strand the earlier pull's trailing
        ``row_idx`` rows — served intermixed with fresh rows and counted
        by every surface, with nothing flagging the mixed vintages. One
        transaction deletes exactly the slice being re-pulled and writes
        the fresh rows (mirroring ``oig_leie``'s replace-in-transaction
        semantics), so a reader never observes a half-replaced slice.

        Slice targeting matches the normalizer's key grammar: unfiltered
        pulls key ``{dataset_key}:{row_idx}`` (one colon segment) and
        filtered pulls ``{dataset_key}:{slice_sig}:{row_idx}`` — dataset
        keys are slugs/UUIDs (never contain ``:``) and signatures are
        fixed-length hex, so the LIKE shapes below classify exactly.
        Only meaningful for the generic ``*_rows`` table.
        """
        tdef = TABLES[table]
        for needed in ("row_key", "dataset_key", "row_idx"):
            if needed not in tdef.columns:
                raise ValueError(
                    f"replace_slice targets generic row tables; {table!r} "
                    f"has no {needed!r} column")
        sql = tdef.upsert_sql()
        now = _utc_now()
        params: List[Tuple[Any, ...]] = []
        for r in rows:
            r = dict(r)
            r.setdefault("ingested_at", now)
            params.append(tuple(_coerce(r.get(c)) for c in tdef.columns))
        with self.conn:  # implicit BEGIN/COMMIT, atomic
            if slice_sig:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':' || ? || ':%'",
                    (dataset_key, dataset_key, slice_sig))
            else:
                self.conn.execute(
                    f"DELETE FROM {tdef.name} WHERE dataset_key = ? "
                    f"AND row_key LIKE ? || ':%' "
                    f"AND row_key NOT LIKE ? || ':%:%'",
                    (dataset_key, dataset_key, dataset_key))
            if params:
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
    cast explicitly. (Columns declared with INTEGER affinity convert the
    string on insert; see :class:`TableDef`.)
    """
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        import json
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)
