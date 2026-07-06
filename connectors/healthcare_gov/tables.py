"""Canonical data.healthcare.gov tables + an idempotent SQLite store.

Seven normalization targets:

  healthcare_gov_catalog              — every dataset in the DKAN catalog,
                                        keyed by its ``identifier``.
  healthcare_gov_plan_attributes      — Plan Attributes PUF (one row per
                                        plan-variant id), keyed
                                        ``{endpoint}:{businessyear}:{planid}``.
  healthcare_gov_benefits_cost_sharing— Benefits and Cost Sharing PUF,
                                        keyed ``{endpoint}:{businessyear}:
                                        {planid}:{benefitname}``.
  healthcare_gov_rates                — Rate PUF (one premium cell per plan
                                        × rating area × tobacco × age ×
                                        effective date).
  healthcare_gov_plan_quality         — Quality PUF star ratings, keyed
                                        ``{endpoint}:{planid}``.
  healthcare_gov_service_areas        — Service Area PUF (service area ×
                                        county coverage rows).
  healthcare_gov_rows                 — generic on-demand rows for ANY
                                        catalog dataset, keyed
                                        ``{dataset_key}:{row_idx}``.

Every PUF column tuple below is a snapshot of the REAL field names a
live datastore sample returned during the build (DKAN lower-cases the
PUF CSV headers; the catalog's camelCase DCAT keys are snake_cased by
:func:`connectors.healthcare_gov.normalize._snake`). Values stay TEXT —
SQLite is dynamically typed and one type model keeps the uniform
``/v1/query`` layer simple; numeric comparisons there cast explicitly.

Storage is SQLite to match the rest of the estate (no pandas/duckdb).
Every write is an **upsert keyed by the composed natural id** so a
re-run never double-counts — idempotency is enforced at the table, not
the caller. All SQL is parameterised; the column lists below are the
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

# Catalog columns: DCAT fields present across the live 337-item catalog,
# snake_cased; nested contact/publisher/distribution fields flattened.
_CATALOG_COLUMNS = (
    "identifier", "title", "description", "access_level",
    "accrual_periodicity", "issued", "modified", "license",
    "theme", "keyword", "publisher_name", "contact_fn", "contact_email",
    "bureau_code", "program_code", "distribution_count", "download_url",
    "media_type", "format", "described_by", "landing_page",
)

# Plan Attributes PUF — 151 fields, live snapshot (PY2026).
_PLAN_ATTRIBUTES_COLUMNS = (
    "businessyear", "statecode", "issuerid", "issuermarketplacemarketingname",
    "sourcename", "importdate", "marketcoverage", "dentalonlyplan",
    "standardcomponentid", "planmarketingname", "hiosproductid", "networkid",
    "serviceareaid", "formularyid", "isnewplan", "plantype", "metallevel",
    "designtype", "uniqueplandesign", "qhpnonqhptypeid",
    "isnoticerequiredforpregnancy", "isreferralrequiredforspecialist",
    "specialistrequiringreferral", "planlevelexclusions",
    "indianplanvariationestimatedadvancedpaymentamountperenrollee",
    "compositeratingoffered", "childonlyoffering", "childonlyplanid",
    "wellnessprogramoffered", "diseasemanagementprogramsoffered",
    "ehbpercenttotalpremium", "ehbpediatricdentalapportionmentquantity",
    "isguaranteedrate", "planeffectivedate", "planexpirationdate",
    "outofcountrycoverage", "outofcountrycoveragedescription",
    "outofserviceareacoverage", "outofserviceareacoveragedescription",
    "nationalnetwork", "urlforenrollmentpayment", "formularyurl", "planid",
    "planvariantmarketingname", "csrvariationtype", "issueractuarialvalue",
    "avcalculatoroutputnumber", "medicaldrugdeductiblesintegrated",
    "medicaldrugmaximumoutofpocketintegrated", "multipleinnetworktiers",
    "firsttierutilization", "secondtierutilization",
    "sbchavingababydeductible", "sbchavingababycopayment",
    "sbchavingababycoinsurance", "sbchavingababylimit",
    "sbchavingdiabetesdeductible", "sbchavingdiabetescopayment",
    "sbchavingdiabetescoinsurance", "sbchavingdiabeteslimit",
    "sbchavingsimplefracturedeductible", "sbchavingsimplefracturecopayment",
    "sbchavingsimplefracturecoinsurance", "sbchavingsimplefracturelimit",
    "specialtydrugmaximumcoinsurance", "inpatientcopaymentmaximumdays",
    "beginprimarycarecostsharingafternumberofvisits",
    "beginprimarycaredeductiblecoinsuranceafternumberofcopays",
    "mehbinntier1individualmoop", "mehbinntier1familyperpersonmoop",
    "mehbinntier1familypergroupmoop", "mehbinntier2individualmoop",
    "mehbinntier2familyperpersonmoop", "mehbinntier2familypergroupmoop",
    "mehboutofnetindividualmoop", "mehboutofnetfamilyperpersonmoop",
    "mehboutofnetfamilypergroupmoop", "mehbcombinnoonindividualmoop",
    "mehbcombinnoonfamilyperpersonmoop", "mehbcombinnoonfamilypergroupmoop",
    "dehbinntier1individualmoop", "dehbinntier1familyperpersonmoop",
    "dehbinntier1familypergroupmoop", "dehbinntier2individualmoop",
    "dehbinntier2familyperpersonmoop", "dehbinntier2familypergroupmoop",
    "dehboutofnetindividualmoop", "dehboutofnetfamilyperpersonmoop",
    "dehboutofnetfamilypergroupmoop", "dehbcombinnoonindividualmoop",
    "dehbcombinnoonfamilyperpersonmoop", "dehbcombinnoonfamilypergroupmoop",
    "tehbinntier1individualmoop", "tehbinntier1familyperpersonmoop",
    "tehbinntier1familypergroupmoop", "tehbinntier2individualmoop",
    "tehbinntier2familyperpersonmoop", "tehbinntier2familypergroupmoop",
    "tehboutofnetindividualmoop", "tehboutofnetfamilyperpersonmoop",
    "tehboutofnetfamilypergroupmoop", "tehbcombinnoonindividualmoop",
    "tehbcombinnoonfamilyperpersonmoop", "tehbcombinnoonfamilypergroupmoop",
    "mehbdedinntier1individual", "mehbdedinntier1familyperperson",
    "mehbdedinntier1familypergroup", "mehbdedinntier1coinsurance",
    "mehbdedinntier2individual", "mehbdedinntier2familyperperson",
    "mehbdedinntier2familypergroup", "mehbdedinntier2coinsurance",
    "mehbdedoutofnetindividual", "mehbdedoutofnetfamilyperperson",
    "mehbdedoutofnetfamilypergroup", "mehbdedcombinnoonindividual",
    "mehbdedcombinnoonfamilyperperson", "mehbdedcombinnoonfamilypergroup",
    "dehbdedinntier1individual", "dehbdedinntier1familyperperson",
    "dehbdedinntier1familypergroup", "dehbdedinntier1coinsurance",
    "dehbdedinntier2individual", "dehbdedinntier2familyperperson",
    "dehbdedinntier2familypergroup", "dehbdedinntier2coinsurance",
    "dehbdedoutofnetindividual", "dehbdedoutofnetfamilyperperson",
    "dehbdedoutofnetfamilypergroup", "dehbdedcombinnoonindividual",
    "dehbdedcombinnoonfamilyperperson", "dehbdedcombinnoonfamilypergroup",
    "tehbdedinntier1individual", "tehbdedinntier1familyperperson",
    "tehbdedinntier1familypergroup", "tehbdedinntier1coinsurance",
    "tehbdedinntier2individual", "tehbdedinntier2familyperperson",
    "tehbdedinntier2familypergroup", "tehbdedinntier2coinsurance",
    "tehbdedoutofnetindividual", "tehbdedoutofnetfamilyperperson",
    "tehbdedoutofnetfamilypergroup", "tehbdedcombinnoonindividual",
    "tehbdedcombinnoonfamilyperperson", "tehbdedcombinnoonfamilypergroup",
    "ishsaeligible", "hsaorhraemployercontribution",
    "hsaorhraemployercontributionamount", "urlforsummaryofbenefitscoverage",
    "planbrochure",
)

# Benefits and Cost Sharing PUF — 24 fields, live snapshot (PY2026).
_BENEFITS_COLUMNS = (
    "businessyear", "statecode", "issuerid", "sourcename", "importdate",
    "standardcomponentid", "planid", "benefitname", "copayinntier1",
    "copayinntier2", "copayoutofnet", "coinsinntier1", "coinsinntier2",
    "coinsoutofnet", "isehb", "iscovered", "quantlimitonsvc", "limitqty",
    "limitunit", "exclusions", "explanation", "ehbvarreason",
    "isexclfrominnmoop", "isexclfromoonmoop",
)

# Rate PUF — 20 fields, live snapshot (PY2026).
_RATES_COLUMNS = (
    "businessyear", "statecode", "issuerid", "sourcename", "importdate",
    "rateeffectivedate", "rateexpirationdate", "planid", "ratingareaid",
    "tobacco", "age", "individualrate", "individualtobaccorate", "couple",
    "primarysubscriberandonedependent", "primarysubscriberandtwodependents",
    "primarysubscriberandthreeormoredependents", "coupleandonedependent",
    "coupleandtwodependents", "coupleandthreeormoredependents",
)

# Quality PUF — 9 fields, live snapshot (PY2026).
_QUALITY_COLUMNS = (
    "issuerid", "state", "plan_type", "reportingunitid", "planid",
    "overallratingvalue", "medicalcareratingvalue",
    "memberexperienceratingvalue", "planadministrationratingvalue",
)

# Service Area PUF — 14 fields, live snapshot (PY2026).
_SERVICE_AREA_COLUMNS = (
    "businessyear", "statecode", "issuerid", "sourcename", "importdate",
    "serviceareaid", "serviceareaname", "coverentirestate", "county",
    "partialcounty", "zipcodes", "partialcountyjustification",
    "marketcoverage", "dentalonlyplan",
)

TABLES: Dict[str, TableDef] = {
    "healthcare_gov_catalog": TableDef(
        "healthcare_gov_catalog", "identifier",
        (*_CATALOG_COLUMNS, *_META),
    ),
    "healthcare_gov_plan_attributes": TableDef(
        "healthcare_gov_plan_attributes", "plan_key",
        ("plan_key", *_PLAN_ATTRIBUTES_COLUMNS, *_META),
    ),
    "healthcare_gov_benefits_cost_sharing": TableDef(
        "healthcare_gov_benefits_cost_sharing", "benefit_key",
        ("benefit_key", *_BENEFITS_COLUMNS, *_META),
    ),
    "healthcare_gov_rates": TableDef(
        "healthcare_gov_rates", "rate_key",
        ("rate_key", *_RATES_COLUMNS, *_META),
    ),
    "healthcare_gov_plan_quality": TableDef(
        "healthcare_gov_plan_quality", "quality_key",
        ("quality_key", *_QUALITY_COLUMNS, *_META),
    ),
    "healthcare_gov_service_areas": TableDef(
        "healthcare_gov_service_areas", "service_area_key",
        ("service_area_key", *_SERVICE_AREA_COLUMNS, *_META),
    ),
    # Generic rows: row_idx stays TEXT like every other column (single
    # type model); it holds the datastore ``record_number`` when DKAN
    # provides one, else the absolute fetch offset.
    "healthcare_gov_rows": TableDef(
        "healthcare_gov_rows", "row_key",
        ("row_key", "dataset_key", "row_idx", "row_json", "fetched_at",
         *_META),
    ),
}

CANONICAL_TABLES: Tuple[str, ...] = tuple(TABLES)


class HealthcareGovStore:
    """Thin SQLite wrapper: schema bootstrap + idempotent batch upsert.

    The only module that talks to the healthcare.gov SQLite file
    directly, mirroring the estate convention that a single store owns
    the connection.
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
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgc_title "
                    "ON healthcare_gov_catalog(title)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgc_modified "
                    "ON healthcare_gov_catalog(modified)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgpa_std_component "
                    "ON healthcare_gov_plan_attributes(standardcomponentid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgpa_state "
                    "ON healthcare_gov_plan_attributes(statecode)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgpa_service_area "
                    "ON healthcare_gov_plan_attributes(serviceareaid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgb_planid "
                    "ON healthcare_gov_benefits_cost_sharing(planid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgb_benefit "
                    "ON healthcare_gov_benefits_cost_sharing(benefitname)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgr_planid "
                    "ON healthcare_gov_rates(planid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgr_state "
                    "ON healthcare_gov_rates(statecode)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgq_planid "
                    "ON healthcare_gov_plan_quality(planid)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgsa_county "
                    "ON healthcare_gov_service_areas(county)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgsa_state "
                    "ON healthcare_gov_service_areas(statecode)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_hgrows_dataset "
                    "ON healthcare_gov_rows(dataset_key)")
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
