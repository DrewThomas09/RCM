# RCM connectors — public healthcare API estate

A set of self-contained, **stdlib-only** connectors that ingest public
healthcare APIs into canonical SQLite tables and re-expose them behind one
uniform `/v1` query surface. Adding a data source is a new connector package
here; nothing else in RCM-MC has to change.

Every connector is an independent vertical slice built to the **same
contract** (modelled on `openfda/`):

```
endpoints ─▶ transport ─▶ connector.discover()/fetch() ─▶ raw pages
                                                              │
                                                        normalize ─▶ canonical SQLite tables
                                                              │              │
                                                          registry ─▶ /v1/query/{dataset} + /aggregate
                                                                        /v1/lookup/…
```

## Connectors

| Connector | Package | API | Base URL | Datasets |
|-----------|---------|-----|----------|----------|
| openFDA | `connectors/openfda` | FDA drug + device (NDC, labels, FAERS, recalls, 510(k), PMA, MAUDE, UDI, …) | `api.fda.gov` | 12 |
| CMS Coverage | `connectors/cms_coverage` | Medicare Coverage Database — NCD/NCA/CAL/MEDCAC/TA, LCD/Proposed-LCD/Article, MAC contractors | `api.coverage.cms.gov` | 9 |
| NPI Registry | `connectors/npi_registry` | NPPES v2.1 — provider search/lookup, taxonomies, addresses, NPI validation | `npiregistry.cms.hhs.gov/api` | 3 |
| ICD-10 | `connectors/icd10` | ICD-10-CM diagnoses + ICD-10-PCS procedures (NLM Clinical Tables) | `clinicaltables.nlm.nih.gov/api` | 2 |
| CMS Open Data | `connectors/cms_open_data` | data.cms.gov data-api — full DCAT catalog (158 datasets) + 53 curated: Medicare utilization & payment (physician/Part D/inpatient/outpatient/DMEPOS), drug spending, geographic variation, market saturation, enrollment, HCRIS cost reports, PECOS ownership, PBJ staffing, telehealth, post-acute, ACOs, Provider-of-Services facility universe (QIES + iQIES + clinical labs), dialysis facilities, ESRD models, home infusion, PSPS, RBCS crosswalk | `data.cms.gov` | 55 |
| Provider Data Catalog | `connectors/provider_data` | Care Compare DKAN — full catalog (234 datasets) + hospital stars/HCAHPS/outcomes, nursing-home 5-star/penalties/MDS, SNF QRP, home health, hospice, dialysis (facility/state/national + ICH-CAHPS + ESRD QIP), ASC quality + OAS CAHPS, imaging efficiency, medical equipment suppliers, Doctors & Clinicians national file | `data.cms.gov/provider-data` | 36 |
| Open Payments | `connectors/open_payments` | Sunshine Act DKAN — full catalog (74 datasets) + PY2024 general/research/ownership payments, profiles, summaries, state totals | `openpaymentsdata.cms.gov` | 11 |
| Medicaid Open Data | `connectors/medicaid_data` | data.medicaid.gov DKAN — full catalog (541 datasets) + NADAC, State Drug Utilization, rebate products, enrollment, managed care, FULs, CMS-64, quality measures | `data.medicaid.gov` | 15 |
| Healthcare.gov | `connectors/healthcare_gov` | Marketplace DKAN — full catalog (337 datasets) + PY2026 QHP PUFs (plan attributes, benefits & cost sharing, rates, quality, service areas) | `data.healthcare.gov` | 7 |
| CDC Open Data | `connectors/cdc_data` | data.cdc.gov Socrata/SODA — full catalog (~1,500 datasets) + PLACES county health (incl. pinned 2023 CKD prevalence), mortality (provisional/weekly/monthly/leading causes), drug overdose, BRFSS, chronic disease, life expectancy | `data.cdc.gov` | 14 |
| HRSA | `connectors/hrsa_data` | HRSA data downloads — HPSA shortage areas (primary care/dental/mental health), MUA/P, health-center sites | `data.hrsa.gov` | 5 |
| NIH RePORTER | `connectors/nih_reporter` | NIH RePORTER v2 (POST JSON) — funded projects + linked publications | `api.reporter.nih.gov` | 2 |
| Census ACS | `connectors/census_acs` | ACS 5-year — county/state/CBSA demographic profiles (population, 65+, income, poverty, uninsured); requires free `CENSUS_API_KEY` | `api.census.gov/data` | 3 |
| OIG LEIE | `connectors/oig_leie` | HHS OIG exclusion list — full database + monthly supplements + reinstatements, NPI-joinable compliance screening | `oig.hhs.gov` | 3 |
| BLS QCEW | `connectors/bls_qcew` | Quarterly Census of Employment & Wages — healthcare employment, wages, location quotients by county/MSA x NAICS | `data.bls.gov/cew` | 2 |

