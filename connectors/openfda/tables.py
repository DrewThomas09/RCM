"""Canonical openFDA tables + an idempotent SQLite store.

The eight normalization targets from the source spec, plus three
crosswalk/rollup helpers this workstream owns:

  dim_drug_product, fact_drug_adverse_event, fact_drug_recall,
  dim_drug_approval, dim_device, fact_device_adverse_event,
  fact_device_recall, dim_device_udi,
  + xwalk_ndc_rxcui  (NDC → RxCUI, wireable to the RxNorm source)
  + xwalk_device_product_code  (the device dimension we APPEND to the
    crosswalk contract — we never rewrite NPI/FIPS/CPT/NDC)
  + dim_company  (normalized manufacturer/sponsor rollup)

Storage is SQLite to match the rest of RCM-MC (no pandas/duckdb in the
runtime). Every write is an **upsert keyed by the native id** so a
re-run or an overlapping date window never double-counts — idempotency
is enforced at the table, not the caller. All SQL is parameterised; the
column lists below are the only interpolated identifiers and they are
module constants, never user input.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence, Tuple


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
            elif c.endswith("_at") or c in ("ingested_at",):
                cols.append(f"{c} TEXT")
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
_META = ("source_endpoint", "company_key", "ingested_at")

TABLES: Dict[str, TableDef] = {
    "dim_drug_product": TableDef(
        "dim_drug_product", "ndc",
        ("ndc", "product_ndc", "rxcui", "proprietary_name", "generic_name",
         "labeler_name", "dosage_form", "route", "marketing_status",
         "product_type", "application_number", "set_id", *_META),
    ),
    "fact_drug_adverse_event": TableDef(
        "fact_drug_adverse_event", "safetyreportid",
        ("safetyreportid", "receivedate", "serious", "ndc", "medicinalproduct",
         "generic_name", "reaction_pt", "patient_sex", "patient_age",
         "occurcountry", *_META),
    ),
    "fact_drug_recall": TableDef(
        "fact_drug_recall", "recall_number",
        ("recall_number", "report_date", "ndc", "product_description",
         "reason_for_recall", "classification", "status", "recalling_firm",
         "voluntary_mandated", "state", *_META),
    ),
    "dim_drug_approval": TableDef(
        "dim_drug_approval", "application_number",
        ("application_number", "sponsor_name", "application_type",
         "brand_name", "generic_name", "marketing_status", "ndc",
         "dosage_form", "route", "products_json", "submission_status_date",
         *_META),
    ),
    "dim_device": TableDef(
        "dim_device", "device_key",
        ("device_key", "product_code", "device_name", "device_class",
         "regulation_number", "medical_specialty", "applicant",
         "decision_date", "decision_type", "k_number", "pma_number",
         "advisory_committee", *_META),
    ),
    "fact_device_adverse_event": TableDef(
        "fact_device_adverse_event", "report_number",
        ("report_number", "date_received", "product_code", "brand_name",
         "generic_name", "manufacturer_name", "device_class", "event_type",
         "mdr_report_key", *_META),
    ),
    "fact_device_recall": TableDef(
        "fact_device_recall", "recall_id",
        ("recall_id", "recall_number", "report_date", "product_code",
         "product_description", "reason_for_recall", "classification",
         "status", "recalling_firm", "root_cause_description", *_META),
    ),
    "dim_device_udi": TableDef(
        "dim_device_udi", "public_device_record_key",
        ("public_device_record_key", "product_code", "brand_name",
         "company_name", "version_or_model_number", "device_description",
         "gmdn_terms", "publish_date", "udi_di", *_META),
    ),
    # ── Crosswalk / rollup helpers we OWN (append-only to the contract) ─
    "xwalk_ndc_rxcui": TableDef(
        "xwalk_ndc_rxcui", "ndc",
        ("ndc", "rxcui", "resolution_status", "resolved_at", "source"),
    ),
    "xwalk_device_product_code": TableDef(
        "xwalk_device_product_code", "product_code",
        ("product_code", "device_name", "device_class", "regulation_number",
         "medical_specialty", "first_decision_date", "clearance_count",
         "ingested_at"),
    ),
    "dim_company": TableDef(
        "dim_company", "company_key",
        ("company_key", "normalized_name", "raw_names_json", "kind",
         "ingested_at"),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = (
    "dim_drug_product", "fact_drug_adverse_event", "fact_drug_recall",
    "dim_drug_approval", "dim_device", "fact_device_adverse_event",
    "fact_device_recall", "dim_device_udi",
)


class OpenFdaStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the openFDA SQLite file directly, mirroring
    the RCM-MC convention that a single store owns the connection.
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
        # Helpful secondary indexes for the /v1/query filter paths.
        cur.execute("CREATE INDEX IF NOT EXISTS ix_ddp_rxcui "
                    "ON dim_drug_product(rxcui)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_dev_pcode "
                    "ON dim_device(product_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_fdae_ndc "
                    "ON fact_drug_adverse_event(ndc)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_fder_pcode "
                    "ON fact_device_recall(product_code)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_fdae_pcode "
                    "ON fact_device_adverse_event(product_code)")
        self.conn.commit()

    def upsert(self, table: str, rows: Sequence[Dict[str, Any]]) -> int:
        """Upsert canonical rows keyed by the table's native PK.

        Rows are dicts of column→value; missing columns default to NULL,
        extra keys are ignored (the normalizer already mapped them).
        Returns the number of rows written.
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
    """SQLite stores TEXT; coerce lists/dicts to JSON-ish and scalars to str.

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