**179 registered datasets across 15 connectors** — plus five full open-data
catalogs synced as first-class tables (data.cms.gov 158, Provider Data
Catalog 234, Open Payments 74, data.medicaid.gov 541, Healthcare.gov 337,
data.cdc.gov ~1,500), each with a generic fetched-rows slot so **any**
catalog dataset can be pulled on demand and queried through the same
uniform surface. See the live list with `python -m connectors.cli datasets`.

## The uniform contract

Because every connector exposes the same shapes, one thin adapter
(`connectors/_spi.py`) drives all of them and the estate-level modules treat
them as a single database:

- `connectors.<name>.registry` — a `RegistryRow` dataclass with **identical
  field names** (`dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table, source, source_filter,
  date_field`) plus `registry_rows()` / `registry_as_dicts()` /
  `by_dataset_id()` / `dataset_ids()`.
- `connectors.<name>.tables` — one `*Store` SQLite wrapper with idempotent,
  native-id-keyed upsert.
- `connectors.<name>.query` — `query()` / `aggregate()` / `QueryError` with
  the same `field__op` grammar and `as_dict` result shapes.
- `connectors.<name>.lookup` — `v1_handlers(store) -> {route_template: fn}`.
- `connectors.<name>.api_server` / `cli` — a standalone `/v1` server and CLI.

## Estate-level surface

| File | Role |
|------|------|
| `_spi.py` | Uniform `Adapter` over each connector + the generic lookup-route binder. |
| `registry.py` | The **one database of every API dataset**: `all_registry_rows()`, `all_dataset_ids()`, `dataset_owner()`, `connectors_summary()`, `catalog()`. |
| `api_server.py` | One stdlib `/v1` server mounting every connector (query dispatched to the owner; lookups delegated). |
| `cli.py` | `python -m connectors.cli connectors｜datasets｜catalog｜serve`. |

### Unified `/v1` routes

```
/health
/v1/connectors                       one row per connector (label, base URLs, datasets)
/v1/datasets                         every dataset (merged registries)
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/{noun}/{id}               drug｜device｜company｜document｜contractor｜provider｜taxonomy｜code｜category
                                     ｜practice｜prescriber｜facility-cost｜ownership｜cms-dataset
                                     ｜hospital｜nursing-home｜home-health｜hospice｜dialysis｜clinician｜pdc-dataset
                                     ｜physician-payments｜manufacturer｜op-dataset
                                     ｜ndc-cost｜state-drug｜medicaid-dataset｜marketplace-plan｜county-plans
                                     ｜county-health｜cdc-dataset｜shortage-area｜health-center
                                     ｜grant｜grantee-org｜county-demographics｜state-demographics
/v1/validate/npi/{npi}
/v1/search/{code_type}?q=&limit=      (ICD-10)
```

The uniform filter grammar (every dataset): `{"field": v}` equality, or
`field__op` — `eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`; sort with
`field` / `-field`.

## Usage

```bash
# See the whole estate
python -m connectors.cli connectors
python -m connectors.cli datasets --connector cms_coverage
python -m connectors.cli catalog            # full JSON catalog

# Serve everything behind one endpoint (in-memory demo, or a dir of DBs)
python -m connectors.cli serve --db :memory:
python -m connectors.cli serve --db ./var/connectors

# Ingest with a connector's own CLI, then query via the unified surface
python -m connectors.cms_coverage.cli discover
```

```python
from connectors import registry as estate
estate.catalog()["n_datasets"]          # 26
estate.dataset_owner("icd10_cm")         # 'icd10'

from connectors.api_server import open_stores, make_server
stores = open_stores(":memory:")
server, port = make_server(stores)       # one /v1 surface over all connectors
```

## Design notes

- **Stdlib only** — `urllib` + `json` + `sqlite3` + `http.server`. No
  pandas/requests/pyarrow/duckdb; no new runtime dependencies.
- **Injectable transport opener** — every retry / backoff / parse path is unit
  tested against an in-memory fake; tests never touch the network.
- **Self-contained connectors** — a connector never imports another; only
  `_spi.py` reaches across them, so each stays independently testable and any
  connector can be dropped in or out without touching the others.
- **Rate floors / endpoint paths** documented per connector are conservative
  best-known mappings — verify live limits before a bulk run (each connector's
  `transport.py` / `README` carries the disclaimer).

## Tests

```bash
# Whole estate (per-connector suites + the unified surface) — 731 tests
python -m unittest discover -s connectors -t . -p "test_*.py"
```
